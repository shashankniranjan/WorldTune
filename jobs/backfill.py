#!/usr/bin/env python3
"""Historical backfill -- two modes, one pipeline.

**1. Synthetic walk-forward (default, offline, deterministic).**
Simulates N days from a seeded synthetic event stream. On each simulated
day D, only events/prices with timestamp <= D are used to generate that
day's predictions; later days then resolve those predictions as their
horizons elapse. This is the project's demo entrypoint and doubles as a
leakage-prevention proof: if the pipeline ever let future data leak into a
prediction, the walk-forward loop below would be impossible to run
causally (each iteration only advances `now`, never rewinds or peeks).

    python -m jobs.backfill --days 20

**2. Real-provider historical backfill.** Downloads real historical events
from the selected free providers over `[--start, --end]`, normalizes them,
cross-source-dedups, persists, then does market prices, event windows
(T-24h .. T+24h) and outcomes -- reusing exactly the same event-window /
returns / prediction / resolution code as mode 1. Only the *event source*
changes.

    python -m jobs.backfill --start 2024-01-01 --end 2024-03-01 --providers usgs,gdelt

Real historical depth, honestly (see docs/data-sources.md):
  * **USGS FDSN**: full ANSS ComCat depth -- significant events back to
    1900, dense global instrumental coverage from the 1970s. Arbitrary
    ranges genuinely work.
  * **GDELT DOC 2.0**: a rolling ~3-month window. Older ranges return few
    or no articles (not an error). Deep GDELT history needs the 15-minute
    Events CSV export, which this prototype documents but does not load.
  * **EONET**: curated natural-event catalog, roughly 2000->present, dense
    from ~2015.
  * **GDACS**: `EVENTS4APP` is a *current* alert list (last few weeks);
    it will return nothing for older windows.
  * **ACLED** (optional, free key): 1997->present for Africa,
    2018->present globally, published weekly with a ~1 week lag.
  * **FIRMS** (optional, free key): MODIS from 2000, VIIRS from 2012 via
    the `*_SP` standard-processing sources.
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from worldpulse import config as config_module
from worldpulse.config import settings
from worldpulse.database import repository as repo
from worldpulse.database.models import Base, PredictionORM, WorldEventORM
from worldpulse.evaluation.calibration import compute_calibration_table
from worldpulse.evaluation.scoring import compute_scoreboard

import jobs.create_predictions as create_predictions
import jobs.ingest_market_data as ingest_market_data
import jobs.ingest_world_events as ingest_world_events
import jobs.resolve_predictions as resolve_predictions

logger = logging.getLogger(__name__)

#: Providers used by the offline deterministic demo when none are given.
DEFAULT_SYNTHETIC_PROVIDERS = "synthetic"


def _prepare_database(db_path: str) -> str:
    db_url = f"sqlite:///{db_path}"
    # Reset to a clean schema. We drop/recreate tables via SQLAlchemy DDL
    # rather than deleting the underlying file: some filesystems (e.g. a
    # FUSE-backed mount) disallow unlinking a file that a prior process
    # still has a handle on, but DDL against an open connection always
    # works.
    reset_engine = repo.make_engine(db_url)
    Base.metadata.drop_all(reset_engine)
    Base.metadata.create_all(reset_engine)
    reset_engine.dispose()

    # Point the shared session factory at an isolated backfill DB so this
    # simulation never touches the "live" demo database.
    config_module.settings.database_url = db_url
    repo.reset_default_session_factory()
    return db_url


def _scoreboard_summary() -> dict:
    factory = repo.get_default_session_factory()
    session = factory()
    try:
        predictions = list(session.execute(select(PredictionORM)).scalars().all())
        event_rows = list(session.execute(
            select(WorldEventORM.provider, WorldEventORM.event_cluster_id)
        ).all())
    finally:
        session.close()

    report = compute_scoreboard(predictions)
    calibration = compute_calibration_table(predictions)
    events_by_provider: dict[str, int] = {}
    for provider, _cluster in event_rows:
        key = provider or "unattributed"
        events_by_provider[key] = events_by_provider.get(key, 0) + 1

    return {
        "data_mode": settings.data_mode,
        "total_events": len(event_rows),
        "event_clusters": len({cluster for _p, cluster in event_rows if cluster}),
        "events_by_provider": events_by_provider,
        "total_predictions": report.total_predictions,
        "total_resolved": report.total_resolved,
        "coverage": report.coverage,
        "directional_accuracy": report.directional_accuracy,
        "precision_by_tier": report.precision_by_tier,
        "accuracy_by_horizon": report.accuracy_by_horizon,
        "accuracy_by_domain": report.accuracy_by_domain,
        "baseline_accuracy": report.baseline_accuracy,
        "calibration_table": [
            {"range": f"{b.bucket_low:.0%}-{b.bucket_high:.0%}", "n": b.n,
             "mean_predicted": round(b.mean_predicted_probability, 3),
             "realized_accuracy": round(b.realized_accuracy, 3)}
            for b in calibration
        ],
    }


def run_backfill(days: int = 30, start: datetime | None = None, seed: int = 42,
                 db_path: str = "./data/local/backfill_run.db",
                 providers: str | None = None) -> dict:
    """Synthetic walk-forward simulation (mode 1)."""
    _prepare_database(db_path)
    # Default to the system clock: the simulated walk-forward window ends
    # "today" and runs backwards `days` simulated days from there, so a
    # fresh run always shows current-looking dates instead of a fixed
    # historical anchor. Pass --start explicitly to pin it to a specific
    # date instead (e.g. for a reproducible fixture).
    start = start or (datetime.now(timezone.utc) - timedelta(days=days))
    providers = providers or DEFAULT_SYNTHETIC_PROVIDERS

    print(f"[backfill] DATA MODE: {settings.data_mode}")
    print(f"[backfill] walk-forward: {days} simulated days from {start.isoformat()} "
          f"(providers={providers}, db={db_path})")

    # Deliberately modest lookback windows: this backfill is a
    # walk-forward *correctness* demonstration, not a scale benchmark. A
    # smaller historical window keeps each simulated day's analogue
    # retrieval fast while still exercising every stage of the pipeline.
    for day_offset in range(days):
        as_of = start + timedelta(days=day_offset)
        ingest_world_events.main(now=as_of, lookback_days=45, seed=seed, providers=providers)
        ingest_market_data.main(now=as_of, lookback_days=45, seed=seed)
        create_predictions.main(now=as_of, seed=seed, lookback_days=45)
        resolve_predictions.main(now=as_of, seed=seed)

    # Final resolution pass, well past the longest horizon (24h), to
    # resolve anything created on the last simulated day.
    final_as_of = start + timedelta(days=days + 3)
    resolve_predictions.main(now=final_as_of, seed=seed)
    return _scoreboard_summary()


def run_historical_backfill(
    start: datetime,
    end: datetime,
    providers: str,
    seed: int = 42,
    db_path: str = "./data/local/backfill_run.db",
    chunk_days: int = 7,
) -> dict:
    """Real-provider historical backfill (mode 2).

    Events are downloaded in `chunk_days` chunks (so a long range does not
    become one enormous request and so each provider's checkpoint advances
    incrementally), then the *existing* market-data / prediction /
    resolution stages run over the same range.
    """
    _prepare_database(db_path)

    print(f"[backfill] DATA MODE: {settings.data_mode}")
    print(f"[backfill] historical: {start.isoformat()} .. {end.isoformat()} "
          f"providers={providers} (db={db_path})")

    total_events = 0
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=chunk_days), end)
        span_days = max(1, (chunk_end - cursor).days)
        total_events += ingest_world_events.main(
            now=chunk_end, lookback_days=span_days, seed=seed, providers=providers,
        )
        cursor = chunk_end
    print(f"[backfill] ingested {total_events} event records from providers={providers}")

    # 2. Market prices over the same span (plus a lead-in so the
    # abnormal-return baseline window is populated).
    ingest_market_data.main(
        now=end, lookback_days=max(1, (end - start).days) + 60, seed=seed,
    )

    # 3. Event windows / analogue retrieval / predictions, then outcomes.
    # Walk day by day so predictions are only ever made from data at or
    # before their own timestamp -- the same causal guarantee mode 1 proves.
    cursor = start
    while cursor <= end:
        create_predictions.main(now=cursor, seed=seed, lookback_days=365)
        resolve_predictions.main(now=cursor, seed=seed)
        cursor += timedelta(days=1)
    resolve_predictions.main(now=end + timedelta(days=3), seed=seed)

    return _scoreboard_summary()


def print_summary(summary: dict) -> None:
    print("\n=== WorldPulse Backfill Scoreboard ===")
    print(f"DATA MODE:              {summary.get('data_mode', 'FREE')}")
    print(f"Total events:           {summary.get('total_events', 0)} "
          f"in {summary.get('event_clusters', 0)} dedup clusters")
    if summary.get("events_by_provider"):
        print("Events by provider:")
        for provider, count in sorted(summary["events_by_provider"].items()):
            print(f"  {provider:15s}: {count}")
    print(f"Total predictions:      {summary['total_predictions']}")
    print(f"Total resolved:         {summary['total_resolved']}")
    print(f"Coverage:               {summary['coverage']:.1%}")
    da = summary["directional_accuracy"]
    print(f"Directional accuracy:   {da:.1%}" if da is not None else "Directional accuracy:   n/a")
    print("Precision by confidence tier:")
    for tier, acc in summary["precision_by_tier"].items():
        print(f"  {tier:8s}: {acc:.1%}")
    print("Accuracy by horizon (hours):")
    for h, acc in summary["accuracy_by_horizon"].items():
        print(f"  {h:>3}h: {acc:.1%}")
    print("Accuracy by event domain:")
    for d, acc in summary["accuracy_by_domain"].items():
        print(f"  {d:25s}: {acc:.1%}")
    print("Baseline accuracy:")
    for name, acc in summary["baseline_accuracy"].items():
        print(f"  {name:25s}: {acc:.1%}")
    print("Calibration table (predicted probability bucket vs realized accuracy):")
    for row in summary["calibration_table"]:
        print(f"  {row['range']:>10s}  n={row['n']:<5d} predicted~{row['mean_predicted']:.2f}  "
              f"realized={row['realized_accuracy']:.2f}")
    print("=======================================\n")


def main(days: int = 30, start: datetime | None = None, seed: int = 42,
         end: datetime | None = None, providers: str | None = None) -> dict:
    """Dispatch between the two modes.

    Historical mode is selected when `--providers` is given *and* a real
    date range is available; otherwise the deterministic synthetic
    walk-forward demo runs, so the offline demo path keeps working
    unchanged.
    """
    if providers and start is not None:
        end = end or datetime.now(timezone.utc)
        summary = run_historical_backfill(
            start=start, end=end, providers=providers, seed=seed,
        )
    else:
        if providers and start is None:
            logger.warning(
                "--providers given without --start; running the synthetic walk-forward "
                "demo instead. Pass --start (and optionally --end) for a real backfill."
            )
            providers = None
        summary = run_backfill(days=days, start=start, seed=seed, providers=providers)
    print_summary(summary)
    return summary


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=30,
                        help="Synthetic walk-forward mode: number of simulated days")
    parser.add_argument("--start", type=str, default=None,
                        help="Window start (ISO). With --providers, selects real historical mode")
    parser.add_argument("--end", type=str, default=None,
                        help="Window end (ISO); defaults to now in historical mode")
    parser.add_argument("--providers", type=str, default=None,
                        help="Comma list, e.g. 'usgs,gdelt,eonet,gdacs' or 'synthetic'")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    main(days=args.days, start=_parse_dt(args.start), seed=args.seed,
         end=_parse_dt(args.end), providers=args.providers)
