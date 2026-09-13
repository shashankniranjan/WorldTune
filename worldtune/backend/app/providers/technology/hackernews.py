"""Hacker News (Algolia) adapter -- free, keyless.

Endpoint:
    GET https://hn.algolia.com/api/v1/search
        ?query=<q>&tags=story&numericFilters=created_at_i><epoch>&hitsPerPage=<n>
    -> {"hits": [{objectID, title, url, points, num_comments,
                  created_at (ISO), created_at_i (epoch), author, ...}]}

HN is used as a *discussion-volume* signal, complementary to GitHub's
*code-activity* signal: points and comment counts say what practitioners are
arguing about this week, which leads job-posting vocabulary by a few months.
`points` maps to the canonical `points` field and comment count into
`mentions`; there is no star concept, so `stars` stays 0.0.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.providers.base import TechnologySignalsProvider
from app.providers.http import ProviderHTTPError, http_get_json
from app.schemas.canonical import CanonicalTechEvent

logger = logging.getLogger(__name__)

BASE_URL = "https://hn.algolia.com/api/v1/search"

DEFAULT_QUERIES = ("apache iceberg", "llm observability", "agent framework",
                   "databricks", "vector database", "data engineering")


class HackerNewsTechnologyProvider(TechnologySignalsProvider):
    name = "hackernews"
    is_live = True

    def __init__(self, client: Optional[httpx.Client] = None,
                 queries: tuple[str, ...] = DEFAULT_QUERIES):
        self._client = client
        self._queries = queries

    def is_available(self) -> bool:
        return True

    def fetch_tech_events(self, *, topics: list[str] | None = None,
                          limit: int = 50) -> list[CanonicalTechEvent]:
        queries = topics or list(self._queries)
        cutoff = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
        per_query = max(1, limit // max(1, len(queries)))
        out: list[CanonicalTechEvent] = []
        for q in queries:
            params = {
                "query": q,
                "tags": "story",
                "numericFilters": f"created_at_i>{cutoff}",
                "hitsPerPage": str(min(100, per_query)),
            }
            try:
                payload = http_get_json(BASE_URL, params=params, client=self._client)
            except ProviderHTTPError as exc:
                logger.warning("hn search %r failed: %s", q, exc)
                continue
            out.extend(self.parse(payload, name=q))
        return out[:limit]

    @staticmethod
    def parse(payload: dict, *, name: str = "") -> list[CanonicalTechEvent]:
        events: list[CanonicalTechEvent] = []
        for hit in (payload or {}).get("hits", []) or []:
            title = (hit.get("title") or "").strip()
            if not title:
                continue  # comments and Ask-HN replies have no title
            created = _parse_created(hit)
            if created is None:
                continue
            events.append(
                CanonicalTechEvent(
                    name=name.title() if name else title[:60],
                    title=title,
                    category="discussion",
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    source="hackernews",
                    observed_at=created,
                    stars=0.0,
                    stars_7d_delta=0.0,
                    points=float(hit.get("points") or 0),
                    mentions=float(hit.get("num_comments") or 0),
                )
            )
        return events


def _parse_created(hit: dict) -> datetime | None:
    epoch = hit.get("created_at_i")
    if epoch is not None:
        try:
            return datetime.fromtimestamp(float(epoch), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    raw = hit.get("created_at")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
