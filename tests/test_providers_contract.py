"""Shared contract test, run against EVERY WorldEventProvider.

One parametrized test body asserts the invariants the rest of the pipeline
relies on, so a newly added provider gets the same scrutiny as the
existing ones for free:

  * `fetch_events` returns a `list[WorldEvent]`;
  * every required field is populated (headline, severity in range,
    event_type/domain, subtype);
  * `provider` and `provider_event_id` are set (provenance is what
    cross-source dedup and `EventEvidence` are built on);
  * all timestamps are timezone-aware UTC;
  * events fall inside the requested window;
  * re-fetching the same window is deterministic (same ids), which is what
    makes ingestion idempotent.

All HTTP is served by `httpx.MockTransport` from fixtures shaped like each
API's real documented response -- no network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests import provider_fixtures as fx
from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.ingestion.providers.acled import ACLEDProvider
from worldpulse.ingestion.providers.base import WorldEventProvider
from worldpulse.ingestion.providers.eonet import EONETProvider
from worldpulse.ingestion.providers.firms import FIRMSProvider
from worldpulse.ingestion.providers.gdacs import GDACSProvider
from worldpulse.ingestion.providers.gdelt import GDELTProvider
from worldpulse.ingestion.providers.usgs import USGSProvider
from worldpulse.ingestion.providers.registry import EVENT_PROVIDER_FACTORIES
from worldpulse.ingestion.providers.worldmonitor import (
    SyntheticEventProvider,
    WorldMonitorProvider,
)
from worldpulse.ingestion.worldmonitor import MockWorldMonitorClient

# The synthetic timeline is sparse (~1 event/day over 10 years), so the
# offline providers get a wider window than the fixture-backed ones.
SYNTHETIC_START = datetime(2022, 1, 1, tzinfo=timezone.utc)
SYNTHETIC_END = SYNTHETIC_START + timedelta(days=120)


def _http_providers() -> list[tuple[str, WorldEventProvider, datetime, datetime]]:
    client = fx.make_client()
    return [
        ("gdelt", GDELTProvider(client=client), fx.WINDOW_START, fx.WINDOW_END),
        ("usgs", USGSProvider(client=client), fx.WINDOW_START, fx.WINDOW_END),
        ("eonet", EONETProvider(client=client), fx.WINDOW_START, fx.WINDOW_END),
        ("gdacs", GDACSProvider(client=client), fx.WINDOW_START, fx.WINDOW_END),
        ("firms", FIRMSProvider(client=client, map_key="test-map-key"),
         fx.WINDOW_START, fx.WINDOW_END),
        ("acled", ACLEDProvider(client=client, email="a@b.test", password="pw"),
         fx.WINDOW_START, fx.WINDOW_END),
    ]


def _offline_providers() -> list[tuple[str, WorldEventProvider, datetime, datetime]]:
    return [
        ("synthetic", SyntheticEventProvider(seed=7), SYNTHETIC_START, SYNTHETIC_END),
        # World Monitor with an explicitly injected mock client: exercises
        # the wrapper without needing (or touching) the paid API.
        ("worldmonitor", WorldMonitorProvider(client=MockWorldMonitorClient(seed=7)),
         SYNTHETIC_START, SYNTHETIC_END),
    ]


ALL_CASES = _http_providers() + _offline_providers()
VALID_DOMAINS = {d.value for d in EventDomain}


@pytest.mark.parametrize("name,provider,start,end", ALL_CASES, ids=[c[0] for c in ALL_CASES])
def test_provider_contract(name, provider, start, end):
    events = provider.fetch_events(start, end)

    assert isinstance(events, list), f"{name}: fetch_events must return a list"
    assert events, f"{name}: fixture window should produce at least one event"
    assert provider.health.error_count == 0, (
        f"{name}: provider recorded an error: {provider.health.last_error}"
    )

    for event in events:
        assert isinstance(event, WorldEvent), f"{name}: not a WorldEvent: {type(event)}"

        # --- provenance ---
        assert event.provider == name, f"{name}: provider field is {event.provider!r}"
        assert event.provider_event_id, f"{name}: provider_event_id is empty"
        assert event.source_id, f"{name}: source_id is empty"
        assert event.id, f"{name}: id is empty"

        # --- required content ---
        assert event.headline.strip(), f"{name}: empty headline"
        assert 0.0 <= event.severity <= 1.0, f"{name}: severity out of range"
        assert 0.0 <= event.source_confidence <= 1.0, f"{name}: source_confidence out of range"
        domain = event.event_type.value if hasattr(event.event_type, "value") else event.event_type
        assert domain in VALID_DOMAINS, f"{name}: unknown domain {domain!r}"
        assert event.event_domain == domain, f"{name}: event_domain out of sync with event_type"
        assert event.event_subtype, f"{name}: empty event_subtype"
        assert event.classification_version, f"{name}: empty classification_version"

        # --- timestamps are UTC-aware ---
        for field in ("occurred_at", "ingested_at", "first_seen_at"):
            value = getattr(event, field)
            assert value is not None, f"{name}: {field} is None"
            assert value.tzinfo is not None, f"{name}: {field} is naive"
            assert value.utcoffset() == timedelta(0), f"{name}: {field} is not UTC"

        # --- inside the requested window ---
        assert start <= event.occurred_at <= end, (
            f"{name}: event at {event.occurred_at} outside {start}..{end}"
        )

        # --- geography is either absent or coherent ---
        if event.latitude is not None:
            assert -90.0 <= event.latitude <= 90.0, f"{name}: bad latitude"
            assert event.longitude is not None, f"{name}: latitude without longitude"
        if event.longitude is not None:
            assert -180.0 <= event.longitude <= 180.0, f"{name}: bad longitude"

        # --- list fields are lists, not None ---
        for field in ("countries", "entities", "affected_channels", "potential_assets",
                      "source_urls", "locations", "industries", "commodities"):
            assert isinstance(getattr(event, field), list), f"{name}: {field} is not a list"

    # --- health bookkeeping happened ---
    assert provider.health.calls >= 1
    assert provider.health.events_received >= len(events)
    assert provider.health.last_success_at is not None
    assert provider.health.status() == "HEALTHY"


@pytest.mark.parametrize("name,provider,start,end", ALL_CASES, ids=[c[0] for c in ALL_CASES])
def test_provider_ids_are_deterministic(name, provider, start, end):
    """Same window twice -> same event ids, so persistence can upsert."""
    first = provider.fetch_events(start, end)
    second = provider.fetch_events(start, end)
    assert [e.id for e in first] == [e.id for e in second]
    assert [e.provider_event_id for e in first] == [e.provider_event_id for e in second]


def test_every_registered_provider_is_covered():
    """A new provider added to the registry must be added to this test."""
    covered = {case[0] for case in ALL_CASES}
    registered = set(EVENT_PROVIDER_FACTORIES)
    assert registered <= covered, (
        f"providers registered but not covered by the contract test: {registered - covered}"
    )


def test_gdelt_filters_non_english_and_parses_seendate():
    provider = GDELTProvider(client=fx.make_client())
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    urls = {e.provider_event_id for e in events}
    assert "https://www.lemonde.fr/international/article/0115" not in urls
    quake = next(e for e in events if "Taiwan" in e.headline)
    assert quake.occurred_at == datetime(2024, 1, 15, 12, 30, tzinfo=timezone.utc)
    assert quake.source_name == "reuters.com"
    assert quake.source_urls == [quake.provider_event_id]
    assert quake.source_url == quake.provider_event_id  # singular alias
    assert "Taiwan" in quake.countries


def test_usgs_maps_magnitude_to_severity_and_geometry():
    provider = USGSProvider(client=fx.make_client())
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    big = next(e for e in events if e.provider_event_id == "us7000abcd")
    assert big.event_subtype == "earthquake"
    assert big.event_domain == EventDomain.DISASTER.value
    # M6.1 + tsunami flag + orange alert -> comfortably "high".
    assert big.severity >= 0.80, big.severity
    assert big.latitude == pytest.approx(23.8312)
    assert big.longitude == pytest.approx(121.6015)
    assert big.countries == ["Taiwan"]
    assert big.source_urls == [
        "https://earthquake.usgs.gov/earthquakes/eventpage/us7000abcd"
    ]

    # A US quake resolves the state suffix to USA.
    small = next(e for e in events if e.provider_event_id == "nc73999999")
    assert small.countries == ["USA"]
    assert small.severity < big.severity


def test_usgs_respects_min_magnitude():
    provider = USGSProvider(client=fx.make_client(), min_magnitude=5.5)
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    assert {e.provider_event_id for e in events} == {"us7000abcd"}


def test_eonet_maps_categories_to_subtypes():
    provider = EONETProvider(client=fx.make_client())
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    by_id = {e.provider_event_id: e for e in events}
    assert by_id["EONET_6789"].event_subtype == "earthquake"
    assert by_id["EONET_6789"].event_subtype_detail == "earthquakes"
    assert by_id["EONET_6790"].event_subtype == "wildfire"
    # 120k acres nudges the wildfire severity prior upward.
    assert by_id["EONET_6790"].severity > 0.55


def test_gdacs_uses_alert_level_for_severity():
    provider = GDACSProvider(client=fx.make_client())
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    assert len(events) == 1
    event = events[0]
    assert event.event_subtype == "earthquake"
    assert event.countries == ["Taiwan"]
    # Orange alert -> 0.70 floor, plus the alertscore nudge.
    assert 0.70 <= event.severity <= 0.80
    assert event.provider_event_id.startswith("EQ1435678")


def test_gdacs_rss_fallback_parses():
    """The RSS path must work on its own, not only as a silent fallback."""
    provider = GDACSProvider(client=fx.make_client())
    events = provider._fetch_rss()
    assert len(events) == 1
    assert events[0].countries == ["Taiwan"]
    assert events[0].latitude == pytest.approx(23.84)


def test_firms_clusters_pixels_into_one_event():
    provider = FIRMSProvider(client=fx.make_client(), map_key="test-map-key",
                             areas={"australia": "112,-44,154,-10"})
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    # 8 nearby detections over 6 minutes -> exactly one wildfire cluster,
    # not 8 separate events.
    assert len(events) == 1
    event = events[0]
    assert event.event_subtype == "wildfire"
    assert event.raw_payload["detection_count"] == 8
    assert event.latitude == pytest.approx(-17.2, abs=0.05)


def test_acled_maps_fatalities_to_severity():
    provider = ACLEDProvider(client=fx.make_client(), email="a@b.test", password="pw")
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    assert len(events) == 1
    event = events[0]
    assert event.event_domain == EventDomain.MILITARY.value
    assert event.event_subtype == "missile_strike"
    assert event.countries == ["Yemen"]
    assert event.severity > 0.30  # 12 fatalities lifts it off the floor


def test_provider_degrades_on_upstream_failure_instead_of_raising():
    """One broken feed must never take the pipeline down."""
    import httpx

    def boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream on fire")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    provider = USGSProvider(client=client)
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    assert events == []
    assert provider.health.error_count == 1
    assert provider.health.status() == "DEGRADED"
