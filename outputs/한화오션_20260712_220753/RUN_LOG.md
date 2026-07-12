# RUN LOG — 한화오션_20260712_220753

## 실행 개요
- **회사**: 한화오션
- **주제**: 2025년 수주잔고 및 향후 사업 전망
- **corp_code**: 00111704
- **기간**: 20230101~20251231
- **재무연도**: 2024
- **소스**: 49건 (DART 19/News 30)
- **claim**: raw 253 → norm 253 → verified 227/weak 8/unsup 18
- **모델**: fast=claude-sonnet-5, smart=claude-opus-4-8
- **뉴스활성**: True

## 단계별 산출물 & 한계

| 단계 | 산출물 | 관찰된 한계 |
|---|---|---|
| Issue Planner | 7개 이슈 트리 + 가설 생성 | MECE는 프롬프트 유도일 뿐 보장되지 않음; 이슈 수는 5~7로 유도 |
| Source Scout | DART 앵커 47개 · 뉴스쿼리 21개 | 도메인 앵커팩을 강제 병합해 리콜 보강; LLM 단독 키워드는 원문 표를 놓칠 수 있음 |
| Source Acquisition (DART 정형+비정형 / News) | 소스 49건 (DART 19 / News 30, 원문파싱 8건), 정형 재무 5계정 | 뉴스 30건 중 22건은 외부매체라 원문파싱 불가→스니펫 사용 |
| Evidence Extractor | 원시 claim 253건 추출 (source_span 필수) | 소스 발췌 밖 내용은 못 봄; 표 셀이 분해돼 숫자-라벨 매칭이 흔들릴 수 있음 |
| Claim Normalizer | 정규화 후 253건 (중복 0 병합) | 중복 판정은 텍스트 유사도 휴리스틱(같은 사실의 다른 표현은 남을 수 있음) |
| Verifier | verified 227 · weak 8 · unsupported 18 | span 실재성은 결정적, 과장/비약 판정은 LLM 의존(경계사례 흔들림 가능) |
| Gap Finder | evidence gap 7건 + next check | gap은 확보된 claim 기준 상대적 판단(모르는 미지의 미지는 못 잡음) |
| Synthesis | fact pack 초안(7개 섹션) 생성 | unsupported 제외 후 종합; verified가 적으면 outlook이 얇아짐 |
| Critic | 지적 9건 + 총평 | 자기비평이라 자체 편향 공유 가능(외부 검토 대체 아님) |
| Report | fact_pack.md / fact_pack.html 렌더 | — |

## 원시 로그
```
[22:07:53] RUN start · 한화오션 · 2025년 수주잔고 및 향후 사업 전망
[22:08:27] STAGE Issue Planner — 7개 이슈 트리 + 가설 생성 | 한계: MECE는 프롬프트 유도일 뿐 보장되지 않음; 이슈 수는 5~7로 유도
[22:08:36] STAGE Source Scout — DART 앵커 47개 · 뉴스쿼리 21개 | 한계: 도메인 앵커팩을 강제 병합해 리콜 보강; LLM 단독 키워드는 원문 표를 놓칠 수 있음
[22:08:37] DART 원문 확보: [기재정정]사업보고서 (2024.12) (636,530자)
[22:08:38] STAGE Source Acquisition (DART 정형+비정형 / News) — 소스 49건 (DART 19 / News 30, 원문파싱 8건), 정형 재무 5계정 | 한계: 뉴스 30건 중 22건은 외부매체라 원문파싱 불가→스니펫 사용
[22:08:49]   extract DART_20250314001630_5: 5 claims
[22:08:50]   extract DART_20250314001630_2: 6 claims
[22:08:52]   extract DART_20250314001630_0: 8 claims
[22:08:52]   extract DART_20250314001630_7: 0 claims
[22:08:53]   extract DART_20250314001630_3: 7 claims
[22:08:53]   extract DART_20250314001630_1: 8 claims
[22:08:53]   extract DART_20250314001630_4: 8 claims
[22:09:04]   extract DART_20250314001630_6: 8 claims
[22:09:04]   extract DART_20250314001630_12: 6 claims
[22:09:07]   extract DART_20250314001630_10: 8 claims
[22:09:09]   extract DART_20250314001630_8: 8 claims
[22:09:09]   extract DART_20250314001630_9: 8 claims
[22:09:14]   extract DART_20250314001630_11: 7 claims
[22:09:18]   extract DART_20250314001630_13: 7 claims
[22:09:20]   extract DART_20250314001630_16: 7 claims
[22:09:22]   extract DART_20250314001630_14: 8 claims
[22:09:23]   extract NEWS_0: 2 claims
[22:09:23]   extract DART_20250314001630_15: 8 claims
[22:09:24]   extract NEWS_1: 2 claims
[22:09:25]   extract DART_20250314001630_17: 6 claims
[22:09:27]   extract NEWS_3: 2 claims
[22:09:29]   extract NEWS_4: 2 claims
[22:09:29]   extract DART_SUPPLY_20250314001630: 8 claims
[22:09:30]   extract NEWS_2: 6 claims
[22:09:31]   extract NEWS_5: 3 claims
[22:09:32]   extract NEWS_6: 4 claims
[22:09:35]   extract NEWS_9: 2 claims
[22:09:38]   extract NEWS_7: 4 claims
[22:09:39]   extract NEWS_12: 4 claims
[22:09:44]   extract NEWS_10: 7 claims
[22:09:47]   extract NEWS_14: 5 claims
[22:09:47]   extract NEWS_11: 8 claims
[22:09:50]   extract NEWS_13: 6 claims
[22:09:51]   extract NEWS_16: 3 claims
[22:09:52]   extract NEWS_8: 8 claims
[22:09:55]   extract NEWS_20: 1 claims
[22:09:57]   extract NEWS_15: 8 claims
[22:09:59]   extract NEWS_19: 2 claims
[22:10:00]   extract NEWS_21: 4 claims
[22:10:02]   extract NEWS_23: 2 claims
[22:10:04]   extract NEWS_18: 7 claims
[22:10:05]   extract NEWS_24: 2 claims
[22:10:07]   extract NEWS_17: 8 claims
[22:10:07]   extract NEWS_26: 2 claims
[22:10:09]   extract NEWS_25: 3 claims
[22:10:11]   extract NEWS_27: 3 claims
[22:10:11]   extract NEWS_28: 2 claims
[22:10:11]   extract NEWS_29: 2 claims
[22:10:12]   extract NEWS_22: 8 claims
[22:10:12] STAGE Evidence Extractor — 원시 claim 253건 추출 (source_span 필수) | 한계: 소스 발췌 밖 내용은 못 봄; 표 셀이 분해돼 숫자-라벨 매칭이 흔들릴 수 있음
[22:10:12] STAGE Claim Normalizer — 정규화 후 253건 (중복 0 병합) | 한계: 중복 판정은 텍스트 유사도 휴리스틱(같은 사실의 다른 표현은 남을 수 있음)
[22:11:44] STAGE Verifier — verified 227 · weak 8 · unsupported 18 | 한계: span 실재성은 결정적, 과장/비약 판정은 LLM 의존(경계사례 흔들림 가능)
[22:12:18] STAGE Gap Finder — evidence gap 7건 + next check | 한계: gap은 확보된 claim 기준 상대적 판단(모르는 미지의 미지는 못 잡음)
[22:13:35] STAGE Synthesis — fact pack 초안(7개 섹션) 생성 | 한계: unsupported 제외 후 종합; verified가 적으면 outlook이 얇아짐
[22:14:19] STAGE Critic — 지적 9건 + 총평 | 한계: 자기비평이라 자체 편향 공유 가능(외부 검토 대체 아님)
[22:14:19] STAGE Report — fact_pack.md / fact_pack.html 렌더
```