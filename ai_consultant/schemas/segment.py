"""
부문 시계열 정합(segment reconciliation)의 핵심 데이터 모델.

문제: 회사가 사업부문을 재편/개명하면 부문 매출 시계열이 끊긴다.
      (예: 2021년까지 '비즈니스플랫폼'+'쇼핑' → 2022년부터 '커머스')
목표: 여러 해 사업보고서에서 부문 매출을 뽑아, 재분류표(회사가 공시에 제공)를
      ground truth 로 삼아 구↔신 부문 매핑을 이합·부분합 보존으로 자동 복원한다.

핵심 3층
  SegmentRow    — 한 보고서가 제시한 부문 매출 관측치 하나 (근거 결착)
  SegmentEdge   — 구 부문(들) ↔ 신 부문(들) 매핑 하나 (판정 + 신뢰도 + 근거)
  ReconResult   — 재편을 관통해 복원한 하나의 연속 시계열 + 매핑이력 + 미해결
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

# 매핑 유형. 재편은 이 넷의 조합으로 표현된다.
MatchType = Literal[
    "identity",      # 1:1, 이름·값 동일
    "rename",        # 1:1, 값 동일·이름만 변경 (온랩→상품)
    "merge",         # n:1, 여러 구부문이 한 신부문으로 (비플+쇼핑→커머스)
    "split",         # 1:n, 한 구부문이 여러 신부문으로
    "new",           # 신부문만 존재 (대응 구부문 없음)
    "discontinued",  # 구부문만 존재 (대응 신부문 없음)
]

# 신뢰도 밴드 — 단일 임계값이 아니라 3구간 (auto-clear / review / escalate).
Band = Literal["auto_clear", "human_review", "escalate"]


class SegmentRow(BaseModel):
    """한 보고서에서 뽑은 부문 매출 관측치 하나. 모든 숫자는 출처에 결착된다."""
    company:      str
    fiscal_year:  str                    # 매출이 귀속되는 회계연도 (예: "2021")
    report_year:  str                    # 이 숫자를 실은 보고서의 연도 (예: "2022")
    structure_id: str                    # 이 보고서가 쓴 부문 구조 식별자 (report_year 로 대용 가능)
    segment_name: str                    # 보고서에 표기된 부문명 (원문 그대로)
    revenue:      Optional[float] = None # 억원 단위로 정규화
    unit_raw:     str = "억원"
    source_type:  str = "DART"
    source_name:  str = ""               # 예: "네이버 2022 사업보고서"
    source_span:  str = ""               # 원문 위치 — 필수 (예: "II.사업의 내용 > 부문별 요약재무 표")
    is_restated:  bool = False           # 재분류표(신구조 재작성)에서 나온 값이면 True


class SegmentEdge(BaseModel):
    """구 부문(들) → 신 부문(들) 매핑 하나."""
    from_segments: list[str]             # 구조 A 의 부문명들 (merge 면 >1)
    to_segments:   list[str]             # 구조 B 의 부문명들 (split 이면 >1)
    match_type:    MatchType
    fiscal_year:   str                   # 매핑을 검증한 겹치는 회계연도
    # 이합 보존 검증: from 값 합 vs to 값 합
    from_sum:      Optional[float] = None
    to_sum:        Optional[float] = None
    residual:      Optional[float] = None   # |from_sum - to_sum| / to_sum
    confidence:    float = 0.0
    band:          Band = "human_review"
    evidence:      str = ""              # 재분류표 주석 문장 / 이합 근거 span
    restatement_backed: bool = False     # 회사 재분류표(ground truth)가 직접 뒷받침하면 True


class ReconResult(BaseModel):
    """정합 최종 산출물 — 최신 구조 기준으로 통일된 부문 시계열."""
    company:        str
    metric:         str = "부문별 매출"
    years:          list[str] = Field(default_factory=list)      # 오름차순 회계연도
    canonical_segments: list[str] = Field(default_factory=list)  # 최신 구조 부문명
    # series[segment_name][fiscal_year] = revenue(억원)  (구조 재편을 관통해 복원)
    series:         dict[str, dict[str, Optional[float]]] = Field(default_factory=dict)
    edges:          list[SegmentEdge] = Field(default_factory=list)   # 매핑 이력
    rows:           list[SegmentRow] = Field(default_factory=list)    # 근거 원본 (출처 결착)
    unresolved:     list[str] = Field(default_factory=list)           # 사람이 봐야 할 것
