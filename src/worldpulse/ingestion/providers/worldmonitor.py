"""World Monitor provider -- OPTIONAL, PAID, never selected by default.

This wraps the pre-existing World Monitor ingestion code (which still
lives at `worldpulse/ingestion/worldmonitor.py`: `WorldMonitorClient`,
`MockWorldMonitorClient`, `WorldMonitorSDKClient`, `RawNewsItem`) behind
the `WorldEventProvider` port, so World Monitor is now *one provider among
many* rather than the mandatory source it used to be.

Behaviour contract:

  * `is_available()` is `bool(settings.worldmonitor_api_key)`. With the key
    unset, the registry logs
    "WorldMonitorProvider disabled: WORLDMONITOR_API_KEY not set" and skips
    it. Nothing raises, nothing crashes.
  * `worldmonitor` is NOT in the default `EVENT_PROVIDERS`, and in
    `WORLDPULSE_MODE=free` (the default) it is refused even if explicitly
    listed, because it is a paid subscription.
  * The deterministic synthetic generator (`MockWorldMonitorClient`) is
    preserved, but it is only reachable by *explicitly* selecting the
    separate `synthetic` provider (see `SyntheticEventProvider` below) or
    by constructing `WorldMonitorProvider(client=MockWorldMonitorClient())`
    by hand. It is never auto-selected as a stand-in for the real API.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from worldpulse.config import settings
from worldpulse.events.schemas import WorldEvent
from worldpulse.ingestion.providers.base import WorldEventProvider
from worldpulse.ingestion.worldmonitor import (
    MockWorldMonitorClient,
    RawNewsItem,
    WorldMonitorClient,
    WorldMonitorSDKClient,
)

logger = logging.getLogger(__name__)


def _raw_items_to_events(items: list[RawNewsItem], provider_name: str) -> list[WorldEvent]:
    """Classify raw World-Monitor-shaped items into `WorldEvent`s.

    Reuses the existing `RuleBasedEventClassifier` unchanged (it already
    knows the `RawNewsItem` shape) and then stamps provider provenance
    onto the result, so this wrapper adds no parallel classification path.
    """
    from worldpulse.events.classifier import RuleBasedEventClassifier

    classifier = RuleBasedEventClassifier()
    events: list[WorldEvent] = []
    now = datetime.now(timezone.utc)
    for item in items:
        event = classifier.classify(item)
        event.provider = provider_name
        event.provider_event_id = item.id
        event.source_name = item.source_name
        event.summary = item.body
        event.ingested_at = event.ingested_at or now
        events.append(event)
    return events


class WorldMonitorProvider(WorldEventProvider):
    """OPTIONAL PAID provider wrapping the World Monitor intel API."""

    name = "worldmonitor"
    requires_key = True
    is_paid = True

    def __init__(self, client: Optional[WorldMonitorClient] = None) -> None:
        super().__init__()
        self._client = client
        self.health.available = self.is_available()
        self.health.disabled_reason = self.disabled_reason()

    def is_available(self) -> bool:
        # An explicitly injected client (e.g. the mock, in a test) makes
        # the provider usable without a key; otherwise the key decides.
        if self._client is not None:
            return True
        return bool(settings.worldmonitor_api_key)

    def disabled_reason(self) -> str | None:
        if self.is_available():
            return None
        return "WorldMonitorProvider disabled: WORLDMONITOR_API_KEY not set"

    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        if not self.is_available():
            logger.info("%s", self.disabled_reason())
            self.health.available = False
            self.health.disabled_reason = self.disabled_reason()
            return []
        events, _ = self._timed(self._fetch, start_time, end_time)
        return events

    def _fetch(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        client = self._client
        if client is None:
            # Constructed lazily so merely *importing* this module never
            # requires the paid SDK to be installed.
            client = WorldMonitorSDKClient(settings.worldmonitor_api_key)
            self._client = client
        items = client.get_news_intelligence(start_time, end_time)
        return _raw_items_to_events(list(items), self.name)


class SyntheticEventProvider(WorldEventProvider):
    """Deterministic offline event source -- the zero-dependency demo path.

    Wraps `MockWorldMonitorClient`'s seeded synthetic timeline. This exists
    so the walk-forward backfill demo and the test suite have a reproducible
    event stream with no network at all, and so that "synthetic" is an
    explicit, honestly-labelled choice in `EVENT_PROVIDERS` rather than a
    silent fallback pretending to be a real feed.
    """

    name = "synthetic"
    requires_key = False
    is_paid = False

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()
        self._seed = settings.random_seed if seed is None else seed
        self._client = MockWorldMonitorClient(seed=self._seed)

    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        events, _ = self._timed(self._fetch, start_time, end_time)
        return events

    def _fetch(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        items = self._client.get_news_intelligence(start_time, end_time)
        return _raw_items_to_events(list(items), self.name)
