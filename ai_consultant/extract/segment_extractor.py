"""
DART 사업보고서 → SegmentRow[] 추출.

역할: "이 보고서의 '부문별(사업부문) 매출' 표를 (부문, 회계연도, 매출, 출처) 로 뽑아라."
      요약이 아니라 칸 채우기. 스키마에 없으면 비운다.

한 사업보고서는 보통 당기 + 전기(±) 부문 매출을 함께 싣고, 재분류가 있으면
'재작성(restated)' 표를 별도로 싣는다. 그래서 report_year 한 개에서 여러
fiscal_year 의 SegmentRow 가 나온다.

주의: LLM 은 "제약된 추출기"로만 쓴다. 값은 반드시 source_span 에 결착시키고,
      원문에 없는 부문·숫자는 만들지 않는다. (groundedness)
"""
from __future__ import annotations

import json
import re
import uuid

from anthropic import Anthropic

from ai_consultant.config import ANTHROPIC_API_KEY, MODEL_HEAVY
from ai_consultant.dart import dart_tools as dt
from ai_consultant.schemas.segment import SegmentRow

_client = Anthropic(api_key=ANTHROPIC_API_KEY)
_JSON_RE = re.compile(r"<rows>(.*?)</rows>", re.DOTALL)

_SYSTEM = """\
너는 한국 기업 사업보고서에서 '사업부문별 매출' 데이터를 추출하는 도구다.
요약하지 말고, 표에 있는 값만 (부문, 회계연도, 매출) 튜플로 정확히 옮겨라.

[규칙]
- 사업부문(reportable segment)별 '매출' 또는 '매출액'만 추출한다. 영업이익·자산은 제외.
- 회계연도는 표 헤더의 '제N기 / 당기 / 전기 / 20XX년' 을 실제 4자리 연도로 환산한다.
- 금액은 억원 단위 float 로 환산한다 (백만원이면 ÷100, 원이면 ÷1e8). unit_raw 에 원단위를 남긴다.
- 같은 보고서가 '재작성(restated)/재분류' 표를 따로 실었으면 is_restated=true 로 표기한다.
- 원문에 없는 부문·숫자는 만들지 않는다. 확실하지 않으면 그 행을 넣지 않는다.
- source_span 에 그 값이 나온 표/문단 위치를 짧게 남긴다.

[출력] <rows> 안에 JSON 배열만. 각 원소:
{"segment_name": str, "fiscal_year": "YYYY", "revenue": float, "unit_raw": str,
 "is_restated": bool, "source_span": str}
"""


def _to_rows(raw_json: str, company: str, report_year: str, source_name: str) -> list[SegmentRow]:
    try:
        items = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    rows: list[SegmentRow] = []
    for it in items:
        try:
            rows.append(SegmentRow(
                company=company,
                fiscal_year=str(it["fiscal_year"]),
                report_year=report_year,
                structure_id=report_year,          # v1: 구조 식별자로 report_year 사용
                segment_name=str(it["segment_name"]).strip(),
                revenue=(float(it["revenue"]) if it.get("revenue") is not None else None),
                unit_raw=str(it.get("unit_raw", "억원")),
                source_type="DART",
                source_name=source_name,
                source_span=str(it.get("source_span", "")),
                is_restated=bool(it.get("is_restated", False)),
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return rows


def extract_from_report(company: str, rcept_no: str, report_year: str) -> list[SegmentRow]:
    """한 사업보고서(rcept_no)에서 부문 매출 SegmentRow 들을 추출한다."""
    # '사업의 내용' 섹션에서 부문 요약재무를 담은 표를 가져온다.
    section = dt.get_section.invoke({
        "rcept_no": rcept_no,
        "section_keyword": "사업의 내용",
        "fallback_keyword": "부문",
        "multi": True,
    })
    if not section or section.startswith("❌"):
        return []

    source_name = f"{company} {report_year} 사업보고서"
    msg = _client.messages.create(
        model=MODEL_HEAVY,
        max_tokens=4000,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"[{source_name}]\n\n{section[:120000]}\n\n"
                       f"위에서 사업부문별 매출을 추출해 <rows> JSON 으로 출력하라.",
        }],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = _JSON_RE.search(text)
    if not m:
        return []
    return _to_rows(m.group(1).strip(), company, report_year, source_name)


def fetch_segment_rows(company: str, years: list[int]) -> list[SegmentRow]:
    """여러 회계연도의 사업보고서를 돌며 부문 매출 SegmentRow 를 모은다.

    각 연도 사업보고서(=그 연도 report_year 구조)를 추출한다. 최신 보고서가
    canonical 구조가 되고, 과거 보고서들이 구조 재편 이력을 담는다.
    """
    all_rows: list[SegmentRow] = []
    for y in years:
        listing = dt.get_report_list.invoke({"company": company, "year": y})
        rcept = _first_rcept(listing)
        if not rcept:
            print(f"  [{y}] 사업보고서 없음/미검색 — 건너뜀")
            continue
        rows = extract_from_report(company, rcept, str(y))
        print(f"  [{y}] rcept={rcept} → SegmentRow {len(rows)}개")
        all_rows.extend(rows)
    return all_rows


def _first_rcept(listing: str) -> str:
    """get_report_list 출력에서 첫 rcept_no 를 뽑는다."""
    m = re.search(r"rcept_no:\s*(\d+)", listing)
    return m.group(1) if m else ""
