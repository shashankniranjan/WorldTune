"""ACLED provider -- curated political violence / protest event data.

ACLED (Armed Conflict Location & Event Data Project) is the highest-quality
structured conflict-event dataset available at no cost, but it requires
free registration and, since 2024, an OAuth password-grant token flow:

  1. POST `https://acleddata.com/oauth/token`
       {username: <ACLED_EMAIL>, password: <ACLED_PASSWORD>,
        grant_type: "password", client_id: "acled"}
     -> {"access_token": "...", "refresh_token": "...",
         "token_type": "Bearer", "expires_in": 3600}
  2. GET `https://acleddata.com/api/acled/read`
       with `Authorization: Bearer <access_token>` and query params
       `event_date=<start>|<end>`, `event_date_where=BETWEEN`,
       `limit`, `page`, `_format=json`.

Response shape (`/api/acled/read`):

    {"status": 200, "success": true, "count": 500, "data": [
       {"event_id_cnty": "SYR12345", "event_date": "2024-01-15",
        "year": "2024", "event_type": "Battles",
        "sub_event_type": "Armed clash", "actor1": "...", "actor2": "...",
        "country": "Syria", "admin1": "...", "location": "...",
        "latitude": "35.12", "longitude": "36.75",
        "fatalities": "7", "notes": "...", "source": "...",
        "source_scale": "..."}, ...]}

This provider is **optional and never in the default `EVENT_PROVIDERS`**:
`is_available()` returns False unless both `ACLED_EMAIL` and
`ACLED_PASSWORD` are set, and it disables itself cleanly otherwise.

Historical availability: 1997->present for Africa, 2010->present for Asia,
and global coverage from 2018; data is published weekly (Tuesdays) with a
~1 week lag, so ACLED is a *research/backfill* source rather than a
low-latency one.
Rate limits: the free academic tier is documented as a limited number of
API calls and rows per month; page through with `limit`/`page` and cache.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from worldpulse.config import settings
from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.ingestion import http_utils
from worldpulse.ingestion.providers.base import WorldEventProvider

logger = logging.getLogger(__name__)

ACLED_TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_READ_URL = "https://acleddata.com/api/acled/read"
ACLED_OAUTH_CLIENT_ID = "acled"

#: ACLED `event_type` -> (WorldPulse domain, subtype, channels)
EVENT_TYPE_MAP: dict[str, tuple[EventDomain, str, list[str]]] = {
    "battles": (EventDomain.MILITARY, "armed_clash", ["regional_security"]),
    "explosions/remote violence": (
        EventDomain.MILITARY, "missile_strike", ["regional_security", "shipping_lanes"]
    ),
    "violence against civilians": (
        EventDomain.CONFLICT, "civilian_violence", ["regional_security"]
    ),
    "protests": (EventDomain.CONFLICT, "protest", ["regional_security"]),
    "riots": (EventDomain.CONFLICT, "riot", ["regional_security", "infrastructure"]),
    "strategic developments": (
        EventDomain.CONFLICT, "strategic_development", ["diplomatic_relations"]
    ),
}


class ACLEDProvider(WorldEventProvider):
    """ACLED conflict-event adapter. Optional; free key, off by default."""

    name = "acled"
    requires_key = True
    is_paid = False

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        email: str | None = None,
        password: str | None = None,
        page_limit: int = 500,
        max_pages: int = 10,
    ) -> None:
        super().__init__()
        self._client = client
        self._email = email if email is not None else settings.acled_email
        self._password = password if password is not None else settings.acled_password
        self._page_limit = page_limit
        self._max_pages = max_pages
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self.health.available = self.is_available()
        self.health.disabled_reason = self.disabled_reason()

    def is_available(self) -> bool:
        return bool(self._email and self._password)

    def disabled_reason(self) -> str | None:
        if self.is_available():
            return None
        return (
            "ACLEDProvider disabled: ACLED_EMAIL and/or ACLED_PASSWORD not set. "
            "Free registration at https://acleddata.com/register/."
        )

    # --- WorldEventProvider -------------------------------------------

    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        if not self.is_available():
            logger.info("%s", self.disabled_reason())
            self.health.available = False
            self.health.disabled_reason = self.disabled_reason()
            return []
        events, _ = self._timed(self._fetch, start_time, end_time)
        return events

    def _fetch(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        start_time = _as_utc(start_time)
        end_time = _as_utc(end_time)
        token = self._ensure_token()

        events: list[WorldEvent] = []
        for page in range(1, self._max_pages + 1):
            params = {
                "_format": "json",
                "event_date": f"{start_time.strftime('%Y-%m-%d')}|{end_time.strftime('%Y-%m-%d')}",
                "event_date_where": "BETWEEN",
                "limit": self._page_limit,
                "page": page,
            }
            payload = http_utils.http_get_json(
                ACLED_READ_URL,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                client=self._client,
            )
            rows = payload.get("data") or [] if isinstance(payload, dict) else []
            if not rows:
                break
            for row in rows:
                if not isinstance(row, dict):
                    continue
                event = self._map_row(row)
                if event is not None:
                    events.append(event)
            if len(rows) < self._page_limit:
                break

        events.sort(key=lambda e: e.occurred_at)
        logger.info("acled: %d conflict events for %s..%s", len(events),
                    start_time.date(), end_time.date())
        return events

    # --- OAuth ---------------------------------------------------------

    def _ensure_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._token and self._token_expires_at and now < self._token_expires_at:
            return self._token
        response = http_utils.request_with_retry(
            ACLED_TOKEN_URL,
            method="POST",
            params={
                "username": self._email,
                "password": self._password,
                "grant_type": "password",
                "client_id": ACLED_OAUTH_CLIENT_ID,
            },
            client=self._client,
        )
        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise http_utils.ProviderHTTPError(f"acled: token endpoint returned non-JSON: {exc}") from exc
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not token:
            raise http_utils.ProviderHTTPError(
                "acled: OAuth token response contained no access_token "
                "(check ACLED_EMAIL / ACLED_PASSWORD)"
            )
        expires_in = payload.get("expires_in") or 3600
        try:
            expires_in = int(expires_in)
        except (TypeError, ValueError):
            expires_in = 3600
        self._token = str(token)
        # Refresh a minute early to avoid racing expiry mid-page.
        self._token_expires_at = now + timedelta(seconds=max(60, expires_in - 60))
        return self._token

    # --- Mapping -------------------------------------------------------

    def _map_row(self, row: dict[str, Any]) -> Optional[WorldEvent]:
        acled_id = str(row.get("event_id_cnty") or row.get("data_id") or "").strip()
        occurred_at = _parse_date(row.get("event_date"))
        if not acled_id or occurred_at is None:
            return None

        raw_event_type = str(row.get("event_type") or "").strip()
        domain, subtype, channels = EVENT_TYPE_MAP.get(
            raw_event_type.lower(), (EventDomain.CONFLICT, "conflict_event", ["regional_security"])
        )
        sub_event_type = str(row.get("sub_event_type") or "").strip()
        country = str(row.get("country") or "").strip()
        location = str(row.get("location") or "").strip()
        fatalities = _safe_int(row.get("fatalities")) or 0
        actors = [str(row.get(key) or "").strip() for key in ("actor1", "actor2")]
        actors = [a for a in actors if a]

        # ACLED gives no severity field; fatalities is the best available
        # proxy. Saturating at ~200 deaths keeps a single mass-casualty
        # event from pinning severity at 1.0 for everything above it.
        severity = min(0.95, 0.30 + min(0.60, fatalities / 200.0 * 0.60))

        now = datetime.now(timezone.utc)
        headline = " ".join(part for part in [
            sub_event_type or raw_event_type or "Conflict event",
            f"in {location}" if location else "",
            f"({country})" if country else "",
            f"- {fatalities} fatalities" if fatalities else "",
        ] if part).strip()

        return WorldEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-acled:{acled_id}")),
            provider=self.name,
            provider_event_id=acled_id,
            source_id=f"acled:{acled_id}",
            occurred_at=occurred_at,
            ingested_at=now,
            first_seen_at=now,
            event_type=domain,
            event_subtype=subtype,
            event_subtype_detail=sub_event_type,
            headline=headline,
            summary=str(row.get("notes") or "")[:1000],
            countries=[country] if country else [],
            locations=[part for part in [location, str(row.get("admin1") or "").strip()] if part],
            latitude=_safe_float(row.get("latitude")),
            longitude=_safe_float(row.get("longitude")),
            entities=actors + ([country] if country else []),
            affected_channels=list(channels),
            potential_assets=[],
            severity=round(severity, 3),
            # ACLED is hand-coded from vetted sources: high confidence.
            source_confidence=0.95,
            corroboration_count=1,
            source_urls=[],
            source_name=f"ACLED ({row.get('source') or 'unspecified'})",
            reasoning_summary=(
                f"ACLED event {acled_id}: event_type='{raw_event_type}', "
                f"sub_event_type='{sub_event_type}', fatalities={fatalities}. Severity is a "
                f"saturating function of fatalities (ACLED supplies no severity field)."
            ),
            raw_payload=dict(row),
        )


def _parse_date(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %B %Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
