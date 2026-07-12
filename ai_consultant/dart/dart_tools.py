"""
DART OpenAPI 도구 — Evidence Lens 독립 모듈.

기존 end_to_end/react_agent/tools.py의 로직을 그대로 포함.
외부 프로젝트 의존 없이 단독으로 동작한다.

포함된 도구: get_report_list, get_toc, get_section, get_financials, finish
"""

import io
import os
import re
import zipfile
from datetime import date
from functools import lru_cache

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv(override=True)
DART_KEY = os.getenv("DART_API_KEY", "")


# ── 기업코드 ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_corp_codes() -> list[dict]:
    from bs4 import BeautifulSoup
    r = requests.get(
        "https://opendart.fss.or.kr/api/corpCode.xml",
        params={"crtfc_key": DART_KEY}, timeout=30,
    )
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        soup = BeautifulSoup(z.read("CORPCODE.xml"), "xml")
    return [
        {
            "corp_name":  c.find("corp_name").text.strip(),
            "corp_code":  c.find("corp_code").text.strip(),
            "stock_code": c.find("stock_code").text.strip(),
        }
        for c in soup.find_all("list")
        if c.find("stock_code").text.strip()
    ]


def _find_corp(name: str) -> dict | None:
    corps = _load_corp_codes()
    hits  = [c for c in corps if name in c["corp_name"]]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        exact = [c for c in hits if c["corp_name"] == name]
        return exact[0] if len(exact) == 1 else hits[0]
    return None


# ── 보고서 목록 ────────────────────────────────────────────────────────────

def _fetch_report_list(corp_code: str, year: int) -> list[dict]:
    r = requests.get(
        "https://opendart.fss.or.kr/api/list.json",
        params={
            "crtfc_key":  DART_KEY,
            "corp_code":  corp_code,
            "pblntf_ty":  "A",
            "bgn_de":     f"{year}0101",
            "end_de":     f"{year + 1}1231",
            "page_count": 20,
        },
        timeout=30,
    ).json()
    if r.get("status") not in ("000", "013"):
        return []
    return [
        {
            "rcept_no":   x["rcept_no"],
            "report_nm":  x["report_nm"],
            "rcept_dt":   x["rcept_dt"],
            "is_revised": "정정" in x.get("rm", ""),
        }
        for x in r.get("list", [])
        if "사업보고서" in x.get("report_nm", "") and str(year) in x.get("report_nm", "")
    ]


# ── XML 파싱 ───────────────────────────────────────────────────────────────

_XML_CACHE: dict[str, tuple[str, list[dict]]] = {}

_TITLE_RE  = re.compile(r'<TITLE\b([^>]*)>(.*?)</TITLE>', re.DOTALL)
_ATOC_RE   = re.compile(r'\bATOC="Y"')
_ATOCID_RE = re.compile(r'\bATOCID="(\d+)"')
_ROMAN_RE  = re.compile(r"^[IVX]+\.")
_NUM_RE    = re.compile(r"^(\d+)\.")


def _clean(s: str) -> str:
    s = (s or "").replace("　", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def _fetch_and_parse_xml(rcept_no: str) -> tuple[str, list[dict]]:
    if rcept_no in _XML_CACHE:
        return _XML_CACHE[rcept_no]

    r = requests.get(
        "https://opendart.fss.or.kr/api/document.xml",
        params={"crtfc_key": DART_KEY, "rcept_no": rcept_no},
        timeout=60,
    )
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        xml_names = [f for f in z.namelist() if f.endswith(".xml")]
        if not xml_names:
            raise ValueError("ZIP 안에 XML 파일 없음")
        main_name = max(xml_names, key=lambda f: z.getinfo(f).file_size)
        xml_bytes = z.read(main_name)

    xml_str  = xml_bytes.decode("utf-8", errors="replace")
    sections = []
    for m in _TITLE_RE.finditer(xml_str):
        attrs = m.group(1)
        if not _ATOC_RE.search(attrs):
            continue
        atocid_m = _ATOCID_RE.search(attrs)
        if not atocid_m:
            continue
        sections.append({
            "atocid": atocid_m.group(1),
            "title":  _clean(m.group(2)),
            "pos":    m.start(),
        })

    _XML_CACHE[rcept_no] = (xml_str, sections)
    return xml_str, sections


def _find_next_atocid(sections: list[dict], idx: int) -> str | None:
    if idx is None or idx + 1 >= len(sections):
        return None
    title = sections[idx]["title"]

    if _ROMAN_RE.match(title):
        for i in range(idx + 1, len(sections)):
            if _ROMAN_RE.match(sections[i]["title"]):
                return sections[i]["atocid"]
        return None

    m = _NUM_RE.match(title)
    if m and "주석" in title:
        current_num = int(m.group(1))
        for i in range(idx + 1, len(sections)):
            m2 = _NUM_RE.match(sections[i]["title"])
            if m2 and int(m2.group(1)) > current_num and "(연결)" not in sections[i]["title"]:
                return sections[i]["atocid"]
        return None

    return sections[idx + 1]["atocid"]


def _find_atocids(
    sections: list[dict],
    keywords: list[str],
    fallback_keywords: list[str],
    multi: bool = False,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    for kw in keywords:
        for s in sections:
            if kw in s["title"] and s["atocid"] not in seen:
                results.append((s["atocid"], s["title"]))
                seen.add(s["atocid"])
                if not multi:
                    return results

    if not results:
        for fb in fallback_keywords:
            for s in sections:
                if fb in s["title"] and s["atocid"] not in seen:
                    results.append((s["atocid"], s["title"]))
                    seen.add(s["atocid"])
                    break

    return results


def _extract_section_text(
    xml_str: str,
    sections: list[dict],
    keywords: list[str],
    fallback_keywords: list[str] | None = None,
    multi: bool = False,
) -> tuple[str, str]:
    if fallback_keywords is None:
        fallback_keywords = []

    matches = _find_atocids(sections, keywords, fallback_keywords, multi=multi)
    if not matches:
        return "", ""

    all_texts = []
    for atocid, _ in matches:
        idx = next((i for i, s in enumerate(sections) if s["atocid"] == atocid), None)
        if idx is None:
            continue
        next_atocid = _find_next_atocid(sections, idx)

        start_pos = sections[idx]["pos"]
        if next_atocid:
            end_sec = next((s for s in sections if s["atocid"] == next_atocid), None)
            end_pos = end_sec["pos"] if end_sec else len(xml_str)
        else:
            end_pos = len(xml_str)

        raw = xml_str[start_pos:end_pos]
        if raw:
            all_texts.append(raw)

    combined       = "\n\n---\n\n".join(all_texts)
    matched_titles = ", ".join(t for _, t in matches)
    return combined, matched_titles


# ── 재무제표 ───────────────────────────────────────────────────────────────

def _to_int(val: str | None) -> int | None:
    if not val:
        return None
    try:
        return int(val.replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def _fetch_financials_raw(corp_code: str, year: str, fs_div: str = "CFS") -> dict:
    r = requests.get(
        "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
        params={
            "crtfc_key":  DART_KEY,
            "corp_code":  corp_code,
            "bsns_year":  year,
            "reprt_code": "11011",
            "fs_div":     fs_div,
        },
        timeout=30,
    ).json()
    if r.get("status") != "000":
        return {"IS": {}, "CIS": {}, "BS": {}, "CF": {}}

    raw     = {"IS": {}, "CIS": {}, "BS": {}, "CF": {}}
    year_i  = int(year)
    for row in r.get("list", []):
        sj = row.get("sj_div", "").upper()
        nm = row.get("account_nm", "").strip()
        if sj not in raw:
            continue
        raw[sj][nm] = {
            str(year_i):     _to_int(row.get("thstrm_amount")),
            str(year_i - 1): _to_int(row.get("frmtrm_amount")),
            str(year_i - 2): _to_int(row.get("bfefrmtrm_amount")),
        }
    return raw


_FINANCIAL_ITEMS = [
    {"field": "revenue",             "fs": ["IS", "CIS"], "kw": ["매출액", "수익(매출액)"],           "yrs": 3},
    {"field": "operating_income",    "fs": ["IS", "CIS"], "kw": ["영업이익", "영업손익"],             "yrs": 3},
    {"field": "net_income",          "fs": ["IS", "CIS"], "kw": ["당기순이익", "당기순손익"],         "yrs": 3},
    {"field": "ocf",                 "fs": ["CF"],        "kw": ["영업활동현금흐름", "영업활동으로인한현금흐름"], "yrs": 3},
    {"field": "total_liabilities",   "fs": ["BS"],        "kw": ["부채총계"],                       "yrs": 1},
    {"field": "equity",              "fs": ["BS"],        "kw": ["자본총계"],                       "yrs": 1},
    {"field": "current_assets",      "fs": ["BS"],        "kw": ["유동자산"],                       "yrs": 1},
    {"field": "current_liabilities", "fs": ["BS"],        "kw": ["유동부채"],                       "yrs": 1},
    {"field": "cash",                "fs": ["BS"],        "kw": ["현금및현금성자산", "현금 및 현금성자산"], "yrs": 1},
    {"field": "short_term_debt",     "fs": ["BS"],        "kw": ["단기차입금"],                     "yrs": 1},
    {"field": "long_term_debt",      "fs": ["BS"],        "kw": ["장기차입금", "사채"],              "yrs": 1},
    {"field": "accounts_receivable", "fs": ["BS"],        "kw": ["매출채권", "매출채권 및 기타채권"], "yrs": 3},
    {"field": "inventory",           "fs": ["BS"],        "kw": ["재고자산"],                       "yrs": 3},
    {"field": "accounts_payable",    "fs": ["BS"],        "kw": ["매입채무", "매입채무 및 기타채무"], "yrs": 3},
]

_CAPEX_KW = ["유형자산의취득", "무형자산의취득"]


def _find_in_fs(raw: dict, fs_list: list[str], keywords: list[str]) -> dict | None:
    for fs in fs_list:
        table = raw.get(fs, {})
        for kw in keywords:
            if kw in table:
                return table[kw]
        for kw in keywords:
            kw_c = kw.replace(" ", "")
            for nm, v in table.items():
                if kw_c in nm.replace(" ", ""):
                    return v
    return None


def _build_financials(corp_code: str, year: str) -> dict:
    raw    = _fetch_financials_raw(corp_code, year)
    year_i = int(year)
    years3 = [str(year_i - i) for i in range(3)]
    res    = {}

    for item in _FINANCIAL_ITEMS:
        vals = _find_in_fs(raw, item["fs"], item["kw"])
        if vals is None:
            res[item["field"]] = {}
            continue
        if item["yrs"] == 1:
            res[item["field"]] = {year: vals.get(year)}
        else:
            res[item["field"]] = {str(year_i - i): vals.get(str(year_i - i)) for i in range(3)}

    # CAPEX = 유형자산취득 + 무형자산취득 (aggregate)
    capex: dict[str, int] = {}
    for kw in _CAPEX_KW:
        vals = _find_in_fs(raw, ["CF"], [kw])
        if vals:
            for y, v in vals.items():
                if v is not None:
                    capex[y] = capex.get(y, 0) + abs(v)
    res["capex"] = {str(year_i - i): capex.get(str(year_i - i)) for i in range(3)}

    def get(f, y):
        return res.get(f, {}).get(y)

    def safe_div(a, b):
        return None if (a is None or b is None or b == 0) else a / b

    # 파생 지표
    for y in years3:
        pass  # 아래에서 처리

    res["operating_margin"] = {
        y: (round(safe_div(get("operating_income", y), get("revenue", y)) * 100, 2)
            if safe_div(get("operating_income", y), get("revenue", y)) is not None else None)
        for y in years3
    }
    res["revenue_yoy"] = {}
    for y in years3:
        curr = get("revenue", y)
        prev = get("revenue", str(int(y) - 1))
        v    = safe_div((curr - prev) if curr and prev else None, prev)
        res["revenue_yoy"][y] = round(v * 100, 2) if v is not None else None

    res["fcf"] = {
        y: ((get("ocf", y) - get("capex", y))
            if get("ocf", y) is not None and get("capex", y) is not None else None)
        for y in years3
    }
    res["ebitda"] = {y: get("operating_income", y) for y in years3}  # 감가 없으면 영업이익 fallback

    res["debt_ratio"]   = {year: (round(safe_div(get("total_liabilities", year), get("equity", year)) * 100, 2)
                                  if safe_div(get("total_liabilities", year), get("equity", year)) is not None else None)}
    res["current_ratio"] = {year: (round(safe_div(get("current_assets", year), get("current_liabilities", year)) * 100, 2)
                                   if safe_div(get("current_assets", year), get("current_liabilities", year)) is not None else None)}
    res["roe"] = {year: (round(safe_div(get("net_income", year), get("equity", year)) * 100, 2)
                         if safe_div(get("net_income", year), get("equity", year)) is not None else None)}

    std  = get("short_term_debt", year)
    ltd  = get("long_term_debt",  year)
    cash = get("cash",            year)
    res["net_debt"] = {year: ((std + ltd - cash) if all(v is not None for v in [std, ltd, cash]) else None)}

    return res


# ── 도구 정의 ──────────────────────────────────────────────────────────────

@tool
def get_report_list(company: str, year: int = None) -> str:
    """DART에서 해당 기업의 사업보고서 목록을 조회합니다.

    Args:
        company: 기업명 (예: "삼성전자", "한화오션")
        year: 회계연도 (생략 시 자동 — 4월 이후면 직전년도, 4월 이전이면 2년 전)
    """
    if year is None:
        today = date.today()
        year  = today.year - 1 if today.month >= 4 else today.year - 2

    corp = _find_corp(company)
    if not corp:
        return f"❌ '{company}' 검색 결과 없음. 정확한 기업명을 사용하세요."

    reports = _fetch_report_list(corp["corp_code"], year)
    lines   = [f"[{corp['corp_name']}] {year}년 사업보고서 목록", f"corp_code: {corp['corp_code']}"]
    if reports:
        for rp in reports:
            revised = " [정정]" if rp["is_revised"] else ""
            lines.append(f"  rcept_no: {rp['rcept_no']}  {rp['report_nm']}  ({rp['rcept_dt']}){revised}")
    else:
        lines.append(f"  {year}년 사업보고서 없음")
    return "\n".join(lines)


@tool
def get_toc(rcept_no: str) -> str:
    """사업보고서 목차(섹션 목록)를 반환합니다. 어떤 섹션을 읽을지 결정하는 데 사용하세요.

    Args:
        rcept_no: 보고서 접수번호 (get_report_list에서 획득)
    """
    try:
        _, sections = _fetch_and_parse_xml(rcept_no)
    except Exception as e:
        return f"❌ XML 파싱 실패: {e}"

    if not sections:
        return "❌ 섹션을 찾을 수 없습니다."

    lines = [f"목차 ({len(sections)}개 섹션):"]
    for s in sections:
        lines.append(f"  [{s['atocid']}] {s['title']}")
    return "\n".join(lines)


@tool
def get_section(
    rcept_no: str,
    section_keyword: str,
    fallback_keyword: str = "",
    multi: bool = False,
) -> str:
    """사업보고서 특정 섹션의 원문을 반환합니다.

    Args:
        rcept_no: 보고서 접수번호
        section_keyword: 섹션 제목 키워드 (예: "사업의 개요", "위험관리")
        fallback_keyword: 1차 매칭 실패 시 대체 키워드
        multi: True면 매칭 섹션 전체를 합쳐서 반환
    """
    try:
        xml_str, sections = _fetch_and_parse_xml(rcept_no)
    except Exception as e:
        return f"❌ XML 파싱 실패: {e}"

    raw_text, matched_title = _extract_section_text(
        xml_str, sections,
        keywords=[section_keyword],
        fallback_keywords=[fallback_keyword] if fallback_keyword else [],
        multi=multi,
    )

    if not raw_text:
        available   = [s["title"] for s in sections]
        suggestions = [t for t in available if any(c in t for c in section_keyword)][:5] or available[:8]
        return (
            f"❌ '{section_keyword}' 섹션 없음.\n"
            f"아래 섹션 중 선택하세요:\n" +
            "\n".join(f"  - {t}" for t in suggestions)
        )

    MAX_CHARS = 50_000
    truncated = ""
    if len(raw_text) > MAX_CHARS:
        truncated = f"\n\n[... 전체 {len(raw_text):,}자 중 {MAX_CHARS:,}자까지 표시]"
        raw_text  = raw_text[:MAX_CHARS]

    return f"[섹션: {matched_title}] ({len(raw_text):,}자)\n\n{raw_text}{truncated}"


@tool
def get_financials(company: str, year: int = None) -> str:
    """DART 재무제표 API에서 주요 재무지표를 가져옵니다.
    수치 근거가 필요하거나 클레임의 수치를 검증할 때 사용하세요.
    매출, 영업이익, FCF, 부채비율, ROE 등 3개년 추이를 반환합니다.

    Args:
        company: 기업명
        year: 회계연도 (생략 시 자동 — 4월 이후면 직전년도, 4월 이전이면 2년 전)
    """
    if year is None:
        today = date.today()
        year  = today.year - 1 if today.month >= 4 else today.year - 2

    corp = _find_corp(company)
    if not corp:
        return f"❌ '{company}' 검색 결과 없음."

    try:
        data = _build_financials(corp["corp_code"], str(year))
    except Exception as e:
        return f"❌ 재무데이터 조회 실패: {e}"

    def fmt(v, mode="억원"):
        if v is None:
            return "N/A"
        if isinstance(v, str):
            return v
        if mode == "억원":
            return f"{v / 1e8:+,.0f}억"
        if mode == "pct":
            return f"{v:+.1f}%"
        if mode == "x":
            return f"{v:.2f}x"
        return str(v)

    def row(field, label, mode="억원"):
        vals = data.get(field, {})
        if not vals:
            return f"    {label:<18} N/A"
        parts = [f"{y} {fmt(vals.get(y), mode)}" for y in sorted(vals.keys())]
        return f"    {label:<18} {'  /  '.join(parts)}"

    lines = [f"[{corp['corp_name']}] {year}년 기준 재무지표\n"]
    lines += ["  ── 수익성",
              row("revenue",          "매출"),
              row("operating_income", "영업이익"),
              row("operating_margin", "영업이익률", "pct"),
              row("net_income",       "당기순이익"),
              row("ebitda",           "EBITDA"),
              row("roe",              "ROE", "pct"),
              "\n  ── 성장성",
              row("revenue_yoy",      "매출YoY", "pct"),
              "\n  ── 현금흐름",
              row("ocf",              "OCF"),
              row("capex",            "CAPEX"),
              row("fcf",              "FCF"),
              "\n  ── 안정성",
              row("debt_ratio",       "부채비율", "pct"),
              row("current_ratio",    "유동비율", "pct"),
              row("net_debt",         "순차입금")]
    return "\n".join(lines)


@tool
def finish(answer: str) -> str:
    """클레임 수집이 완료되면 호출합니다.

    Args:
        answer: 수집 완료 사유 또는 요약
    """
    return answer


# ── pre-fetch 헬퍼 (도구 형식 아님 — Python에서 직접 호출) ───────────────────

def prefetch_latest_report(company: str) -> tuple[str, str]:
    """최신 사업보고서의 (rcept_no, report_year) 반환. 실패 시 ('', '')."""
    today = date.today()
    year  = today.year - 1 if today.month >= 4 else today.year - 2
    corp  = _find_corp(company)
    if not corp:
        return "", ""
    reports = _fetch_report_list(corp["corp_code"], year)
    if not reports:
        reports = _fetch_report_list(corp["corp_code"], year - 1)
        if reports:
            year -= 1
    if not reports:
        return "", ""
    return reports[0]["rcept_no"], str(year)


def prefetch_toc_text(rcept_no: str) -> str:
    """목차 텍스트 반환 (에이전트 도구 형식 아님)."""
    try:
        _, sections = _fetch_and_parse_xml(rcept_no)
    except Exception as e:
        return f"목차 로드 실패: {e}"
    if not sections:
        return "섹션 없음"
    lines = [f"목차 ({len(sections)}개 섹션):"]
    for s in sections:
        lines.append(f"  [{s['atocid']}] {s['title']}")
    return "\n".join(lines)


# ── 외부 공개 ──────────────────────────────────────────────────────────────

# ReAct 에이전트용 도구 — get_report_list / get_toc는 pre-fetch로 처리
DART_AGENT_TOOLS = [get_section, get_financials, finish]
TOOL_MAP         = {t.name: t for t in DART_AGENT_TOOLS}

__all__ = [
    "get_report_list", "get_toc", "get_section", "get_financials", "finish",
    "DART_AGENT_TOOLS", "TOOL_MAP",
    "prefetch_latest_report", "prefetch_toc_text",
]
