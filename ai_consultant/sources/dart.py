"""DART OpenAPI source layer.

Two kinds of evidence, exactly as the project brief asks for:
  * 정형(structured): JSON endpoints (fnlttSinglAcnt 주요계정, list 공시목록) -> numeric facts.
  * 비정형(unstructured): document.xml 원본(zip) -> plaintext passages with source spans.

Every network call is cached under a run-local cache dir to keep re-runs cheap and offline-repeatable.
"""
from __future__ import annotations
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from .. import config

BASE = "https://opendart.fss.or.kr/api"
UA = {"User-Agent": "ai-consultant-research/0.1"}


@dataclass
class Filing:
    corp_name: str
    report_nm: str
    rcept_no: str
    rcept_dt: str      # YYYYMMDD

    @property
    def date_iso(self) -> str:
        d = self.rcept_dt
        return f"{d[0:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else d

    @property
    def url(self) -> str:
        return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={self.rcept_no}"


class DartClient:
    def __init__(self, key: str | None = None, cache_dir: str | Path | None = None):
        self.key = key or config.require_dart()
        self.cache = Path(cache_dir) if cache_dir else None
        if self.cache:
            self.cache.mkdir(parents=True, exist_ok=True)
        self._corp_index: dict[str, str] | None = None  # stock_code/name -> corp_code

    # ---------- low level ----------
    def _get(self, path: str, params: dict, *, binary: bool = False):
        p = dict(params)
        p["crtfc_key"] = self.key
        r = requests.get(f"{BASE}/{path}", params=p, headers=UA, timeout=90)
        r.raise_for_status()
        return r.content if binary else r.json()

    # ---------- corp code ----------
    def _load_corp_index(self) -> dict[str, str]:
        if self._corp_index is not None:
            return self._corp_index
        cache_file = self.cache / "corpCode.xml" if self.cache else None
        if cache_file and cache_file.exists():
            xml_bytes = cache_file.read_bytes()
        else:
            content = self._get("corpCode.xml", {}, binary=True)
            z = zipfile.ZipFile(io.BytesIO(content))
            xml_bytes = z.read(z.namelist()[0])
            if cache_file:
                cache_file.write_bytes(xml_bytes)
        root = ET.fromstring(xml_bytes)
        idx: dict[str, str] = {}
        for el in root.iter("list"):
            code = (el.findtext("corp_code") or "").strip()
            name = (el.findtext("corp_name") or "").strip()
            stock = (el.findtext("stock_code") or "").strip()
            if name:
                idx.setdefault(name, code)
            if stock:
                idx[stock] = code
        self._corp_index = idx
        return idx

    def resolve_corp(self, company: str) -> Optional[str]:
        """Resolve a company name or 6-digit stock code to a corp_code (exact match preferred)."""
        idx = self._load_corp_index()
        if company in idx:
            return idx[company]
        # loosen: strip whitespace, try contains for listed names
        for name, code in idx.items():
            if name.replace(" ", "") == company.replace(" ", ""):
                return code
        return None

    # ---------- 정형: structured financials ----------
    def key_accounts(self, corp_code: str, year: str, reprt_code: str = "11011") -> list[dict]:
        """fnlttSinglAcnt 단일회사 주요계정. reprt_code 11011=사업보고서."""
        j = self._get("fnlttSinglAcnt.json", {
            "corp_code": corp_code, "bsns_year": year, "reprt_code": reprt_code,
        })
        if j.get("status") != "000":
            return []
        return j.get("list", [])

    # ---------- 공시 목록 ----------
    def list_filings(self, corp_code: str, bgn: str, end: str,
                     pblntf_ty: str | None = None, page_count: int = 100) -> list[dict]:
        params = {"corp_code": corp_code, "bgn_de": bgn, "end_de": end,
                  "page_count": str(page_count)}
        if pblntf_ty:
            params["pblntf_ty"] = pblntf_ty
        j = self._get("list.json", params)
        if j.get("status") != "000":
            return []
        return j.get("list", [])

    def latest_business_report(self, corp_code: str, bgn: str, end: str) -> Optional[Filing]:
        """Latest 사업보고서 by receipt date. A [기재정정] supersedes the original and is
        typically the more complete document, so we take the most recent regardless of 정정."""
        rows = self.list_filings(corp_code, bgn, end, pblntf_ty="A")
        biz = [x for x in rows if "사업보고서" in x["report_nm"]]
        biz.sort(key=lambda x: x["rcept_dt"], reverse=True)
        if not biz:
            return None
        x = biz[0]
        return Filing(x["corp_name"].strip(), x["report_nm"].strip(), x["rcept_no"], x["rcept_dt"])

    def supply_contracts(self, corp_code: str, bgn: str, end: str) -> list[Filing]:
        rows = self.list_filings(corp_code, bgn, end)
        out = []
        for x in rows:
            nm = x["report_nm"]
            if "공급계약" in nm or "단일판매" in nm:
                out.append(Filing(x["corp_name"].strip(), nm.strip(), x["rcept_no"], x["rcept_dt"]))
        return out

    # ---------- 비정형: raw document ----------
    def document_text(self, rcept_no: str) -> str:
        """Download document.xml(zip), decode (utf-8 -> cp949 fallback), strip tags to plaintext."""
        cache_file = self.cache / f"doc_{rcept_no}.txt" if self.cache else None
        if cache_file and cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        content = self._get("document.xml", {"rcept_no": rcept_no}, binary=True)
        z = zipfile.ZipFile(io.BytesIO(content))
        raw = z.read(z.namelist()[0])
        txt = None
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                txt = raw.decode(enc)
                break
            except Exception:
                continue
        if txt is None:
            txt = raw.decode("utf-8", errors="replace")
        plain = _to_plaintext(txt)
        if cache_file:
            cache_file.write_text(plain, encoding="utf-8")
        return plain


# ----------------- passage helpers -----------------
def _to_plaintext(xml_text: str) -> str:
    # DART docs are SGML/XML-ish; drop tags, collapse whitespace, keep table cell spacing.
    t = re.sub(r"<[^>]+>", " ", xml_text)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


_DIGIT_GROUP = re.compile(r"\d[\d,]{2,}")


def find_passages(plaintext: str, keywords: list[str], window: int = 900,
                  max_per_kw: int = 2) -> list[dict]:
    """Return passages (windows) around occurrences of each keyword.

    For every keyword we scan ALL occurrences, score each window by numeric density
    (count of digit groups) and keep the top `max_per_kw`. This biases toward the real
    tables (수주잔고/매출 등) instead of an incidental mention. Each passage carries the
    keyword and char offset so the extractor can cite a real span.
    """
    passages: list[dict] = []
    seen_spans: list[tuple[int, int]] = []
    for kw in keywords:
        cands: list[tuple[int, int, int, int]] = []  # (score, offset, a, b)
        start = 0
        while True:
            idx = plaintext.find(kw, start)
            if idx == -1:
                break
            a = max(0, idx - window // 3)
            b = min(len(plaintext), idx + window)
            score = len(_DIGIT_GROUP.findall(plaintext[a:b]))
            cands.append((score, idx, a, b))
            start = idx + len(kw)
        # richest windows first; keep up to max_per_kw non-overlapping
        cands.sort(key=lambda c: c[0], reverse=True)
        kept = 0
        for score, idx, a, b in cands:
            if kept >= max_per_kw:
                break
            if any(not (b < s or a > e) and min(b, e) - max(a, s) > window // 2 for s, e in seen_spans):
                continue
            seen_spans.append((a, b))
            passages.append({"keyword": kw, "offset": idx, "score": score, "text": plaintext[a:b]})
            kept += 1
    return passages
