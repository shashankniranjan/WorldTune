"""Critical leakage test: predictions must be bit-for-bit invariant to any
future (>as_of) data present in the database at generation time, and no
repository query used by the predictor may ever return a row timestamped
after `as_of`.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from worldpulse.database.repository import get_bars_as_of, get_events_as_of, save_bars, save_events
from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.ingestion.markets import Bar, SyntheticMarketDataProvider
from worldpulse.prediction.predictor import create_predictions_for_event

EPOCH = datetime(2023, 1, 1, tzinfo=timezone.utc)


def _make_event(idx, occurred_at, severity=0.75):
    return WorldEvent(
        id=str(uuid.uuid4()),
        source_id=f"src-{idx}",
        occurred_at=occurred_at,
        ingested_at=occurred_at,
        event_type=EventDomain.MILITARY,
        event_subtype="missile_strike",
        countries=["Russia", "Ukraine"],
        entities=["Naval Fleet"],
        affected_channels=["shipping_lanes", "regional_security"],
        potential_assets=["GC=F"],
        severity=severity,
        headline=f"Missile strike incident #{idx}",
        source_confidence=0.8,
        corroboration_count=3,
    )


def _seed_history(session, provider, n_events=25, as_of_bar_end=None):
    events = [_make_event(i, EPOCH + timedelta(days=i * 3)) for i in range(n_events)]
    save_events(session, events)
    last_event_time = events[-1].occurred_at
    bar_end = as_of_bar_end or (last_event_time + timedelta(hours=48))
    bars = provider.get_bars("GC=F", EPOCH - timedelta(days=30), bar_end, interval="1h")
    save_bars(session, bars)
    return events


def test_no_lookahead_leakage_prefix_test(db_session):
    provider = SyntheticMarketDataProvider(base_seed=7)
    history_events = _seed_history(db_session, provider, n_events=25)

    target_time = history_events[-1].occurred_at + timedelta(days=3)
    target = _make_event(999, target_time)
    save_events(db_session, [target])

    as_of = target_time  # prediction time T

    results_before = create_predictions_for_event(db_session, provider, target, as_of)
    results_before_serialized = [asdict(r) for r in results_before]

    # Now inject FUTURE data (after `as_of`): a dramatic future event and a
    # future price spike bar for the same symbol.
    future_event = _make_event(12345, as_of + timedelta(days=10), severity=0.99)
    save_events(db_session, [future_event])

    future_bar = Bar(
        symbol="GC=F", timestamp=as_of + timedelta(hours=5),
        open=100000.0, high=100000.0, low=100000.0, close=100000.0,
        volume=1.0, source="poison",
    )
    save_bars(db_session, [future_bar])

    results_after = create_predictions_for_event(db_session, provider, target, as_of)
    results_after_serialized = [asdict(r) for r in results_after]

    assert results_before_serialized == results_after_serialized, (
        "Prediction changed after adding future (> as_of) data -- lookahead leakage detected."
    )


def test_repository_bar_query_never_returns_future_rows(db_session):
    provider = SyntheticMarketDataProvider(base_seed=3)
    as_of = EPOCH + timedelta(days=10)

    normal_bars = provider.get_bars("GC=F", EPOCH, as_of, interval="1h")
    save_bars(db_session, normal_bars)

    # Poison the DB with a future-dated bar.
    poison_bar = Bar(
        symbol="GC=F", timestamp=as_of + timedelta(hours=1),
        open=999.0, high=999.0, low=999.0, close=999.0, volume=1.0, source="poison",
    )
    save_bars(db_session, [poison_bar])

    result = get_bars_as_of(db_session, "GC=F", start=EPOCH, as_of=as_of)
    assert all(b.timestamp <= as_of for b in result)
    assert all(b.close != 999.0 for b in result)


def test_repository_event_query_never_returns_future_rows(db_session):
    as_of = EPOCH + timedelta(days=10)
    past_event = _make_event(1, EPOCH + timedelta(days=1))
    future_event = _make_event(2, as_of + timedelta(days=1))
    save_events(db_session, [past_event, future_event])

    result = get_events_as_of(db_session, as_of=as_of)
    result_ids = {e.id for e in result}
    assert past_event.id in result_ids
    assert future_event.id not in result_ids
    assert all(e.occurred_at <= as_of for e in result)
