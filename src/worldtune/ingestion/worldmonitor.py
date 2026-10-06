"""WorldMonitor news/intel client interface + implementations.

`WorldMonitorClient` is the port. `MockWorldMonitorClient` is a deterministic
(seeded) synthetic generator used by default and by all tests -- it produces
a realistic-looking stream of geopolitical/military/energy/economic/disaster
news without any network access. `WorldMonitorSDKClient` is a thin skeleton
for the real `worldmonitor-sdk` + `WORLDMONITOR_API_KEY` integration; it is
never used by default and raises immediately if no key is configured.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone  # noqa: F401


@dataclass
class RawNewsItem:
    """A single raw news/intel item as returned by a WorldMonitorClient."""

    id: str
    published_at: datetime
    headline: str
    body: str
    countries: list[str]
    entities: list[str]
    channels: list[str]
    category_hint: str  # coarse hint the source assigns, e.g. "military"
    severity_hint: float  # 0-1, source's own severity estimate
    source_name: str
    corroboration_count: int = 1


class WorldMonitorClient(ABC):
    """Port for the WorldMonitor intelligence API."""

    @abstractmethod
    def get_news_intelligence(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        ...

    @abstractmethod
    def get_conflict_events(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        ...

    @abstractmethod
    def get_energy_intelligence(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        ...

    @abstractmethod
    def get_intel_timeline(self, entity: str, start: datetime, end: datetime) -> list[RawNewsItem]:
        ...

    @abstractmethod
    def search_intel_history(self, query: str, limit: int = 20) -> list[RawNewsItem]:
        ...

    @abstractmethod
    def get_similar_events(self, item_id: str, limit: int = 10) -> list[RawNewsItem]:
        ...


# --- Synthetic scenario library used by the mock client -------------------

_COUNTRIES = ["Russia", "Ukraine", "Israel", "Iran", "Taiwan", "China", "USA",
              "Saudi Arabia", "Venezuela", "North Korea", "Poland", "Japan"]

_SCENARIOS: list[dict] = [
    dict(category_hint="military", channels=["shipping_lanes", "regional_security"],
         entities=["Naval Fleet", "Border Forces"],
         templates=[
             "{c1} masses troops near {c2} border",
             "Naval clash reported between {c1} and {c2} forces",
             "{c1} launches missile strike near {c2} territory",
         ], severity_range=(0.4, 0.95)),
    dict(category_hint="conflict", channels=["regional_security", "diplomatic_relations"],
         entities=["Government", "Rebel Faction"],
         templates=[
             "Ceasefire talks between {c1} and {c2} collapse",
             "{c1} declares state of emergency amid escalation with {c2}",
             "Airstrikes reported in {c1}-{c2} border region",
         ], severity_range=(0.3, 0.9)),
    dict(category_hint="energy", channels=["energy_supply", "shipping_lanes"],
         entities=["Pipeline Operator", "OPEC", "Refinery Co"],
         templates=[
             "Major pipeline explosion disrupts {c1} energy exports",
             "{c1} announces surprise oil production cut",
             "Tanker attacked near {c1} coast, oil shipments disrupted",
         ], severity_range=(0.3, 0.85)),
    dict(category_hint="economic", channels=["monetary_policy", "trade_policy"],
         entities=["Central Bank", "Finance Ministry"],
         templates=[
             "{c1} central bank announces surprise rate decision",
             "{c1} imposes new trade sanctions on {c2}",
             "{c1} inflation data shocks markets",
         ], severity_range=(0.2, 0.75)),
    dict(category_hint="disaster", channels=["infrastructure", "supply_chain"],
         entities=["Disaster Relief Agency", "Local Government"],
         templates=[
             "Major earthquake strikes {c1}, infrastructure damaged",
             "Category 4 storm makes landfall in {c1}",
             "Flooding disrupts {c1} industrial production",
         ], severity_range=(0.3, 0.9)),
]


class MockWorldMonitorClient(WorldMonitorClient):
    """Deterministic synthetic news generator.

    Given a fixed `seed`, `generate_stream` always produces the same
    sequence of events for the same time range, which is what makes the
    test-suite and demo pipeline reproducible.
    """

    # Fixed epoch and span for the deterministic superset timeline. Using a
    # fixed epoch/span/count (independent of any query's start/end) means
    # the same historical timestamp always yields the same synthetic event
    # regardless of what "now" a caller queries with -- required for
    # walk-forward backfill and the no-lookahead tests to be meaningful.
    EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)
    SPAN_DAYS = 3650
    TOTAL_ITEMS = 4000

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._all_items: list[RawNewsItem] = []
        self._generated = False

    def generate_stream(self, start: datetime, end: datetime, count: int = 200) -> list[RawNewsItem]:
        """Deprecated direct-generation entry point, kept for API
        compatibility; delegates to the fixed superset generator and
        filters to [start, end]. `count` is ignored (the superset is a
        fixed size so timestamps stay stable across calls)."""
        self._ensure_generated()
        return [i for i in self._all_items if start <= i.published_at <= end]

    def _ensure_generated(self) -> None:
        if self._generated:
            return
        rng = random.Random(self._seed)
        items: list[RawNewsItem] = []
        span_seconds = self.SPAN_DAYS * 24 * 3600
        for i in range(self.TOTAL_ITEMS):
            scenario = rng.choice(_SCENARIOS)
            c1, c2 = rng.sample(_COUNTRIES, 2)
            template = rng.choice(scenario["templates"])
            headline = template.format(c1=c1, c2=c2)
            sev_lo, sev_hi = scenario["severity_range"]
            severity = round(rng.uniform(sev_lo, sev_hi), 3)
            offset = timedelta(seconds=rng.randint(0, span_seconds))
            published_at = self.EPOCH + offset
            entities = rng.sample(scenario["entities"], k=min(2, len(scenario["entities"])))
            corroboration = rng.randint(1, 5)
            item = RawNewsItem(
                id=f"news-{self._seed}-{i:05d}",
                published_at=published_at,
                headline=headline,
                body=f"{headline}. Analysts are monitoring the situation for wider implications.",
                countries=[c1, c2],
                entities=entities,
                channels=list(scenario["channels"]),
                category_hint=scenario["category_hint"],
                severity_hint=severity,
                source_name=rng.choice(["Reuters-sim", "AP-sim", "LocalWire-sim"]),
                corroboration_count=corroboration,
            )
            items.append(item)
        items.sort(key=lambda x: x.published_at)
        self._all_items = items
        self._generated = True

    # --- WorldMonitorClient interface -------------------------------------

    def get_news_intelligence(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        self._ensure_generated()
        return [i for i in self._all_items if start <= i.published_at <= end]

    def get_conflict_events(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        return [i for i in self.get_news_intelligence(start, end)
                if i.category_hint in ("military", "conflict")]

    def get_energy_intelligence(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        return [i for i in self.get_news_intelligence(start, end) if i.category_hint == "energy"]

    def get_intel_timeline(self, entity: str, start: datetime, end: datetime) -> list[RawNewsItem]:
        return [i for i in self.get_news_intelligence(start, end) if entity in i.entities]

    def search_intel_history(self, query: str, limit: int = 20) -> list[RawNewsItem]:
        query_lower = query.lower()
        matches = [i for i in self._all_items if query_lower in i.headline.lower()]
        return matches[:limit]

    def get_similar_events(self, item_id: str, limit: int = 10) -> list[RawNewsItem]:
        target = next((i for i in self._all_items if i.id == item_id), None)
        if target is None:
            return []
        matches = [
            i for i in self._all_items
            if i.id != item_id and i.category_hint == target.category_hint
        ]
        return matches[:limit]


class WorldMonitorSDKClient(WorldMonitorClient):
    """Real integration skeleton -- NOT used by default or in tests.

    Would wrap the `worldmonitor-sdk` package using `WORLDMONITOR_API_KEY`.
    """

    def __init__(self, api_key: str | None):
        if not api_key:
            raise RuntimeError(
                "WorldMonitorSDKClient requires WORLDMONITOR_API_KEY to be set. "
                "Configure it in .env or use MockWorldMonitorClient for local/dev/test."
            )
        self._api_key = api_key
        try:
            import worldmonitor_sdk  # type: ignore  # noqa: F401
        except ImportError as exc:  # pragma: no cover - real-integration path
            raise RuntimeError(
                "worldmonitor-sdk is not installed. `pip install worldmonitor-sdk` "
                "to use WorldMonitorSDKClient."
            ) from exc

    def get_news_intelligence(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        raise NotImplementedError("Real WorldMonitor SDK integration not wired up in this prototype.")

    def get_conflict_events(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        raise NotImplementedError

    def get_energy_intelligence(self, start: datetime, end: datetime) -> list[RawNewsItem]:
        raise NotImplementedError

    def get_intel_timeline(self, entity: str, start: datetime, end: datetime) -> list[RawNewsItem]:
        raise NotImplementedError

    def search_intel_history(self, query: str, limit: int = 20) -> list[RawNewsItem]:
        raise NotImplementedError

    def get_similar_events(self, item_id: str, limit: int = 10) -> list[RawNewsItem]:
        raise NotImplementedError
