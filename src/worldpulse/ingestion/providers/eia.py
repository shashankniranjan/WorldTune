"""EIA provider -- energy context/feature series (NOT an event source).

Same rationale as `fred.py`: the US Energy Information Administration
publishes energy *time series* (crude stocks, refinery utilization,
production, spot prices). A weekly inventory print is a feature, not a
newsworthy discrete event, so `EIAProvider` implements
`ContextDataProvider` and **not** `WorldEventProvider`. It cannot be
listed in `EVENT_PROVIDERS`.

Authentication: a **free** API key from https://www.eia.gov/opendata/
(instant, no cost) -- set `EIA_API_KEY`. Absent it, `is_available()` is
False and the feature layer runs without energy context.

Real endpoint (API v2, legacy-series compatibility route):

    https://api.eia.gov/v2/seriesid/{SERIES_ID}?api_key=...&start=YYYY-MM-DD&end=YYYY-MM-DD

Response shape:

    {"response": {"total": 123, "dateFormat": "YYYY-MM-DD",
                  "frequency": "weekly", "data": [
                     {"period": "2024-01-05", "value": 431234,
                      "units": "MBBL", "series": "PET.WCESTUS1.W", ...}]},
     "request": {...}, "apiVersion": "2.x.x"}

The fully-general v2 route (`/v2/petroleum/stoc/wstk/data/?frequency=...&data[0]=value&facets[...]`)
is also real but requires a per-dataset route + facet vocabulary; the
`seriesid` route reaches the same data with a single stable identifier,
which is what a context lookup needs.

Rate limits: EIA documents a per-key limit (on the order of a few
thousand requests/hour); the API returns HTTP 429 when exceeded, which
`http_utils` honours via `Retry-After`.
Historical availability: full series history (weekly petroleum series
reach back to the 1980s).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from worldpulse.config import settings
from worldpulse.ingestion import http_utils
from worldpulse.ingestion.providers.base import ContextDataProvider, SeriesPoint

logger = logging.getLogger(__name__)

EIA_SERIES_URL_TEMPLATE = "https://api.eia.gov/v2/seriesid/{series_id}"

#: Energy series the feature layer uses for the energy_supply channel.
DEFAULT_SERIES: dict[str, str] = {
    "PET.WCESTUS1.W": "US crude oil stocks excluding SPR (weekly, MBBL)",
    "PET.RWTC.D": "WTI crude spot price FOB (daily, $/bbl)",
    "PET.RBRTE.D": "Brent crude spot price FOB (daily, $/bbl)",
    "PET.WCRFPUS2.W": "US refinery net input of crude oil (weekly)",
    "NG.RNGWHHD.D": "Henry Hub natural gas spot price (daily, $/MMBtu)",
}


class EIAProvider(ContextDataProvider):
    """EIA Open Data v2 adapter (context/feature source only)."""

    name = "eia"
    requires_key = True

    def __init__(self, client: Optional[httpx.Client] = None, api_key: str | None = None) -> None:
        super().__init__()
        self._client = client
        self._api_key = api_key if api_key is not None else settings.eia_api_key
        self.health.available = self.is_available()
        self.health.disabled_reason = self.disabled_reason()

    def is_available(self) -> bool:
        return bool(self._api_key)

    def disabled_reason(self) -> str | None:
        if self.is_available():
            return None
        return (
            "EIAProvider disabled: EIA_API_KEY not set. Get a free key at "
            "https://www.eia.gov/opendata/ (no cost)."
        )

    def get_series(self, series_id: str, start: datetime, end: datetime) -> list[SeriesPoint]:
        if not self.is_available():
            logger.info("%s", self.disabled_reason())
            return []
        url = EIA_SERIES_URL_TEMPLATE.format(series_id=series_id)
        params = {
            "api_key": self._api_key,
            "start": _as_utc(start).strftime("%Y-%m-%d"),
            "end": _as_utc(end).strftime("%Y-%m-%d"),
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
        }
        started = time.perf_counter()
        try:
            payload = http_utils.http_get_json(url, params=params, client=self._client)
        except Exception as exc:  # noqa: BLE001
            self.health.record_failure(exc, latency_ms=(time.perf_counter() - started) * 1000.0)
            logger.warning("eia: series %s failed: %s", series_id, exc)
            return []

        response = payload.get("response") or {} if isinstance(payload, dict) else {}
        rows = response.get("data") or [] if isinstance(response, dict) else []
        points: list[SeriesPoint] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            when = _parse_period(row.get("period"))
            if when is None:
                continue
            points.append(SeriesPoint(
                series_id=series_id,
                timestamp=when,
                value=_safe_float(row.get("value")),
                source="eia",
                unit=str(row.get("units") or DEFAULT_SERIES.get(series_id, "")),
                raw=dict(row),
            ))
        points.sort(key=lambda p: p.timestamp)
        self.health.record_success(
            received=len(points), accepted=len(points), deduplicated=0,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
        return points


def _parse_period(raw: Any) -> Optional[datetime]:
    """EIA `period` granularity varies by series frequency."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    for fmt in ("%Y-%m-%dT%H", "%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
