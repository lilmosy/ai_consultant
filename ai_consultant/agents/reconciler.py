"""Reconciler — 교차소스 정합 (의미적 중복 병합 + 시점 타임라인 + 충돌 표면화).

Normalizer의 결정적 중복제거는 '같은 소스의 거의 동일한 텍스트'만 잡는다. 반면 "DART 수주잔고 26조"와
"뉴스 수주잔고 26조 돌파"가 같은 사실인지는 의미 판단이 필요하다 — 이 판단을 LLM에게 맡긴다.

또한 DART(예: 2025-12-31, 2026-03-31 스냅샷)와 뉴스(예: 2026-07)는 시점이 다르다. 같은 지표를
시점축으로 정렬해 흐름(timeline)을 만들고, 시점 차이/값 충돌/공시 vs 뉴스 불일치를 명시적으로 표시한다.
"""
from __future__ import annotations
from .. import config
from ..llm import call_json
from ..schemas import Claim

SYSTEM = """당신은 리서치 정합(reconciliation) 담당입니다. 여러 소스·여러 시점에서 나온 claim들을 받아,
(1) 같은 지표/사실을 가리키는 claim을 의미적으로 묶고,
(2) 수치 지표는 시점축(as_of)으로 정렬해 흐름(timeline)을 만들고,
(3) 시점 차이/값 충돌/공시 vs 뉴스 불일치를 명시적으로 드러냅니다.
근거에 있는 숫자만 사용하고, 없는 값을 만들지 마세요. 반드시 JSON만 출력합니다."""

USER_TMPL = """[회사] {company}
[오늘] {today}

아래는 검증된 claim 목록입니다. 형식: [id | type | topic | time_horizon | source_type | source_date] claim_text
{claims}

작업:
1) timelines: 수치로 추적 가능한 **가장 중요한 지표 최대 12개**(예: 전사/상선 수주잔고, 매출액, 영업이익,
   순이익, 자본총계, 미국 유상증자 등)를 시점(as_of)별 포인트로 정렬. 같은 지표의 서로 다른 시점 값을 한 묶음으로.
   (지표를 12개로 압축하되 conflicts/cross_source_notes를 반드시 채우세요.)
2) conflicts: (a) 같은 지표인데 시점이 달라 값이 다른 경우(kind="시점차이"),
   (b) 같은 시점인데 소스마다 값이 다른 경우(kind="값충돌"),
   (c) 공시엔 근거가 약한데 뉴스가 단정하는 경우(kind="공시vs뉴스").
3) cross_source_notes: 공시엔 없고 뉴스에만 있는 주장, 또는 여러 소스가 상호 보강하는 지점.

출력(JSON):
{{
 "timelines": [
   {{"metric":"수주잔고(상선)","unit":"백만원",
     "points":[{{"as_of":"YYYY-MM-DD","value":"26,003,671","source":"DART 사업보고서(2025.12)","claim_id":"C_..."}}],
     "trend":"증가|감소|보합|불명확","note":"한 줄 해석"}}
 ],
 "conflicts": [
   {{"topic":"...","kind":"시점차이|값충돌|공시vs뉴스","description":"무엇이 어떻게 다른가","claim_ids":["C_..."]}}
 ],
 "cross_source_notes": ["..."]
}}"""


def run(company: str, claims: list[Claim], today: str = "", model: str | None = None) -> dict:
    # 정합 대상: 검증된 것 중 수치/이벤트성 위주(시장·전략 프로즈는 타임라인 부적합하나 충돌엔 유용)
    usable = [c for c in claims if c.verification in ("verified", "weak")]
    # 시점 정보가 있는 것 우선, 최대 120건
    usable.sort(key=lambda c: (c.claim_type not in ("Metric", "Event"), c.source_date), reverse=False)
    blob = "\n".join(
        f"[{c.claim_id} | {c.claim_type} | {c.topic} | {c.time_horizon} | {c.source_type} | {c.source_date}] {c.claim_text}"
        for c in usable[:120]
    )
    data = call_json(
        SYSTEM,
        USER_TMPL.format(company=company, today=today or "최신", claims=blob),
        model=model or config.MODEL_SMART, max_tokens=10000,
    )
    if isinstance(data, list):
        data = {"timelines": data}
    # 절단 salvage가 배열을 "claims" 키로 감싸는 경우, timeline 객체이면 매핑
    if not data.get("timelines") and isinstance(data.get("claims"), list):
        if data["claims"] and "points" in data["claims"][0]:
            data["timelines"] = data["claims"]
    data.setdefault("timelines", [])
    data.setdefault("conflicts", [])
    data.setdefault("cross_source_notes", [])
    return data
