"""
정합 채점 — 매핑 복원 정밀도/재현율.

전략(ground truth)은 두 곳에서 온다:
  1. 회사 재분류표: 신구조 재작성 표가 곧 정답 매핑. (라벨링 0 — 공짜 전략)
  2. 합성 gold: 픽스처에 심어둔 정답 매핑 (엔진 회귀 테스트).

이 스크립트는 (2) 합성 gold 로 엔진 자체를 채점한다. 실제 회사에 대해서는
재분류표 파싱(restatement.py, v1.1)이 gold 를 자동 생성하도록 확장한다.

지표: 매핑 edge 단위 Precision / Recall / F1, orphan율(미해결 비중).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_consultant.fixtures import NAVER_GOLD_EDGES, naver_like_rows
from ai_consultant.reconcile.matcher import match_views


def _edge_key(froms, tos, mtype):
    return (frozenset(froms), frozenset(tos), mtype)


def score(pred_edges, gold_edges):
    pred = {_edge_key(e.from_segments, e.to_segments, e.match_type)
            for e in pred_edges if e.match_type in ("identity", "rename", "merge", "split")}
    gold = {_edge_key(a, b, t) for a, b, t in gold_edges}
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1}


def main():
    old = {"서치플랫폼": 30000, "비즈니스플랫폼": 28000, "쇼핑": 19000,
           "핀테크": 9000, "콘텐츠": 6000, "클라우드": 4000}
    new = {"검색플랫폼": 30000, "커머스": 47000,
           "핀테크": 9000, "콘텐츠": 6000, "클라우드": 4000}
    edges = match_views(old, new, "2021", restatement_backed=True)
    m = score(edges, NAVER_GOLD_EDGES)

    print("=== 합성 gold 채점 (NAVER형) ===")
    print(f"  TP={m['tp']}  FP={m['fp']}  FN={m['fn']}")
    print(f"  Precision={m['precision']:.3f}  Recall={m['recall']:.3f}  F1={m['f1']:.3f}")

    # 베이스라인 대비: 이름 완전일치만 매칭 (naive) → 개명·병합을 전혀 못 잡음.
    naive_pred = {_edge_key([s], [s], "identity") for s in set(old) & set(new)}
    gold = {_edge_key(a, b, t) for a, b, t in NAVER_GOLD_EDGES}
    naive_tp = len(naive_pred & gold)
    print(f"\n  [베이스라인] 이름 완전일치만: 정답 {naive_tp}/{len(gold)} "
          f"(개명·병합 {len(gold) - naive_tp}건 놓침)")
    print(f"  [제안]       이합 보존 매칭:  정답 {m['tp']}/{len(gold)}")


if __name__ == "__main__":
    main()
