"""Issue Planner — 사용자 리서치 요청을 컨설팅 이슈트리 + 초기 가설 + 소스 플랜으로 분해."""
from __future__ import annotations
from .. import config
from ..llm import call_json
from ..schemas import Issue

SYSTEM = """당신은 전략컨설팅의 리서치 리드입니다.
주니어의 리서치 요청을 '이슈 트리'로 분해합니다. 요청 자체를 결론으로 만들지 말고,
검증해야 할 핵심 질문과 초기 가설로 바꾸세요. 각 이슈는 서로 겹치지 않고(MECE 지향)
근거로 검증 가능한 형태여야 합니다. 반드시 JSON만 출력합니다."""

USER_TMPL = """[회사] {company}
[리서치 주제] {topic}
[산출물] 주니어가 바로 리뷰할 수 있는 1차 fact pack

이 요청을 5~7개의 핵심 이슈로 분해하세요. 각 이슈에 대해:
- question: 검증 대상 핵심 질문 (요청 재진술 금지)
- hypothesis: 현 시점 초기 가설 (근거로 반증 가능해야 함)
- sub_questions: 하위 확인 질문 2~4개
- source_plan: 어떤 소스를 볼지 (["DART 사업보고서","DART 단일판매공급계약","뉴스"] 중에서, 필요시 구체화)

조선/방산 도메인이면 최소한 다음 축을 포함하세요:
수주(신규·잔고), 제품믹스/수익성, 방산·특수선, 미국 사업(필리조선소/미해군 MRO),
시장·업황 전망, 리스크.

출력 형식(JSON):
{{"issues":[{{"issue_id":"I1","question":"...","hypothesis":"...","sub_questions":["..."],"source_plan":["..."]}}]}}"""


def run(company: str, topic: str, model: str | None = None) -> list[Issue]:
    data = call_json(SYSTEM, USER_TMPL.format(company=company, topic=topic),
                     model=model or config.MODEL_SMART, max_tokens=3000)
    issues = []
    for i, it in enumerate(data.get("issues", []), 1):
        issues.append(Issue(
            issue_id=it.get("issue_id") or f"I{i}",
            question=it.get("question", "").strip(),
            hypothesis=it.get("hypothesis", "").strip(),
            sub_questions=[s for s in it.get("sub_questions", []) if s],
            source_plan=[s for s in it.get("source_plan", []) if s],
        ))
    return issues
