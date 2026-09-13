import uuid
from datetime import datetime, timedelta, timezone

from worldpulse.database.models import PredictionORM, WorldEventORM
from worldpulse.database.repository import save_bars
from worldpulse.evaluation.outcome_resolver import resolve_predictions
from worldpulse.ingestion.markets import SyntheticMarketDataProvider


def _make_event_row(event_id, occurred_at):
    return WorldEventORM(
        id=event_id, source_id="src-1", occurred_at=occurred_at, ingested_at=occurred_at,
        event_type="military_activity", event_subtype="missile_strike",
        countries="[]", entities="[]", affected_channels="[]", potential_assets="[]",
        severity=0.7, reasoning_summary="", headline="Test event",
    )


def _make_prediction_row(event_id, symbol, horizon_hours, created_at):
    return PredictionORM(
        id=str(uuid.uuid4()), event_id=event_id, symbol=symbol, horizon_hours=horizon_hours,
        direction="UP", probability=0.75, expected_return=0.01, median_return=0.01,
        p25_return=0.0, p75_return=0.02, sample_size=20, confidence_tier="MEDIUM",
        event_domain="military_activity", created_at=created_at,
    )


def test_resolution_does_not_mutate_immutable_prediction_fields(db_session):
    event_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    event_row = _make_event_row("event-1", event_time)
    db_session.add(event_row)
    db_session.commit()

    prediction = _make_prediction_row("event-1", "GC=F", 4, event_time)
    db_session.add(prediction)
    db_session.commit()

    provider = SyntheticMarketDataProvider(base_seed=1)
    bars = provider.get_bars("GC=F", event_time - timedelta(hours=24 * 21), event_time + timedelta(hours=24), interval="1h")
    save_bars(db_session, bars)

    before = dict(
        direction=prediction.direction, probability=prediction.probability,
        expected_return=prediction.expected_return, median_return=prediction.median_return,
        p25_return=prediction.p25_return, p75_return=prediction.p75_return,
        sample_size=prediction.sample_size, confidence_tier=prediction.confidence_tier,
        created_at=prediction.created_at,
    )

    now = event_time + timedelta(hours=5)
    resolve_predictions(db_session, provider, now)

    db_session.refresh(prediction)

    for field_name, value in before.items():
        assert getattr(prediction, field_name) == value, f"{field_name} was mutated by resolution"

    assert prediction.resolved_at is not None
    assert prediction.actual_return is not None
    assert prediction.result in ("correct", "incorrect")
    assert prediction.created_at < prediction.resolved_at


def test_prediction_not_resolved_before_horizon_elapses(db_session):
    event_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db_session.add(_make_event_row("event-2", event_time))
    db_session.commit()

    prediction = _make_prediction_row("event-2", "GC=F", 24, event_time)
    db_session.add(prediction)
    db_session.commit()

    provider = SyntheticMarketDataProvider(base_seed=1)
    bars = provider.get_bars("GC=F", event_time - timedelta(hours=24 * 21), event_time + timedelta(hours=48), interval="1h")
    save_bars(db_session, bars)

    now = event_time + timedelta(hours=5)  # horizon is 24h, hasn't elapsed
    resolve_predictions(db_session, provider, now)

    db_session.refresh(prediction)
    assert prediction.resolved_at is None
    assert prediction.actual_return is None
