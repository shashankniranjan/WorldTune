#!/usr/bin/env python3
"""Job: ingest events from every active provider, classify, dedup, persist.

Pipeline per run:

    registry.get_active_providers()      # EVENT_PROVIDERS, key-gated
      -> provider.fetch_events(start, end)  (checkpoint-aware per provider)
      -> classifier.enrich(...)             # impact channels, subtypes
      -> cluster_events(...)                # cross-source + embedding dedup
      -> save_events(...)                   # idempotent upsert
      -> add_evidence(...)                  # one row per contributing source
      -> set_checkpoint(provider, ...)      # so the next run resumes

Nothing here requires World Monitor, or any key at all: with the default
`EVENT_PROVIDERS=gdelt,usgs,eonet,gdacs` all four sources are open feeds.

Usage:
    # default providers from EVENT_PROVIDERS / settings
    python -m jobs.ingest_world_events --now 2024-06-01T00:00:00 --lookback-days 7

    # explicit providers
    python -m jobs.ingest_world_events --providers gdelt,usgs --lookback-days 2

    # deterministic offline synthetic source (no network at all)
    python -m jobs.ingest_world_events --providers synthetic --lookback-days 60
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone

from worldpulse.config import settings
from worldpulse.database.repository import (
    add_evidence,
    get_checkpoint,
    get_default_session_factory,
    save_events,
    set_checkpoint,
)
from worldpulse.events.classifier import RuleBasedEventClassifier, get_classifier
from worldpulse.events.deduplication import (
    apply_cluster_corroboration,
    build_cluster_evidence,
    cluster_events,
)
from worldpulse.ingestion.providers import registry

logger = logging.getLogger(__name__)


def run(
    now: datetime,
    lookback_days: int = 60,
    seed: int | None = None,
    providers: str | None = None,
    use_checkpoints: bool = True,
) -> int:
    """Ingest one window. Returns the number of events persisted.

    `providers` overrides `EVENT_PROVIDERS` for this run only.
    """
    seed = seed if seed is not None else settings.random_seed
    window_start = now - timedelta(days=lookback_days)

    if providers:
        # Scoped override: restore afterwards so a caller's process-wide
        # settings are not mutated permanently.
        previous = settings.event_providers
        settings.event_providers = providers
        registry.reset_registry()
        try:
            return _run_window(now, window_start, seed, use_checkpoints)
        finally:
            settings.event_providers = previous
            registry.reset_registry()
    return _run_window(now, window_start, seed, use_checkpoints)


def _run_window(now: datetime, window_start: datetime, seed: int, use_checkpoints: bool) -> int:
    active = registry.get_active_providers()
    if not active:
        logger.warning(
            "[ingest_world_events] no active providers (EVENT_PROVIDERS=%r). Skips: %s",
            settings.event_providers, registry.get_skips(),
        )
        return 0

    factory = get_default_session_factory()
    session = factory()
    try:
        collected: list = []
        for provider in active:
            start = window_start
            if use_checkpoints:
                checkpoint = get_checkpoint(session, provider.name)
                if checkpoint is not None and checkpoint.last_event_time is not None:
                    # Resume from the watermark (with a small overlap so an
                    # event that landed exactly on the boundary is not
                    # missed); the idempotent upsert absorbs the overlap.
                    resume_from = checkpoint.last_event_time - timedelta(minutes=5)
                    start = max(window_start, resume_from)
            if start >= now:
                logger.info("[ingest_world_events] %s already up to date", provider.name)
                continue

            events = provider.fetch_events(start, now)
            logger.info("[ingest_world_events] %s -> %d events (%s..%s)",
                        provider.name, len(events), start.isoformat(), now.isoformat())
            collected.extend(events)

        if not collected:
            return 0

        classifier = get_classifier()
        if isinstance(classifier, RuleBasedEventClassifier):
            collected = classifier.enrich_all(collected)

        clustered = cluster_events(
            collected,
            window_hours=settings.dedup_window_hours,
            similarity_threshold=settings.dedup_similarity_threshold,
        )
        # Cross-source agreement is what `corroboration_count` measures,
        # and the impact-score gate reads it -- so set it from the cluster.
        clustered = apply_cluster_corroboration(clustered)
        saved = save_events(session, clustered)
        add_evidence(session, build_cluster_evidence(clustered))

        # Advance each provider's watermark to its newest event this run.
        newest: dict[str, datetime] = {}
        for event in clustered:
            if not event.provider:
                continue
            current = newest.get(event.provider)
            if current is None or event.occurred_at > current:
                newest[event.provider] = event.occurred_at
        for provider_name, last_event_time in newest.items():
            set_checkpoint(session, provider_name, last_event_time=last_event_time)

        clusters = len({e.event_cluster_id for e in clustered})
        logger.info(
            "[ingest_world_events] %d records -> %d clusters, %d new rows persisted",
            len(clustered), clusters, saved,
        )
        return len(clustered)
    finally:
        session.close()


def main(
    now: datetime | None = None,
    lookback_days: int = 60,
    seed: int | None = None,
    providers: str | None = None,
) -> int:
    now = now or datetime.now(timezone.utc)
    count = run(now, lookback_days=lookback_days, seed=seed, providers=providers)
    active = providers or settings.event_providers
    print(f"[ingest_world_events] DATA MODE: {settings.data_mode} | providers={active} | "
          f"ingested/classified {count} events up to {now.isoformat()}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", "--as-of", dest="now", type=str, default=None)
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--providers", type=str, default=None,
        help="Comma list overriding EVENT_PROVIDERS, e.g. 'gdelt,usgs' or 'synthetic'",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    now_dt = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    main(now=now_dt, lookback_days=args.lookback_days, seed=args.seed, providers=args.providers)
