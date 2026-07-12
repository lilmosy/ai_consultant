"""Source Scout — 이슈트리별로 DART 원문 앵커 키워드와 뉴스 검색어를 생성.

실제 자료 확보(공시 조회/원문 다운로드/뉴스 API 호출)는 sources 레이어가 담당하고,
여기서는 '무엇을 어떻게 찾을지'의 검색 계획을 만든다. 조선/방산 도메인의 고가치 DART
앵커는 기본 팩으로 보강한다(리트리벌 튜닝)."""
from __future__ import annotations
from .. import config
from ..llm import call_json

# 조선/방산 사업보고서에서 근거가 실제로 있는 위치를 정확히 때리는 앵커들
DART_ANCHOR_PACK = [
    "납기 수주총액",       # 수주상황 표 (수주총액/기납품액/수주잔고)
    "선별적 수주",         # 업황·수주 전략 서술
    "미 해군",             # 미국 사업 전망 서술
    "미해군 MRO",          # 연혁상 미해군 MRO 수주
    "필리조선소",          # 미국 조선업 진출
    "방위력개선",          # 특수선/잠수함 방산
    "잠수함",
    "LNG운반선",
    "친환경",
    "풍력",
    "FPSO",
    "영업이익",
    "매출액",
    "위험",                # 리스크 관련 서술
]

SYSTEM = """당신은 리서치 소스 스카우트입니다. 각 이슈에 대해 DART 사업보고서 원문에서
근거 문단을 찾기 위한 한국어 앵커 키워드와, 네이버 뉴스에서 쓸 검색어를 만듭니다.
키워드는 원문에 실제로 등장할 법한 구체 표현이어야 합니다. JSON만 출력합니다."""

USER_TMPL = """[회사] {company}
[이슈 트리]
{issues}

각 이슈별로 아래를 생성하세요:
- dart_keywords: DART 사업보고서 원문에서 근거 문단을 찾을 한국어 앵커 2~4개
- news_queries: 네이버 뉴스 검색어 1~3개 (회사명 포함 권장)

출력(JSON):
{{"plan":[{{"issue_id":"I1","dart_keywords":["..."],"news_queries":["..."]}}]}}"""


def run(company: str, issues, model: str | None = None) -> dict:
    issue_blob = "\n".join(
        f"- {i.issue_id}: {i.question} (가설: {i.hypothesis})" for i in issues
    )
    data = call_json(SYSTEM, USER_TMPL.format(company=company, issues=issue_blob),
                     model=model or config.MODEL_FAST, max_tokens=2500)
    plan = {p["issue_id"]: p for p in data.get("plan", [])}

    # merge: dedupe keywords, always append the domain anchor pack for DART coverage
    all_dart = list(DART_ANCHOR_PACK)
    all_news: list[str] = []
    for p in plan.values():
        for kw in p.get("dart_keywords", []):
            if kw and kw not in all_dart:
                all_dart.append(kw)
        for q in p.get("news_queries", []):
            if q and q not in all_news:
                all_news.append(q)
    if not all_news:
        all_news = [f"{company} 수주", f"{company} 방산", f"{company} 실적"]
    return {"by_issue": plan, "dart_keywords": all_dart, "news_queries": all_news}
