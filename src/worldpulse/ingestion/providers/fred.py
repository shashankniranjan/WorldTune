"""FRED provider -- macro context/feature series (NOT an event source).

FRED (Federal Reserve Economic Data, St. Louis Fed) publishes macro time
series: policy rates, treasury yields, CPI, unemployment, spreads. These
are **context/feature** inputs, not discrete newsworthy events. Turning
each weekly CPI print or daily yield observation into a `WorldEvent` would
flood the event table with records that carry no event semantics and would
corrupt the novelty/dedup signals that the prediction gate depends on.

For that reason `FREDProvider` deliberately implements
`ContextDataProvider` and **not** `WorldEventProvider`; it can never be
listed in `EVENT_PROVIDERS` and the registry will not return it from
`get_active_providers()`.

Authentication: a **free** API key, instantly issued at
https://fredaccount.stlouisfed.org/apikeys -- set `FRED_API_KEY`. Without
it, `is_available()` is False and the feature layer simply has no macro
context; nothing crashes.

Real endpoint:
    https://api.stlouisfed.org/fred/series/observations
      ?series_id=DGS10&api_key=...&file_type=json
      &observation_start=YYYY-MM-DD&observation_end=YYYY-MM-DD

Response shape:
    {"realtime_start": "...", "observations": [
        {"realtime_start": "...", "realtime_end": "...",
         "date": "2024-01-02", "value": "3.95"}, ...]}
Missing observations come back with `value == "."`, which is mapped to
`None` rather than dropped, so gaps stay visible to the feature layer.

Rate limits: FRED documents 120 requests/minute per API key.
Historical availability: full series history (many series reach back
decades; DGS10 to 1962).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from worldpulse.config import settings
from worldpulse.ingestion import http_utils
from worldpulse.ingestion.providers.base import ContextDataProvider, SeriesPoint

logger = logging.getLogger(__name__)

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"

#: Series WorldPulse's feature layer cares about, with the impact channel
#: each one informs.
DEFAULT_SERIES: dict[str, str] = {
    "DGS10": "10-Year Treasury constant maturity yield",
    "DGS2": "2-Year Treasury constant maturity yield",
    "DFF": "Effective federal funds rate",
    "T10Y2Y": "10Y-2Y treasury spread",
    "VIXCLS": "CBOE Volatility Index",
    "DTWEXBGS": "Nominal broad US dollar index",
    "CPIAUCSL": "CPI, all urban consumers",
    "DCOILBRENTEU": "Brent crude spot price",
}


class FREDProvider(ContextDataProvider):
    """FRED macro time-series adapter (context/feature source only)."""

    name = "fred"
    requires_key = True

    def __init__(self, client: Optional[httpx.Client] = None, api_key: str | None = None) -> None:
        super().__init__()
        self._client = client
        self._api_key = api_key if api_key is not None else settings.fred_api_key
        self.health.available = self.is_available()
        self.health.disabled_reason = self.disabled_reason()

    def is_available(self) -> bool:
        return bool(self._api_key)

    def disabled_reason(self) -> str | None:
        if self.is_available():
            return None
        return (
            "FREDProvider disabled: FRED_API_KEY not set. Get a free key at "
            "https://fredaccount.stlouisfed.org/apikeys (no cost)."
        )

    def get_series(self, series_id: str, start: datetime, end: datetime) -> list[SeriesPoint]:
        """Normalized observations for `series_id` within [start, end]."""
        if not self.is_available():
            logger.info("%s", self.disabled_reason())
            return []
        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "observation_start": _as_utc(start).strftime("%Y-%m-%d"),
            "observation_end": _as_utc(end).strftime("%Y-%m-%d"),
            "sort_order": "asc",
        }
        import time

        started = time.perf_counter()
        try:
            payload = http_utils.http_get_json(FRED_OBSERVATIONS_URL, params=params, client=self._client)
        except Exception as exc:  # noqa: BLE001
            self.health.record_failure(exc, latency_ms=(time.perf_counter() - started) * 1000.0)
            logger.warning("fred: series %s failed: %s", series_id, exc)
            return []

        observations = payload.get("observations") or [] if isinstance(payload, dict) else []
        points: list[SeriesPoint] = []
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            when = _parse_date(observation.get("date"))
            if when is None:
                continue
            points.append(SeriesPoint(
                series_id=series_id,
                timestamp=when,
                value=_fred_value(observation.get("value")),
                source="fred",
                unit=DEFAULT_SERIES.get(series_id, ""),
                raw=dict(observation),
            ))
        self.health.record_success(
            received=len(points), accepted=len(points), deduplicated=0,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
        return points


def _fred_value(raw: Any) -> Optional[float]:
    """FRED encodes a missing observation as the string "."."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text in ("", "."):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
