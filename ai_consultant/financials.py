"""정형 재무(DART fnlttSinglAcnt 주요계정)를 fact pack용 마크다운/구조로 정리.

이 숫자들은 LLM을 거치지 않은 '원천 정형 데이터'이므로 fact pack에서 신뢰 기준선 역할을 한다."""
from __future__ import annotations

# 우선 노출할 핵심 계정 (연결 우선)
_PRIORITY = ["자산총계", "부채총계", "자본총계", "매출액", "영업이익", "당기순이익"]


def _fmt_won(amount: str) -> str:
    try:
        n = int(str(amount).replace(",", ""))
    except Exception:
        return amount
    trillion = n / 1_000_000_000_000
    if abs(trillion) >= 1:
        return f"{n:,} 원 (≈ {trillion:.2f}조)"
    return f"{n:,} 원"


def summarize(rows: list[dict]) -> tuple[str, list[dict]]:
    """returns (markdown_table, structured_rows). 연결재무제표 우선."""
    if not rows:
        return "(정형 재무 없음)", []
    consolidated = [r for r in rows if r.get("fs_div") == "CFS" or r.get("fs_nm", "").startswith("연결")]
    use = consolidated or rows

    picked: list[dict] = []
    seen = set()
    for name in _PRIORITY:
        for r in use:
            if r.get("account_nm") == name and name not in seen:
                picked.append(r)
                seen.add(name)
                break
    # any remaining income-statement-ish not captured
    for r in use:
        nm = r.get("account_nm", "")
        if nm not in seen and nm in ("매출총이익",):
            picked.append(r); seen.add(nm)

    lines = ["| 계정 | 당기 | 전기 |", "|---|---|---|"]
    struct = []
    for r in picked:
        nm = r.get("account_nm", "")
        cur = r.get("thstrm_amount", "")
        prev = r.get("frmtrm_amount", "")
        lines.append(f"| {nm} | {_fmt_won(cur)} | {_fmt_won(prev)} |")
        struct.append({"account": nm, "current": cur, "previous": prev,
                       "fs": r.get("fs_nm", "")})
    return "\n".join(lines), struct
