"""Adzuna jobs adapter -- free developer registration required.

Endpoint:
    GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
        ?app_id=...&app_key=...&results_per_page=50&what=...&where=...
    -> {"results": [{id, title, company:{display_name}, description,
                     location:{display_name, area[]}, created,
                     redirect_url, salary_min, salary_max, ...}]}

Gated behind `is_available()` (the WorldPulse pattern for optional-key
providers): with `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` unset this adapter reports
itself unavailable and the registry skips it -- it never raises and never
blocks startup.

Adzuna is the provider that gives Career Pulse *Bengaluru* coverage
(`country="in"`), which RemoteOK structurally cannot: every RemoteOK posting
is remote and location-agnostic.

Note: Adzuna's `description` is a truncated snippet ending in an ellipsis,
not the full posting. Skill extraction over a snippet under-counts, so
`skill_share` from Adzuna-sourced rows is a lower bound.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.providers.base import JobsProvider
from app.providers.http import ProviderHTTPError, http_get_json
from app.schemas.canonical import CanonicalJob

logger = logging.getLogger(__name__)

BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class AdzunaProvider(JobsProvider):
    name = "adzuna"
    is_live = True
    requires_credentials = ("ADZUNA_APP_ID", "ADZUNA_APP_KEY")

    def __init__(self, client: Optional[httpx.Client] = None, country: str = "in"):
        self._client = client
        self._country = country

    def is_available(self) -> bool:
        return bool(settings.adzuna_app_id and settings.adzuna_app_key)

    def fetch_jobs(self, *, query: str = "data engineer", location: str = "Bengaluru",
                   limit: int = 50) -> list[CanonicalJob]:
        if not self.is_available():
            logger.info("adzuna skipped: credentials not configured")
            return []
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "results_per_page": str(min(50, limit)),
            "what": query or "data engineer",
            "content-type": "application/json",
        }
        if location:
            params["where"] = location
        try:
            payload = http_get_json(f"{BASE_URL}/{self._country}/search/1",
                                    params=params, client=self._client)
        except ProviderHTTPError as exc:
            logger.warning("adzuna fetch failed: %s", exc)
            return []
        return self.parse(payload)[:limit]

    @staticmethod
    def parse(payload: dict) -> list[CanonicalJob]:
        jobs: list[CanonicalJob] = []
        for item in (payload or {}).get("results", []) or []:
            title = str(item.get("title") or "").strip()
            posted = _parse_created(item.get("created"))
            if not title or posted is None:
                continue
            loc = item.get("location") or {}
            area = loc.get("area") or []
            jobs.append(
                CanonicalJob(
                    external_id=str(item.get("id") or ""),
                    title=title,
                    company=str((item.get("company") or {}).get("display_name") or "").strip(),
                    description=str(item.get("description") or ""),
                    location=str(loc.get("display_name") or "").strip(),
                    # Adzuna's `area` is ordered broadest-first: ["India", "Karnataka", ...]
                    country=str(area[0]) if area else "",
                    remote="remote" in title.lower(),
                    salary_min=_num(item.get("salary_min")),
                    salary_max=_num(item.get("salary_max")),
                    salary_currency=_CURRENCY_BY_COUNTRY.get(
                        str(area[0]).lower() if area else "", ""
                    ),
                    url=str(item.get("redirect_url") or ""),
                    source="adzuna",
                    posted_at=posted,
                )
            )
        return jobs


_CURRENCY_BY_COUNTRY = {"india": "INR", "united states": "USD", "united kingdom": "GBP"}


def _num(value) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if num > 0 else None


def _parse_created(value) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
