# 01. 해결 방식 — 역할 분리 + 검증 루프

단일 LLM에게 "조사해줘"라고 시키는 대신, 리서치를 **분해→수집→추출→정규화→검증→갭→종합→비평**의
역할로 나눈다. 프레임워크(LangGraph/CrewAI 등)가 핵심이 아니라 **역할 분리와 검증 루프**가 핵심이다.

## 파이프라인
`pipeline.py`의 `run(RunConfig)`가 8개 에이전트를 소스 레이어와 엮는다.

1. **Issue Planner** (opus) — 요청을 이슈트리+가설로. 조선/방산이면 수주·수익성·방산·미국·업황·리스크 축 강제.
2. **Source Scout** (sonnet) — 이슈별 DART 앵커/뉴스 쿼리 생성 + **도메인 앵커팩** 병합(리콜 보강).
3. **Source Acquisition** — DART 정형(주요계정 JSON) + 비정형(사업보고서 원문 발췌) + 네이버 뉴스.
   - 원문 발췌는 숫자 밀도 랭킹으로 실제 표를 우선.
4. **Evidence Extractor** (sonnet) — 원문에서만 atomic claim 추출, `source_span` 필수.
5. **Claim Normalizer** (결정적) — enum 표준화 + 중복 병합.
6. **Verifier** (sonnet) — `source_span`이 원문에 실재하는지 **결정적 차단** 후, 과장/비약을 LLM 판정.
7. **Reconciler** (opus) — 교차소스 정합: 같은 지표를 **의미적으로 그룹핑**하고 **시점축 timeline**으로 정렬,
   값이 어긋나면 `값충돌`/`시점차이`/`공시vs뉴스`로 표면화. (Normalizer의 결정적 중복제거가 놓치는 부분.)
8. **Gap Finder** (sonnet) — 근거 공백/빈 비교축 + next check.
9. **Synthesis** (opus) — verified/weak + timeline으로 fact pack 10섹션. → **Critic** (opus) 자기비평.

DART는 **가장 최신 정기보고서 2개(예: 사업 2025.12 + 분기 2026.03)** 를 함께 읽어 "지금 흐름"을 본다.

## 왜 이게 나은가 (검증 대상 가설)
- **Citation**: 모든 claim에 source_span → 시니어 재검증 비용↓.
- **Hallucination**: Verifier가 span 실재성으로 근거 없는 수치를 unsupported로 차단.
- **Coverage**: 이슈트리 + 앵커팩으로 핵심 축 누락↓.
- **Usefulness**: 사실/전망 분리 + Gap/Next check로 "다음 액션"이 명확.

정량 측정 방법은 [`02_measurement.md`](02_measurement.md).
