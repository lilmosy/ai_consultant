"""Naver 뉴스 검색 API source layer.

Official endpoint: https://openapi.naver.com/v1/search/news.json
Auth headers: X-Naver-Client-Id / X-Naver-Client-Secret  (BOTH required).

Flow: query -> JSON items -> HTML-tag/entity clean -> relevance filter (company must appear,
at least one topic term appears) -> deduped, date-parsed items.

검색 API는 title/description 스니펫만 준다. 실제 근거(claim)를 뽑으려면 기사 원문이 필요하므로,
네이버 뉴스로 제공된 기사(n.news.naver.com)는 원문 페이지를 직접 받아 본문을 파싱한다
(`#dic_area` 등). 원문 파싱이 신뢰 불가한 외부 매체는 스니펫으로 안전하게 폴백한다.
"""
from __future__ import annotations
import html
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

from .. import config

ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
_BROWSER_UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")}
# 네이버 뉴스 본문 컨테이너 후보
_ARTICLE_SELECTORS = ["#dic_area", "#articleBodyContents", "#newsct_article article", "#newsEndContents"]


@dataclass
class NewsItem:
    title: str
    description: str
    link: str
    original_link: str
    pub_date: str          # ISO YYYY-MM-DD
    query: str
    matched_terms: list[str] = field(default_factory=list)
    body: str = ""             # 원문 파싱 성공 시 기사 본문
    body_source: str = "snippet"  # naver_article | snippet

    @property
    def passage(self) -> str:
        # 본문 파싱에 성공하면 제목+본문, 아니면 제목+스니펫
        if self.body:
            return f"{self.title}. {self.body}"
        return f"{self.title}. {self.description}"


def fetch_article_body(url: str, timeout: int = 10, max_chars: int = 6000) -> Optional[str]:
    """네이버 뉴스 기사(n.news.naver.com)의 본문을 파싱해 반환. 실패/저품질이면 None.

    외부 매체(원문 링크)는 사이트별 구조가 제각각이라 nav/footer 잡음이 섞이므로 시도하지 않는다.
    """
    if "n.news.naver.com" not in url and "news.naver.com" not in url:
        return None
    try:
        from bs4 import BeautifulSoup
        r = requests.get(url, headers=_BROWSER_UA, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or r.encoding
    except Exception:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    node = None
    for sel in _ARTICLE_SELECTORS:
        node = soup.select_one(sel)
        if node:
            break
    if not node:
        return None
    text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
    return text[:max_chars] if len(text) >= 200 else None


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
                 max_items: int = 30, fetch_bodies: bool = True,
                 body_workers: int = 8) -> tuple[list[NewsItem], dict]:
    """Run each query, filter for relevance, dedupe, then fetch full article bodies
    for Naver-hosted articles. Returns (items, diagnostics)."""
    client = client or NaverNewsClient()
    diag = {"ready": client.ready, "queries": [], "errors": [], "raw_count": 0,
            "kept_count": 0, "bodies_fetched": 0}
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

    # 원문 본문 파싱 (네이버 뉴스 기사에 한해, 동시 실행)
    if fetch_bodies and out:
        def _grab(item: NewsItem):
            body = fetch_article_body(item.link) or fetch_article_body(item.original_link)
            if body:
                item.body = body
                item.body_source = "naver_article"
            return item
        with ThreadPoolExecutor(max_workers=body_workers) as ex:
            list(ex.map(_grab, out))
        diag["bodies_fetched"] = sum(1 for n in out if n.body_source == "naver_article")
    return out, diag
