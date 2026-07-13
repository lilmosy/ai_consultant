"""Orchestrator — wires the 8 agents to the DART/News source layer with a verification loop.

User Request -> Issue Planner -> Source Scout -> (DART 정형+비정형 / News 확보)
             -> Evidence Extractor -> Claim Normalizer -> Verifier
             -> Gap Finder -> Synthesis -> Critic -> Final Fact Pack
"""
from __future__ import annotations
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import config, financials as fin
from .artifacts import RunArtifacts
from .schemas import SourceDoc, Claim, to_jsonable
from .sources.dart import DartClient, find_passages
from .sources.naver_news import NaverNewsClient, collect_news
from .agents import (issue_planner, source_scout, evidence_extractor,
                     claim_normalizer, verifier, reconciler, gap_finder, synthesis, critic)
from . import report


@dataclass
class RunConfig:
    company: str
    topic: str
    bgn: str = "20240101"
    end: str = "20261231"          # 2026년 최신 정기보고서까지 포함
    fin_year: str = "2025"          # (fallback) 실제로는 최신 연간보고서에서 자동 도출
    dart_reports: int = 2           # 최신 정기보고서 몇 개(시점)를 쓸지
    today: str = ""                 # 정합 기준 '오늘'(빈 값이면 실행시각으로 채움)
    max_news: int = config.MAX_NEWS_ITEMS
    dart_passage_per_kw: int = 1
    max_extract_workers: int = 6
    max_verify_workers: int = 6


def _run_id(company: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"\s+", "", company)
    return f"{slug}_{ts}"


def run(cfg: RunConfig, out_base: str = "outputs", run_id: str | None = None) -> dict:
    if not cfg.today:
        cfg.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    art = RunArtifacts(out_base, run_id or _run_id(cfg.company))
    art.log(f"RUN start · {cfg.company} · {cfg.topic}")
    art.write_json("00_request.json", {"company": cfg.company, "topic": cfg.topic,
                                        "period": [cfg.bgn, cfg.end], "fin_year": cfg.fin_year})

    # ---------- 1) Issue Planner ----------
    issues = issue_planner.run(cfg.company, cfg.topic)
    art.write_json("01_issue_tree.json", issues)
    art.stage("Issue Planner", f"{len(issues)}개 이슈 트리 + 가설 생성",
              "MECE는 프롬프트 유도일 뿐 보장되지 않음; 이슈 수는 5~7로 유도")

    # ---------- 2) Source Scout ----------
    scout = source_scout.run(cfg.company, issues)
    art.write_json("02_source_plan.json", scout)
    art.stage("Source Scout",
              f"DART 앵커 {len(scout['dart_keywords'])}개 · 뉴스쿼리 {len(scout['news_queries'])}개",
              "도메인 앵커팩을 강제 병합해 리콜 보강; LLM 단독 키워드는 원문 표를 놓칠 수 있음")

    # ---------- 3) Source acquisition ----------
    dart = DartClient(cache_dir=f"{out_base}/_cache")  # shared cache: cheap re-runs
    corp = dart.resolve_corp(cfg.company)
    sources: list[SourceDoc] = []
    fin_md, fin_struct = "(정형 재무 없음)", []
    dart_limit = ""
    if corp:
        # 최신 정기보고서 k개(서로 다른 시점) → 시점 흐름을 위한 다중 타임포인트
        reports = dart.latest_periodic_reports(corp, cfg.bgn, cfg.end, k=cfg.dart_reports)
        supplies = dart.supply_contracts(corp, cfg.bgn, cfg.end)
        art.write_json("03b_filings.json", {
            "reports": [to_jsonable(r) for r in reports],
            "supply_contracts": [to_jsonable(s) for s in supplies],
        })
        # 재무(정형): 연간 보고서 우선(YoY 비교 가능), 없으면 최신 보고서
        annual = next((r for r in reports if "사업보고서" in r.report_nm), reports[0] if reports else None)
        if annual:
            yr, rc = annual.fin_params
            acc = dart.key_accounts(corp, yr, rc)
            fin_md, fin_struct = fin.summarize(acc)
            art.write_json("03a_financials.json", {"corp_code": corp, "as_of": annual.as_of_iso,
                                                    "report": annual.report_nm, "rows": acc,
                                                    "structured": fin_struct})
        # 비정형 원문: 각 보고서에서 앵커 발췌 (source_date = 보고 기준일 = 데이터 시점)
        for rep in reports:
            doc = dart.document_text(rep.rcept_no)
            art.log(f"DART 원문: {rep.report_nm} as_of={rep.as_of_iso} ({len(doc):,}자)")
            passages = find_passages(doc, scout["dart_keywords"], max_per_kw=cfg.dart_passage_per_kw)
            for k, p in enumerate(passages):
                sources.append(SourceDoc(
                    source_id=f"DART_{rep.rcept_no}_{k}",
                    source_type="DART", source_name=f"{cfg.company} {rep.report_nm}",
                    source_date=rep.as_of_iso, url=rep.url, text=p["text"],
                    meta={"keyword": p["keyword"], "offset": p["offset"], "rcept_no": rep.rcept_no,
                          "period": rep.period, "as_of": rep.as_of_iso},
                ))
        # 단일판매·공급계약 이벤트 (공시 제목/날짜)
        if reports and supplies:
            sc_text = "단일판매·공급계약 공시 목록:\n" + "\n".join(
                f"- {s.rcept_dt[:4]}-{s.rcept_dt[4:6]}-{s.rcept_dt[6:8]} {s.report_nm}" for s in supplies[:20])
            sources.append(SourceDoc(
                source_id="DART_SUPPLY", source_type="DART",
                source_name=f"{cfg.company} 단일판매·공급계약 공시목록", source_date=reports[0].as_of_iso,
                url="https://dart.fss.or.kr", text=sc_text, meta={"count": len(supplies)}))
        if not reports:
            dart_limit = "기간 내 정기보고서 미발견"
    else:
        dart_limit = f"corp_code 미해결({cfg.company})"

    # News
    news_client = NaverNewsClient()
    topic_terms = ["수주", "수주잔고", "방산", "특수선", "MRO", "필리조선소", "미국",
                   "LNG", "실적", "영업이익", "매출", "잠수함"]
    news_items, news_diag = collect_news(cfg.company, topic_terms, scout["news_queries"],
                                          client=news_client, max_items=cfg.max_news)
    art.write_json("03c_news.json", {"diag": news_diag, "items": [to_jsonable(n) for n in news_items]})
    for k, n in enumerate(news_items):
        sources.append(SourceDoc(
            source_id=f"NEWS_{k}", source_type="News", source_name=f"네이버뉴스: {n.title[:40]}",
            source_date=n.pub_date, url=n.link or n.original_link, text=n.passage,
            meta={"query": n.query, "matched": n.matched_terms,
                  "body_source": n.body_source, "body_chars": len(n.body)}))

    n_dart = sum(1 for s in sources if s.source_type == "DART")
    n_news = sum(1 for s in sources if s.source_type == "News")
    art.write_json("03_sources.json", sources)
    bodies = news_diag.get("bodies_fetched", 0)
    news_limit = "" if news_diag.get("ready") else "네이버 뉴스 인증정보(CLIENT_SECRET) 없음 → 뉴스 소스 0건"
    if news_diag.get("ready") and n_news and bodies < n_news:
        news_limit = (news_limit + "; " if news_limit else "") + \
            f"뉴스 {n_news}건 중 {n_news - bodies}건은 외부매체라 원문파싱 불가→스니펫 사용"
    art.stage("Source Acquisition (DART 정형+비정형 / News)",
              f"소스 {len(sources)}건 (DART {n_dart} / News {n_news}, 원문파싱 {bodies}건), 정형 재무 {len(fin_struct)}계정",
              "; ".join(x for x in [dart_limit, news_limit] if x) or
              "DART 원문은 키워드 앵커 주변 발췌만 사용(전체 문서 아님)")

    # ---------- 4) Evidence Extractor (concurrent) ----------
    raw_claims: list[Claim] = []
    def _extract(src: SourceDoc):
        return evidence_extractor.run(cfg.company, src)
    with ThreadPoolExecutor(max_workers=cfg.max_extract_workers) as ex:
        futs = {ex.submit(_extract, s): s for s in sources}
        for f in as_completed(futs):
            s = futs[f]
            try:
                cs = f.result()
                raw_claims.extend(cs)
                art.log(f"  extract {s.source_id}: {len(cs)} claims")
            except Exception as e:
                art.log(f"  extract {s.source_id} FAILED: {e}")
    art.write_json("04_raw_claims.json", raw_claims)
    art.stage("Evidence Extractor", f"원시 claim {len(raw_claims)}건 추출 (source_span 필수)",
              "소스 발췌 밖 내용은 못 봄; 표 셀이 분해돼 숫자-라벨 매칭이 흔들릴 수 있음")

    # ---------- 5) Claim Normalizer ----------
    norm_claims = claim_normalizer.run(raw_claims)
    art.write_json("05_normalized_claims.json", norm_claims)
    art.stage("Claim Normalizer", f"정규화 후 {len(norm_claims)}건 (중복 {len(raw_claims)-len(norm_claims)} 병합)",
              "중복 판정은 텍스트 유사도 휴리스틱(같은 사실의 다른 표현은 남을 수 있음)")

    # ---------- 6) Verifier (concurrent) ----------
    src_by_id = {s.source_id: s for s in sources}
    def _verify(c: Claim):
        s = src_by_id.get(c.source_id)
        return verifier.run(c, s) if s else c
    verified: list[Claim] = []
    with ThreadPoolExecutor(max_workers=cfg.max_verify_workers) as ex:
        futs = {ex.submit(_verify, c): c for c in norm_claims}
        for f in as_completed(futs):
            try:
                verified.append(f.result())
            except Exception as e:
                c = futs[f]; c.verification = "weak"; c.verification_reason = f"검증 예외: {e}"
                verified.append(c)
    n_ver = sum(1 for c in verified if c.verification == "verified")
    n_weak = sum(1 for c in verified if c.verification == "weak")
    n_unsup = sum(1 for c in verified if c.verification == "unsupported")
    art.write_json("06_verified_claims.json", verified)
    art.stage("Verifier", f"verified {n_ver} · weak {n_weak} · unsupported {n_unsup}",
              "span 실재성은 결정적, 과장/비약 판정은 LLM 의존(경계사례 흔들림 가능)")

    # ---------- 7) Reconciler (교차소스 정합: 의미중복 병합 + 시점 타임라인 + 충돌) ----------
    recon = reconciler.run(cfg.company, verified, today=cfg.today)
    art.write_json("07_reconciliation.json", recon)
    art.stage("Reconciler", f"timeline {len(recon['timelines'])} · 충돌 {len(recon['conflicts'])} · "
              f"교차노트 {len(recon['cross_source_notes'])}",
              "의미적 그룹핑/충돌은 LLM 판단(임베딩 아님); 근거 시점(as_of)에 의존")

    # ---------- 8) Gap Finder ----------
    gaps = gap_finder.run(issues, verified)
    art.write_json("08_gaps.json", gaps)
    art.stage("Gap Finder", f"evidence gap {len(gaps)}건 + next check",
              "gap은 확보된 claim 기준 상대적 판단(모르는 미지의 미지는 못 잡음)")

    # ---------- 9) Synthesis ----------
    synth = synthesis.run(cfg.company, cfg.topic, issues, verified, gaps, fin_md, recon)
    art.write_json("09_synthesis.json", synth)
    art.stage("Synthesis", "fact pack 초안(8개 섹션, 시점·소스 정합 포함) 생성",
              "unsupported 제외 후 종합; verified가 적으면 outlook이 얇아짐")

    # ---------- 10) Critic ----------
    stats = {"verified": n_ver, "weak": n_weak, "unsupported": n_unsup,
             "total": len(verified), "sources": len(sources),
             "dart_sources": n_dart, "news_sources": n_news,
             "timelines": len(recon["timelines"]), "conflicts": len(recon["conflicts"])}
    draft_md = report.render_markdown(cfg.company, cfg.topic, synth, {}, stats, fin_md, recon)
    crit = critic.run(draft_md, n_ver, n_weak, n_unsup)
    art.write_json("10_critic.json", crit)
    art.stage("Critic", f"지적 {len(crit.get('issues_found',[]))}건 + 총평",
              "자기비평이라 자체 편향 공유 가능(외부 검토 대체 아님)")

    # ---------- Final render ----------
    final_md = report.render_markdown(cfg.company, cfg.topic, synth, crit, stats, fin_md, recon)
    art.write_text("fact_pack.md", final_md)
    art.write_text("fact_pack.html", report.markdown_to_html(final_md, f"{cfg.company} Fact Pack"))
    art.stage("Report", "fact_pack.md / fact_pack.html 렌더", "")

    art.finalize_run_log({
        "회사": cfg.company, "주제": cfg.topic, "corp_code": corp,
        "기간": f"{cfg.bgn}~{cfg.end}", "오늘": cfg.today,
        "소스": f"{len(sources)}건 (DART {n_dart}/News {n_news})",
        "claim": f"raw {len(raw_claims)} → norm {len(norm_claims)} → verified {n_ver}/weak {n_weak}/unsup {n_unsup}",
        "정합": f"timeline {len(recon['timelines'])} · 충돌 {len(recon['conflicts'])}",
        "모델": f"fast={config.MODEL_FAST}, smart={config.MODEL_SMART}",
        "뉴스활성": news_diag.get("ready"),
    })
    art.log(f"RUN done · outputs/{art.run_id}")
    return {"run_dir": str(art.dir), "stats": stats, "issues": len(issues),
            "claims": len(verified), "news_ready": news_diag.get("ready")}
