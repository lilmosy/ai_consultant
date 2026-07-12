# 03 · 로드맵 & Loop Engineering

전략 견고성 순서로 쌓는다. 채점이 가장 단단한 코어(이합 보존)를 먼저, 소프트한 확장을 뒤에.
각 버전은 **같은 정합 골격**(추출→매칭→정합→근거결착→측정) 위에서 한 조각씩 깊어진다.

## v1 — 부문 시계열 정합 (현재, 코어) ✅ 엔진 검증됨

- `SegmentRow / SegmentEdge / ReconResult` 스키마
- `matcher.py` 이합 보존 매칭 (identity/rename/merge/split/new/discontinued)
- `reconciler.py` 인접 구조 합성 → 최신 구조 투영
- `xlsx_writer.py` 시계열/매핑이력/근거/미해결 4시트
- `run_v1.py --demo` 오프라인 실행, `run_eval.py` 합성 gold 채점
- **남은 것:** `segment_extractor.py` 실제 DART 배선 검증 (아래 Loop 1).

## v1.1 — 실제 데이터 + 재분류표 정답

- `reconcile/restatement.py`: 사업보고서의 재작성(신구조) 표를 파싱해
  `restatement_pairs` 와 회사별 gold 자동 생성.
- 다중 hop 체이닝(재편 2회 이상) — split 배분 비율 처리 포함.
- 실제 회사 5~10개로 매핑 Precision/Recall 표.

## v2 — 이벤트 축 (변화점 → 공시 매칭)

- 시계열 **변화점**(급증/급감/신설/중단) 자동 감지.
- 그 시점 DART 공시(단일판매·공급계약, 최대주주변경, 합병 등)를 매칭해 "왜"를 근거 결착.
- 상태 승계(supersession): LOI→본계약→취소. **공시가 이벤트 경계를 그어** 모호함 제거.

## v3 — 소스 축 정합 (부문 scope 모듈로 흡수)

- DART ↔ IR ↔ 뉴스 같은 지표를 정합, 기간차/범위차/충돌 판정 (evidence_lens의 `Verdict` 재사용).
- **부문 scope 정합**을 여기 한 모듈로: 부문이 재편되면 소스 간 비교의 scope가 흔들리므로
  v1 정합이 그 전처리가 된다.

## P&C 공고와의 직접 접점 (감사·상시감시)

- **상시감시(ongoing monitoring):** 정합을 주기적으로 재실행 → **바뀐 것만** 노출(델타).
- **내부통제 감사가능성:** 출처 결착 + 재현성 = "이 숫자 어디서 왔나" 답변 가능.
- KYC/KYB/AML은 기술 대응(엔티티 정합)일 뿐 데이터가 없어 **은유로만** — 과장 금지.

## [Scale Automation] Loop Engineering

에이전트에게 위임해 자율 루프로 돌릴 작업 단위 (각각 독립·검증 가능):

- **Loop 1 (다음):** `segment_extractor.py`를 실제 DART로 구동. 네이버 1개년 보고서에서
  부문 표 추출 → SegmentRow 검증 (추출 정확도 샘플 대조). *토큰 소량, 먼저 체크인.*
- **Loop 2:** `restatement.py` 구현 + 회사별 gold 자동 생성.
- **Loop 3:** 회사 배치 실행 → 매핑 Precision/Recall 표 (`eval/output/`에 리포트).
- **Loop 4:** v2 변화점-공시 매칭.

**루프 규율:** 각 루프는 (1) 하나의 좁은 산출물, (2) 검증(테스트/채점) 포함,
(3) 실제 API를 쓰는 확장은 먼저 소량으로 체크인. `AGENTS.md`의 계약을 따른다.
