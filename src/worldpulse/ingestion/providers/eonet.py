"""NASA EONET provider -- natural events (wildfires, storms, volcanoes...).

Real endpoint, no key, no cost:
`https://eonet.gsfc.nasa.gov/api/v3/events?status=all&start=YYYY-MM-DD&end=YYYY-MM-DD&limit=N`

A note on `status`: EONET's `status` parameter takes `open`, `closed` or
`all`. `status=open` returns only events that are *still ongoing*, which
is right for live polling but wrong for backfill (a wildfire from 2022 has
long since closed). This adapter therefore defaults to `status=all` and
lets the caller pass `status="open"` for a live-only poll.

Category ids in EONET v3 are: `drought`, `dustHaze`, `earthquakes`,
`floods`, `landslides`, `manmade`, `seaLakeIce`, `severeStorms`, `snow`,
`tempExtremes`, `volcanoes`, `waterColor`, `wildfires`. Each is mapped to
an `event_subtype` below.

Historical availability: EONET's curated event catalog starts around
2000-2002 depending on category, with dense coverage from ~2015.
Rate limits: none published; it is a small static-ish JSON API.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.ingestion import http_utils
from worldpulse.ingestion.providers.base import WorldEventProvider
from worldpulse.ingestion.providers.country_focus import get_focus, matches as focus_matches

logger = logging.getLogger(__name__)

EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

#: EONET category id -> (event_subtype, affected_channels, severity prior)
CATEGORY_MAP: dict[str, tuple[str, list[str], float]] = {
    "wildfires": ("wildfire", ["infrastructure", "supply_chain"], 0.55),
    "severeStorms": ("storm", ["infrastructure", "shipping_lanes", "supply_chain"], 0.62),
    "volcanoes": ("volcanic_eruption", ["infrastructure", "shipping_lanes"], 0.65),
    "floods": ("flooding", ["infrastructure", "supply_chain"], 0.58),
    "earthquakes": ("earthquake", ["infrastructure", "supply_chain"], 0.70),
    "landslides": ("landslide", ["infrastructure", "supply_chain"], 0.45),
    "drought": ("drought", ["supply_chain", "agriculture"], 0.50),
    "dustHaze": ("dust_storm", ["infrastructure"], 0.35),
    "seaLakeIce": ("sea_ice", ["shipping_lanes"], 0.35),
    "snow": ("snowstorm", ["infrastructure", "supply_chain"], 0.40),
    "tempExtremes": ("temperature_extreme", ["energy_supply", "supply_chain"], 0.48),
    "manmade": ("manmade_incident", ["infrastructure"], 0.45),
    "waterColor": ("water_quality", ["supply_chain"], 0.25),
}

_DEFAULT_MAPPING = ("natural_event", ["infrastructure"], 0.40)


class EONETProvider(WorldEventProvider):
    """NASA Earth Observatory Natural Event Tracker (EONET) v3 adapter."""

    name = "eonet"
    requires_key = False
    is_paid = False

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        status: str = "all",
        limit: int = 500,
    ) -> None:
        super().__init__()
        self._client = client
        self._status = status
        self._limit = limit

    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        events, _ = self._timed(self._fetch, start_time, end_time)
        return events

    def _fetch(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        start_time = _as_utc(start_time)
        end_time = _as_utc(end_time)
        params = {
            "status": self._status,
            # EONET's start/end are date-granularity (YYYY-MM-DD).
            "start": start_time.strftime("%Y-%m-%d"),
            "end": end_time.strftime("%Y-%m-%d"),
            "limit": self._limit,
        }
        payload = http_utils.http_get_json(EONET_EVENTS_URL, params=params, client=self._client)
        raw_events = payload.get("events") or [] if isinstance(payload, dict) else []

        events: list[WorldEvent] = []
        for raw in raw_events:
            if not isinstance(raw, dict):
                continue
            event = self._map_event(raw)
            if event is None:
                continue
            # EONET's date filter is day-granular; enforce the caller's
            # exact window ourselves.
            if not (start_time <= event.occurred_at <= end_time):
                continue
            focus = get_focus()
            if focus is not None and not focus_matches(
                focus, lat=event.latitude, lon=event.longitude,
                text=f"{event.headline} {event.summary}",
            ):
                # EONET's API takes no country/region filter, so this is a
                # client-side filter on the coordinates/title we already
                # parsed out of the response.
                continue
            events.append(event)
        events.sort(key=lambda e: e.occurred_at)
        logger.info("eonet: %d natural events for %s..%s", len(events),
                    params["start"], params["end"])
        return events

    def _map_event(self, raw: dict[str, Any]) -> Optional[WorldEvent]:
        eonet_id = str(raw.get("id") or "").strip()
        title = str(raw.get("title") or "").strip()
        if not eonet_id or not title:
            return None

        categories = [c for c in (raw.get("categories") or []) if isinstance(c, dict)]
        category_id = str(categories[0].get("id")) if categories else ""
        category_title = str(categories[0].get("title") or category_id) if categories else ""
        subtype, channels, severity_prior = CATEGORY_MAP.get(category_id, _DEFAULT_MAPPING)

        # `geometry` is a list of observations over the event's lifetime;
        # the earliest one is when the event started.
        geometries = [g for g in (raw.get("geometry") or []) if isinstance(g, dict)]
        occurred_at, latitude, longitude, magnitude, magnitude_unit = _earliest_geometry(geometries)
        if occurred_at is None:
            return None

        sources = [s for s in (raw.get("sources") or []) if isinstance(s, dict)]
        source_urls = [str(s.get("url")) for s in sources if s.get("url")]
        if raw.get("link"):
            source_urls.append(str(raw["link"]))

        severity = severity_prior
        # EONET only supplies magnitudes for a few categories (e.g. wildfire
        # acreage, storm wind speed); when present, nudge severity with it.
        if magnitude is not None and magnitude_unit:
            severity = min(1.0, severity + _magnitude_bump(magnitude, magnitude_unit))

        now = datetime.now(timezone.utc)
        closed = raw.get("closed")

        return WorldEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-eonet:{eonet_id}")),
            provider=self.name,
            provider_event_id=eonet_id,
            source_id=f"eonet:{eonet_id}",
            occurred_at=occurred_at,
            ingested_at=now,
            first_seen_at=now,
            event_type=EventDomain.DISASTER,
            event_subtype=subtype,
            event_subtype_detail=category_id,
            headline=title,
            summary=str(raw.get("description") or ""),
            countries=[],  # EONET gives coordinates, not country codes
            locations=[title],
            latitude=latitude,
            longitude=longitude,
            entities=[category_title] if category_title else [],
            affected_channels=list(channels),
            potential_assets=[],
            severity=round(severity, 3),
            source_confidence=0.9,
            corroboration_count=max(1, len(sources)),
            source_urls=source_urls[:5],
            source_name="NASA EONET",
            reasoning_summary=(
                f"NASA EONET v3 event {eonet_id}, category '{category_id}' -> subtype "
                f"'{subtype}'. occurred_at = earliest geometry observation date. "
                f"status={'closed ' + str(closed) if closed else 'open'}."
            ),
            raw_payload=dict(raw),
        )


def _earliest_geometry(
    geometries: list[dict[str, Any]],
) -> tuple[Optional[datetime], Optional[float], Optional[float], Optional[float], str]:
    best_at: Optional[datetime] = None
    best: Optional[dict[str, Any]] = None
    for geometry in geometries:
        when = _parse_eonet_date(geometry.get("date"))
        if when is None:
            continue
        if best_at is None or when < best_at:
            best_at, best = when, geometry
    if best is None or best_at is None:
        return None, None, None, None, ""

    latitude = longitude = None
    coords = best.get("coordinates")
    geom_type = str(best.get("type") or "").lower()
    if isinstance(coords, list) and coords:
        if geom_type == "point" and len(coords) >= 2:
            longitude, latitude = _safe_float(coords[0]), _safe_float(coords[1])
        else:
            # Polygon: use the centroid of the first ring so cross-source
            # geo matching still has a point to work with.
            ring = coords[0]
            while isinstance(ring, list) and ring and isinstance(ring[0], list) and \
                    ring[0] and isinstance(ring[0][0], list):
                ring = ring[0]
            points = [p for p in ring if isinstance(p, list) and len(p) >= 2] if isinstance(ring, list) else []
            if points:
                longitude = sum(_safe_float(p[0]) or 0.0 for p in points) / len(points)
                latitude = sum(_safe_float(p[1]) or 0.0 for p in points) / len(points)

    magnitude = _safe_float(best.get("magnitudeValue"))
    magnitude_unit = str(best.get("magnitudeUnit") or "")
    return best_at, latitude, longitude, magnitude, magnitude_unit


def _magnitude_bump(magnitude: float, unit: str) -> float:
    """Small severity nudge from EONET's category-specific magnitude."""
    unit_lower = unit.lower()
    if "acre" in unit_lower:
        # Wildfire acreage: 100k acres is a very large fire.
        return min(0.25, magnitude / 400_000.0)
    if "kts" in unit_lower or "knot" in unit_lower or "mph" in unit_lower:
        # Storm wind speed: 130kts+ is catastrophic.
        return min(0.30, max(0.0, (magnitude - 60.0) / 240.0))
    return 0.0


def _parse_eonet_date(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw.strip(), fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
