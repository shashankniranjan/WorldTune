"""Provider ABCs -- one per signal type.

Every adapter declares:
  * `name` -- provenance string written to the `source` column;
  * `is_live` -- False for the deterministic Demo* adapters;
  * `is_available()` -- False when a required credential is absent, so a
    missing key disables a provider instead of crashing the app;
  * a single fetch method returning canonical models.

Nothing downstream of these interfaces knows a third-party schema exists.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.schemas.canonical import (
    CanonicalJob,
    CanonicalMarketPrice,
    CanonicalNewsEvent,
    CanonicalTechEvent,
)


class Provider(ABC):
    name: str = "provider"
    is_live: bool = True
    requires_credentials: tuple[str, ...] = ()

    def is_available(self) -> bool:
        """True when this adapter can run right now."""
        return True

    def status(self) -> dict:
        """Row for GET /api/system/data-sources."""
        return {
            "name": self.name,
            "kind": self.kind,
            "mode": "live" if self.is_live else "demo",
            "available": self.is_available(),
            "requires_credentials": list(self.requires_credentials),
        }

    @property
    @abstractmethod
    def kind(self) -> str: ...


class MarketDataProvider(Provider):
    kind = "market"

    @abstractmethod
    def fetch_prices(self, symbols: list[str], *, days: int = 90) -> list[CanonicalMarketPrice]:
        """Daily OHLCV bars covering roughly the last `days` days."""


class NewsProvider(Provider):
    kind = "news"

    @abstractmethod
    def fetch_news(self, *, query: str = "", since: datetime | None = None,
                   limit: int = 50) -> list[CanonicalNewsEvent]: ...


class JobsProvider(Provider):
    kind = "jobs"

    @abstractmethod
    def fetch_jobs(self, *, query: str = "", location: str = "",
                   limit: int = 50) -> list[CanonicalJob]: ...


class TechnologySignalsProvider(Provider):
    kind = "technology"

    @abstractmethod
    def fetch_tech_events(self, *, topics: list[str] | None = None,
                          limit: int = 50) -> list[CanonicalTechEvent]: ...
