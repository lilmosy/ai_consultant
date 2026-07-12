"""Claim Normalizer — enum/필드 값을 표준 스키마로 정규화하고 명백한 중복을 병합.

LLM 없이 결정적으로 수행(값 매핑 + 정규화). 서로 다른 표현을 같은 스키마로 맞춘다."""
from __future__ import annotations
import re
from ..schemas import Claim, CLAIM_TYPES, DIRECTIONS, FACT_OR_VIEW

_TYPE_MAP = {
    "metric": "Metric", "지표": "Metric", "수치": "Metric",
    "event": "Event", "사건": "Event", "계약": "Event",
    "market": "Market", "시장": "Market", "업황": "Market",
    "strategic": "Strategic", "전략": "Strategic",
    "risk": "Risk", "리스크": "Risk", "위험": "Risk",
    "assumption": "Assumption", "가정": "Assumption", "가설": "Assumption",
}
_DIR_MAP = {
    "increase": "increase", "증가": "increase", "상승": "increase", "up": "increase",
    "decrease": "decrease", "감소": "decrease", "하락": "decrease", "down": "decrease",
    "stable": "stable", "유지": "stable", "보합": "stable",
    "uncertain": "uncertain", "불확실": "uncertain",
}
_VIEW_MAP = {
    "fact": "fact", "사실": "fact",
    "forecast": "forecast", "전망": "forecast", "예상": "forecast",
    "interpretation": "interpretation", "해석": "interpretation", "추론": "interpretation",
    "promotion": "promotion", "홍보": "promotion",
}
_STRENGTH = {"high", "medium", "low"}


def _norm(val: str, mapping: dict, allowed, default):
    v = (val or "").strip().lower()
    if v in mapping:
        return mapping[v]
    if val in allowed:
        return val
    for k, out in mapping.items():
        if k in v:
            return out
    return default


def _key(c: Claim) -> str:
    txt = re.sub(r"\s+", "", c.claim_text.lower())
    return f"{c.source_id}|{c.topic}|{txt[:40]}"


def run(claims: list[Claim]) -> list[Claim]:
    seen: dict[str, Claim] = {}
    for c in claims:
        c.claim_type = _norm(c.claim_type, _TYPE_MAP, CLAIM_TYPES, "Market")
        c.direction = _norm(c.direction, _DIR_MAP, DIRECTIONS, "not_applicable")
        c.fact_or_view = _norm(c.fact_or_view, _VIEW_MAP, FACT_OR_VIEW, "fact")
        c.evidence_strength = c.evidence_strength if c.evidence_strength in _STRENGTH else "medium"
        c.time_horizon = c.time_horizon.strip()
        k = _key(c)
        # keep the higher-strength duplicate
        if k in seen:
            rank = {"high": 3, "medium": 2, "low": 1}
            if rank.get(c.evidence_strength, 0) > rank.get(seen[k].evidence_strength, 0):
                seen[k] = c
        else:
            seen[k] = c
    return list(seen.values())
