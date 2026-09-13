"""Google News RSS adapter -- free, keyless.

Endpoint:
    GET https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en
    -> RSS 2.0 XML, <item> with <title>, <link>, <pubDate>, <source>.

Parsed with the stdlib `xml.etree.ElementTree` rather than a feed library:
the surface is three tags, and adding a dependency for that is not worth it.
`resolve_entities=False` is not available on ElementTree, but ElementTree does
not expand external entities by default, so the XXE surface is closed.

Titles arrive as "Headline - Publisher"; the publisher suffix is split off so
it does not pollute entity matching.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from xml.etree import ElementTree

import httpx

from app.analytics.sentiment import score_sentiment
from app.entities.graph import get_entity_graph
from app.providers.base import NewsProvider
from app.providers.http import ProviderHTTPError, http_get_text
from app.schemas.canonical import CanonicalNewsEvent

logger = logging.getLogger(__name__)

BASE_URL = "https://news.google.com/rss/search"

DEFAULT_QUERIES = (
    "AI chips OR NVIDIA earnings",
    "bitcoin OR ethereum price",
    "data engineering OR databricks OR snowflake",
)


class GoogleNewsRSSProvider(NewsProvider):
    name = "google-news-rss"
    is_live = True

    def __init__(self, client: Optional[httpx.Client] = None,
                 queries: tuple[str, ...] = DEFAULT_QUERIES):
        self._client = client
        self._queries = queries

    def is_available(self) -> bool:
        return True

    def fetch_news(self, *, query: str = "", since: datetime | None = None,
                   limit: int = 50) -> list[CanonicalNewsEvent]:
        queries = (query,) if query else self._queries
        out: list[CanonicalNewsEvent] = []
        for q in queries:
            try:
                body = http_get_text(
                    BASE_URL,
                    params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                    client=self._client,
                )
            except ProviderHTTPError as exc:
                logger.warning("google news query %r failed: %s", q, exc)
                continue
            out.extend(self.parse(body))
        if since is not None:
            out = [e for e in out if e.published_at >= since]
        return out[:limit]

    @staticmethod
    def parse(body: str) -> list[CanonicalNewsEvent]:
        if not (body or "").strip():
            return []
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as exc:
            logger.warning("google news RSS parse failed: %s", exc)
            return []
        graph = get_entity_graph()
        events: list[CanonicalNewsEvent] = []
        for item in root.iterfind(".//item"):
            raw_title = (item.findtext("title") or "").strip()
            if not raw_title:
                continue
            title, publisher = _split_publisher(raw_title)
            published = _parse_pubdate(item.findtext("pubDate"))
            if published is None:
                continue
            source_el = item.find("source")
            domain = (source_el.get("url") if source_el is not None else "") or ""
            keys = graph.resolve_text(title)
            events.append(
                CanonicalNewsEvent(
                    title=title,
                    summary=publisher,
                    url=item.findtext("link") or "",
                    published_at=published,
                    source="google-news-rss",
                    domain=domain.replace("https://", "").replace("http://", "").strip("/"),
                    language="en",
                    sentiment=score_sentiment(title),
                    entities=[graph.label(k) for k in keys],
                    tickers=graph.tickers_for(keys),
                    sectors=graph.sectors_for(keys),
                )
            )
        return events


def _split_publisher(title: str) -> tuple[str, str]:
    """'Nvidia beats estimates - Reuters' -> ('Nvidia beats estimates', 'Reuters')."""
    if " - " in title:
        head, _, tail = title.rpartition(" - ")
        if head and len(tail) <= 40:
            return head.strip(), tail.strip()
    return title, ""


def _parse_pubdate(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
