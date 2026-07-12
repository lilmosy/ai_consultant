"""matcher + reconciler 단위 검증 — API 불필요, 합성 픽스처로 이합 보존을 확인."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_consultant.fixtures import NAVER_GOLD_EDGES, naver_like_rows
from ai_consultant.reconcile.matcher import match_views
from ai_consultant.reconcile.reconciler import reconcile


def _as_edge_set(edges):
    return {
        (frozenset(e.from_segments), frozenset(e.to_segments), e.match_type)
        for e in edges
        if e.match_type in ("identity", "rename", "merge", "split")
    }


def test_match_views_naver():
    """겹치는 2021년에서 구→신 매핑이 gold 와 일치하는가."""
    old = {"서치플랫폼": 30000, "비즈니스플랫폼": 28000, "쇼핑": 19000,
           "핀테크": 9000, "콘텐츠": 6000, "클라우드": 4000}
    new = {"검색플랫폼": 30000, "커머스": 47000,
           "핀테크": 9000, "콘텐츠": 6000, "클라우드": 4000}
    edges = match_views(old, new, "2021", restatement_backed=True)
    got = _as_edge_set(edges)
    gold = {(frozenset(a), frozenset(b), t) for a, b, t in NAVER_GOLD_EDGES}
    assert got == gold, f"\n got={got}\n gold={gold}"
    # 이합 보존이면 잔차 0, 재분류표 뒷받침이면 auto_clear.
    merge = next(e for e in edges if e.match_type == "merge")
    assert merge.residual == 0.0
    assert merge.band == "auto_clear"
    print("✓ test_match_views_naver")


def test_reconcile_series():
    """재편을 관통해 2020 커머스가 (비플+쇼핑) 으로 복원되는가."""
    rows = naver_like_rows()
    res = reconcile(rows, restatement_pairs={("2021", "2022")})
    assert res.canonical_segments == sorted(
        ["검색플랫폼", "커머스", "핀테크", "콘텐츠", "클라우드"]
    )
    # 2020 은 구 구조에만 있음 → 매핑으로 커머스에 투영: 비플(23800)+쇼핑(16150)=39950
    v2020 = res.series["커머스"]["2020"]
    assert v2020 == 23800 + 16150, v2020
    # 2020 검색플랫폼 = 서치플랫폼 개명 투영 = 25500
    assert res.series["검색플랫폼"]["2020"] == 25500
    # 모든 canonical 부문이 전 연도 값을 가져야 함 (끊긴 시계열 복원).
    for seg in res.canonical_segments:
        for y in ("2020", "2021", "2022"):
            assert res.series[seg][y] is not None, f"{seg}/{y} 비어있음"
    print("✓ test_reconcile_series  (2020 커머스 =", v2020, ")")


if __name__ == "__main__":
    test_match_views_naver()
    test_reconcile_series()
    print("\n모든 테스트 통과 ✅")
