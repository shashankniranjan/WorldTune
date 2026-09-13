"""GitHub repository-search adapter -- free, key optional.

Endpoint:
    GET https://api.github.com/search/repositories
        ?q=<topic>+pushed:>=<date>&sort=stars&order=desc&per_page=<n>
    -> {"items": [{full_name, description, html_url, stargazers_count,
                   pushed_at, topics[], ...}]}

"Trending" is not a GitHub API concept (the trending page is scraped HTML with
no endpoint), so WorldTune approximates it honestly: stars-sorted repositories
*recently pushed*, per topic. That is a proxy for activity, and it is labelled
as one -- `stars_7d_delta` is left at 0.0 by this adapter because a single
search response carries no star history. Velocity is computed downstream by
differencing successive snapshots stored in `technology_events`, which is the
only way to get it without a time-series source.

Rate limits: 10 searches/minute unauthenticated, 30/minute with a token.
`GITHUB_TOKEN` is optional and only raises the ceiling; the adapter reports
`is_available() == True` either way.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import settings
from app.providers.base import TechnologySignalsProvider
from app.providers.http import ProviderHTTPError, http_get_json
from app.schemas.canonical import CanonicalTechEvent

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com/search/repositories"

DEFAULT_TOPICS = ("data-engineering", "llm", "vector-database", "mlops", "agents", "lakehouse")


class GitHubTechnologyProvider(TechnologySignalsProvider):
    name = "github"
    is_live = True
    requires_credentials = ()  # token optional

    def __init__(self, client: Optional[httpx.Client] = None):
        self._client = client

    def is_available(self) -> bool:
        return True

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        return headers

    def fetch_tech_events(self, *, topics: list[str] | None = None,
                          limit: int = 50) -> list[CanonicalTechEvent]:
        topic_list = topics or list(DEFAULT_TOPICS)
        since = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
        per_topic = max(1, limit // max(1, len(topic_list)))
        out: list[CanonicalTechEvent] = []
        for topic in topic_list:
            params = {
                "q": f"topic:{topic} pushed:>={since}",
                "sort": "stars",
                "order": "desc",
                "per_page": str(min(100, per_topic)),
            }
            try:
                payload = http_get_json(BASE_URL, params=params,
                                        headers=self._headers(), client=self._client)
            except ProviderHTTPError as exc:
                logger.warning("github search for topic %r failed: %s", topic, exc)
                continue
            out.extend(self.parse(payload, category=topic))
        return out[:limit]

    @staticmethod
    def parse(payload: dict, *, category: str = "") -> list[CanonicalTechEvent]:
        events: list[CanonicalTechEvent] = []
        for repo in (payload or {}).get("items", []) or []:
            full_name = repo.get("full_name") or ""
            if not full_name:
                continue
            observed = _parse_iso(repo.get("pushed_at")) or datetime.now(timezone.utc)
            events.append(
                CanonicalTechEvent(
                    # The repo name, not owner/repo -- that is the entity people
                    # actually say ("iceberg", not "apache/iceberg").
                    name=full_name.split("/")[-1],
                    title=(repo.get("description") or full_name)[:300],
                    category=category or (repo.get("topics") or [""])[0],
                    url=repo.get("html_url") or "",
                    source="github",
                    observed_at=observed,
                    stars=float(repo.get("stargazers_count") or 0),
                    stars_7d_delta=0.0,  # see module docstring: needs two snapshots
                    points=0.0,
                    mentions=1.0,
                )
            )
        return events


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
