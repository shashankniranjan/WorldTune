#!/usr/bin/env python3
"""Job: resolve predictions whose horizon has elapsed as of `now`.

Usage:
    python jobs/resolve_predictions.py --now 2024-06-05T00:00:00
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from worldpulse.config import settings
from worldpulse.database.repository import get_default_session_factory
from worldpulse.evaluation.outcome_resolver import resolve_predictions
from worldpulse.ingestion.markets import SyntheticMarketDataProvider


def run(now: datetime, seed: int | None = None) -> int:
    seed = seed if seed is not None else settings.random_seed
    provider = SyntheticMarketDataProvider(base_seed=seed)
    factory = get_default_session_factory()
    session = factory()
    try:
        outcomes = resolve_predictions(session, provider, now)
    finally:
        session.close()
    return len(outcomes)


def main(now: datetime | None = None, seed: int | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    count = run(now, seed=seed)
    print(f"[resolve_predictions] resolved {count} predictions as of {now.isoformat()}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", "--as-of", dest="now", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    now_dt = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    main(now=now_dt, seed=args.seed)
