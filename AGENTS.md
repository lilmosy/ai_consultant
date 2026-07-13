# AGENTS.md — 에이전트 위임 계약

이 문서는 각 에이전트의 **역할·입력·출력·불변식(invariant)**을 규정한다.
핵심은 "프레임워크"가 아니라 **역할 분리 + 검증 루프**다. 단일 LLM 요약 대비
근거 정확도/누락률이 개선되는지가 이 구조의 존재 이유다.

## 공통 규약

- 모든 LLM 에이전트는 **JSON만** 반환한다(`ai_consultant/llm.py:call_json`, 파싱 실패 시 재시도).
- claim은 **사용자 질문이 아니라 원문에서 추출된 검증 가능한 최소 단위 주장**이다.
- 근거 문구(`source_span`)가 없으면 claim으로 승격하지 않는다.
- 사실/전망/해석/홍보를 `fact_or_view`로 구분한다.

## 에이전트

| Agent | 파일 | 입력 → 출력 | 모델 | 불변식 |
|---|---|---|---|---|
| Issue Planner | `agents/issue_planner.py` | (회사, 주제) → issue tree + 가설 | smart | 요청 재진술 금지, 5~7 이슈 |
| Source Scout | `agents/source_scout.py` | issues → DART 앵커/뉴스 쿼리 | fast | 도메인 앵커팩 강제 병합 |
| Evidence Extractor | `agents/evidence_extractor.py` | source text → raw claims | fast | source_span 필수, 원문 밖 생성 금지 |
| Claim Normalizer | `agents/claim_normalizer.py` | raw claims → normalized | (없음) | 결정적 enum 매핑 + 중복 병합 |
| Verifier | `agents/verifier.py` | claim + source → verdict | fast | span 실재성 결정적 차단 후 LLM 판정 |
| Reconciler | `agents/reconciler.py` | verified claims → timeline+충돌 | smart | 의미적 그룹핑·시점정렬·충돌표시(근거 숫자만) |
| Gap Finder | `agents/gap_finder.py` | issues + claims → gaps | fast | 확보 claim 기준 상대 판단 |
| Synthesis | `agents/synthesis.py` | verified + timeline + gaps → fact pack | smart | unsupported 제외, claim 밖 수치 금지 |
| Critic | `agents/critic.py` | draft → 지적/개선 | smart | 과장·비약·누락 지적 |

> **Normalizer(결정적) vs Reconciler(LLM)**: Normalizer는 같은 소스의 거의 동일 텍스트만 병합한다.
> 소스·시점이 다른 "같은 사실"의 정합(의미 판단)은 Reconciler가 맡아 시점 timeline을 만들고
> `값충돌`/`시점차이`/`공시vs뉴스` 충돌을 표면화한다.

## 데이터 모델 (`ai_consultant/schemas.py`)

- `Issue`: issue_id, question, hypothesis, sub_questions, source_plan
- `SourceDoc`: source_id, source_type(DART|News|IR…), source_name, source_date, url, text, meta
- `Claim`: claim_type, topic, claim_text, direction, time_horizon, scope,
  source_type/name/date, **source_span**, evidence_strength, fact_or_view,
  verification(verified|weak|unsupported|pending)
- `Gap`: description, why_it_matters, next_check

## 소스 레이어 (`ai_consultant/sources/`)

- `dart.py` — 정형(`key_accounts`), 공시목록(`list_filings`,`latest_business_report`,
  `supply_contracts`), 비정형(`document_text` + `find_passages`). 온디스크 캐시.
- `naver_news.py` — `collect_news`: 쿼리→관련성 필터(회사명+토픽어)→중복제거→**원문 본문 파싱**
  (`fetch_article_body`, 네이버 뉴스 기사만; 외부매체는 스니펫 폴백). 인증 없으면 graceful degrade.

## 오케스트레이션 (`ai_consultant/pipeline.py`)

- 추출/검증은 `ThreadPoolExecutor`로 동시 실행.
- 각 단계는 `RunArtifacts.stage(name, produced, limitations)`로 **산출물+한계**를 RUN_LOG에 축적.
- Gap Finder 이후 "추가 수집 필요 시 Source Scout로 되돌아가는" 루프는 훅만 남겨둠(현재 1-pass).

## 확장 지점 (다음 단계)

1. **뉴스 원문 파싱 확장**: 외부 매체까지 안정적 본문 추출(readability류) → 근거 깊이 향상.
2. **경쟁사 비교**: HD현대중공업/삼성중공업 corp_code로 동일 파이프라인 → 동일 비교축 fact pack.
3. **Gap→Scout 재수집 루프** 실제 연결(현재 1회전).
4. **평가 하니스**: 가이드 §7의 Baseline A/B 대비 Citation Precision·Coverage·Hallucination 측정.
