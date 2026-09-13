"""USGS earthquake provider -- no API key, no cost, full historical depth.

Two real endpoints are used, for two different jobs:

  * **Live/recent**:
    `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson`
    (also `all_day`/`all_week`/`all_month`, and magnitude-filtered
    variants such as `4.5_day.geojson`). These are static, CDN-cached
    files -- cheap to poll every few minutes.
  * **Historical range queries**:
    `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=...&endtime=...&minmagnitude=...`
    This is the FDSN event web service and it is the reason historical
    backfill genuinely works: the ANSS ComCat catalog behind it reaches
    back to **1900** for significant events (and to the 1960s-70s with
    good global instrumental coverage), so `--start 2010-01-01` is a real,
    answerable query rather than an aspiration.

`fetch_events` picks the endpoint automatically: the cached summary feed
when the requested window is inside the last hour, the FDSN query
otherwise.

Rate limits: USGS asks for reasonable use rather than publishing a hard
quota. FDSN queries returning more than 20,000 events are rejected
(HTTP 400), so long backfills must be chunked -- `fetch_events` chunks by
`max_days_per_request` days automatically.
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
from worldpulse.ingestion.providers.country_focus import get_focus

logger = logging.getLogger(__name__)

SUMMARY_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
FDSN_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

#: FDSN rejects result sets above this size with HTTP 400.
FDSN_MAX_EVENTS = 20_000

#: `place` strings end in a country or a US state. Anything matching a US
#: state (or the "of California"-style tail) is mapped to USA.
_US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming",
    "puerto rico", "cnmi", "guam", "us virgin islands",
}

#: Normalizations for the country names USGS uses in `place`.
_PLACE_COUNTRY_ALIASES = {
    "taiwan": "Taiwan",
    "japan": "Japan",
    "indonesia": "Indonesia",
    "philippines": "Philippines",
    "chile": "Chile",
    "peru": "Peru",
    "mexico": "Mexico",
    "turkey": "Turkey",
    "iran": "Iran",
    "china": "China",
    "russia": "Russia",
    "india": "India",
    "new zealand": "New Zealand",
    "papua new guinea": "Papua New Guinea",
    "greece": "Greece",
    "italy": "Italy",
    "afghanistan": "Afghanistan",
    "pakistan": "Pakistan",
    "nepal": "Nepal",
    "ecuador": "Ecuador",
    "colombia": "Colombia",
    "vanuatu": "Vanuatu",
    "tonga": "Tonga",
    "fiji": "Fiji",
    "morocco": "Morocco",
    "syria": "Syria",
    "myanmar": "Myanmar",
}


def magnitude_to_severity(magnitude: float | None, *, tsunami: int = 0,
                          alert: str | None = None) -> float:
    """Map Richter/moment magnitude onto WorldPulse's 0-1 severity scale.

    A linear normalization of the 0-9 magnitude range badly understates
    large quakes (magnitude is logarithmic in energy), so the mapping is
    linear-with-floors: `(mag - 2.5) / 6.0` clamped to [0, 1], then pushed
    up by hard floors at magnitude 6 / 7 / 8, plus small bumps for a
    tsunami flag and a PAGER alert level of orange/red.
    """
    if magnitude is None:
        return 0.3
    base = (float(magnitude) - 2.5) / 6.0
    severity = max(0.0, min(1.0, base))
    if magnitude >= 8.0:
        severity = max(severity, 0.97)
    elif magnitude >= 7.0:
        severity = max(severity, 0.88)
    elif magnitude >= 6.0:
        severity = max(severity, 0.75)
    if tsunami:
        severity = min(1.0, severity + 0.05)
    if (alert or "").lower() in ("orange", "red"):
        severity = min(1.0, severity + 0.05)
    return round(severity, 3)


def countries_from_place(place: str | None) -> tuple[list[str], list[str]]:
    """Best-effort `(countries, locations)` from a USGS `place` string.

    USGS `place` looks like `"14 km SSE of Hualien City, Taiwan"` or
    `"7km NW of The Geysers, CA"`. We take the text after the last comma
    as the region and normalize it.
    """
    if not place:
        return [], []
    locations = [place.strip()]
    tail = place.split(",")[-1].strip()
    key = tail.lower()
    if key in _US_STATES or (len(tail) == 2 and tail.isupper()):
        return ["USA"], locations
    for fragment, canonical in _PLACE_COUNTRY_ALIASES.items():
        if fragment in key:
            return [canonical], locations
    if tail and not tail.lower().startswith("region"):
        return [tail], locations
    return [], locations


class USGSProvider(WorldEventProvider):
    """USGS earthquake adapter (summary feed + FDSN historical query)."""

    name = "usgs"
    requires_key = False
    is_paid = False

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        min_magnitude: float | None = None,
        max_days_per_request: int = 30,
    ) -> None:
        super().__init__()
        self._client = client
        self._min_magnitude = (
            settings.usgs_min_magnitude if min_magnitude is None else min_magnitude
        )
        self._max_days_per_request = max(1, max_days_per_request)

    # --- WorldEventProvider -------------------------------------------

    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        events, _ = self._timed(self._fetch, start_time, end_time)
        return events

    def _fetch(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        start_time = _as_utc(start_time)
        end_time = _as_utc(end_time)
        now = datetime.now(timezone.utc)

        if start_time >= now - timedelta(hours=1):
            # Fully inside the last hour -> the CDN-cached summary feed is
            # cheaper and fresher than an FDSN query.
            features = self._fetch_summary_feed()
        else:
            features = self._fetch_fdsn_range(start_time, end_time)

        focus = get_focus()
        if focus is not None:
            # The summary feed has no bbox param, so filter client-side;
            # the FDSN query already narrowed server-side (see below), this
            # is a cheap safety net that also catches the summary-feed path.
            min_lat, max_lat, min_lon, max_lon = focus.bbox
            filtered = []
            for f in features:
                coords = ((f.get("geometry") or {}).get("coordinates") or [])
                if len(coords) < 2:
                    continue
                lon, lat = coords[0], coords[1]
                if lon is None or lat is None:
                    continue
                if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                    filtered.append(f)
            features = filtered

        events: list[WorldEvent] = []
        for feature in features:
            event = self._feature_to_event(feature)
            if event is None:
                continue
            if not (start_time <= event.occurred_at <= end_time):
                continue
            if event.raw_payload and (event.raw_payload.get("properties") or {}).get("mag") is not None:
                mag = (event.raw_payload["properties"] or {}).get("mag")
                if mag is not None and float(mag) < self._min_magnitude:
                    continue
            events.append(event)
        events.sort(key=lambda e: e.occurred_at)
        logger.info("usgs: %d earthquakes for %s..%s", len(events),
                    start_time.isoformat(), end_time.isoformat())
        return events

    # --- HTTP ----------------------------------------------------------

    def _fetch_summary_feed(self) -> list[dict[str, Any]]:
        payload = http_utils.http_get_json(SUMMARY_FEED_URL, client=self._client)
        return _features(payload)

    def _fetch_fdsn_range(self, start_time: datetime, end_time: datetime) -> list[dict[str, Any]]:
        """FDSN event query, chunked so we never trip the 20k result cap."""
        features: list[dict[str, Any]] = []
        chunk = timedelta(days=self._max_days_per_request)
        cursor = start_time
        while cursor < end_time:
            chunk_end = min(cursor + chunk, end_time)
            params = {
                "format": "geojson",
                # FDSN accepts ISO-8601; it treats naive times as UTC.
                "starttime": cursor.strftime("%Y-%m-%dT%H:%M:%S"),
                "endtime": chunk_end.strftime("%Y-%m-%dT%H:%M:%S"),
                "minmagnitude": self._min_magnitude,
                "orderby": "time-asc",
                "limit": FDSN_MAX_EVENTS,
            }
            focus = get_focus()
            if focus is not None:
                min_lat, max_lat, min_lon, max_lon = focus.bbox
                params.update({
                    "minlatitude": min_lat, "maxlatitude": max_lat,
                    "minlongitude": min_lon, "maxlongitude": max_lon,
                })
            payload = http_utils.http_get_json(FDSN_QUERY_URL, params=params, client=self._client)
            features.extend(_features(payload))
            cursor = chunk_end
        return features

    # --- Mapping -------------------------------------------------------

    def _feature_to_event(self, feature: dict[str, Any]) -> Optional[WorldEvent]:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        usgs_id = str(feature.get("id") or props.get("code") or "").strip()
        epoch_ms = props.get("time")
        if not usgs_id or epoch_ms is None:
            return None
        try:
            occurred_at = datetime.fromtimestamp(float(epoch_ms) / 1000.0, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

        coords = geometry.get("coordinates") or []
        longitude = float(coords[0]) if len(coords) > 0 and coords[0] is not None else None
        latitude = float(coords[1]) if len(coords) > 1 and coords[1] is not None else None
        depth_km = float(coords[2]) if len(coords) > 2 and coords[2] is not None else None

        magnitude = props.get("mag")
        place = props.get("place")
        countries, locations = countries_from_place(place)
        title = props.get("title") or (
            f"M {magnitude} - {place}" if magnitude is not None else f"Earthquake - {place}"
        )
        url = props.get("url")
        now = datetime.now(timezone.utc)
        severity = magnitude_to_severity(
            float(magnitude) if magnitude is not None else None,
            tsunami=int(props.get("tsunami") or 0),
            alert=props.get("alert"),
        )

        return WorldEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-usgs:{usgs_id}")),
            provider=self.name,
            provider_event_id=usgs_id,
            source_id=f"usgs:{usgs_id}",
            occurred_at=occurred_at,
            ingested_at=now,
            first_seen_at=now,
            event_type=EventDomain.DISASTER,
            event_subtype="earthquake",
            event_subtype_detail=str(props.get("magType") or ""),
            headline=str(title),
            summary=(
                f"Magnitude {magnitude} earthquake"
                + (f" at {depth_km:.1f} km depth" if depth_km is not None else "")
                + (f", {place}" if place else "")
            ),
            countries=countries,
            locations=locations,
            latitude=latitude,
            longitude=longitude,
            entities=list(countries),
            affected_channels=["infrastructure", "supply_chain"],
            potential_assets=[],  # impact-channel layer decides
            severity=severity,
            # An instrumented seismic network is about as authoritative as
            # a source gets.
            source_confidence=0.98,
            corroboration_count=1,
            source_urls=[str(url)] if url else [],
            source_name="USGS ANSS ComCat",
            reasoning_summary=(
                f"USGS ComCat event {usgs_id}: magnitude {magnitude} ({props.get('magType')}), "
                f"severity {severity} derived from magnitude with floors at M6/M7/M8, "
                f"tsunami={props.get('tsunami')}, PAGER alert={props.get('alert')}."
            ),
            raw_payload={"id": usgs_id, "properties": dict(props), "geometry": dict(geometry)},
        )


def _features(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    return [f for f in (payload.get("features") or []) if isinstance(f, dict)]


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
