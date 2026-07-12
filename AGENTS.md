# AGENTS.md — 에이전트 위임 계약

이 파일은 Claude Code / Codex 등 코딩 에이전트가 이 프로젝트에서 자율 루프를 돌 때
따르는 규율이다. 사람(조소영)이 위임하고, 에이전트가 관리·구현·검증한다.

## 이 프로젝트가 뭔지 (1문단)

DART 사업보고서의 **사업부문 매출**을, 회사가 부문을 재편/개명해 끊긴 시계열을,
**이합(부분합) 보존**으로 매핑을 자동 복원해 하나의 연속 시계열로 잇는다.
전략(정답)은 회사 재분류표 또는 이합 계산에서 온다 — 라벨링하지 않는다.
자세한 맥락은 `docs/00~03`. 요약봇이 아니라 **판정·근거결착·측정** 시스템이다.

## 실행 환경

- 파이썬: 저장소 루트 `../../.venv/bin/python` (3.13, anthropic·langgraph·openpyxl·lxml·bs4 설치됨).
  `rapidfuzz`는 없음 — 부문 매칭은 이름 유사도가 아니라 **숫자(이합)** 이므로 불필요.
- 키: 저장소 루트 `.env` 의 `DART_API_KEY`, `ANTHROPIC_API_KEY`, `NAVER_API_KEY`.
  기업코드는 DART에서 라이브로 받는다(캐시 파일 없음).
- 모든 명령은 `PROJECTS/ai_consultant/` 에서 실행하고, import는 패키지 루트 기준
  (`from ai_consultant... import`). 스크립트는 `sys.path` 에 프로젝트 루트를 넣어 둔다.

## 불변 규칙 (INVARIANTS)

1. **근거 결착(groundedness).** 모든 `SegmentRow` 는 `source_span` 을 가진다.
   추출기는 원문에 없는 부문·숫자를 만들지 않는다. 근거 없는 값은 미해결로 격리한다.
2. **이름을 믿지 말고 숫자를 믿어라.** 매핑은 이합 보존(값)으로 판정한다.
   이름 유사도는 보조 신호일 뿐 주 근거가 아니다.
3. **전략을 지어내지 않는다.** 정답은 재분류표/이합 계산에서만. 없으면 미해결로 남긴다.
4. **채점 없는 기능 추가 금지.** 새 능력에는 반드시 테스트(`tests/`) 또는 채점(`eval/`)을 붙인다.
5. **API 확장은 소량 먼저.** 실제 DART/LLM을 쓰는 변경은 회사 1개·연도 1개로 먼저 돌려
   토큰·정확도를 확인하고, 대량 배치는 그 다음. 결과를 로그로 남긴다.
6. **evidence_lens 를 수정하지 않는다.** 원본은 `z.MINE/project/evidence_lens` 에 그대로 둔다.
   재사용은 이 프로젝트로 **포팅**해서 한다 (이미 `dart/dart_tools.py`, `schemas/claim.py` 복사됨).

## 작업 루프 규율 (Loop Engineering)

한 루프 = (1) 좁은 산출물 하나, (2) 검증 포함, (3) 커밋. `docs/03_roadmap.md`의 Loop 순서:

- **Loop 1 (다음):** `extract/segment_extractor.py` 를 실제 DART로 구동.
  `run_v1.py --company 네이버 --years 2024` 한 해로 먼저. 추출된 SegmentRow 를 원문과
  샘플 대조(추출 정확도). 사람에게 체크인 후 다개년으로 확장.
- **Loop 2:** `reconcile/restatement.py` — 재작성(신구조) 표 파싱 → `restatement_pairs`
  + 회사별 gold 자동 생성.
- **Loop 3:** 회사 배치 → 매핑 Precision/Recall 표 (`eval/output/`).
- **Loop 4:** v2 변화점→공시 매칭.

## 검증 명령 (커밋 전 필수)

```bash
cd PROJECTS/ai_consultant
../../.venv/bin/python tests/test_matcher.py   # 매칭·정합 회귀 (API 불필요)
../../.venv/bin/python eval/run_eval.py         # 합성 gold 채점
../../.venv/bin/python scripts/run_v1.py --demo # end-to-end 오프라인
```

세 개가 통과하지 않으면 커밋하지 않는다.

## 커밋 규약

- 한 루프 = 한 커밋. 메시지는 한국어, `feat/fix/docs/test/chore:` 접두.
- 커밋 본문에 무엇을 검증했는지(테스트/채점 결과) 한 줄 남긴다.
- 사람이 명시적으로 요청할 때만 push. 지금은 로컬 커밋만.

## 현재 상태

- v1 정합 엔진(matcher/reconciler/xlsx/CLI/eval) 구현·검증 완료 (오프라인, 합성 gold F1=1.0).
- 미배선: 실제 DART 추출(`segment_extractor.py`는 작성됐으나 실 DART로 미검증), restatement 파싱.
- 다음 진입점: **Loop 1**.
