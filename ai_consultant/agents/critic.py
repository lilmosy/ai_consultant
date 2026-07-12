"""Critic Agent — fact pack 초안의 과장/근거 약함/논리 비약/누락 경쟁사 비교를 지적."""
from __future__ import annotations
from .. import config
from ..llm import call_json

SYSTEM = """당신은 리서치 크리틱입니다. fact pack 초안을 읽고 다음을 지적합니다:
- 과장/단정 (근거 대비 강한 표현)
- 근거 약함 (source_span 없이 서술된 수치·결론)
- 사실과 전망의 혼동
- 논리 비약
- 누락된 비교축(경쟁사/기간)
개선 코멘트를 구체적으로. JSON만 출력합니다."""

USER_TMPL = """[fact pack 초안(마크다운 종합)]
{draft}

[검증 상태 요약] verified={n_ver}, weak={n_weak}, unsupported(제외됨)={n_unsup}

지적사항과 개선안을 도출하세요.
출력(JSON): {{"issues_found":[{{"where":"섹션","problem":"문제","fix":"개선안","severity":"high|medium|low"}}],
"overall_note":"한 문단 총평"}}"""


def run(draft_md: str, n_ver: int, n_weak: int, n_unsup: int, model: str | None = None) -> dict:
    data = call_json(
        SYSTEM,
        USER_TMPL.format(draft=draft_md[:12000], n_ver=n_ver, n_weak=n_weak, n_unsup=n_unsup),
        model=model or config.MODEL_SMART, max_tokens=2500,
    )
    # 모델이 배열만 반환하거나 다른 키(claims/issues/findings)로 반환하는 경우를 정규화
    if isinstance(data, list):
        data = {"issues_found": data, "overall_note": ""}
    elif not isinstance(data, dict):
        data = {"issues_found": [], "overall_note": str(data)}
    if not data.get("issues_found"):
        for alt in ("claims", "issues", "findings", "items"):
            if isinstance(data.get(alt), list) and data[alt]:
                data["issues_found"] = data[alt]
                break
    data.setdefault("issues_found", [])
    data.setdefault("overall_note", "")
    if not isinstance(data["issues_found"], list):
        data["issues_found"] = []
    return data
