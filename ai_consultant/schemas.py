"""Data models for the evidence pipeline. Plain dataclasses (no pydantic dependency)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import hashlib

CLAIM_TYPES = ["Metric", "Event", "Market", "Strategic", "Risk", "Assumption"]
DIRECTIONS = ["increase", "decrease", "stable", "uncertain", "not_applicable"]
FACT_OR_VIEW = ["fact", "forecast", "interpretation", "promotion"]
SOURCE_TYPES = ["DART", "IR", "News", "Company PR", "Analyst Report"]


@dataclass
class Issue:
    issue_id: str
    question: str          # 핵심 질문
    hypothesis: str        # 초기 가설
    sub_questions: list[str] = field(default_factory=list)
    source_plan: list[str] = field(default_factory=list)  # 어떤 소스를 볼지


@dataclass
class SourceDoc:
    """A retrieved source document (or passage) that claims will be extracted from."""
    source_id: str
    source_type: str        # DART | News | IR ...
    source_name: str        # e.g. "한화오션 2024 사업보고서"
    source_date: str        # YYYY-MM-DD
    url: str
    text: str               # the passage/plaintext used for extraction
    meta: dict[str, Any] = field(default_factory=dict)
    issue_ids: list[str] = field(default_factory=list)


@dataclass
class Claim:
    claim_id: str
    issue_id: str
    claim_type: str
    company: str
    topic: str
    claim_text: str
    direction: str
    time_horizon: str
    scope: str
    source_type: str
    source_name: str
    source_date: str
    source_span: str            # 원문 근거 문구 (quote)
    evidence_strength: str      # high | medium | low
    fact_or_view: str           # fact | forecast | interpretation | promotion
    needs_verification: bool = True
    source_id: str = ""
    # filled by Verifier
    verification: str = "pending"   # verified | weak | unsupported | pending
    verification_reason: str = ""

    @staticmethod
    def new_id(source_id: str, claim_text: str) -> str:
        h = hashlib.sha1(f"{source_id}|{claim_text}".encode("utf-8")).hexdigest()[:12]
        return f"C_{h}"


@dataclass
class Gap:
    gap_id: str
    issue_id: str
    description: str        # 무엇이 비어있나
    why_it_matters: str
    next_check: str        # 다음에 확인할 자료/검색어


def to_jsonable(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj
