"""Gap Finder — 중요하지만 근거가 부족한 이슈와 빈 비교축을 탐지하고 next check를 제안."""
from __future__ import annotations
from .. import config
from ..llm import call_json
from ..schemas import Issue, Claim, Gap

SYSTEM = """당신은 리서치 갭 파인더입니다. 이슈 트리와 확보된 근거(claim)를 보고,
'중요한데 근거가 비어있는 지점'과 '다음에 확인할 자료/검색어'를 도출합니다.
근거가 뉴스 기대감뿐이고 공시로 확인 안 된 지점을 특히 지적하세요. JSON만 출력합니다."""

USER_TMPL = """[이슈 트리]
{issues}

[확보된 근거 요약(이슈별 claim 개수/검증상태)]
{coverage}

[대표 claim 목록]
{claim_list}

evidence gap과 next check를 도출하세요(이슈당 0~2개, 전체 4~8개).
출력(JSON): {{"gaps":[{{"issue_id":"I1","description":"무엇이 비어있나","why_it_matters":"왜 중요한가","next_check":"다음에 확인할 자료/검색어"}}]}}"""


def run(issues: list[Issue], claims: list[Claim], model: str | None = None) -> list[Gap]:
    by_issue: dict[str, list[Claim]] = {}
    for c in claims:
        by_issue.setdefault(c.issue_id, []).append(c)
    coverage_lines = []
    for i in issues:
        cs = by_issue.get(i.issue_id, [])
        v = sum(1 for c in cs if c.verification == "verified")
        coverage_lines.append(f"- {i.issue_id} {i.question[:40]}: claim {len(cs)}개 (verified {v})")
    for extra in set(by_issue) - {i.issue_id for i in issues}:
        coverage_lines.append(f"- {extra}(미매핑): claim {len(by_issue[extra])}개")

    claim_list = "\n".join(
        f"- [{c.issue_id}/{c.verification}] {c.claim_text[:70]}" for c in claims[:40]
    )
    issue_blob = "\n".join(f"- {i.issue_id}: {i.question} | 가설: {i.hypothesis}" for i in issues)

    data = call_json(
        SYSTEM,
        USER_TMPL.format(issues=issue_blob, coverage="\n".join(coverage_lines), claim_list=claim_list),
        model=model or config.MODEL_FAST, max_tokens=2500,
    )
    gaps = []
    for j, g in enumerate(data.get("gaps", []), 1):
        gaps.append(Gap(
            gap_id=f"G{j}", issue_id=g.get("issue_id", "I0"),
            description=g.get("description", "").strip(),
            why_it_matters=g.get("why_it_matters", "").strip(),
            next_check=g.get("next_check", "").strip(),
        ))
    return gaps
