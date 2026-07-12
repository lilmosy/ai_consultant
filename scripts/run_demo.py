"""CLI entry: 전체 멀티에이전트 리서치 데모 실행.

  python scripts/run_demo.py --company 한화오션 --topic "2025년 수주잔고 및 향후 사업 전망"
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_consultant.pipeline import RunConfig, run  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--company", default="한화오션")
    ap.add_argument("--topic", default="2025년 수주잔고 및 향후 사업 전망")
    ap.add_argument("--bgn", default="20230101")
    ap.add_argument("--end", default="20251231")
    ap.add_argument("--fin-year", default="2024")
    ap.add_argument("--max-news", type=int, default=30)
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()

    cfg = RunConfig(company=args.company, topic=args.topic, bgn=args.bgn, end=args.end,
                    fin_year=args.fin_year, max_news=args.max_news)
    res = run(cfg, out_base=args.out)
    print("\n=== RESULT ===")
    for k, v in res.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
