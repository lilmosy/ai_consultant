# RUN LOG — 한화오션_20260712_213607

## 실행 개요
- **회사**: 한화오션
- **주제**: 2025년 수주잔고 및 향후 사업 전망
- **corp_code**: 00111704
- **기간**: 20230101~20251231
- **재무연도**: 2024
- **소스**: 20건 (DART 20/News 0)
- **claim**: raw 130 → norm 129 → verified 111/weak 6/unsup 12
- **모델**: fast=claude-sonnet-5, smart=claude-opus-4-8
- **뉴스활성**: False

## 단계별 산출물 & 한계

| 단계 | 산출물 | 관찰된 한계 |
|---|---|---|
| Issue Planner | 7개 이슈 트리 + 가설 생성 | MECE는 프롬프트 유도일 뿐 보장되지 않음; 이슈 수는 5~7로 유도 |
| Source Scout | DART 앵커 46개 · 뉴스쿼리 21개 | 도메인 앵커팩을 강제 병합해 리콜 보강; LLM 단독 키워드는 원문 표를 놓칠 수 있음 |
| Source Acquisition (DART 정형+비정형 / News) | 소스 20건 (DART 20 / News 0), 정형 재무 5계정 | 네이버 뉴스 인증정보(CLIENT_SECRET) 없음 → 뉴스 소스 0건 |
| Evidence Extractor | 원시 claim 130건 추출 (source_span 필수) | 소스 발췌 밖 내용은 못 봄; 표 셀이 분해돼 숫자-라벨 매칭이 흔들릴 수 있음 |
| Claim Normalizer | 정규화 후 129건 (중복 1 병합) | 중복 판정은 텍스트 유사도 휴리스틱(같은 사실의 다른 표현은 남을 수 있음) |
| Verifier | verified 111 · weak 6 · unsupported 12 | span 실재성은 결정적, 과장/비약 판정은 LLM 의존(경계사례 흔들림 가능) |
| Gap Finder | evidence gap 7건 + next check | gap은 확보된 claim 기준 상대적 판단(모르는 미지의 미지는 못 잡음) |
| Synthesis | fact pack 초안(7개 섹션) 생성 | unsupported 제외 후 종합; verified가 적으면 outlook이 얇아짐 |
| Critic | 지적 0건 + 총평 | 자기비평이라 자체 편향 공유 가능(외부 검토 대체 아님) |
| Report | fact_pack.md / fact_pack.html 렌더 | — |

## 원시 로그
```
[21:36:07] RUN start · 한화오션 · 2025년 수주잔고 및 향후 사업 전망
[21:36:42] STAGE Issue Planner — 7개 이슈 트리 + 가설 생성 | 한계: MECE는 프롬프트 유도일 뿐 보장되지 않음; 이슈 수는 5~7로 유도
[21:36:53] STAGE Source Scout — DART 앵커 46개 · 뉴스쿼리 21개 | 한계: 도메인 앵커팩을 강제 병합해 리콜 보강; LLM 단독 키워드는 원문 표를 놓칠 수 있음
[21:36:54] DART 원문 확보: [기재정정]사업보고서 (2024.12) (636,530자)
[21:36:54] STAGE Source Acquisition (DART 정형+비정형 / News) — 소스 20건 (DART 20 / News 0), 정형 재무 5계정 | 한계: 네이버 뉴스 인증정보(CLIENT_SECRET) 없음 → 뉴스 소스 0건
[21:37:06]   extract DART_20250314001630_5: 6 claims
[21:37:07]   extract DART_20250314001630_0: 8 claims
[21:37:08]   extract DART_20250314001630_1: 8 claims
[21:37:08]   extract DART_20250314001630_7: 0 claims
[21:37:09]   extract DART_20250314001630_2: 8 claims
[21:37:12]   extract DART_20250314001630_4: 8 claims
[21:37:12]   extract DART_20250314001630_3: 8 claims
[21:37:19]   extract DART_20250314001630_6: 7 claims
[21:37:20]   extract DART_20250314001630_9: 8 claims
[21:37:23]   extract DART_20250314001630_10: 8 claims
[21:37:25]   extract DART_20250314001630_12: 8 claims
[21:37:26]   extract DART_20250314001630_8: 8 claims
[21:37:29]   extract DART_20250314001630_11: 7 claims
[21:37:30]   extract DART_20250314001630_17: 0 claims
[21:37:33]   extract DART_20250314001630_13: 6 claims
[21:37:33]   extract DART_20250314001630_14: 6 claims
[21:37:40]   extract DART_20250314001630_16: 8 claims
[21:37:42]   extract DART_20250314001630_15: 8 claims
[21:37:45]   extract DART_20250314001630_18: 8 claims
[21:37:45]   extract DART_SUPPLY_20250314001630: 2 claims
[21:37:45] STAGE Evidence Extractor — 원시 claim 130건 추출 (source_span 필수) | 한계: 소스 발췌 밖 내용은 못 봄; 표 셀이 분해돼 숫자-라벨 매칭이 흔들릴 수 있음
[21:37:45] STAGE Claim Normalizer — 정규화 후 129건 (중복 1 병합) | 한계: 중복 판정은 텍스트 유사도 휴리스틱(같은 사실의 다른 표현은 남을 수 있음)
[21:38:58] STAGE Verifier — verified 111 · weak 6 · unsupported 12 | 한계: span 실재성은 결정적, 과장/비약 판정은 LLM 의존(경계사례 흔들림 가능)
[21:39:30] STAGE Gap Finder — evidence gap 7건 + next check | 한계: gap은 확보된 claim 기준 상대적 판단(모르는 미지의 미지는 못 잡음)
[21:40:56] STAGE Synthesis — fact pack 초안(7개 섹션) 생성 | 한계: unsupported 제외 후 종합; verified가 적으면 outlook이 얇아짐
[21:41:42] STAGE Critic — 지적 0건 + 총평 | 한계: 자기비평이라 자체 편향 공유 가능(외부 검토 대체 아님)
[21:41:42] STAGE Report — fact_pack.md / fact_pack.html 렌더
```