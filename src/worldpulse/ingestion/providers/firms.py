"""NASA FIRMS provider -- active fire detections, clustered into wildfires.

Authentication: FIRMS needs a **free MAP_KEY**. Register (no cost, instant)
at https://firms.modaps.eosdis.nasa.gov/api/ and set
`NASA_FIRMS_API_KEY`. With the key absent, `is_available()` returns False
and the registry skips this provider entirely -- WorldPulse never crashes
for a missing FIRMS key.

Real endpoint (Area CSV API):

    https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}/{DATE}

  * `SOURCE`: `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT` (near
    real-time, last ~2 months) or `VIIRS_SNPP_SP`, `MODIS_SP` (standard
    processing, the full archive from 2000 for MODIS / 2012 for VIIRS).
  * `AREA`: `west,south,east,north` in decimal degrees, or the literal
    `world`.
  * `DAY_RANGE`: 1-10 days.
  * `DATE` (optional): `YYYY-MM-DD` start date; omitted means "ending today".

CSV columns (VIIRS): `latitude, longitude, bright_ti4, scan, track,
acq_date, acq_time, satellite, instrument, confidence, version,
bright_ti5, frp, daynight`. MODIS is the same shape with `brightness` and
`bright_t31` in place of the two `bright_ti*` columns. This adapter reads
by **column name** from the CSV header, so either layout works.

Why clustering: FIRMS returns one row per satellite fire *pixel*. A single
large wildfire is thousands of pixels across many overpasses; emitting one
`WorldEvent` per pixel would swamp the event table and destroy the
dedup/novelty signal. `_cluster_detections` therefore groups detections
within `firms_cluster_radius_km` and `firms_cluster_window_hours` into one
wildfire-cluster event, whose severity is driven by detection count and
total FRP (fire radiative power, in MW).

Rate limits: FIRMS documents a soft limit of ~5000 transactions per
10-minute window per MAP_KEY, and the API rejects `DAY_RANGE` > 10, so
longer windows are fetched as consecutive 10-day chunks.
"""
from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import httpx

from worldpulse.config import settings
from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.ingestion import http_utils
from worldpulse.ingestion.providers.base import WorldEventProvider, haversine_km

logger = logging.getLogger(__name__)

FIRMS_AREA_CSV_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

#: FIRMS refuses a DAY_RANGE above this.
MAX_DAY_RANGE = 10

#: Regions worth monitoring for market-relevant wildfire activity, as
#: `west,south,east,north`. Querying `world` daily returns hundreds of
#: thousands of pixels; these bounding boxes keep volume sane while
#: covering the fire-prone areas that actually move commodity/insurance
#: prices.
DEFAULT_AREAS: dict[str, str] = {
    "north_america_west": "-130,30,-100,60",
    "mediterranean": "-10,32,42,48",
    "australia": "112,-44,154,-10",
    "amazon": "-75,-20,-44,5",
    "siberia": "60,50,140,72",
    "southeast_asia": "95,-11,142,22",
}


class FIRMSProvider(WorldEventProvider):
    """NASA FIRMS active-fire adapter with spatio-temporal clustering."""

    name = "firms"
    requires_key = True
    is_paid = False

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        map_key: str | None = None,
        source: str = "VIIRS_SNPP_NRT",
        areas: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._client = client
        self._map_key = map_key if map_key is not None else settings.nasa_firms_api_key
        self._source = source
        self._areas = areas if areas is not None else DEFAULT_AREAS
        self.health.available = self.is_available()
        self.health.disabled_reason = self.disabled_reason()

    # --- availability --------------------------------------------------

    def is_available(self) -> bool:
        return bool(self._map_key)

    def disabled_reason(self) -> str | None:
        if self.is_available():
            return None
        return (
            "FIRMSProvider disabled: NASA_FIRMS_API_KEY not set. Get a free MAP_KEY at "
            "https://firms.modaps.eosdis.nasa.gov/api/ (no cost, instant)."
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
        detections: list[dict[str, Any]] = []
        for area_name, bbox in self._areas.items():
            for chunk_start, day_range in _chunk_days(start_time, end_time):
                url = (
                    f"{FIRMS_AREA_CSV_BASE}/{self._map_key}/{self._source}/{bbox}/"
                    f"{day_range}/{chunk_start.strftime('%Y-%m-%d')}"
                )
                try:
                    body = http_utils.http_get_text(url, client=self._client)
                except Exception as exc:  # noqa: BLE001 - one area failing is survivable
                    logger.warning("firms: area %s chunk %s failed: %s", area_name,
                                   chunk_start.date(), exc)
                    continue
                for row in parse_firms_csv(body):
                    row["_area"] = area_name
                    detections.append(row)

        in_window = [
            d for d in detections
            if d.get("acquired_at") and start_time <= d["acquired_at"] <= end_time
        ]
        clusters = _cluster_detections(
            in_window,
            radius_km=settings.firms_cluster_radius_km,
            window_hours=settings.firms_cluster_window_hours,
        )
        events = [
            self._cluster_to_event(cluster)
            for cluster in clusters
            if len(cluster) >= settings.firms_min_cluster_detections
        ]
        events = [e for e in events if e is not None]
        events.sort(key=lambda e: e.occurred_at)
        logger.info("firms: %d detections -> %d clusters -> %d events",
                    len(in_window), len(clusters), len(events))
        return events

    # --- Mapping -------------------------------------------------------

    def _cluster_to_event(self, cluster: list[dict[str, Any]]) -> Optional[WorldEvent]:
        if not cluster:
            return None
        earliest = min(cluster, key=lambda d: d["acquired_at"])
        latest = max(cluster, key=lambda d: d["acquired_at"])
        latitude = sum(d["latitude"] for d in cluster) / len(cluster)
        longitude = sum(d["longitude"] for d in cluster) / len(cluster)
        total_frp = sum(d.get("frp") or 0.0 for d in cluster)
        area_name = str(earliest.get("_area") or "unknown")
        high_confidence = sum(1 for d in cluster if _is_high_confidence(d.get("confidence")))

        # Severity from detection count + radiated power. A ~500-pixel,
        # multi-GW cluster is a major fire; a 10-pixel one is routine.
        severity = min(
            0.95,
            0.25
            + min(0.40, len(cluster) / 500.0 * 0.40)
            + min(0.30, total_frp / 20_000.0 * 0.30),
        )

        # Cluster identity must be stable across re-runs so re-ingesting a
        # window upserts rather than duplicates: quantize the centroid and
        # the start hour.
        cluster_key = (
            f"{self._source}|{area_name}|{latitude:.2f},{longitude:.2f}|"
            f"{earliest['acquired_at'].strftime('%Y%m%dT%H')}"
        )
        now = datetime.now(timezone.utc)
        duration_h = (latest["acquired_at"] - earliest["acquired_at"]).total_seconds() / 3600.0

        return WorldEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-firms:{cluster_key}")),
            provider=self.name,
            provider_event_id=cluster_key,
            source_id=f"firms:{cluster_key}",
            occurred_at=earliest["acquired_at"],
            ingested_at=now,
            first_seen_at=now,
            event_type=EventDomain.DISASTER,
            event_subtype="wildfire",
            event_subtype_detail=f"{self._source}/{area_name}",
            headline=(
                f"Wildfire cluster: {len(cluster)} active-fire detections near "
                f"{latitude:.2f}, {longitude:.2f} ({area_name.replace('_', ' ')})"
            ),
            summary=(
                f"{len(cluster)} FIRMS {self._source} detections ({high_confidence} high-confidence) "
                f"over {duration_h:.1f}h, total FRP {total_frp:.0f} MW."
            ),
            countries=[],
            locations=[area_name.replace("_", " ")],
            latitude=round(latitude, 4),
            longitude=round(longitude, 4),
            entities=["Wildfire"],
            affected_channels=["infrastructure", "supply_chain"],
            potential_assets=[],
            severity=round(severity, 3),
            source_confidence=0.85,
            # Each satellite overpass is an independent observation.
            corroboration_count=min(5, max(1, len({d["acquired_at"].date() for d in cluster}))),
            source_urls=["https://firms.modaps.eosdis.nasa.gov/map/"],
            source_name=f"NASA FIRMS ({self._source})",
            reasoning_summary=(
                f"Aggregated {len(cluster)} FIRMS fire pixels within "
                f"{settings.firms_cluster_radius_km} km / "
                f"{settings.firms_cluster_window_hours} h into one wildfire-cluster event. "
                f"Severity from detection count ({len(cluster)}) and total FRP ({total_frp:.0f} MW)."
            ),
            raw_payload={
                "source": self._source,
                "area": area_name,
                "detection_count": len(cluster),
                "total_frp_mw": round(total_frp, 2),
                "first_detection": {k: v for k, v in earliest.items() if k != "acquired_at"},
            },
        )


# --- CSV parsing + clustering ------------------------------------------

def parse_firms_csv(body: str) -> list[dict[str, Any]]:
    """Parse a FIRMS area-CSV response into detection dicts.

    Reads by header name so both the VIIRS (`bright_ti4`/`bright_ti5`) and
    MODIS (`brightness`/`bright_t31`) column layouts parse unchanged.
    """
    body = (body or "").strip()
    if not body:
        return []
    # A bad MAP_KEY returns an HTML/plain-text error, not CSV.
    if body.lower().startswith(("<", "invalid", "error")):
        raise http_utils.ProviderHTTPError(f"firms: non-CSV response: {body[:200]}")

    reader = csv.DictReader(io.StringIO(body))
    detections: list[dict[str, Any]] = []
    for row in reader:
        latitude = _safe_float(row.get("latitude"))
        longitude = _safe_float(row.get("longitude"))
        acquired_at = _parse_acq(row.get("acq_date"), row.get("acq_time"))
        if latitude is None or longitude is None or acquired_at is None:
            continue
        detections.append({
            "latitude": latitude,
            "longitude": longitude,
            "acquired_at": acquired_at,
            "brightness": _safe_float(row.get("bright_ti4") or row.get("brightness")),
            "frp": _safe_float(row.get("frp")),
            "confidence": (row.get("confidence") or "").strip(),
            "satellite": (row.get("satellite") or "").strip(),
            "instrument": (row.get("instrument") or "").strip(),
            "daynight": (row.get("daynight") or "").strip(),
        })
    return detections


def _cluster_detections(
    detections: list[dict[str, Any]], *, radius_km: float, window_hours: float
) -> list[list[dict[str, Any]]]:
    """Greedy single-link spatio-temporal clustering.

    Detections are processed in time order; each is attached to the first
    open cluster whose running centroid is within `radius_km` and whose
    latest detection is within `window_hours`, otherwise it starts a new
    cluster. Greedy (rather than DBSCAN) keeps this dependency-free and
    deterministic, which matters for reproducible tests.
    """
    ordered = sorted(detections, key=lambda d: d["acquired_at"])
    clusters: list[list[dict[str, Any]]] = []
    centroids: list[tuple[float, float, datetime]] = []  # (lat, lon, last_seen)
    window = timedelta(hours=window_hours)

    for detection in ordered:
        placed = False
        for index, (c_lat, c_lon, c_last) in enumerate(centroids):
            if detection["acquired_at"] - c_last > window:
                continue
            if haversine_km(c_lat, c_lon, detection["latitude"], detection["longitude"]) > radius_km:
                continue
            clusters[index].append(detection)
            members = clusters[index]
            centroids[index] = (
                sum(m["latitude"] for m in members) / len(members),
                sum(m["longitude"] for m in members) / len(members),
                max(c_last, detection["acquired_at"]),
            )
            placed = True
            break
        if not placed:
            clusters.append([detection])
            centroids.append((detection["latitude"], detection["longitude"], detection["acquired_at"]))
    return clusters


def _chunk_days(start: datetime, end: datetime) -> Iterable[tuple[datetime, int]]:
    """Yield `(chunk_start, day_range)` pairs of at most MAX_DAY_RANGE days."""
    cursor = start
    while cursor < end:
        remaining_days = max(1, min(MAX_DAY_RANGE, (end - cursor).days + 1))
        yield cursor, remaining_days
        cursor = cursor + timedelta(days=remaining_days)


def _is_high_confidence(value: Any) -> bool:
    """VIIRS reports `l`/`n`/`h`; MODIS reports 0-100."""
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in ("h", "high"):
        return True
    numeric = _safe_float(text)
    return numeric is not None and numeric >= 80.0


def _parse_acq(acq_date: Any, acq_time: Any) -> Optional[datetime]:
    """FIRMS splits acquisition into `YYYY-MM-DD` + `HHMM` (UTC)."""
    if not isinstance(acq_date, str) or not acq_date.strip():
        return None
    raw_time = str(acq_time or "0").strip() or "0"
    try:
        minutes_of_day = int(float(raw_time))
    except ValueError:
        minutes_of_day = 0
    hours, minutes = divmod(minutes_of_day, 100)
    try:
        day = datetime.strptime(acq_date.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return day + timedelta(hours=min(23, hours), minutes=min(59, minutes))


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
