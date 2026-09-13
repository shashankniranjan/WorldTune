"""Background scheduler wiring for the "real" deployment (worker service).

Uses APScheduler to periodically run the same jobs that `jobs/*.py` expose
as standalone scripts. Not used by the test suite (tests call the job
functions directly with an explicit `as_of`), but demonstrates how the
pipeline would run continuously against wall-clock time in production.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from worldpulse.config import settings

logger = logging.getLogger(__name__)


def _run_ingest_world_events():
    """Poll every provider in `EVENT_PROVIDERS` for the newest window.

    Provider-agnostic: the job resolves the active providers from the
    registry on each tick, so adding/removing a feed is a config change,
    not a scheduler change. A short lookback is enough because each
    provider resumes from its own persisted checkpoint.
    """
    from jobs.ingest_world_events import main as ingest_world_events_main
    ingest_world_events_main(now=datetime.now(timezone.utc), lookback_days=1)


def _run_ingest_market_data():
    from jobs.ingest_market_data import main as ingest_market_data_main
    ingest_market_data_main(now=datetime.now(timezone.utc))


def _run_create_predictions():
    from jobs.create_predictions import main as create_predictions_main
    create_predictions_main(now=datetime.now(timezone.utc))


def _run_resolve_predictions():
    from jobs.resolve_predictions import main as resolve_predictions_main
    resolve_predictions_main(now=datetime.now(timezone.utc))


def build_scheduler() -> BlockingScheduler:
    from worldpulse.ingestion.providers import registry

    active = [p.name for p in registry.get_active_providers()]
    logger.info("scheduler: DATA MODE=%s, active event providers=%s, skipped=%s",
                settings.data_mode, active, registry.get_skips() or "none")
    if not active:
        logger.warning(
            "scheduler: no active event providers -- ingestion will be a no-op. "
            "Check EVENT_PROVIDERS (default: gdelt,usgs,eonet,gdacs)."
        )

    scheduler = BlockingScheduler()
    scheduler.add_job(_run_ingest_world_events, "interval",
                       seconds=settings.news_ingest_interval_seconds, id="ingest_world_events")
    scheduler.add_job(_run_ingest_market_data, "interval",
                       seconds=settings.market_ingest_interval_seconds, id="ingest_market_data")
    scheduler.add_job(_run_create_predictions, "interval",
                       seconds=settings.prediction_interval_seconds, id="create_predictions")
    scheduler.add_job(_run_resolve_predictions, "interval",
                       seconds=settings.resolution_interval_seconds, id="resolve_predictions")
    return scheduler


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    build_scheduler().start()
