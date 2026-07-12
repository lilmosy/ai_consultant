"""
부문 매핑의 핵심 — 이합·부분합 보존 매칭.

핵심 아이디어 (이름을 믿지 말고 숫자를 믿어라):
  회사가 부문을 재편해도 겹치는 회계연도의 이합(부분합)은 보존된다.
  '온랩 4000'이 '상품 4000'으로 이름만 바뀌면 값이 같으니 identity/rename,
  '비플 2800 + 쇼핑 1900' 이 '커머스 4700' 이면 부분합이 같으니 merge.
  → 매핑을 이름 유사도가 아니라 (값 집합의) 부분합 일치로 찾는다.

입력: 같은 회계연도(fiscal_year)에 대한 두 구조 뷰
      old = {segment_name: revenue}, new = {segment_name: revenue}
      (old = 구조 A / 이전 보고서, new = 구조 B / 최신·재분류 보고서)
출력: list[SegmentEdge]  — identity/rename/merge/split/new/discontinued

전략(ground truth)이 필요 없다: 이합 보존은 회사 공시 숫자에서 계산으로 검증된다.
회사 재분류표가 있으면 restatement_backed=True 로 신뢰도를 올린다.
"""
from __future__ import annotations

from itertools import combinations
from typing import Optional

from ai_consultant.config import (
    MATCH_AUTO_CLEAR,
    MATCH_REL_TOL,
    MATCH_REVIEW_FLOOR,
)
from ai_consultant.schemas.segment import Band, SegmentEdge

# 부분합 탐색 시 결합 최대 크기 — 부문 수는 보통 <10 이라 안전.
_MAX_SUBSET = 6


def _close(a: float, b: float, tol: float = MATCH_REL_TOL) -> bool:
    """상대 허용오차 내에서 두 값이 같은가."""
    if b == 0:
        return abs(a) <= tol
    return abs(a - b) / abs(b) <= tol


def _residual(a: float, b: float) -> float:
    return 0.0 if b == 0 else abs(a - b) / abs(b)


def _band(confidence: float) -> Band:
    if confidence >= MATCH_AUTO_CLEAR:
        return "auto_clear"
    if confidence >= MATCH_REVIEW_FLOOR:
        return "human_review"
    return "escalate"


def _confidence(residual: float, restatement_backed: bool) -> float:
    """이합 잔차가 작을수록, 재분류표가 뒷받침할수록 높다."""
    base = max(0.0, 1.0 - residual / MATCH_REL_TOL * 0.2)   # 잔차 0 → 1.0, 잔차=tol → 0.8
    base = min(base, 1.0)
    if restatement_backed:
        base = min(1.0, base + 0.1)
    return round(base, 4)


def _find_subset(
    target: float,
    pool: dict[str, float],
    tol: float = MATCH_REL_TOL,
) -> Optional[list[str]]:
    """pool 에서 합이 target 에 가장 근접(오차 내)하는 부분집합을 찾는다.

    작은 부분집합을 우선(단순한 설명을 선호), 동률이면 잔차 최소.
    """
    names = list(pool)
    best: Optional[list[str]] = None
    best_res = tol + 1.0
    for size in range(1, min(_MAX_SUBSET, len(names)) + 1):
        for combo in combinations(names, size):
            s = sum(pool[n] for n in combo)
            if _close(s, target, tol):
                res = _residual(s, target)
                if res < best_res:
                    best, best_res = list(combo), res
        if best is not None:
            # 이 크기에서 이미 맞는 게 있으면 더 큰 조합은 보지 않는다 (최소 설명).
            break
    return best


def match_views(
    old: dict[str, Optional[float]],
    new: dict[str, Optional[float]],
    fiscal_year: str,
    restatement_backed: bool = False,
) -> list[SegmentEdge]:
    """두 구조 뷰를 이합 보존으로 매핑해 SegmentEdge 리스트를 만든다.

    old, new 는 같은 fiscal_year 의 {부문명: 매출}. None 값은 제외한다.
    """
    o = {k: float(v) for k, v in old.items() if v is not None}
    n = {k: float(v) for k, v in new.items() if v is not None}

    edges: list[SegmentEdge] = []
    used_old: set[str] = set()
    used_new: set[str] = set()

    def make_edge(froms, tos, mtype):
        fsum = sum(o[f] for f in froms)
        tsum = sum(n[t] for t in tos)
        res = _residual(fsum, tsum)
        conf = _confidence(res, restatement_backed)
        return SegmentEdge(
            from_segments=list(froms),
            to_segments=list(tos),
            match_type=mtype,
            fiscal_year=fiscal_year,
            from_sum=round(fsum, 4),
            to_sum=round(tsum, 4),
            residual=round(res, 6),
            confidence=conf,
            band=_band(conf),
            restatement_backed=restatement_backed,
            evidence=(
                f"이합 보존: from={round(fsum, 2)} ≈ to={round(tsum, 2)} "
                f"(잔차 {res:.4%})"
            ),
        )

    # 1) 1:1 매칭 (identity / rename) — 값이 같은 단일 쌍을 먼저 소진.
    for on, ov in list(o.items()):
        if on in used_old:
            continue
        for nn, nv in n.items():
            if nn in used_new:
                continue
            if _close(ov, nv):
                mtype = "identity" if on == nn else "rename"
                edges.append(make_edge([on], [nn], mtype))
                used_old.add(on)
                used_new.add(nn)
                break

    # 2) merge (n:1) — 남은 신부문 각각에 대해 남은 구부문들의 부분합을 찾는다.
    for nn, nv in n.items():
        if nn in used_new:
            continue
        pool = {k: v for k, v in o.items() if k not in used_old}
        subset = _find_subset(nv, pool)
        if subset and len(subset) >= 2:
            edges.append(make_edge(subset, [nn], "merge"))
            used_old.update(subset)
            used_new.add(nn)

    # 3) split (1:n) — 남은 구부문 각각에 대해 남은 신부문들의 부분합을 찾는다.
    for on, ov in o.items():
        if on in used_old:
            continue
        pool = {k: v for k, v in n.items() if k not in used_new}
        subset = _find_subset(ov, pool)
        if subset and len(subset) >= 2:
            edges.append(make_edge([on], subset, "split"))
            used_old.add(on)
            used_new.update(subset)

    # 4) 남은 것 — new / discontinued (미해결 후보)
    for nn in n:
        if nn not in used_new:
            edges.append(SegmentEdge(
                from_segments=[], to_segments=[nn], match_type="new",
                fiscal_year=fiscal_year, to_sum=round(n[nn], 4),
                confidence=0.0, band="escalate", restatement_backed=restatement_backed,
                evidence="대응 구부문 없음 — 신설 또는 미해결",
            ))
    for on in o:
        if on not in used_old:
            edges.append(SegmentEdge(
                from_segments=[on], to_segments=[], match_type="discontinued",
                fiscal_year=fiscal_year, from_sum=round(o[on], 4),
                confidence=0.0, band="escalate", restatement_backed=restatement_backed,
                evidence="대응 신부문 없음 — 중단 또는 미해결",
            ))

    return edges
