"""
v1 CLI — 회사 부문 매출 시계열 정합.

  # 오프라인 데모 (API 불필요, 합성 픽스처):
  python scripts/run_v1.py --demo

  # 실제 DART (ANTHROPIC/DART 키 필요):
  python scripts/run_v1.py --company 네이버 --years 2020 2021 2022 2023 2024

산출물: eval/output/<회사>_부문정합.xlsx  (시계열 / 매핑이력 / 근거 / 미해결)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_consultant.reconcile.reconciler import reconcile
from ai_consultant.report.xlsx_writer import write_xlsx


def _print_series(res):
    print(f"\n=== {res.company} 부문 매출 시계열 (최신 구조 기준) ===")
    hdr = "부문".ljust(16) + "".join(y.rjust(10) for y in res.years)
    print(hdr)
    for seg in res.canonical_segments:
        line = seg.ljust(16) + "".join(
            (f"{res.series[seg][y]:,.0f}" if res.series[seg][y] is not None else "—").rjust(10)
            for y in res.years
        )
        print(line)
    print(f"\n매핑 {len(res.edges)}개, 미해결 {len(res.unresolved)}건")
    for u in res.unresolved:
        print("  ⚠", u)


def main():
    ap = argparse.ArgumentParser(description="부문 매출 시계열 정합 (v1)")
    ap.add_argument("--company", help="기업명 (예: 네이버)")
    ap.add_argument("--years", nargs="+", type=int, help="회계연도들 (오름차순)")
    ap.add_argument("--demo", action="store_true", help="합성 픽스처로 오프라인 실행")
    ap.add_argument("--out", default=None, help="출력 xlsx 경로")
    args = ap.parse_args()

    if args.demo:
        from ai_consultant.fixtures import naver_like_rows
        rows = naver_like_rows()
        pairs = {("2021", "2022")}
        company = rows[0].company
    else:
        if not args.company or not args.years:
            ap.error("--company 와 --years 를 지정하거나 --demo 를 쓰세요.")
        from ai_consultant.extract.segment_extractor import fetch_segment_rows
        print(f"DART 수집 — {args.company} {args.years}")
        rows = fetch_segment_rows(args.company, args.years)
        pairs = set()   # 재분류표 자동탐지는 v1.1 — 지금은 이합 보존만으로 판정
        company = args.company

    if not rows:
        print("SegmentRow 가 없습니다. 종료.")
        return

    res = reconcile(rows, restatement_pairs=pairs)
    _print_series(res)

    out = args.out or f"eval/output/{company}_부문정합.xlsx"
    path = write_xlsx(res, out)
    print(f"\n엑셀 저장 → {path}")


if __name__ == "__main__":
    main()
