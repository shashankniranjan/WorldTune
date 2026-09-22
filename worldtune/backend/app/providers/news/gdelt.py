"""GDELT DOC 2.0 news adapter -- free, keyless.

Endpoint:
    GET https://api.gdeltproject.org/api/v2/doc/doc
        ?query=<q>&mode=artlist&format=json&maxrecords=<n>&sort=datedesc
    -> {"articles": [{"url","title","seendate","socialimage","domain",
                      "language","sourcecountry", ...}, ...]}

Why DOC 2.0 rather than the 15-minute CSV export: it is a request/response
API with no key and no unzip step, which is what an adapter wants. Its
documented tradeoff is a rolling ~3-month window; deeper history needs the
bulk export path.

Two real quirks handled below:
  * `seendate` is `YYYYMMDDTHHMMSSZ` (note the literal T and Z), not ISO;
  * an empty result set can come back as `text/html` with an empty body,
    which `http_get_json` already normalizes to `{}`.

GDELT's DOC API does not return per-article tone in artlist mode, so
sentiment falls back to the local lexicon.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.analytics.sentiment import score_sentiment
from app.entities.graph import get_entity_graph
from app.providers.base import NewsProvider
from app.providers.http import ProviderHTTPError, http_get_json
from app.schemas.canonical import CanonicalNewsEvent

logger = logging.getLogger(__name__)

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# One query per interest domain of the demo persona. Unioned by the caller.
DEFAULT_QUERIES = (
    '("artificial intelligence" OR "AI chips" OR NVIDIA) sourcelang:english',
    '(bitcoin OR ethereum OR cryptocurrency) sourcelang:english',
    '("data platform" OR databricks OR snowflake OR "data engineering") sourcelang:english',
)


class GDELTNewsProvider(NewsProvider):
    name = "gdelt"
    is_live = True

    def __init__(self, client: Optional[httpx.Client] = None,
                 queries: tuple[str, ...] = DEFAULT_QUERIES):
        self._client = client
        self._queries = queries

    def is_available(self) -> bool:
        return True  # keyless

    def fetch_news(self, *, query: str = "", since: datetime | None = None,
                   limit: int = 50) -> list[CanonicalNewsEvent]:
        queries = (query,) if query else self._queries
        per_query = max(1, limit // max(1, len(queries)))
        out: list[CanonicalNewsEvent] = []
        for q in queries:
            params = {
                "query": q,
                "mode": "artlist",
                "format": "json",
                "maxrecords": str(min(250, per_query)),
                "sort": "datedesc",
            }
            if since is not None:
                params["startdatetime"] = since.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
            try:
                payload = http_get_json(BASE_URL, params=params, client=self._client)
            except ProviderHTTPError as exc:
                logger.warning("gdelt query %r failed: %s", q, exc)
                continue
            out.extend(self.parse(payload))
        return out[:limit]

    @staticmethod
    def parse(payload: dict) -> list[CanonicalNewsEvent]:
        graph = get_entity_graph()
        events: list[CanonicalNewsEvent] = []
        for art in (payload or {}).get("articles", []) or []:
            title = (art.get("title") or "").strip()
            if not title:
                continue
            published = _parse_seendate(art.get("seendate"))
            if published is None:
                continue
            keys = graph.resolve_text(title)
            social_image = (art.get("socialimage") or "").strip()
            events.append(
                CanonicalNewsEvent(
                    title=title,
                    summary="",
                    url=art.get("url") or "",
                    published_at=published,
                    source="gdelt",
                    domain=art.get("domain") or "",
                    language=(art.get("language") or "English").lower()[:2],
                    sentiment=score_sentiment(title),
                    entities=[graph.label(k) for k in keys],
                    tickers=graph.tickers_for(keys),
                    sectors=graph.sectors_for(keys),
                    image_url=social_image or None,
                )
            )
        return events


def _parse_seendate(value: str | None) -> datetime | None:
    """`20250913T104500Z` -> aware UTC datetime. Tolerates the ISO form too."""
    if not value:
        return None
    raw = value.strip().replace("-", "").replace(":", "")
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
