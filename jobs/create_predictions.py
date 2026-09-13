#!/usr/bin/env python3
"""Job: generate predictions for events that don't have one yet.

Usage:
    python jobs/create_predictions.py --now 2024-06-01T00:00:00
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import select

from worldpulse.config import settings
from worldpulse.database.models import PredictionORM
from worldpulse.database.repository import get_default_session_factory, get_events_as_of, save_prediction
from worldpulse.ingestion.markets import SyntheticMarketDataProvider
from worldpulse.prediction.predictor import create_predictions_for_event, prediction_result_to_orm


def run(now: datetime, seed: int | None = None, lookback_days: int = 365) -> int:
    seed = seed if seed is not None else settings.random_seed
    provider = SyntheticMarketDataProvider(base_seed=seed)

    factory = get_default_session_factory()
    session = factory()
    created = 0
    try:
        events = get_events_as_of(session, as_of=now)
        already_scored_event_ids = {
            row.event_id for row in session.execute(select(PredictionORM.event_id)).all()
        }
        for event in events:
            if event.id in already_scored_event_ids:
                continue
            results = create_predictions_for_event(session, provider, event, now, lookback_days=lookback_days)
            for result in results:
                orm = prediction_result_to_orm(result)
                save_prediction(session, orm)
                created += 1
    finally:
        session.close()
    return created


def main(now: datetime | None = None, seed: int | None = None, lookback_days: int = 365) -> int:
    now = now or datetime.now(timezone.utc)
    count = run(now, seed=seed, lookback_days=lookback_days)
    print(f"[create_predictions] created {count} predictions as of {now.isoformat()}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", "--as-of", dest="now", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--lookback-days", type=int, default=365)
    args = parser.parse_args()
    now_dt = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    main(now=now_dt, seed=args.seed, lookback_days=args.lookback_days)
