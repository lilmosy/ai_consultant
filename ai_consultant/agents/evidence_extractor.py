"""Evidence Extractor — 소스 원문에서 검증 가능한 atomic claim을 추출.

가이드의 Extractor 규칙을 그대로 프롬프트에 반영:
- 사용자 질문을 claim으로 만들지 말 것
- 원문에 있는 주장만 추출할 것
- 숫자/기간/방향/범위 중 최소 2개 이상 포함된 문장을 우선할 것
- source_span(원문 근거 문구)이 없으면 claim으로 만들지 말 것
- 전망성 문장은 fact_or_view=forecast/interpretation, 홍보성은 promotion
"""
from __future__ import annotations
from .. import config
from ..llm import call_json
from ..schemas import Claim, SourceDoc

SYSTEM = """당신은 근거 추출기입니다. 주어진 '원문 그대로'에서만 검증 가능한 최소 단위 주장(claim)을 뽑습니다.
규칙:
- 사용자 질문/요청을 claim으로 만들지 마세요.
- 원문에 실제로 있는 내용만 뽑고, 없는 숫자/사건을 지어내지 마세요.
- 숫자·기간·방향·범위 중 최소 2가지가 담긴 문장을 우선하세요.
- source_span은 원문에서 '그대로 복사한' 근거 문구여야 합니다(요약 금지, 30~200자).
- 전망/추정 문장은 fact_or_view를 forecast 또는 interpretation으로, 회사 홍보성 표현은 promotion으로 표시하세요.
- 근거가 약하면 뽑지 마세요. 억지로 개수를 채우지 마세요.
반드시 JSON만 출력합니다."""

USER_TMPL = """[회사] {company}
[소스 종류] {source_type}
[소스명] {source_name}
[관련 이슈 후보] {issue_ids}

아래는 '{source_name}'의 원문 발췌입니다. 이 안에 실제로 존재하는 주장만 claim으로 추출하세요.

--- 원문 발췌 시작 ---
{passage}
--- 원문 발췌 끝 ---

각 claim(JSON 배열 요소):
{{"issue_id":"가장 관련된 이슈 id(모르면 I0)",
  "claim_type":"Metric|Event|Market|Strategic|Risk|Assumption",
  "topic":"짧은 주제어(예: 수주잔고)",
  "claim_text":"검증 가능한 한 문장 주장",
  "direction":"increase|decrease|stable|uncertain|not_applicable",
  "time_horizon":"연도/기간(예: 2024, 2025E)",
  "scope":"전체|상선|해양및특수선|방산|미국사업 등",
  "source_span":"원문에서 그대로 복사한 근거 문구",
  "evidence_strength":"high|medium|low",
  "fact_or_view":"fact|forecast|interpretation|promotion"}}

한 발췌에서 **최대 8개**까지만, 가장 근거가 분명한 것부터 추출하세요(억지로 채우지 말 것).
출력: {{"claims":[...]}} (없으면 빈 배열)"""


def _coerce(company, source: SourceDoc, raw: dict) -> Claim | None:
    span = (raw.get("source_span") or "").strip()
    ctext = (raw.get("claim_text") or "").strip()
    if not span or not ctext:
        return None
    return Claim(
        claim_id=Claim.new_id(source.source_id, ctext),
        issue_id=raw.get("issue_id") or "I0",
        claim_type=raw.get("claim_type", "Market"),
        company=company,
        topic=raw.get("topic", "").strip(),
        claim_text=ctext,
        direction=raw.get("direction", "not_applicable"),
        time_horizon=str(raw.get("time_horizon", "")).strip(),
        scope=raw.get("scope", "").strip(),
        source_type=source.source_type,
        source_name=source.source_name,
        source_date=source.source_date,
        source_span=span,
        evidence_strength=raw.get("evidence_strength", "medium"),
        fact_or_view=raw.get("fact_or_view", "fact"),
        source_id=source.source_id,
    )


def run(company: str, source: SourceDoc, model: str | None = None,
        max_tokens: int = 8000) -> list[Claim]:
    data = call_json(
        SYSTEM,
        USER_TMPL.format(company=company, source_type=source.source_type,
                         source_name=source.source_name,
                         issue_ids=",".join(source.issue_ids) or "미지정",
                         passage=source.text[:config.MAX_DOC_CHARS]),
        model=model or config.MODEL_FAST, max_tokens=max_tokens,
    )
    out = []
    for raw in data.get("claims", []):
        c = _coerce(company, source, raw)
        if c:
            out.append(c)
    return out
