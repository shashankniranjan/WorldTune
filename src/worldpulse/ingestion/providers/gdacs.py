"""GDACS provider -- multi-hazard disaster alerts with severity scoring.

Which GDACS surface and why
---------------------------
GDACS (the EC/UN Global Disaster Alert and Coordination System) publishes
two public, key-free surfaces:

  * an **RSS/XML feed**: `https://www.gdacs.org/xml/rss.xml`
  * a **REST/GeoJSON API**:
    `https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP`

This adapter uses the **REST/GeoJSON API** as its primary source because
it returns structured fields WorldPulse needs and the RSS feed does not:
`alertlevel` (Green/Orange/Red) and `alertscore`, `eventtype` code,
`iso3`/`country`, `fromdate`/`todate`, `severitydata`, and a proper Point
geometry -- all as typed JSON rather than prose inside a `<description>`
element. The RSS feed is implemented as a fallback (`_fetch_rss`) because
it is occasionally reachable when the API host is not, and it needs no
JSON schema assumptions.

GDACS `eventtype` codes: `EQ` earthquake, `TC` tropical cyclone,
`FL` flood, `VO` volcano, `DR` drought, `WF` wildfire, `TS` tsunami.

Historical availability: `EVENTS4APP` returns the *current* alert list
(roughly the last few weeks of active events), so GDACS is a live/recent
provider, not a deep-history one. GDACS does host a historical archive per
event id, but there is no documented bulk range query, so `fetch_events`
filters the returned list to the requested window and will simply return
nothing for a window older than the feed's horizon.
Rate limits: none published; poll politely (every 15+ minutes).
"""
from __future__ import annotations

import logging
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.ingestion import http_utils
from worldpulse.ingestion.providers.base import WorldEventProvider
from worldpulse.ingestion.providers.country_focus import get_focus, matches as focus_matches

logger = logging.getLogger(__name__)

GDACS_EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"
GDACS_RSS_URL = "https://www.gdacs.org/xml/rss.xml"

#: GDACS eventtype -> (event_subtype, affected_channels)
EVENT_TYPE_MAP: dict[str, tuple[str, list[str]]] = {
    "EQ": ("earthquake", ["infrastructure", "supply_chain"]),
    "TC": ("tropical_cyclone", ["infrastructure", "shipping_lanes", "supply_chain"]),
    "FL": ("flooding", ["infrastructure", "supply_chain"]),
    "VO": ("volcanic_eruption", ["infrastructure", "shipping_lanes"]),
    "DR": ("drought", ["supply_chain", "agriculture"]),
    "WF": ("wildfire", ["infrastructure", "supply_chain"]),
    "TS": ("tsunami", ["infrastructure", "shipping_lanes", "supply_chain"]),
}

#: GDACS alert level -> WorldPulse severity floor. This is GDACS's own
#: expert-system humanitarian-impact judgement, so we trust it as the
#: primary severity signal rather than re-deriving one.
ALERT_LEVEL_SEVERITY: dict[str, float] = {
    "green": 0.35,
    "orange": 0.70,
    "red": 0.92,
}


class GDACSProvider(WorldEventProvider):
    """GDACS multi-hazard alert adapter (REST/GeoJSON primary, RSS fallback)."""

    name = "gdacs"
    requires_key = False
    is_paid = False

    def __init__(self, client: Optional[httpx.Client] = None, allow_rss_fallback: bool = True) -> None:
        super().__init__()
        self._client = client
        self._allow_rss_fallback = allow_rss_fallback

    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        events, _ = self._timed(self._fetch, start_time, end_time)
        return events

    def _fetch(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        start_time = _as_utc(start_time)
        end_time = _as_utc(end_time)
        try:
            events = self._fetch_geojson()
        except Exception as exc:  # noqa: BLE001
            if not self._allow_rss_fallback:
                raise
            logger.warning("gdacs: REST API failed (%s); falling back to RSS feed", exc)
            events = self._fetch_rss()

        in_window = [e for e in events if start_time <= e.occurred_at <= end_time]
        focus = get_focus()
        if focus is not None:
            # Neither GDACS surface (REST or RSS) takes a country/region
            # filter, so this is a client-side filter on the parsed
            # coordinates/country/headline -- applied once here so it
            # covers both `_fetch_geojson` and the `_fetch_rss` fallback.
            in_window = [
                e for e in in_window
                if focus_matches(focus, lat=e.latitude, lon=e.longitude,
                                  text=e.headline, countries=e.countries)
            ]
        in_window.sort(key=lambda e: e.occurred_at)
        logger.info("gdacs: %d/%d alerts inside %s..%s", len(in_window), len(events),
                    start_time.isoformat(), end_time.isoformat())
        return in_window

    # --- REST / GeoJSON ------------------------------------------------

    def _fetch_geojson(self) -> list[WorldEvent]:
        payload = http_utils.http_get_json(GDACS_EVENTS_URL, client=self._client)
        features = payload.get("features") or [] if isinstance(payload, dict) else []
        events: list[WorldEvent] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            event = self._map_feature(feature)
            if event is not None:
                events.append(event)
        return events

    def _map_feature(self, feature: dict[str, Any]) -> Optional[WorldEvent]:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}

        event_type_code = str(props.get("eventtype") or "").strip().upper()
        event_id = str(props.get("eventid") or "").strip()
        episode_id = str(props.get("episodeid") or "").strip()
        if not event_id:
            return None
        provider_event_id = f"{event_type_code}{event_id}" + (f"-{episode_id}" if episode_id else "")

        occurred_at = _parse_gdacs_date(props.get("fromdate")) or _parse_gdacs_date(props.get("datemodified"))
        if occurred_at is None:
            return None

        subtype, channels = EVENT_TYPE_MAP.get(event_type_code, ("natural_disaster", ["infrastructure"]))
        alert_level = str(props.get("alertlevel") or props.get("episodealertlevel") or "").strip().lower()
        severity = ALERT_LEVEL_SEVERITY.get(alert_level, 0.45)
        # `alertscore` is a 0-3-ish continuous score behind the traffic
        # light; use it to spread severity inside the band.
        alert_score = _safe_float(props.get("alertscore"))
        if alert_score is not None:
            severity = min(1.0, severity + min(0.08, max(0.0, alert_score) * 0.02))

        latitude = longitude = None
        coords = geometry.get("coordinates")
        if isinstance(coords, list) and len(coords) >= 2:
            longitude, latitude = _safe_float(coords[0]), _safe_float(coords[1])

        country = str(props.get("country") or "").strip()
        countries = [c.strip() for c in re.split(r"[,;]", country) if c.strip()][:4]
        name = str(props.get("eventname") or "").strip()
        severity_data = props.get("severitydata") or {}
        severity_text = str(severity_data.get("severitytext") or "") if isinstance(severity_data, dict) else ""

        headline = " ".join(part for part in [
            f"GDACS {alert_level.title() or 'Unclassified'} alert:",
            subtype.replace("_", " ").title(),
            f"'{name}'" if name else "",
            f"in {country}" if country else "",
        ] if part).strip()

        url_field = props.get("url") or {}
        source_urls: list[str] = []
        if isinstance(url_field, dict):
            for key in ("report", "details", "geometry"):
                value = url_field.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    source_urls.append(value)
        if not source_urls:
            source_urls.append(
                "https://www.gdacs.org/report.aspx?eventtype="
                f"{event_type_code}&eventid={event_id}"
            )

        now = datetime.now(timezone.utc)
        return WorldEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-gdacs:{provider_event_id}")),
            provider=self.name,
            provider_event_id=provider_event_id,
            source_id=f"gdacs:{provider_event_id}",
            occurred_at=occurred_at,
            ingested_at=now,
            first_seen_at=now,
            event_type=EventDomain.DISASTER,
            event_subtype=subtype,
            event_subtype_detail=f"{event_type_code}/{alert_level}" if alert_level else event_type_code,
            headline=headline or f"GDACS {event_type_code} {event_id}",
            summary=severity_text or _strip_html(str(props.get("htmldescription") or "")),
            countries=countries,
            locations=[part for part in [name, country] if part],
            latitude=latitude,
            longitude=longitude,
            entities=countries,
            affected_channels=list(channels),
            potential_assets=[],
            severity=round(severity, 3),
            source_confidence=0.93,
            corroboration_count=1,
            source_urls=source_urls[:3],
            source_name="GDACS",
            reasoning_summary=(
                f"GDACS event {provider_event_id} ({event_type_code}); severity derived from "
                f"GDACS's own alert level '{alert_level or 'unknown'}' "
                f"(alertscore={props.get('alertscore')}), which already encodes expected "
                f"humanitarian impact."
            ),
            raw_payload={"properties": dict(props), "geometry": dict(geometry)},
        )

    # --- RSS fallback --------------------------------------------------

    def _fetch_rss(self) -> list[WorldEvent]:
        """Parse the GDACS RSS feed.

        Each `<item>` carries `title`, `link`, `pubDate`, `description`
        plus GDACS-namespaced elements (`gdacs:eventtype`,
        `gdacs:eventid`, `gdacs:alertlevel`, `gdacs:country`) and
        `geo:Point/geo:lat|geo:long`. Namespace URIs are matched loosely by
        local tag name so a namespace-URI change upstream does not break us.
        """
        body = http_utils.http_get_text(GDACS_RSS_URL, client=self._client)
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise http_utils.ProviderHTTPError(f"gdacs: unparseable RSS: {exc}") from exc

        events: list[WorldEvent] = []
        now = datetime.now(timezone.utc)
        for item in root.iter():
            if _local_name(item.tag) != "item":
                continue
            fields: dict[str, str] = {}
            for child in item.iter():
                if child is item:
                    continue
                text = (child.text or "").strip()
                if text:
                    fields.setdefault(_local_name(child.tag), text)

            event_id = fields.get("eventid", "").strip()
            event_type_code = fields.get("eventtype", "").strip().upper()
            title = fields.get("title", "").strip()
            if not title:
                continue
            provider_event_id = f"{event_type_code}{event_id}" if event_id else title[:80]
            occurred_at = _parse_gdacs_date(fields.get("fromdate") or fields.get("pubDate"))
            if occurred_at is None:
                continue
            subtype, channels = EVENT_TYPE_MAP.get(event_type_code, ("natural_disaster", ["infrastructure"]))
            alert_level = fields.get("alertlevel", "").strip().lower()
            country = fields.get("country", "").strip()
            link = fields.get("link", "").strip()

            events.append(WorldEvent(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-gdacs:{provider_event_id}")),
                provider=self.name,
                provider_event_id=provider_event_id,
                source_id=f"gdacs:{provider_event_id}",
                occurred_at=occurred_at,
                ingested_at=now,
                first_seen_at=now,
                event_type=EventDomain.DISASTER,
                event_subtype=subtype,
                event_subtype_detail=f"{event_type_code}/{alert_level}" if alert_level else event_type_code,
                headline=title,
                summary=_strip_html(fields.get("description", "")),
                countries=[country] if country else [],
                locations=[country] if country else [],
                latitude=_safe_float(fields.get("lat")),
                longitude=_safe_float(fields.get("long")),
                entities=[country] if country else [],
                affected_channels=list(channels),
                potential_assets=[],
                severity=round(ALERT_LEVEL_SEVERITY.get(alert_level, 0.45), 3),
                source_confidence=0.9,
                corroboration_count=1,
                source_urls=[link] if link else [],
                source_name="GDACS (RSS)",
                reasoning_summary=(
                    f"GDACS RSS item {provider_event_id}; severity from alert level "
                    f"'{alert_level or 'unknown'}'."
                ),
                raw_payload=dict(fields),
            ))
        return events


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()[:800]


def _parse_gdacs_date(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
