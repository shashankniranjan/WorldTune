"""Full pipeline smoke test: mock ingestion -> classify -> cluster ->
similarity -> prediction -> resolve -> score, using a temp SQLite DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from worldpulse.database.models import PredictionORM
from worldpulse.database.repository import get_events_as_of, save_events, save_bars
from worldpulse.evaluation.outcome_resolver import resolve_predictions
from worldpulse.evaluation.scoring import compute_scoreboard
from worldpulse.events.classifier import RuleBasedEventClassifier
from worldpulse.events.deduplication import cluster_events
from worldpulse.ingestion.markets import SyntheticMarketDataProvider
from worldpulse.ingestion.worldmonitor import MockWorldMonitorClient
from worldpulse.markets.instruments import all_symbols
from worldpulse.prediction.predictor import create_predictions_for_event, prediction_result_to_orm


def test_full_pipeline_smoke(db_session):
    epoch = datetime(2022, 1, 1, tzinfo=timezone.utc)
    end_of_history = epoch + timedelta(days=200)

    # 1. Ingest (mock) + classify
    client = MockWorldMonitorClient(seed=99)
    raw_items = client.get_news_intelligence(epoch, end_of_history)
    assert len(raw_items) > 20

    classifier = RuleBasedEventClassifier()
    events = [classifier.classify(item) for item in raw_items]

    # 2. Dedup/cluster
    events = cluster_events(events)
    assert all(e.event_cluster_id is not None for e in events)

    save_events(db_session, events)

    # 3. Ingest market data for all instruments over the same span.
    provider = SyntheticMarketDataProvider(base_seed=99)
    for symbol in all_symbols():
        bars = provider.get_bars(symbol, epoch - timedelta(days=30), end_of_history, interval="1h")
        save_bars(db_session, bars)

    # 4. Generate predictions for a batch of events well within history so
    # some outcomes are resolvable, using an as_of near the end of history.
    as_of = end_of_history - timedelta(days=5)
    candidate_events = [e for e in get_events_as_of(db_session, as_of=as_of) if e.occurred_at < as_of - timedelta(days=10)]

    created_predictions = []
    for event in candidate_events[:15]:
        results = create_predictions_for_event(db_session, provider, event, as_of)
        for result in results:
            orm = prediction_result_to_orm(result)
            db_session.add(orm)
            created_predictions.append(orm)
    db_session.commit()

    assert len(created_predictions) > 0
    for p in created_predictions:
        assert p.created_at <= as_of

    # 5. Simulate time passing and resolve.
    resolve_as_of = as_of + timedelta(hours=30)
    resolve_predictions(db_session, provider, resolve_as_of)

    all_predictions = list(db_session.execute(select(PredictionORM)).scalars().all())
    resolved = [p for p in all_predictions if p.resolved_at is not None]
    assert len(resolved) > 0
    for p in resolved:
        assert p.created_at < p.resolved_at

    # 6. Score.
    report = compute_scoreboard(all_predictions)
    assert 0.0 <= report.coverage <= 1.0
    if report.directional_accuracy is not None:
        assert 0.0 <= report.directional_accuracy <= 1.0
    for acc in report.precision_by_tier.values():
        assert 0.0 <= acc <= 1.0
