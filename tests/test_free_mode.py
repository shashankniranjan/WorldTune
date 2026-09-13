"""`WORLDPULSE_MODE=free`: no paid code path may be reached, ever.

`free` is the default mode. These tests assert it is enforced rather than
merely documented: the paid World Monitor provider is refused by the
registry even when explicitly requested, its SDK constructor and HTTP
endpoint are never touched during a normal pipeline run, and `/health`
advertises `data_mode == "FREE"`.
"""
from __future__ import annotations

from datetime import timedelta

import httpx
import pytest

from tests import provider_fixtures as fx
from worldpulse.config import PAID_PROVIDERS, settings
from worldpulse.ingestion.providers import registry


@pytest.fixture()
def free_mode(monkeypatch):
    monkeypatch.setenv("WORLDPULSE_MODE", "free")
    monkeypatch.setattr(settings, "worldpulse_mode", "free")
    monkeypatch.setattr(settings, "event_providers", "gdelt,usgs,eonet,gdacs")
    monkeypatch.setattr(settings, "worldmonitor_api_key", None)
    registry.reset_registry()
    yield
    registry.reset_registry()


def test_free_mode_is_the_default():
    """A fresh Settings() with no env overrides must be free/rules."""
    from worldpulse.config import Settings

    fresh = Settings(_env_file=None)
    assert fresh.worldpulse_mode == "free"
    assert fresh.is_free_mode is True
    assert fresh.data_mode == "FREE"
    assert fresh.ai_classifier == "rules"
    assert fresh.event_providers == "gdelt,usgs,eonet,gdacs"
    assert fresh.market_data_provider == "synthetic"
    # No provider in the default set costs anything.
    assert not (set(fresh.provider_names()) & PAID_PROVIDERS)


def test_paid_provider_refused_in_free_mode_even_with_a_key(free_mode, monkeypatch):
    """A configured paid key must not override the free-mode policy."""
    monkeypatch.setattr(settings, "worldmonitor_api_key", "pretend-paid-key")
    monkeypatch.setattr(settings, "event_providers", "gdelt,worldmonitor")
    registry.reset_registry()

    active = [p.name for p in registry.get_active_providers()]
    assert active == ["gdelt"]
    reason = registry.get_skips()["worldmonitor"]
    assert "paid" in reason.lower()
    assert "WORLDPULSE_MODE=free" in reason


def test_paid_provider_allowed_only_when_mode_is_paid(monkeypatch):
    """The escape hatch works, so `free` is a policy and not a dead end."""
    monkeypatch.setattr(settings, "worldpulse_mode", "paid")
    monkeypatch.setattr(settings, "worldmonitor_api_key", "pretend-paid-key")
    monkeypatch.setattr(settings, "event_providers", "worldmonitor")
    registry.reset_registry()
    try:
        active = [p.name for p in registry.get_active_providers()]
        assert active == ["worldmonitor"]
    finally:
        registry.reset_registry()


def test_no_worldmonitor_http_call_during_a_pipeline_run(free_mode, db_session, monkeypatch):
    """Patch the transport layer and assert nothing talks to World Monitor.

    Rather than trusting that the registry filtered it out, this asserts
    at the network boundary: every outbound request is intercepted, and any
    request to a World Monitor host -- or any construction of its SDK
    client -- fails the test.
    """
    requested_hosts: list[str] = []
    worldmonitor_calls: list[str] = []

    real_request = httpx.Client.request

    def recording_request(self, method, url, *args, **kwargs):
        host = httpx.URL(url).host or ""
        requested_hosts.append(host)
        if "worldmonitor" in host.lower():
            worldmonitor_calls.append(str(url))
            raise AssertionError(f"World Monitor endpoint contacted in FREE mode: {url}")
        return real_request(self, method, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "request", recording_request)

    def sdk_tripwire(*args, **kwargs):
        worldmonitor_calls.append("WorldMonitorSDKClient()")
        raise AssertionError("WorldMonitorSDKClient constructed in FREE mode")

    monkeypatch.setattr(
        "worldpulse.ingestion.worldmonitor.WorldMonitorSDKClient.__init__", sdk_tripwire
    )

    # Drive the real providers through the mock transport.
    from worldpulse.events.classifier import RuleBasedEventClassifier
    from worldpulse.events.deduplication import (
        apply_cluster_corroboration,
        build_cluster_evidence,
        cluster_events,
    )
    from worldpulse.database.repository import add_evidence, save_events
    from worldpulse.ingestion.providers.eonet import EONETProvider
    from worldpulse.ingestion.providers.gdacs import GDACSProvider
    from worldpulse.ingestion.providers.gdelt import GDELTProvider
    from worldpulse.ingestion.providers.usgs import USGSProvider

    client = fx.make_client()
    events = []
    for provider in (GDELTProvider(client=client), USGSProvider(client=client),
                     EONETProvider(client=client), GDACSProvider(client=client)):
        events.extend(provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END))
    assert events

    classifier = RuleBasedEventClassifier()
    events = apply_cluster_corroboration(cluster_events(classifier.enrich_all(events)))
    save_events(db_session, events)
    add_evidence(db_session, build_cluster_evidence(events))

    assert worldmonitor_calls == []
    assert requested_hosts, "the providers should have issued HTTP requests"
    assert not any("worldmonitor" in h.lower() for h in requested_hosts)
    # Only the documented free endpoints were contacted.
    assert set(requested_hosts) <= {
        "api.gdeltproject.org", "earthquake.usgs.gov",
        "eonet.gsfc.nasa.gov", "www.gdacs.org",
    }, requested_hosts


def test_ingest_job_in_free_mode_never_selects_worldmonitor(free_mode, monkeypatch, tmp_path):
    """The job entrypoint honours free mode too."""
    from worldpulse import config as config_module
    from worldpulse.database import repository as repo
    import jobs.ingest_world_events as ingest

    monkeypatch.setattr(config_module.settings, "database_url",
                        f"sqlite:///{tmp_path / 'free.db'}")
    repo.reset_default_session_factory()
    try:
        invoked: list[str] = []
        monkeypatch.setattr(
            "worldpulse.ingestion.providers.worldmonitor.WorldMonitorProvider._fetch",
            lambda *a, **k: invoked.append("worldmonitor") or [],
        )
        # `synthetic` is the offline provider: no network, no keys, and
        # deliberately labelled as synthetic rather than posing as a feed.
        count = ingest.run(
            now=fx.WINDOW_END, lookback_days=90, providers="synthetic",
            use_checkpoints=False,
        )
        assert count > 0
        assert invoked == []
    finally:
        repo.reset_default_session_factory()


def test_health_endpoint_advertises_free_mode(free_mode):
    from fastapi.testclient import TestClient

    from apps.api.main import create_app

    client = TestClient(create_app())
    payload = client.get("/health").json()
    assert payload["data_mode"] == "FREE"
    assert payload["worldpulse_mode"] == "free"
    assert "worldmonitor" not in payload["event_providers"]


def test_market_data_default_is_free_and_offline(free_mode):
    from worldpulse.ingestion.markets import (
        SyntheticMarketDataProvider,
        get_market_data_provider,
    )

    assert isinstance(get_market_data_provider(), SyntheticMarketDataProvider)


def test_binance_and_stooq_need_no_credentials(free_mode):
    """Both free market providers parse real payload shapes with no auth."""
    from worldpulse.ingestion.markets import (
        BinancePublicMarketProvider,
        StooqMarketProvider,
    )

    client = fx.make_client()
    bars = BinancePublicMarketProvider(client=client).get_bars(
        "BTC-USD", fx.WINDOW_START, fx.WINDOW_START + timedelta(hours=2), interval="1h",
    )
    assert len(bars) == 2
    assert bars[0].source == "binance"
    assert bars[0].close == pytest.approx(42750.20)

    daily = StooqMarketProvider(client=client).get_bars(
        "^GSPC", fx.WINDOW_START - timedelta(days=5), fx.WINDOW_END, interval="1d",
    )
    assert len(daily) == 2
    assert daily[-1].source == "stooq"
    assert daily[-1].close == pytest.approx(4807.12)


def test_context_providers_are_not_event_providers(free_mode):
    """FRED/EIA must never leak into the event stream."""
    from worldpulse.ingestion.providers.base import WorldEventProvider
    from worldpulse.ingestion.providers.eia import EIAProvider
    from worldpulse.ingestion.providers.fred import FREDProvider

    assert not issubclass(FREDProvider, WorldEventProvider)
    assert not issubclass(EIAProvider, WorldEventProvider)
    assert not FREDProvider().is_available()  # no key configured
    assert not EIAProvider().is_available()


def test_context_providers_parse_real_series_shapes(free_mode):
    from datetime import datetime, timezone

    from worldpulse.ingestion.providers.eia import EIAProvider
    from worldpulse.ingestion.providers.fred import FREDProvider

    client = fx.make_client()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 16, tzinfo=timezone.utc)

    fred = FREDProvider(client=client, api_key="test-fred-key")
    points = fred.get_series("DGS10", start, end)
    assert len(points) == 3
    assert points[1].value == pytest.approx(3.95)
    # FRED's "." missing marker becomes None, not a dropped row.
    assert points[2].value is None

    eia = EIAProvider(client=client, api_key="test-eia-key")
    series = eia.get_series("PET.WCESTUS1.W", start, end)
    assert len(series) == 2
    assert series[0].unit == "MBBL"
    assert series[-1].value == pytest.approx(429876)


def test_context_providers_return_empty_without_a_key(free_mode):
    from datetime import datetime, timezone

    from worldpulse.ingestion.providers.eia import EIAProvider
    from worldpulse.ingestion.providers.fred import FREDProvider

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 16, tzinfo=timezone.utc)
    assert FREDProvider(api_key=None).get_series("DGS10", start, end) == []
    assert EIAProvider(api_key=None).get_series("PET.RWTC.D", start, end) == []
