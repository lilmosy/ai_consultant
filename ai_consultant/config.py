"""전역 설정 — API 키, 모델명, 임계값.

evidence_lens/config.py 를 계승하되, 정합(reconciliation) 파라미터를 추가한다.
"""
import os

from dotenv import load_dotenv

# 저장소 루트의 .env 를 읽는다 (DART_API_KEY, ANTHROPIC_API_KEY, NAVER_API_KEY).
load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DART_API_KEY      = os.getenv("DART_API_KEY", "")
NAVER_API_KEY     = os.getenv("NAVER_API_KEY", "")

# claude-haiku-4-5 : 라우팅·경량 추출
# claude-sonnet-4-6: 부문표 추출·정규화 등 핵심 작업
MODEL_HEAVY = "claude-sonnet-4-6"
MODEL_LIGHT = "claude-haiku-4-5"

# ── DART ReAct ────────────────────────────────────────────────────────────
MAX_DART_TURNS = 8

# ── 정합 임계값 (matcher.py) ───────────────────────────────────────────────
# 이합(부분합) 보존 매핑에서 "숫자가 같다"고 판정하는 상대 허용오차.
# 재분류 시 회사가 반올림·단위 정리를 하므로 완전 일치는 드물다.
MATCH_REL_TOL = 0.005          # 0.5%
# 매핑 신뢰도 3구간 밴드. 이 값 이상이면 auto-clear, 이하이면 human-review.
MATCH_AUTO_CLEAR = 0.98
MATCH_REVIEW_FLOOR = 0.80
