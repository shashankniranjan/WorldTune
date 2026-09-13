"""THE critical test: WorldPulse works fully with WORLDMONITOR_API_KEY unset.

Before the provider refactor, World Monitor was the mandatory event
source. This module is the regression guard for that no longer being true.
Every test here runs with `WORLDMONITOR_API_KEY` (and the optional
free-registration keys) explicitly deleted from the environment, and
asserts:

  1. importing/constructing the app and the provider registry succeeds;
  2. `WorldMonitorProvider.is_available()` is False and it is excluded
     from `get_active_providers()`;
  3. the default active provider set is the four no-key open feeds;
  4. `/health` and `/health/providers` respond 200, reporting World
     Monitor as DISABLED -- a normal state, not an error;
  5. a prediction can be generated **end to end** -- ingest -> classify ->
     cross-source dedup -> persist -> market data -> analogue retrieval ->
     prediction -> resolution -> scoreboard -- using only free providers
     with their HTTP mocked;
  6. no World Monitor code path is ever entered while doing so.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests import provider_fixtures as fx
from worldpulse.config import settings
from worldpulse.database.models import PredictionORM, WorldEventORM
from worldpulse.database.repository import (
    add_evidence,
    get_events_as_of,
    save_bars,
    save_events,
)
from worldpulse.evaluation.outcome_resolver import resolve_predictions
from worldpulse.evaluation.scoring import compute_scoreboard
from worldpulse.events.classifier import RuleBasedEventClassifier, get_classifier
from worldpulse.events.deduplication import (
    apply_cluster_corroboration,
    build_cluster_evidence,
    cluster_events,
)
from worldpulse.ingestion.markets import SyntheticMarketDataProvider
from worldpulse.ingestion.providers import registry
from worldpulse.ingestion.providers.eonet import EONETProvider
from worldpulse.ingestion.providers.gdacs import GDACSProvider
from worldpulse.ingestion.providers.gdelt import GDELTProvider
from worldpulse.ingestion.providers.usgs import USGSProvider
from worldpulse.ingestion.providers.worldmonitor import WorldMonitorProvider
from worldpulse.markets.instruments import all_symbols
from worldpulse.prediction.predictor import create_predictions_for_event, prediction_result_to_orm

OPTIONAL_KEYS = [
    "WORLDMONITOR_API_KEY",
    "NASA_FIRMS_API_KEY",
    "ACLED_EMAIL",
    "ACLED_PASSWORD",
    "FRED_API_KEY",
    "EIA_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
]


@pytest.fixture()
def no_keys(monkeypatch):
    """Delete every optional key from both the env and the loaded settings."""
    for key in OPTIONAL_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(settings, "worldmonitor_api_key", None)
    monkeypatch.setattr(settings, "nasa_firms_api_key", None)
    monkeypatch.setattr(settings, "acled_email", None)
    monkeypatch.setattr(settings, "acled_password", None)
    monkeypatch.setattr(settings, "fred_api_key", None)
    monkeypatch.setattr(settings, "eia_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    monkeypatch.setattr(settings, "event_providers", "gdelt,usgs,eonet,gdacs")
    monkeypatch.setattr(settings, "worldpulse_mode", "free")
    registry.reset_registry()
    yield
    registry.reset_registry()


# --- 1 & 2: registry behaviour ------------------------------------------

def test_registry_builds_without_worldmonitor_key(no_keys):
    active = registry.get_active_providers()
    assert active, "the free provider set must still produce active providers"
    assert "worldmonitor" not in [p.name for p in active]


def test_worldmonitor_provider_reports_unavailable(no_keys):
    provider = WorldMonitorProvider()
    assert provider.is_available() is False
    assert provider.disabled_reason() == (
        "WorldMonitorProvider disabled: WORLDMONITOR_API_KEY not set"
    )
    # And it degrades to an empty list rather than raising.
    events = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
    assert events == []
    assert provider.health.status() == "DISABLED"


def test_worldmonitor_excluded_even_when_explicitly_requested(no_keys, monkeypatch):
    """Listing it without a key is a logged skip, never a crash."""
    monkeypatch.setattr(settings, "event_providers", "gdelt,usgs,worldmonitor")
    registry.reset_registry()
    active = registry.get_active_providers()
    assert [p.name for p in active] == ["gdelt", "usgs"]
    skips = registry.get_skips()
    assert "worldmonitor" in skips
    assert "paid" in skips["worldmonitor"].lower() or "WORLDMONITOR_API_KEY" in skips["worldmonitor"]


# --- 3: default provider set --------------------------------------------

def test_default_provider_set_needs_no_keys(no_keys):
    assert settings.provider_names() == ["gdelt", "usgs", "eonet", "gdacs"]
    assert [p.name for p in registry.get_active_providers()] == [
        "gdelt", "usgs", "eonet", "gdacs"
    ]
    for provider in registry.get_active_providers():
        assert provider.requires_key is False
        assert provider.is_paid is False


def test_classifier_default_needs_no_llm_key(no_keys):
    assert settings.ai_classifier == "rules"
    assert isinstance(get_classifier(), RuleBasedEventClassifier)


# --- 4: API startup + health -------------------------------------------

def test_app_starts_and_reports_free_mode(no_keys):
    from apps.api.main import create_app

    app = create_app()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["data_mode"] == "FREE"
    assert health.json()["classifier"] == "rules"

    providers = client.get("/health/providers")
    assert providers.status_code == 200, "a missing optional key must not be an API error"
    payload = providers.json()
    assert payload["data_mode"] == "FREE"
    assert "worldmonitor" not in payload["active_providers"]

    by_name = {p["provider"]: p for p in payload["providers"]}
    assert by_name["worldmonitor"]["status"] == "DISABLED"
    assert by_name["worldmonitor"]["disabled_reason"]
    assert by_name["firms"]["status"] == "DISABLED"
    for name in ("gdelt", "usgs", "eonet", "gdacs"):
        assert by_name[name]["status"] != "DISABLED"
    assert payload["cost_groups"]["optional_paid"] == ["worldmonitor"]


# --- 5 & 6: full end-to-end prediction on free providers only ----------

def test_end_to_end_prediction_using_only_free_providers(no_keys, db_session, monkeypatch):
    """Ingest -> classify -> dedup -> persist -> predict -> resolve -> score.

    Free providers only, all HTTP mocked. Also asserts World Monitor is
    never invoked: both its client classes are replaced with tripwires.
    """
    # --- tripwires: any World Monitor code path fails the test loudly ---
    invoked: list[str] = []

    def tripwire(*args, **kwargs):
        invoked.append("worldmonitor")
        raise AssertionError("World Monitor code path was invoked in FREE mode")

    monkeypatch.setattr(
        "worldpulse.ingestion.worldmonitor.WorldMonitorSDKClient.__init__", tripwire
    )
    monkeypatch.setattr(
        "worldpulse.ingestion.providers.worldmonitor.WorldMonitorProvider._fetch", tripwire
    )

    # --- 1. ingest from the free providers (HTTP mocked) ---
    client = fx.make_client()
    providers = [
        GDELTProvider(client=client),
        USGSProvider(client=client, min_magnitude=4.0),
        EONETProvider(client=client),
        GDACSProvider(client=client),
    ]
    raw_events = []
    for provider in providers:
        fetched = provider.fetch_events(fx.WINDOW_START, fx.WINDOW_END)
        assert provider.health.error_count == 0, f"{provider.name}: {provider.health.last_error}"
        raw_events.extend(fetched)
    assert len(raw_events) >= 5, f"expected several events, got {len(raw_events)}"
    assert {e.provider for e in raw_events} == {"gdelt", "usgs", "eonet", "gdacs"}

    # --- 2. classify/enrich with the rule-based (keyless) classifier ---
    classifier = RuleBasedEventClassifier()
    events = classifier.enrich_all(raw_events)
    assert all(e.potential_assets for e in events), \
        "the impact-channel table must give every event candidate assets"

    # --- 3. cross-source dedup + persist + provenance ---
    events = apply_cluster_corroboration(cluster_events(events))
    assert all(e.event_cluster_id for e in events)
    # The Taiwan quake is reported by all four feeds -> 4-source corroboration.
    quake = next(e for e in events if e.provider == "usgs")
    assert quake.corroboration_count >= 3, (
        "cross-source clustering must raise corroboration_count"
    )
    save_events(db_session, events)
    add_evidence(db_session, build_cluster_evidence(events))

    persisted = db_session.execute(select(WorldEventORM)).scalars().all()
    assert len(persisted) == len(events)
    assert {row.provider for row in persisted} == {"gdelt", "usgs", "eonet", "gdacs"}

    # --- 4. market data (synthetic: deterministic, offline, free) ---
    market = SyntheticMarketDataProvider(base_seed=42)
    # A long history so analogue retrieval has enough samples to clear the
    # min_sample_size gate; the event window is T-24h..T+24h around each
    # event, so bars must extend past the last event too.
    history_start = fx.WINDOW_START - timedelta(days=400)
    history_end = fx.WINDOW_END + timedelta(days=3)
    target_symbols = sorted({s for e in events for s in e.potential_assets})
    assert target_symbols, "no candidate assets to price"
    for symbol in target_symbols:
        save_bars(db_session, market.get_bars(symbol, history_start, history_end, interval="1h"))

    # --- 5. synthetic historical analogues so the model has a sample ---
    # Analogue retrieval needs *past* events of the same kind. Free
    # providers only cover the requested window, so seed the history from
    # the deterministic offline source -- still zero-cost, still no key.
    from worldpulse.ingestion.providers.worldmonitor import SyntheticEventProvider

    historical = SyntheticEventProvider(seed=11).fetch_events(
        history_start, fx.WINDOW_START - timedelta(days=1)
    )
    historical = classifier.enrich_all(historical)
    historical = apply_cluster_corroboration(cluster_events(historical))
    save_events(db_session, historical)
    for symbol in sorted({s for e in historical for s in e.potential_assets}):
        if symbol not in target_symbols:
            save_bars(db_session,
                      market.get_bars(symbol, history_start, history_end, interval="1h"))

    # --- 6. predictions ---
    as_of = fx.WINDOW_END
    candidates = [
        e for e in get_events_as_of(db_session, as_of=as_of)
        if e.provider in {"gdelt", "usgs", "eonet", "gdacs"}
    ]
    assert candidates, "free-provider events must be retrievable point-in-time"

    created = []
    for event in candidates:
        for result in create_predictions_for_event(db_session, market, event, as_of):
            orm = prediction_result_to_orm(result)
            db_session.add(orm)
            created.append(orm)
    db_session.commit()
    assert created, "a prediction must be generatable from free providers alone"
    for prediction in created:
        assert prediction.created_at <= as_of, "no look-ahead"

    # --- 7. resolution + scoreboard ---
    resolve_predictions(db_session, market, as_of + timedelta(hours=30))
    all_predictions = list(db_session.execute(select(PredictionORM)).scalars().all())
    assert [p for p in all_predictions if p.resolved_at is not None], \
        "at least one prediction must resolve"
    report = compute_scoreboard(all_predictions)
    assert 0.0 <= report.coverage <= 1.0

    # --- 8. World Monitor was never touched ---
    assert invoked == [], f"World Monitor was invoked: {invoked}"


def test_backfill_synthetic_path_still_works_without_any_keys(no_keys, tmp_path):
    """The offline demo entrypoint must not have regressed."""
    from jobs.backfill import run_backfill
    from worldpulse.database import repository as repo

    summary = run_backfill(days=3, seed=42, db_path=str(tmp_path / "backfill.db"))
    assert summary["data_mode"] == "FREE"
    assert summary["total_events"] > 0
    assert summary["events_by_provider"].get("synthetic", 0) > 0
    assert "worldmonitor" not in summary["events_by_provider"]
    repo.reset_default_session_factory()


def test_historical_backfill_mode_runs_on_free_providers(no_keys, monkeypatch, tmp_path):
    """`jobs.backfill --start ... --providers usgs,gdelt` end to end.

    The real-provider historical mode is a documented entrypoint, so it
    gets coverage too -- with the providers' HTTP mocked, since the test
    suite makes no network calls.
    """
    from worldpulse.ingestion.providers import registry as reg
    import jobs.backfill as backfill

    monkeypatch.setattr(
        "worldpulse.ingestion.providers.registry.EVENT_PROVIDER_FACTORIES",
        {
            "usgs": lambda: USGSProvider(client=fx.make_client(), min_magnitude=4.0),
            "gdelt": lambda: GDELTProvider(client=fx.make_client()),
        },
    )
    reg.reset_registry()
    try:
        summary = backfill.run_historical_backfill(
            start=fx.WINDOW_START,
            end=fx.WINDOW_END,
            providers="usgs,gdelt",
            db_path=str(tmp_path / "historical.db"),
            chunk_days=1,
        )
    finally:
        reg.reset_registry()
        from worldpulse.database import repository as repo

        repo.reset_default_session_factory()

    assert summary["data_mode"] == "FREE"
    assert summary["total_events"] > 0
    assert set(summary["events_by_provider"]) <= {"usgs", "gdelt"}
    assert "worldmonitor" not in summary["events_by_provider"]
    assert summary["event_clusters"] > 0
