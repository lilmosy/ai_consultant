"""
ReconResult → 엑셀(.xlsx). 실무 산출물은 요약이 아니라 '정렬된 시계열'이다.

시트
  1. 시계열   : 최신 구조 기준 부문 × 회계연도 매출 (근거 결착된 값)
  2. 매핑이력 : 구부문 → 신부문 edge (유형·이합잔차·신뢰도·밴드)
  3. 근거     : 모든 SegmentRow 원본 (부문·연도·값·출처 span)
  4. 미해결   : 사람이 봐야 할 항목
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from ai_consultant.schemas.segment import ReconResult

_HEAD = Font(bold=True, color="FFFFFF")
_HEAD_FILL = PatternFill("solid", fgColor="17324D")
_REVIEW_FILL = PatternFill("solid", fgColor="FFF7E6")
_ESCALATE_FILL = PatternFill("solid", fgColor="FFF1F0")


def _header(ws, cols):
    for i, c in enumerate(cols, 1):
        cell = ws.cell(1, i, c)
        cell.font = _HEAD
        cell.fill = _HEAD_FILL
        cell.alignment = Alignment(horizontal="center")


def write_xlsx(result: ReconResult, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    # 1) 시계열
    ws = wb.active
    ws.title = "시계열"
    _header(ws, ["부문(최신구조)"] + result.years)
    for seg in result.canonical_segments:
        row = [seg] + [result.series.get(seg, {}).get(y) for y in result.years]
        ws.append(row)

    # 2) 매핑이력
    ws2 = wb.create_sheet("매핑이력")
    _header(ws2, ["구부문", "→", "신부문", "유형", "회계연도",
                  "from합", "to합", "이합잔차", "신뢰도", "밴드", "재분류표근거", "근거"])
    for e in result.edges:
        r = ws2.max_row + 1
        ws2.append([
            " + ".join(e.from_segments) or "—", "→",
            " + ".join(e.to_segments) or "—",
            e.match_type, e.fiscal_year,
            e.from_sum, e.to_sum,
            (f"{e.residual:.4%}" if e.residual is not None else ""),
            e.confidence, e.band,
            "O" if e.restatement_backed else "",
            e.evidence,
        ])
        if e.band == "human_review":
            ws2.cell(r, 10).fill = _REVIEW_FILL
        elif e.band == "escalate":
            ws2.cell(r, 10).fill = _ESCALATE_FILL

    # 3) 근거
    ws3 = wb.create_sheet("근거")
    _header(ws3, ["부문", "회계연도", "보고서연도", "구조", "매출(억원)",
                  "재작성", "출처", "출처위치"])
    for row in result.rows:
        ws3.append([
            row.segment_name, row.fiscal_year, row.report_year, row.structure_id,
            row.revenue, "O" if row.is_restated else "",
            row.source_name, row.source_span,
        ])

    # 4) 미해결
    ws4 = wb.create_sheet("미해결")
    _header(ws4, ["사람이 확인할 항목"])
    for u in (result.unresolved or ["(없음)"]):
        ws4.append([u])

    for w in (ws, ws2, ws3, ws4):
        for col in w.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
            w.column_dimensions[col[0].column_letter].width = min(width + 3, 60)

    wb.save(path)
    return path
