# RUN LOG — demo

## 실행 개요
- **회사**: 한화오션
- **주제**: 2026년 수주잔고 흐름 및 향후 사업 전망
- **corp_code**: 00111704
- **기간**: 20240101~20261231
- **오늘**: 2026-07-13
- **소스**: 75건 (DART 45/News 30)
- **claim**: raw 421 → norm 421 → verified 388/weak 11/unsup 22
- **정합**: timeline 12 · 충돌 10 · 교차노트 6
- **모델**: fast=claude-sonnet-5, smart=claude-opus-4-8
- **뉴스활성**: True

## 단계별 산출물 & 한계

| 단계 | 산출물 | 관찰된 한계 |
|---|---|---|
| Issue Planner | 7개 이슈 트리 + 가설 생성 | MECE는 프롬프트 유도일 뿐 보장되지 않음; 이슈 수는 5~7로 유도 |
| Source Scout | DART 앵커 39개 · 뉴스쿼리 21개 | 도메인 앵커팩을 강제 병합해 리콜 보강; LLM 단독 키워드는 원문 표를 놓칠 수 있음 |
| Source Acquisition (DART 정형+비정형 / News) | 소스 75건 (DART 45 / News 30, 원문파싱 6건), 정형 재무 5계정 | 뉴스 30건 중 24건은 외부매체라 원문파싱 불가→스니펫 사용 |
| Evidence Extractor | 원시 claim 421건 추출 (source_span 필수) | 소스 발췌 밖 내용은 못 봄; 표 셀이 분해돼 숫자-라벨 매칭이 흔들릴 수 있음 |
| Claim Normalizer | 정규화 후 421건 (중복 0 병합) | 중복 판정은 텍스트 유사도 휴리스틱(같은 사실의 다른 표현은 남을 수 있음) |
| Verifier | verified 388 · weak 11 · unsupported 22 | span 실재성은 결정적, 과장/비약 판정은 LLM 의존(경계사례 흔들림 가능) |
| Reconciler | timeline 12 · 충돌 10 · 교차노트 6 | 의미적 그룹핑/충돌은 LLM 판단(임베딩 아님); 근거 시점(as_of)에 의존 |
| Gap Finder | evidence gap 5건 + next check | gap은 확보된 claim 기준 상대적 판단(모르는 미지의 미지는 못 잡음) |
| Synthesis | fact pack 초안(10개 섹션, 시점·소스 정합 포함) 생성 | unsupported 제외 후 종합; verified가 적으면 outlook이 얇아짐 |
| Critic | 지적 9건 + 총평 | 자기비평이라 자체 편향 공유 가능(외부 검토 대체 아님) |
| Report | fact_pack.md / fact_pack.html 렌더 | — |

## 원시 로그
```
[06:51:24] RUN start · 한화오션 · 2026년 수주잔고 흐름 및 향후 사업 전망
[06:52:11] STAGE Issue Planner — 7개 이슈 트리 + 가설 생성 | 한계: MECE는 프롬프트 유도일 뿐 보장되지 않음; 이슈 수는 5~7로 유도
[06:52:21] STAGE Source Scout — DART 앵커 39개 · 뉴스쿼리 21개 | 한계: 도메인 앵커팩을 강제 병합해 리콜 보강; LLM 단독 키워드는 원문 표를 놓칠 수 있음
[06:52:22] DART 원문: 분기보고서 (2026.03) as_of=2026-03-31 (290,128자)
[06:52:22] DART 원문: 사업보고서 (2025.12) as_of=2025-12-31 (855,141자)
[06:52:23] STAGE Source Acquisition (DART 정형+비정형 / News) — 소스 75건 (DART 45 / News 30, 원문파싱 6건), 정형 재무 5계정 | 한계: 뉴스 30건 중 24건은 외부매체라 원문파싱 불가→스니펫 사용
[06:52:33]   extract DART_20260513000552_4: 5 claims
[06:52:37]   extract DART_20260513000552_0: 6 claims
[06:52:39]   extract DART_20260513000552_5: 7 claims
[06:52:39]   extract DART_20260513000552_2: 7 claims
[06:52:40]   extract DART_20260513000552_3: 6 claims
[06:52:40]   extract DART_20260513000552_1: 8 claims
[06:52:49]   extract DART_20260513000552_6: 5 claims
[06:52:51]   extract DART_20260513000552_7: 7 claims
[06:52:52]   extract DART_20260513000552_9: 6 claims
[06:52:52]   extract DART_20260513000552_10: 8 claims
[06:52:56]   extract DART_20260513000552_8: 7 claims
[06:52:58]   extract DART_20260513000552_11: 8 claims
[06:53:03]   extract DART_20260513000552_13: 7 claims
[06:53:04]   extract DART_20260513000552_12: 7 claims
[06:53:07]   extract DART_20260513000552_14: 7 claims
[06:53:11]   extract DART_20260513000552_16: 8 claims
[06:53:11]   extract DART_20260513000552_15: 8 claims
[06:53:14]   extract DART_20260513000552_17: 8 claims
[06:53:16]   extract DART_20260513000552_18: 8 claims
[06:53:19]   extract DART_20260513000552_19: 6 claims
[06:53:22]   extract DART_20260513000552_20: 8 claims
[06:53:23]   extract DART_20260311004557_1: 5 claims
[06:53:25]   extract DART_20260311004557_0: 7 claims
[06:53:28]   extract DART_20260311004557_2: 8 claims
[06:53:32]   extract DART_20260311004557_4: 8 claims
[06:53:33]   extract DART_20260311004557_6: 4 claims
[06:53:35]   extract DART_20260311004557_5: 6 claims
[06:53:38]   extract DART_20260311004557_3: 8 claims
[06:53:42]   extract DART_20260311004557_8: 7 claims
[06:53:44]   extract DART_20260311004557_7: 8 claims
[06:53:48]   extract DART_20260311004557_9: 8 claims
[06:53:49]   extract DART_20260311004557_10: 8 claims
[06:53:54]   extract DART_20260311004557_12: 7 claims
[06:53:55]   extract DART_20260311004557_13: 7 claims
[06:53:56]   extract DART_20260311004557_14: 6 claims
[06:53:58]   extract DART_20260311004557_15: 0 claims
[06:53:59]   extract DART_20260311004557_11: 7 claims
[06:54:06]   extract DART_20260311004557_16: 8 claims
[06:54:08]   extract DART_20260311004557_19: 8 claims
[06:54:10]   extract DART_20260311004557_18: 7 claims
[06:54:10]   extract DART_20260311004557_20: 6 claims
[06:54:11]   extract DART_20260311004557_17: 8 claims
[06:54:13]   extract DART_20260311004557_21: 7 claims
[06:54:18]   extract NEWS_1: 4 claims
[06:54:20]   extract NEWS_0: 3 claims
[06:54:20]   extract DART_20260311004557_22: 8 claims
[06:54:24]   extract DART_SUPPLY: 8 claims
[06:54:24]   extract NEWS_4: 3 claims
[06:54:27]   extract NEWS_5: 2 claims
[06:54:27]   extract NEWS_6: 3 claims
[06:54:32]   extract NEWS_8: 4 claims
[06:54:32]   extract NEWS_7: 5 claims
[06:54:33]   extract NEWS_10: 2 claims
[06:54:34]   extract NEWS_2: 8 claims
[06:54:35]   extract NEWS_9: 3 claims
[06:54:36]   extract NEWS_3: 8 claims
[06:54:36]   extract NEWS_11: 1 claims
[06:54:37]   extract NEWS_13: 2 claims
[06:54:38]   extract NEWS_12: 3 claims
[06:54:39]   extract NEWS_15: 2 claims
[06:54:42]   extract NEWS_18: 1 claims
[06:54:43]   extract NEWS_20: 1 claims
[06:54:43]   extract NEWS_14: 2 claims
[06:54:44]   extract NEWS_19: 2 claims
[06:54:45]   extract NEWS_16: 5 claims
[06:54:48]   extract NEWS_23: 3 claims
[06:54:49]   extract NEWS_17: 8 claims
[06:54:51]   extract NEWS_22: 2 claims
[06:54:51]   extract NEWS_25: 2 claims
[06:54:54]   extract NEWS_26: 2 claims
[06:54:56]   extract NEWS_27: 3 claims
[06:55:00]   extract NEWS_28: 3 claims
[06:55:07]   extract NEWS_21: 8 claims
[06:55:08]   extract NEWS_24: 8 claims
[06:55:12]   extract NEWS_29: 7 claims
[06:55:12] STAGE Evidence Extractor — 원시 claim 421건 추출 (source_span 필수) | 한계: 소스 발췌 밖 내용은 못 봄; 표 셀이 분해돼 숫자-라벨 매칭이 흔들릴 수 있음
[06:55:12] STAGE Claim Normalizer — 정규화 후 421건 (중복 0 병합) | 한계: 중복 판정은 텍스트 유사도 휴리스틱(같은 사실의 다른 표현은 남을 수 있음)
[06:58:15] STAGE Verifier — verified 388 · weak 11 · unsupported 22 | 한계: span 실재성은 결정적, 과장/비약 판정은 LLM 의존(경계사례 흔들림 가능)
[07:xx] STAGE Reconciler — timeline 12 · 충돌 10 · 교차노트 6 (재실행) | 한계: 의미적 그룹핑/충돌은 LLM 판단(임베딩 아님); 근거 시점(as_of)에 의존
[07:xx] STAGE Gap Finder — evidence gap 5건 + next check (재실행) | 한계: gap은 확보된 claim 기준 상대적 판단(모르는 미지의 미지는 못 잡음)
[07:02:11] STAGE Synthesis — fact pack 초안(8개 섹션, 시점·소스 정합 포함) 생성 | 한계: unsupported 제외 후 종합; verified가 적으면 outlook이 얇아짐
[07:02:57] STAGE Critic — 지적 9건 + 총평 | 한계: 자기비평이라 자체 편향 공유 가능(외부 검토 대체 아님)
[07:02:57] STAGE Report — fact_pack.md / fact_pack.html 렌더
```

> 주: 07~10 단계(Reconciler·Gap·Synthesis·Critic)는 Reconciler 토큰상한 상향 수정 후 `scripts/resume_from_verified.py`로 재생성됨(추출·검증 수치는 원 full run 기준).
