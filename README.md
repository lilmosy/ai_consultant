# Evidence-grounded Multi-agent Research Assistant

컨설팅형 기업 리서치를 위한 **근거 기반 멀티에이전트 리서치 어시스턴트**.
교수님 인턴 프로젝트 가이드(`consulting_research_agent_intern_guide.html`)의 8-에이전트 워크플로우를
DART OpenAPI(정형+비정형)와 네이버 뉴스 API 위에 그대로 구현한 **동작하는 데모**입니다.

> 목표는 "그럴듯한 요약"이 아니라, 시니어가 바로 리뷰할 수 있는 **fact pack** —
> 각 주장(claim)이 출처·근거 문구(source_span)·검증상태를 달고 있는 1차 리서치 산출물.

---

## 무엇을 하나

사용자 요청(회사 + 리서치 주제)을 받아 아래 파이프라인을 실행하고,
`outputs/<run_id>/` 에 **모든 중간 산출물**과 최종 fact pack(md/html)을 남깁니다.

```
User Request
  → Issue Planner       요청을 이슈트리 + 초기 가설로 분해
  → Source Scout        이슈별 DART 앵커 키워드 / 뉴스 검색어 생성 (+ 도메인 앵커팩)
  → Source Acquisition  DART 정형(주요계정 JSON) + 비정형(사업보고서 원문 발췌) + 네이버 뉴스
  → Evidence Extractor  원문에서 검증 가능한 atomic claim 추출 (source_span 필수)
  → Claim Normalizer    enum/필드 표준화 + 중복 병합 (결정적)
  → Verifier            claim이 source_span에 실제로 근거하는지 판정 (span 실재성=결정적 + LLM)
  → Gap Finder          비어있는 근거·비교축 탐지 + next check
  → Synthesis           검증된 근거만으로 fact pack 초안(7섹션)
  → Critic              과장·근거약함·논리비약·누락 자기비평
  → Final Fact Pack     fact_pack.md / fact_pack.html
```

## 데이터 소스

| 소스 | 종류 | 사용 | 엔드포인트 |
|---|---|---|---|
| DART 주요계정 | 정형(JSON) | 신뢰 기준선 재무 (자산/부채/자본/매출/영업이익/순이익) | `fnlttSinglAcnt.json` |
| DART 공시목록 | 정형(JSON) | 사업보고서·단일판매/공급계약 탐지 | `list.json` |
| DART 사업보고서 원문 | 비정형(XML→text) | 수주상황·방산·미국사업·업황 서술의 근거 문단 | `document.xml` (zip) |
| 네이버 뉴스(검색) | 비정형(JSON) | 후보 기사 검색 (관련성 필터 후) | `openapi.naver.com/v1/search/news.json` |
| 네이버 뉴스(원문) | 비정형(HTML→text) | 기사 **본문** 파싱해 claim 근거 확보 | `n.news.naver.com` 기사 페이지 |

- DART 원문은 **utf-8 → cp949 폴백** 디코딩(구형 보고서 대비) 후 태그 제거.
- 원문 발췌는 **숫자 밀도 랭킹**으로 실제 표(수주잔고 등)를 우선 선택.
- 뉴스는 **회사명 필수 + 토픽어 1개 이상** 매칭만 통과(정확도 우선).
- 검색 API는 title+요약 스니펫만 주므로, **네이버 뉴스로 제공된 기사는 원문 페이지를 직접 받아
  본문(`#dic_area` 등)을 파싱**해 근거로 사용한다. 외부 매체(원문 링크)는 구조가 제각각이라
  스니펫으로 안전하게 폴백한다(RUN_LOG에 `원문파싱 N건`으로 집계).

## 실행

```bash
# 1) 의존성
pip install -r requirements.txt

# 2) 키 설정 (.env — 저장소 루트 또는 상위 모노레포 루트)
cp .env.example .env   # DART_API_KEY / ANTHROPIC_API_KEY (필수), NAVER_CLIENT_ID+SECRET (뉴스)

# 3) 데모 실행
python scripts/run_demo.py --company 한화오션 --topic "2025년 수주잔고 및 향후 사업 전망"
```

산출물: `outputs/<회사>_<timestamp>/`
- `00_request.json` … `09_critic.json` — 단계별 중간 산출물
- `fact_pack.md` / `fact_pack.html` — 최종 fact pack
- `RUN_LOG.md` — **각 단계가 무엇을 냈고 어떤 한계가 있었는지** + 원시 로그

## 모델

- 고volume 추출/검증: `claude-sonnet-5`
- 종합/비평: `claude-opus-4-8`
- `AIC_MODEL_FAST` / `AIC_MODEL_SMART` 환경변수로 교체 가능.

## 알려진 한계 (요약)

- **네이버 뉴스**: `X-Naver-Client-Id` + `X-Naver-Client-Secret` **둘 다** 필요하고, 개발자센터에서
  해당 앱에 **검색(Search) API가 활성화**돼 있어야 함(미활성 시 `Scope Status Invalid`). 인증이 안 되면
  뉴스 소스는 0건으로 degrade하고 파이프라인은 DART만으로 완주합니다(RUN_LOG에 명시).
- **뉴스 원문 파싱**: 네이버 뉴스로 제공된 기사만 본문 파싱이 안정적. 외부 매체는 스니펫 폴백이라
  근거 깊이가 얕음. 본문 추출은 휴리스틱(주요 컨테이너 선택)이라 광고/캡션이 섞일 수 있음.
- DART 원문은 **키워드 앵커 주변 발췌**만 사용 → 앵커 밖 사실은 못 봄.
- 표가 플레인텍스트로 분해되면 숫자-라벨 매칭이 흔들릴 수 있음(Verifier가 span 실재성으로 1차 차단).
- Critic은 자기비평이라 자체 편향을 공유할 수 있음(외부 검토 대체 아님).

자세한 배경/설계/측정은 [`docs/`](docs/) 및 [`AGENTS.md`](AGENTS.md) 참고.
