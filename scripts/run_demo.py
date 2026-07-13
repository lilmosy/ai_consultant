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
    ap.add_argument("--topic", default="2026년 수주잔고 흐름 및 향후 사업 전망")
    ap.add_argument("--bgn", default="20240101")
    ap.add_argument("--end", default="20261231")
    ap.add_argument("--max-news", type=int, default=30)
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--out-name", default=None, help="고정 출력 폴더명(기본: 타임스탬프)")
    args = ap.parse_args()

    cfg = RunConfig(company=args.company, topic=args.topic, bgn=args.bgn, end=args.end,
                    max_news=args.max_news)
    res = run(cfg, out_base=args.out, run_id=args.out_name)
    print("\n=== RESULT ===")
    for k, v in res.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
