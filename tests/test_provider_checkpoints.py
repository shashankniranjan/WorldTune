"""Checkpoints + idempotent ingestion.

Re-running ingestion over an overlapping window must not duplicate rows,
and each provider's watermark must let the next run resume instead of
re-downloading. Both are what make a scheduled live poll cheap and a
re-run of a backfill safe.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from tests import provider_fixtures as fx
from worldpulse.database.models import EventEvidenceORM, WorldEventORM
from worldpulse.database.repository import (
    add_evidence,
    event_exists,
    get_checkpoint,
    save_events,
    set_checkpoint,
)
from worldpulse.events.deduplication import build_cluster_evidence, cluster_events
from worldpulse.ingestion.providers.usgs import USGSProvider


def _usgs_events():
    return USGSProvider(client=fx.make_client()).fetch_events(fx.WINDOW_START, fx.WINDOW_END)


def test_checkpoint_roundtrip_and_forward_only(db_session):
    assert get_checkpoint(db_session, "usgs") is None

    t1 = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
    set_checkpoint(db_session, "usgs", last_event_time=t1, last_cursor="cursor-1")
    row = get_checkpoint(db_session, "usgs")
    assert row is not None
    assert row.last_event_time == t1
    assert row.last_cursor == "cursor-1"
    assert row.updated_at.tzinfo is not None

    # Advancing works.
    t2 = t1 + timedelta(hours=6)
    set_checkpoint(db_session, "usgs", last_event_time=t2)
    assert get_checkpoint(db_session, "usgs").last_event_time == t2

    # Rewinding does NOT: a backfill of an older window must not make the
    # next live poll re-download months of data.
    set_checkpoint(db_session, "usgs", last_event_time=t1 - timedelta(days=30))
    assert get_checkpoint(db_session, "usgs").last_event_time == t2

    # Checkpoints are per-provider.
    assert get_checkpoint(db_session, "gdelt") is None


def test_reingesting_the_same_window_is_idempotent(db_session):
    events = cluster_events(_usgs_events())

    first = save_events(db_session, events)
    assert first == len(events)
    add_evidence(db_session, build_cluster_evidence(events))

    # A second run over the same window: same provider_event_ids, so no
    # new rows and no duplicate evidence.
    again = cluster_events(_usgs_events())
    assert save_events(db_session, again) == 0
    assert add_evidence(db_session, build_cluster_evidence(again)) == 0

    total_events = db_session.execute(select(func.count()).select_from(WorldEventORM)).scalar_one()
    total_evidence = db_session.execute(
        select(func.count()).select_from(EventEvidenceORM)
    ).scalar_one()
    assert total_events == len(events)
    assert total_evidence == len(events)


def test_provider_event_id_upsert_survives_a_changed_primary_key(db_session):
    """Dedup on `(provider, provider_event_id)`, not only on `id`.

    If a provider ever changes how it derives `WorldEvent.id`, the
    provider-namespaced pair still prevents a duplicate row.
    """
    events = cluster_events(_usgs_events())
    save_events(db_session, events)
    assert event_exists(db_session, "usgs", "us7000abcd")

    relabelled = [e.model_copy(deep=True) for e in events]
    for event in relabelled:
        event.id = f"different-{event.provider_event_id}"
    assert save_events(db_session, relabelled) == 0

    total = db_session.execute(select(func.count()).select_from(WorldEventORM)).scalar_one()
    assert total == len(events)


def test_event_exists_is_false_for_unknown_and_blank_ids(db_session):
    assert event_exists(db_session, "usgs", "nope") is False
    assert event_exists(db_session, "", "") is False


def test_ingest_job_resumes_from_the_checkpoint(monkeypatch, tmp_path):
    """The job must narrow the fetch window to the provider's watermark."""
    from worldpulse import config as config_module
    from worldpulse.database import repository as repo
    import jobs.ingest_world_events as ingest

    monkeypatch.setattr(config_module.settings, "database_url",
                        f"sqlite:///{tmp_path / 'ckpt.db'}")
    repo.reset_default_session_factory()
    try:
        windows: list[tuple[datetime, datetime]] = []

        class RecordingProvider(USGSProvider):
            name = "usgs"

            def fetch_events(self, start_time, end_time):
                windows.append((start_time, end_time))
                return super().fetch_events(start_time, end_time)

        monkeypatch.setattr(
            "worldpulse.ingestion.providers.registry.EVENT_PROVIDER_FACTORIES",
            {"usgs": lambda: RecordingProvider(client=fx.make_client())},
        )
        from worldpulse.ingestion.providers import registry

        registry.reset_registry()

        as_of = fx.WINDOW_END
        assert ingest.run(now=as_of, lookback_days=30, providers="usgs") > 0
        first_start = windows[0][0]

        # Second run: the checkpoint should push `start` forward to the
        # newest event already seen (minus the small overlap margin).
        ingest.run(now=as_of + timedelta(hours=1), lookback_days=30, providers="usgs")
        second_start = windows[1][0]
        assert second_start > first_start, (
            f"expected the checkpoint to advance the window: {first_start} -> {second_start}"
        )

        factory = repo.get_default_session_factory()
        session = factory()
        try:
            checkpoint = get_checkpoint(session, "usgs")
            assert checkpoint is not None
            assert checkpoint.last_event_time is not None
            # And no duplicate rows from the overlapping second run.
            total = session.execute(
                select(func.count()).select_from(WorldEventORM)
            ).scalar_one()
            assert total == 2  # the two fixture earthquakes
        finally:
            session.close()
    finally:
        from worldpulse.ingestion.providers import registry as reg

        reg.reset_registry()
        repo.reset_default_session_factory()
