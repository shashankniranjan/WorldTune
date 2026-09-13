"""`WorldEventProvider` port + per-provider health bookkeeping.

Every event source WorldPulse can ingest from implements this one
interface, which means the rest of the pipeline (classify -> dedup ->
persist -> predict) is completely decoupled from *which* feeds are
configured. Providers that require credentials report
`is_available() == False` when those credentials are missing, and the
registry then skips them cleanly instead of crashing at startup -- this is
what lets WorldPulse run with `WORLDMONITOR_API_KEY` unset.
"""
from __future__ import annotations

import logging
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from worldpulse.events.schemas import WorldEvent

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two lat/lon points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


@dataclass
class ProviderHealth:
    """Rolling health/observability record, updated on every fetch call."""

    provider: str
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    events_received: int = 0
    events_accepted: int = 0
    events_deduplicated: int = 0
    latency_ms: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    # Not part of the spec's tuple but needed by /health/providers to
    # distinguish "nothing wrong, just switched off" from "broken".
    available: bool = True
    disabled_reason: Optional[str] = None
    calls: int = 0

    def record_success(self, *, received: int, accepted: int, deduplicated: int,
                       latency_ms: float) -> None:
        self.last_success_at = datetime.now(timezone.utc)
        self.events_received += received
        self.events_accepted += accepted
        self.events_deduplicated += deduplicated
        self.latency_ms = round(latency_ms, 2)
        self.calls += 1

    def record_failure(self, error: Exception | str, latency_ms: float = 0.0) -> None:
        self.last_failure_at = datetime.now(timezone.utc)
        self.error_count += 1
        self.last_error = str(error)[:500]
        self.latency_ms = round(latency_ms, 2)
        self.calls += 1

    def status(self) -> str:
        """HEALTHY / DEGRADED / DISABLED / UNKNOWN.

        DISABLED is a *normal* state (missing optional key), never an
        error. DEGRADED means the provider is configured but its most
        recent outcome was a failure.
        """
        if not self.available:
            return "DISABLED"
        if self.calls == 0:
            return "UNKNOWN"
        if self.last_failure_at is None:
            return "HEALTHY"
        if self.last_success_at is None:
            return "DEGRADED"
        return "HEALTHY" if self.last_success_at >= self.last_failure_at else "DEGRADED"

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "status": self.status(),
            "available": self.available,
            "disabled_reason": self.disabled_reason,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "events_received": self.events_received,
            "events_accepted": self.events_accepted,
            "events_deduplicated": self.events_deduplicated,
            "latency_ms": self.latency_ms,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "calls": self.calls,
        }


class WorldEventProvider(ABC):
    """Port for a source of real-world events.

    Subclasses must set `name` and implement `fetch_events`. They should
    call `_fetch_events` indirectly via `fetch_events_tracked` (or use the
    `track` context helper) so `health` stays accurate.
    """

    #: Stable short name used in EVENT_PROVIDERS, `WorldEvent.provider`,
    #: checkpoints and health output.
    name: str = "unnamed"

    #: Set False on providers that need credentials/paid access so
    #: `WORLDPULSE_MODE=free` and the registry can reason about them.
    requires_key: bool = False
    is_paid: bool = False

    def __init__(self) -> None:
        self.health = ProviderHealth(provider=self.name)

    def is_available(self) -> bool:
        """Whether this provider can run right now.

        Default: always available (open feeds needing no credentials).
        Providers with credential requirements override this and return
        False when the key is absent, which makes them self-disabling
        rather than fatal.
        """
        return True

    def disabled_reason(self) -> str | None:
        """Human-readable explanation when `is_available()` is False."""
        return None

    @abstractmethod
    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        """Return normalized events occurring within [start_time, end_time].

        Implementations MUST NOT raise on a transient upstream failure that
        they can degrade from; they should record it in `health` and return
        what they have (possibly an empty list) so one broken feed never
        takes the pipeline down.
        """
        raise NotImplementedError

    # --- helpers used by subclasses ------------------------------------

    def _timed(self, fn, *args, **kwargs):
        """Run `fn`, updating `health` with latency and success/failure.

        Returns `(events, ok)`. Never propagates the exception: a single
        failing feed degrades to zero events for that window.
        """
        started = time.perf_counter()
        try:
            events = fn(*args, **kwargs) or []
        except Exception as exc:  # noqa: BLE001 - deliberate: degrade, don't crash
            elapsed = (time.perf_counter() - started) * 1000.0
            self.health.record_failure(exc, latency_ms=elapsed)
            logger.warning("provider=%s fetch failed: %s", self.name, exc)
            return [], False
        elapsed = (time.perf_counter() - started) * 1000.0
        self.health.record_success(
            received=len(events), accepted=len(events), deduplicated=0, latency_ms=elapsed
        )
        return events, True

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.name!r} available={self.is_available()}>"


class ContextDataProvider(ABC):
    """Port for *context/feature* sources (FRED, EIA).

    These publish macro/energy time series, not discrete newsworthy
    events. Turning every weekly inventory print into a `WorldEvent` would
    flood the event table with records that carry no event semantics, so
    they deliberately do NOT implement `WorldEventProvider`; the feature
    layer pulls series from them instead.
    """

    name: str = "unnamed-context"
    requires_key: bool = True

    def __init__(self) -> None:
        self.health = ProviderHealth(provider=self.name)

    def is_available(self) -> bool:
        return True

    def disabled_reason(self) -> str | None:
        return None

    @abstractmethod
    def get_series(self, series_id: str, start: datetime, end: datetime) -> list["SeriesPoint"]:
        raise NotImplementedError


@dataclass
class SeriesPoint:
    """One observation of a context time series."""

    series_id: str
    timestamp: datetime
    value: Optional[float]
    source: str
    unit: str = ""
    raw: dict = field(default_factory=dict)
