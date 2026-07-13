"""Synthesis Agent — 검증된 claim과 gap을 주니어용 fact pack(마크다운)으로 종합.

사실/전망/해석을 분리하고, 근거(source_span)를 보존하며, 표 위주로 정리한다."""
from __future__ import annotations
from .. import config
from ..llm import call_json
from ..schemas import Issue, Claim, Gap

SYSTEM = """당신은 컨설팅 리서치 신디사이저입니다. 검증된 근거만으로 주니어 컨설턴트용 1차 fact pack을 작성합니다.
원칙:
- 사실(fact)과 전망(forecast)/해석(interpretation)을 명확히 분리한다.
- 확인 안 된 것은 단정하지 말고 'open question'으로 남긴다.
- 근거 없는 숫자/결론을 만들지 않는다(제공된 claim 밖의 수치 금지).
- 표 중심으로, 주니어가 슬라이드로 옮길 수 있게 정리한다.
Executive Summary는 '무엇을 알고, 무엇이 아직 비어있는지'를 담아야 한다.
반드시 JSON만 출력합니다(값은 마크다운 문자열)."""

USER_TMPL = """[회사] {company}
[리서치 주제] {topic}

[이슈 트리]
{issues}

[검증된/약한 근거(claim)] — verified/weak만 사용, unsupported는 제외
{claims}

[핵심 재무(정형, DART 주요계정)]
{financials}

[시점·소스 정합(Reconciler)] — 핵심 지표의 시점 흐름과 소스 간 충돌
{reconciliation}

[Evidence Gaps]
{gaps}

아래 JSON 구조로 fact pack을 작성하세요(각 값은 마크다운):
{{
 "executive_summary": "- 결론 3~5개 (사실/전망 구분, 무엇이 비어있는지 포함)",
 "issue_tree_md": "| Issue | Hypothesis | Evidence Status |\\n|...| 표",
 "evidence_table_md": "| Claim | Type | Source | Span(축약) | Strength | View |\\n 표 (검증된 것 위주 12행 내외)",
 "timeline_md": "핵심 지표의 시점 흐름 표 (예: | 지표 | 2025-12-31 | 2026-03-31 | 최근 뉴스 | 추세 |). Reconciler 근거만 사용.",
 "order_backlog_md": "수주/수주잔고/계약 관련 표 또는 요약 (가장 최신 시점 명시)",
 "strategic_outlook_md": "성장 동력과 제약 요인, 사실과 전망 분리",
 "risks_open_questions_md": "| Risk/Gap | Why it matters | Next check | 표",
 "next_research_agenda_md": "- 추가로 확인할 자료/검색어 목록"
}}"""


def _recon_blob(recon: dict) -> str:
    if not recon:
        return "(없음)"
    lines = []
    for t in recon.get("timelines", [])[:10]:
        pts = " → ".join(f"{p.get('as_of','?')}:{p.get('value','?')}({p.get('source','')})"
                         for p in t.get("points", []))
        lines.append(f"- [{t.get('metric','')}/{t.get('unit','')}] {pts} | 추세:{t.get('trend','')} {t.get('note','')}")
    for c in recon.get("conflicts", [])[:10]:
        lines.append(f"- [충돌:{c.get('kind','')}] {c.get('topic','')}: {c.get('description','')}")
    for n in recon.get("cross_source_notes", [])[:6]:
        lines.append(f"- [교차] {n}")
    return "\n".join(lines) or "(없음)"


def run(company: str, topic: str, issues: list[Issue], claims: list[Claim],
        gaps: list[Gap], financials_md: str, reconciliation: dict | None = None,
        model: str | None = None) -> dict:
    usable = [c for c in claims if c.verification in ("verified", "weak")]
    issue_blob = "\n".join(f"- {i.issue_id}: {i.question} | 가설: {i.hypothesis}" for i in issues)
    claim_blob = "\n".join(
        f"- [{c.issue_id}/{c.claim_type}/{c.verification}/{c.fact_or_view}] {c.claim_text} "
        f"(근거: {c.source_span[:60]}… | {c.source_name} {c.source_date})"
        for c in usable[:50]
    )
    gap_blob = "\n".join(f"- [{g.issue_id}] {g.description} → next: {g.next_check}" for g in gaps)
    data = call_json(
        SYSTEM,
        USER_TMPL.format(company=company, topic=topic, issues=issue_blob,
                         claims=claim_blob or "(없음)", financials=financials_md or "(없음)",
                         reconciliation=_recon_blob(reconciliation), gaps=gap_blob or "(없음)"),
        model=model or config.MODEL_SMART, max_tokens=6500,
    )
    return data
