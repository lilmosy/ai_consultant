# 03. 로드맵

## 현재 (v0.1 — 동작 데모)
- [x] DART 정형(주요계정 JSON) + 비정형(사업보고서 원문 발췌) 소스 레이어
- [x] 네이버 뉴스 소스 레이어 (관련성 필터 / 인증 없으면 graceful degrade)
- [x] 8-에이전트 파이프라인 (Planner→…→Critic)
- [x] 중간 산출물 + RUN_LOG(산출물/한계) 기록
- [x] fact_pack.md / fact_pack.html 렌더
- [x] 한화오션 end-to-end 런 성공

## 다음 (Loop 1)
- [ ] `NAVER_CLIENT_SECRET` 확보 → 뉴스 claim 활성화, **공시 vs 뉴스 전망 분리** 데모
- [ ] Gap Finder → Source Scout **재수집 루프** 실제 연결(현재 1-pass)
- [ ] 분기·반기 보고서까지 확장(수주잔고 시계열)

## 그다음 (Loop 2)
- [ ] 경쟁사(HD현대중공업 00164742 / 삼성중공업) 동일 파이프라인 → **경쟁사 비교 fact pack** (가이드 시나리오 3)
- [ ] `eval/` 평가 하니스: Baseline A/B vs Proposed, Citation Precision·Coverage·Hallucination
- [ ] 단일판매·공급계약 원문 상세 파싱(계약금액/상대/기간) → Event claim 강화

## 알려진 기술 한계 (개선 대상)
- 원문 발췌 기반이라 앵커 밖 사실은 미포착 → 전체 문서 청킹/인덱싱 고려.
- 플레인텍스트 표 분해 시 숫자-라벨 매칭 흔들림 → 표 구조 보존 파서 고려.
- Critic이 자기비평(동일 모델) → 이종 모델 교차검증 고려.
