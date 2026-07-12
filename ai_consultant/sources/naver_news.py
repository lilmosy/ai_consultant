"""Naver 뉴스 검색 API source layer.

Official endpoint: https://openapi.naver.com/v1/search/news.json
Auth headers: X-Naver-Client-Id / X-Naver-Client-Secret  (BOTH required).

Flow: query -> JSON items -> HTML-tag/entity clean -> relevance filter (company must appear,
at least one topic term appears) -> deduped, date-parsed passages ready for claim extraction.
"""
from __future__ import annotations
import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

from .. import config

ENDPOINT = "https://openapi.naver.com/v1/search/news.json"


@dataclass
class NewsItem:
    title: str
    description: str
    link: str
    original_link: str
    pub_date: str          # ISO YYYY-MM-DD
    query: str
    matched_terms: list[str] = field(default_factory=list)

    @property
    def passage(self) -> str:
        return f"{self.title}. {self.description}"


class NaverNewsClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = client_id or config.NAVER_CLIENT_ID
        self.client_secret = client_secret or config.NAVER_CLIENT_SECRET

    @property
    def ready(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def search(self, query: str, display: int = 20, sort: str = "date") -> tuple[list[dict], Optional[str]]:
        """Return (items, error). error is a human string when auth/other failure occurs."""
        if not self.ready:
            return [], "NAVER_CLIENT_ID/SECRET 미설정 (뉴스 인증 불가)"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {"query": query, "display": min(display, 100), "sort": sort}
        try:
            r = requests.get(ENDPOINT, params=params, headers=headers, timeout=30)
        except Exception as e:
            return [], f"요청 실패: {e}"
        if r.status_code != 200:
            return [], f"HTTP {r.status_code}: {r.text[:160]}"
        return r.json().get("items", []), None


def _clean(text: str) -> str:
    text = re.sub(r"</?b>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(rfc822: str) -> str:
    for fmt in ("%a, %d %b %Y %H:%M:%S %z",):
        try:
            return datetime.strptime(rfc822, fmt).astimezone(timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            pass
    return rfc822[:16]


def collect_news(company: str, topic_terms: list[str], queries: list[str],
                 client: NaverNewsClient | None = None,
                 max_items: int = 30) -> tuple[list[NewsItem], dict]:
    """Run each query, filter for relevance, dedupe. Returns (items, diagnostics)."""
    client = client or NaverNewsClient()
    diag = {"ready": client.ready, "queries": [], "errors": [], "raw_count": 0,
            "kept_count": 0}
    if not client.ready:
        diag["errors"].append("Naver 인증정보 없음 — 뉴스 소스 비활성화")
        return [], diag

    seen_links: set[str] = set()
    out: list[NewsItem] = []
    company_key = company.replace(" ", "")
    for q in queries:
        items, err = client.search(q, display=30, sort="date")
        diag["queries"].append({"q": q, "n": len(items), "error": err})
        if err:
            diag["errors"].append(f"{q}: {err}")
            continue
        diag["raw_count"] += len(items)
        for it in items:
            title = _clean(it.get("title", ""))
            desc = _clean(it.get("description", ""))
            blob = (title + " " + desc).replace(" ", "")
            # relevance: company name must appear AND >=1 topic term must appear
            if company_key not in blob:
                continue
            matched = [t for t in topic_terms if t.replace(" ", "") in blob]
            if not matched:
                continue
            link = it.get("originallink") or it.get("link", "")
            if link in seen_links:
                continue
            seen_links.add(link)
            out.append(NewsItem(
                title=title, description=desc,
                link=it.get("link", ""), original_link=it.get("originallink", ""),
                pub_date=_parse_date(it.get("pubDate", "")), query=q, matched_terms=matched,
            ))
            if len(out) >= max_items:
                break
        if len(out) >= max_items:
            break
    diag["kept_count"] = len(out)
    return out, diag
