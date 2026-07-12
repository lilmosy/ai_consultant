"""
Evidence Lens 핵심 데이터 모델.

Claim      — 소스 하나에서 추출된 정규화된 주장 하나
AlignResult — 클레임 두 개 사이의 관계 판정
SubReport   — 세부 주제 하나의 분석 결과 (클레임 묶음 + 관계 + 다음 확인)
"""
from typing import Literal, Optional
from pydantic import BaseModel

Direction   = Literal["increase", "decrease", "stable", "uncertain"]
SourceType  = Literal["DART", "NEWS", "PDF"]
Credibility = Literal["HIGH", "MEDIUM", "LOW"]
Verdict     = Literal["agreement", "conflict", "temporal_shift", "scope_difference", "evidence_gap"]


class Claim(BaseModel):
    claim_id:          str
    topic:             str
    object:            str            # 기업명 또는 섹터
    direction:         Direction
    time_horizon:      Optional[str] = None
    scope:             Optional[str] = None
    claim_text:        str
    source_type:       SourceType
    source_name:       str
    source_date:       str            = ""
    source_span:       str            # 원문 위치 — 필수
    source_credibility: Credibility  = "MEDIUM"


class AlignResult(BaseModel):
    claim_a_id: str
    claim_b_id: str
    verdict:    Verdict
    reason:     str


class SubReport(BaseModel):
    sub_topic:     str
    claim_ids:     list[str]
    relationships: list[AlignResult] = []
    evidence_gaps: list[str]         = []
    next_checks:   list[str]         = []
