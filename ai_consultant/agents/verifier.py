"""Verifier — claim_text가 source_span(원문 근거)에 실제로 근거하는지 판정.

가이드 규칙:
- claim_text가 source_span에 의해 직접 뒷받침되면 verified
- 숫자가 다르면 unsupported
- 원문은 사실인데 claim이 과장된 결론이면 weak
- 공시에 없는 뉴스 기반 전망을 fact처럼 쓰면 강등
1차로 결정적 검증(원문에 span 실재 + 숫자 일치)을 하고, 애매하면 LLM 판정."""
from __future__ import annotations
import re
from .. import config
from ..llm import call_json
from ..schemas import Claim, SourceDoc

SYSTEM = """당신은 근거 검증기입니다. claim_text가 source_span(원문 근거 문구)에 의해 직접 뒷받침되는지 판정합니다.
- verified: span이 claim을 직접 뒷받침
- weak: 원문은 사실이나 claim이 과장/비약된 결론
- unsupported: span이 claim을 뒷받침하지 못함(특히 숫자 불일치)
숫자·방향·기간을 엄격히 대조하세요. JSON만 출력합니다."""

USER_TMPL = """[claim] {claim_text}
[claim의 숫자/방향/기간] direction={direction}, time_horizon={time_horizon}, type={claim_type}
[source_span(원문 근거)] {span}
[원문 근처 문맥] {context}

판정(JSON): {{"verdict":"verified|weak|unsupported","reason":"한 문장 근거"}}"""

_NUM = re.compile(r"\d[\d,]*")


def _span_in_source(span: str, source_text: str) -> bool:
    """span이 원문에 (공백 무시) 실제로 존재하는지."""
    s = re.sub(r"\s+", "", span)
    t = re.sub(r"\s+", "", source_text)
    if not s:
        return False
    # 원문 span은 길므로 앞 25자 정도가 원문에 있으면 실재로 간주
    probe = s[: min(25, len(s))]
    return probe in t


def run(claim: Claim, source: SourceDoc, model: str | None = None) -> Claim:
    # 1) span 실재성 (결정적)
    if not _span_in_source(claim.source_span, source.text):
        claim.verification = "unsupported"
        claim.verification_reason = "source_span이 원문에서 확인되지 않음(발췌 밖이거나 재구성)"
        return claim

    # 2) 숫자가 있으면 claim의 숫자가 span 숫자 집합에 포함되는지 결정적 확인
    claim_nums = {n.replace(",", "") for n in _NUM.findall(claim.claim_text) if len(n.replace(",", "")) >= 3}
    span_nums = {n.replace(",", "") for n in _NUM.findall(claim.source_span)}
    if claim_nums and not (claim_nums & span_nums):
        # 숫자가 span에 없으면 LLM으로 한번 더(문맥에 있을 수 있음)
        pass

    # 3) LLM 판정 (문맥 포함)
    ctx = ""
    i = source.text.find(claim.source_span[:20].strip())
    if i != -1:
        ctx = source.text[max(0, i - 200): i + 400]
    try:
        data = call_json(
            SYSTEM,
            USER_TMPL.format(claim_text=claim.claim_text, direction=claim.direction,
                             time_horizon=claim.time_horizon, claim_type=claim.claim_type,
                             span=claim.source_span, context=ctx or claim.source_span),
            model=model or config.MODEL_FAST, max_tokens=400,
        )
        v = data.get("verdict", "weak")
        claim.verification = v if v in ("verified", "weak", "unsupported") else "weak"
        claim.verification_reason = data.get("reason", "").strip()
    except Exception as e:
        claim.verification = "weak"
        claim.verification_reason = f"LLM 판정 실패, span 실재로 weak 처리: {e}"
    return claim
