"""RemoteOK jobs adapter -- free, keyless, real.

Endpoint:
    GET https://remoteok.com/api
    -> a JSON *array* whose FIRST element is a legal/attribution object
       ({"legal": "..."}), not a job. Elements after it carry:
       id, slug, company, position, tags[], description (HTML), location,
       date (ISO-8601 with offset), url, salary_min, salary_max.

Real quirks handled:
  * the leading legal element must be skipped (it has no "id"/"position");
  * `description` is HTML -- stripped to text before skill extraction, or
    every posting would "mention" nothing but tag names;
  * `salary_min`/`salary_max` are 0 (not null) when unknown;
  * the endpoint requires a non-default User-Agent, which
    `app.providers.http.build_client` always sets.

Chosen as the primary real jobs source because it is the only one of the
three candidates (Adzuna / RemoteOK / Arbeitnow) that needs no registration
at all. Adzuna is implemented alongside it for location-specific (Bengaluru)
coverage, gated on `is_available()`.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.providers.base import JobsProvider
from app.providers.http import ProviderHTTPError, http_get_json
from app.schemas.canonical import CanonicalJob

logger = logging.getLogger(__name__)

BASE_URL = "https://remoteok.com/api"

_TAG_RE = re.compile(r"<[^>]+>")


class RemoteOKProvider(JobsProvider):
    name = "remoteok"
    is_live = True

    def __init__(self, client: Optional[httpx.Client] = None):
        self._client = client

    def is_available(self) -> bool:
        return True  # keyless

    def fetch_jobs(self, *, query: str = "", location: str = "",
                   limit: int = 50) -> list[CanonicalJob]:
        try:
            payload = http_get_json(BASE_URL, client=self._client)
        except ProviderHTTPError as exc:
            logger.warning("remoteok fetch failed: %s", exc)
            return []
        jobs = self.parse(payload)
        needle = (query or "").strip().lower()
        if needle:
            jobs = [j for j in jobs
                    if needle in j.title.lower() or needle in j.description.lower()]
        return jobs[:limit]

    @staticmethod
    def parse(payload: list) -> list[CanonicalJob]:
        jobs: list[CanonicalJob] = []
        for item in payload or []:
            if not isinstance(item, dict) or "position" not in item:
                continue  # the legal/attribution element
            posted = _parse_date(item.get("date"))
            if posted is None:
                continue
            tags = [str(t) for t in (item.get("tags") or [])]
            description = strip_html(item.get("description") or "")
            # Tags carry real skill vocabulary that is often absent from the
            # prose, so they are appended to the text the extractor sees.
            if tags:
                description = f"{description}\nTags: {', '.join(tags)}"
            jobs.append(
                CanonicalJob(
                    external_id=str(item.get("id") or item.get("slug") or ""),
                    title=str(item.get("position") or "").strip(),
                    company=str(item.get("company") or "").strip(),
                    description=description,
                    location=str(item.get("location") or "Remote").strip() or "Remote",
                    country="",
                    remote=True,  # every RemoteOK posting is remote by construction
                    salary_min=_positive(item.get("salary_min")),
                    salary_max=_positive(item.get("salary_max")),
                    salary_currency="USD" if _positive(item.get("salary_min")) else "",
                    url=str(item.get("url") or ""),
                    source="remoteok",
                    posted_at=posted,
                )
            )
        return jobs


def strip_html(raw: str) -> str:
    """HTML -> plain text. Entity-unescaped so '&amp;' does not split words."""
    text = _TAG_RE.sub(" ", raw or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _positive(value) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if num > 0 else None


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:  # some rows carry an epoch instead
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except (TypeError, ValueError):
            return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
