# ai_consultant — 부문 시계열 정합 에이전트

여러 해 DART 사업보고서에서 **사업부문 매출**을 뽑아, 이름·구조가 바뀌는 재편
(개명·병합·분할)을 **이합(부분합) 보존**으로 관통해 하나의 연속 시계열로 복원한다.
모든 숫자는 출처에 결착되고, 매핑 정확도는 채점된다.

> 요약봇/대시보드는 정보를 *보여준다*. 이 시스템은 **판정을 내리고, 근거에 결착하고, 채점된다.**

자세한 배경·결정은 [`docs/`](docs/) — 문제정의 → 솔루션 → 측정 → 로드맵.

## 왜 이 문제인가 (한눈에)

- 회사가 부문을 재편하면 이름이 바뀌어 부문 매출 **시계열이 끊긴다.** 손으로 맞추면 반나절.
- **이름을 믿지 말고 숫자를 믿어라:** 재편해도 겹치는 연도의 이합은 보존된다
  (`비플 2800 + 쇼핑 1900 = 커머스 4700`). 이걸로 매핑을 자동 복원한다.
- **정답이 공짜다:** 회사 재분류표(신구조 재작성)가 곧 정답 매핑 → 라벨링 0.

## 빠른 시작

```bash
# 저장소 루트의 .venv 사용 (anthropic, langgraph, openpyxl 등 설치됨)
cd PROJECTS/ai_consultant

# 1) 오프라인 데모 — API 불필요, 합성 픽스처로 엔진 확인
../../.venv/bin/python scripts/run_v1.py --demo

# 2) 엔진 채점 — 이합 보존 매칭 vs 이름 완전일치 베이스라인
../../.venv/bin/python eval/run_eval.py

# 3) 회귀 테스트
../../.venv/bin/python tests/test_matcher.py

# 4) 실제 DART (ANTHROPIC_API_KEY, DART_API_KEY 필요 — 저장소 루트 .env)
../../.venv/bin/python scripts/run_v1.py --company 네이버 --years 2020 2021 2022 2023 2024
```

데모 출력: 재편(비플+쇼핑→커머스, 서치→검색)을 관통해 2020년 커머스를
`비플+쇼핑`으로 복원한 시계열 + `eval/output/*.xlsx` 4시트.

## 구조

```
ai_consultant/
  config.py                 설정·임계값 (매칭 허용오차, 신뢰도 밴드)
  schemas/
    segment.py              SegmentRow / SegmentEdge / ReconResult  ← 핵심 모델
    claim.py                (evidence_lens 계승 — v3 소스정합용)
  dart/dart_tools.py        DART OpenAPI (기업코드·목차·섹션·재무) — evidence_lens에서 포팅
  extract/segment_extractor.py   사업보고서 → SegmentRow[] (제약된 LLM 추출 + 근거결착)
  reconcile/
    matcher.py              이합 보존 매칭 (identity/rename/merge/split)  ← 크라운 주얼
    reconciler.py           인접 구조 합성 → 최신 구조 투영, 시계열 복원
  report/xlsx_writer.py     시계열/매핑이력/근거/미해결 4시트
  fixtures.py               NAVER형 합성 픽스처 (오프라인 데모·gold)
scripts/run_v1.py           CLI
eval/run_eval.py            합성 gold 채점 (+ 베이스라인 대비)
tests/test_matcher.py       매칭·정합 회귀
docs/                       00 문제 · 01 솔루션 · 02 측정 · 03 로드맵
AGENTS.md                   에이전트 위임 계약 (자율 루프 규율)
```

## 계보

`z.MINE/project/evidence_lens`(LangGraph 다중소스 정합 파이프라인, `Verdict` =
agreement/conflict/temporal_shift/scope_difference/evidence_gap)의 정합 골격을
계승·형식화한 것. DART 툴체인과 Claim 스키마를 재사용한다.

상태: **v1 정합 엔진 검증 완료(오프라인).** 다음은 실제 DART 추출 배선 → `docs/03_roadmap.md`.
