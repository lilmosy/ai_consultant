# 02. 측정 — 단일 LLM 대비 무엇이 좋아지나

가이드 §7의 평가 골격을 이 데모에 매핑한다. 현재는 파이프라인이 자체 통계를 남기고,
정식 평가 하니스는 다음 단계(로드맵)에서 붙인다.

## 비교군
- **Baseline A**: LLM에게 바로 "한화오션 수주 전망 조사해줘".
- **Baseline B**: DART/뉴스 문서를 넣고 단일 RAG 요약.
- **Proposed**: 본 멀티에이전트(역할 분리 + 검증 루프).

## 지표
| 지표 | 측정 방법 | 목표 |
|---|---|---|
| Citation Precision | source_span이 claim을 실제로 뒷받침하는 비율 | ≥ 80% |
| Fact Accuracy | 숫자/날짜/계약이 원문과 일치하는지 샘플 검토 | Baseline 대비 오류율↓ |
| Coverage | gold issue list 중 다룬 비율 | 핵심 이슈 ≥ 70% |
| Hallucination Rate | 근거 없는 수치/계약/전망 비율 | Baseline 대비↓ |
| Gap Quality | next check가 실제 추가 리서치에 유용한지 | 평균 4/5 이상 |

## 현재 런에서 자동 집계되는 프록시
`RUN_LOG.md` / `fact_pack.md` 헤더에 매 실행마다:
- `verified / weak / unsupported` claim 수 (Verifier 결과)
- 총 claim 수, 소스 수(DART/News)
- Verifier가 걸러낸 unsupported 수 = **근거 없는 주장 차단량**의 프록시

이 수치들이 Citation Precision·Hallucination Rate의 대리 지표다.
정식 비교(Baseline A/B vs Proposed)는 `eval/`에 하니스로 추가 예정.
