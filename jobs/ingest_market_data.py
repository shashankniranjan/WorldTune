#!/usr/bin/env python3
"""Job: generate/persist synthetic OHLCV bars for all tracked instruments.

Usage:
    python jobs/ingest_market_data.py --now 2024-06-01T00:00:00 --lookback-days 60
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from worldpulse.config import settings
from worldpulse.database.models import MarketBarORM
from worldpulse.database.repository import get_default_session_factory, save_bars
from worldpulse.ingestion.markets import SyntheticMarketDataProvider
from worldpulse.markets.instruments import all_symbols


def run(now: datetime, lookback_days: int = 60, seed: int | None = None, interval: str = "1h") -> int:
    """Incrementally extend each symbol's bar history up to `now`.

    Rather than a naive "already have *some* bar in this window? skip"
    check (which would silently stop advancing once a symbol has any
    history at all), this looks at the latest persisted timestamp per
    symbol and only fetches/saves the new tail of bars from there to
    `now`. On a symbol's first run it backfills the full `lookback_days`
    window.
    """
    seed = seed if seed is not None else settings.random_seed
    default_start = now - timedelta(days=lookback_days)
    provider = SyntheticMarketDataProvider(base_seed=seed)

    factory = get_default_session_factory()
    session = factory()
    total = 0
    try:
        for symbol in all_symbols():
            latest = session.execute(
                select(func.max(MarketBarORM.timestamp)).where(MarketBarORM.symbol == symbol)
            ).scalar_one_or_none()
            start = max(latest, default_start) if latest is not None else default_start
            if start >= now:
                continue  # already up to date
            bars = provider.get_bars(symbol, start, now, interval=interval)
            # Avoid re-inserting the boundary bar if `start` came from an
            # existing row.
            if latest is not None:
                bars = [b for b in bars if b.timestamp > latest]
            save_bars(session, bars)
            total += len(bars)
    finally:
        session.close()
    return total


def main(now: datetime | None = None, lookback_days: int = 60, seed: int | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    count = run(now, lookback_days=lookback_days, seed=seed)
    print(f"[ingest_market_data] ingested {count} bars up to {now.isoformat()}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", "--as-of", dest="now", type=str, default=None)
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    now_dt = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    main(now=now_dt, lookback_days=args.lookback_days, seed=args.seed)
