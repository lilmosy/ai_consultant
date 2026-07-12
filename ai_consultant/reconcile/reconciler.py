"""
정합 조립 — SegmentRow 관측치들을 하나의 연속 시계열(ReconResult)로.

절차
  1. 보고서 구조(structure_id)를 report_year 오름차순으로 정렬. 최신 = canonical.
  2. 인접 구조쌍마다 겹치는 회계연도에서 match_views() 로 매핑(edge) 산출.
  3. 각 구조의 부문 → canonical 부문 변환맵을 합성(compose).
     - identity/rename/merge (n:1) 은 old→canonical dict 로 표현 가능.
     - split (1:n) / new / discontinued 는 값 배분 비율이 없으면 투영 불가 → unresolved.
  4. 회계연도별로 값을 canonical 부문에 집계. 재작성(restated) 값을 우선.

전략(ground truth)은 회사 재분류표에서 나온다. 재분류표가 있으면 그 구조쌍의
edge 들이 restatement_backed=True 가 되어 신뢰도가 높아진다.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from ai_consultant.reconcile.matcher import match_views
from ai_consultant.schemas.segment import ReconResult, SegmentEdge, SegmentRow


def _views_by_structure(rows: list[SegmentRow]) -> dict[str, dict[str, dict[str, float]]]:
    """structure_id → { fiscal_year → { segment: revenue } }."""
    out: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if r.revenue is None:
            continue
        out[r.structure_id][r.fiscal_year][r.segment_name] = r.revenue
    return out


def _overlap_year(a: dict[str, dict], b: dict[str, dict]) -> Optional[str]:
    """두 구조가 공통으로 값을 가진 회계연도 중 가장 최근 것."""
    common = set(a) & set(b)
    return max(common) if common else None


def reconcile(
    rows: list[SegmentRow],
    restatement_pairs: Optional[set[tuple[str, str]]] = None,
) -> ReconResult:
    """부문 관측치들을 최신 구조 기준 연속 시계열로 정합한다.

    restatement_pairs: (old_structure_id, new_structure_id) 쌍의 집합.
        회사 재분류표가 두 구조를 직접 이어준다고 알려진 경우 신뢰도 가산.
    """
    restatement_pairs = restatement_pairs or set()
    if not rows:
        return ReconResult(company="")

    company = rows[0].company
    views = _views_by_structure(rows)
    structures = sorted(views)                     # report_year/structure_id 오름차순
    canonical = structures[-1]
    canonical_segments = sorted(
        {seg for fy in views[canonical].values() for seg in fy}
    )

    edges: list[SegmentEdge] = []
    unresolved: list[str] = []

    # structure_id → (old_seg -> canonical_seg) 변환맵. canonical 은 항등.
    to_canon: dict[str, dict[str, str]] = {canonical: {s: s for s in canonical_segments}}

    # 인접 구조쌍을 최신에서 과거로 합성.
    for i in range(len(structures) - 1, 0, -1):
        new_id, old_id = structures[i], structures[i - 1]
        y = _overlap_year(views[old_id], views[new_id])
        if y is None:
            unresolved.append(
                f"구조 {old_id}↔{new_id}: 겹치는 회계연도 없음 — 매핑 불가"
            )
            continue
        backed = (old_id, new_id) in restatement_pairs
        pair_edges = match_views(views[old_id][y], views[new_id][y], y, backed)
        edges.extend(pair_edges)

        # old_seg -> new_seg (n:1 만 안전하게 투영). new_seg -> canonical 은 이미 있음.
        new_to_canon = to_canon.get(new_id, {})
        step: dict[str, str] = {}
        for e in pair_edges:
            if e.match_type in ("identity", "rename", "merge"):
                canon = new_to_canon.get(e.to_segments[0])
                if canon is None:
                    continue
                for f in e.from_segments:
                    step[f] = canon
            elif e.match_type == "split":
                unresolved.append(
                    f"{y} '{e.from_segments[0]}' 1:n 분할 — 배분 비율 없어 투영 보류"
                )
            elif e.match_type == "discontinued":
                unresolved.append(f"{y} '{e.from_segments[0]}' 중단/미해결")
        to_canon[old_id] = step

    # 회계연도별 값 집계.
    all_years = sorted({fy for st in views.values() for fy in st})
    series: dict[str, dict[str, Optional[float]]] = {
        seg: {y: None for y in all_years} for seg in canonical_segments
    }

    for y in all_years:
        # 재작성/최신 구조가 이 연도를 직접 커버하면 우선 사용.
        provider = None
        for st in reversed(structures):          # 최신 구조 우선
            if y in views[st]:
                provider = st
                break
        if provider is None:
            continue
        mapping = to_canon.get(provider, {})
        for seg, val in views[provider][y].items():
            canon = mapping.get(seg)
            if canon is None:
                continue
            prev = series[canon][y]
            series[canon][y] = (prev or 0.0) + val

    return ReconResult(
        company=company,
        years=all_years,
        canonical_segments=canonical_segments,
        series=series,
        edges=edges,
        rows=rows,
        unresolved=unresolved,
    )
