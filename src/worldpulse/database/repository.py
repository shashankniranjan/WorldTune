"""Persistence layer: engine/session management + point-in-time-safe queries.

Every read used by the prediction pipeline goes through a function here
that takes an explicit `as_of` cutoff and is guaranteed (see
tests/test_no_lookahead.py) to never return a row with a timestamp strictly
after `as_of`. This is the enforcement point for the causality contract
described in docs/LLD.md.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from worldpulse.database.models import (
    Base,
    EventEvidenceORM,
    MarketBarORM,
    PredictionORM,
    ProviderCheckpointORM,
    WorldEventORM,
)
from worldpulse.events.schemas import EventDomain, EventEvidence, WorldEvent
from worldpulse.ingestion.markets import Bar


def make_engine(database_url: str, echo: bool = False):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, echo=echo, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        # A plain rollback-journal on SQLite relies on POSIX file locking,
        # which some mounted/networked filesystems (FUSE, some container
        # bind mounts) don't fully support and which then surfaces as
        # opaque "disk I/O error"s. An in-process journal keeps SQLite's
        # crash-safety guarantees usable in this prototype's local/dev/test
        # context (a single-process demo DB, not a production deployment)
        # while working everywhere, including such mounts.
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=MEMORY")
            cursor.close()
    return engine


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def make_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)


_default_engine = None
_default_session_factory: sessionmaker | None = None


def get_default_session_factory(database_url: str | None = None) -> sessionmaker:
    """Lazily-created process-wide engine/session factory, used by the API
    and dashboard so they share one SQLite file without re-creating the
    engine on every request."""
    global _default_engine, _default_session_factory
    if _default_session_factory is None:
        from worldpulse.config import settings
        url = database_url or settings.database_url
        _default_engine = make_engine(url)
        init_db(_default_engine)
        _default_session_factory = make_session_factory(_default_engine)
    return _default_session_factory


def reset_default_session_factory() -> None:
    """Test helper: forces a fresh engine/session factory on next access."""
    global _default_engine, _default_session_factory
    _default_engine = None
    _default_session_factory = None


# --- WorldEvent persistence ------------------------------------------------

def _event_to_orm(event: WorldEvent) -> WorldEventORM:
    event_type = event.event_type.value if hasattr(event.event_type, "value") else event.event_type
    return WorldEventORM(
        id=event.id or str(uuid.uuid4()),
        source_id=event.source_id,
        occurred_at=event.occurred_at,
        ingested_at=event.ingested_at,
        event_type=event_type,
        event_subtype=event.event_subtype,
        countries=json.dumps(event.countries),
        entities=json.dumps(event.entities),
        affected_channels=json.dumps(event.affected_channels),
        potential_assets=json.dumps(event.potential_assets),
        severity=event.severity,
        reasoning_summary=event.reasoning_summary,
        headline=event.headline,
        source_confidence=event.source_confidence,
        corroboration_count=event.corroboration_count,
        event_cluster_id=event.event_cluster_id,
        embedding=json.dumps(event.embedding) if event.embedding is not None else None,
        # --- provenance / multi-provider fields ---
        provider=event.provider or "",
        provider_event_id=event.provider_event_id or "",
        first_seen_at=event.first_seen_at,
        event_domain=event.event_domain or event_type,
        event_subtype_detail=event.event_subtype_detail or "",
        summary=event.summary or "",
        source_urls=json.dumps(event.source_urls),
        source_name=event.source_name or "",
        raw_payload=json.dumps(event.raw_payload) if event.raw_payload is not None else None,
        classification_version=event.classification_version or "",
        locations=json.dumps(event.locations),
        latitude=event.latitude,
        longitude=event.longitude,
        industries=json.dumps(event.industries),
        commodities=json.dumps(event.commodities),
        novelty_score=event.novelty_score,
    )


def _load_json(raw: str | None, default):
    """Tolerant JSON decode: pre-refactor rows may hold NULL for the
    columns added by the provider abstraction."""
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _orm_to_event(row: WorldEventORM) -> WorldEvent:
    return WorldEvent(
        id=row.id,
        source_id=row.source_id,
        occurred_at=row.occurred_at,
        ingested_at=row.ingested_at,
        event_type=EventDomain(row.event_type),
        event_subtype=row.event_subtype,
        countries=json.loads(row.countries),
        entities=json.loads(row.entities),
        affected_channels=json.loads(row.affected_channels),
        potential_assets=json.loads(row.potential_assets),
        severity=row.severity,
        reasoning_summary=row.reasoning_summary,
        headline=row.headline,
        source_confidence=row.source_confidence,
        corroboration_count=row.corroboration_count,
        event_cluster_id=row.event_cluster_id,
        embedding=json.loads(row.embedding) if row.embedding else None,
        # --- provenance / multi-provider fields ---
        provider=row.provider or "",
        provider_event_id=row.provider_event_id or "",
        first_seen_at=row.first_seen_at,
        event_domain=row.event_domain or row.event_type,
        event_subtype_detail=row.event_subtype_detail or "",
        summary=row.summary or "",
        source_urls=_load_json(row.source_urls, []),
        source_name=row.source_name or "",
        raw_payload=_load_json(row.raw_payload, None),
        classification_version=row.classification_version or "",
        locations=_load_json(row.locations, []),
        latitude=row.latitude,
        longitude=row.longitude,
        industries=_load_json(row.industries, []),
        commodities=_load_json(row.commodities, []),
        novelty_score=row.novelty_score,
    )


def save_events(session: Session, events: list[WorldEvent]) -> int:
    """Insert events, skipping ones already present. Returns rows inserted.

    Idempotency has two keys: the primary key `id` (deterministic uuid5
    per provider event) *and* the `(provider, provider_event_id)` pair, so
    re-running ingestion over an overlapping window never duplicates rows
    even if a provider changes how it derives `id`.
    """
    inserted = 0
    for event in events:
        if event.id and session.get(WorldEventORM, event.id) is not None:
            continue
        if event.provider and event.provider_event_id:
            duplicate = session.execute(
                select(WorldEventORM.id)
                .where(WorldEventORM.provider == event.provider)
                .where(WorldEventORM.provider_event_id == event.provider_event_id)
                .limit(1)
            ).first()
            if duplicate is not None:
                continue
        session.add(_event_to_orm(event))
        inserted += 1
    session.commit()
    return inserted


def event_exists(session: Session, provider: str, provider_event_id: str) -> bool:
    """Whether this provider event has already been ingested."""
    if not provider or not provider_event_id:
        return False
    row = session.execute(
        select(WorldEventORM.id)
        .where(WorldEventORM.provider == provider)
        .where(WorldEventORM.provider_event_id == provider_event_id)
        .limit(1)
    ).first()
    return row is not None


# --- EventEvidence persistence ---------------------------------------------

def _evidence_to_orm(evidence: EventEvidence) -> EventEvidenceORM:
    return EventEvidenceORM(
        event_id=evidence.event_id,
        provider=evidence.provider,
        provider_event_id=evidence.provider_event_id or "",
        source_url=evidence.source_url,
        source_name=evidence.source_name or "",
        observed_at=evidence.observed_at,
        raw_payload=json.dumps(evidence.raw_payload) if evidence.raw_payload is not None else None,
    )


def _orm_to_evidence(row: EventEvidenceORM) -> EventEvidence:
    return EventEvidence(
        event_id=row.event_id,
        provider=row.provider,
        provider_event_id=row.provider_event_id or "",
        source_url=row.source_url,
        source_name=row.source_name or "",
        observed_at=row.observed_at,
        raw_payload=_load_json(row.raw_payload, None),
    )


def add_evidence(session: Session, evidence: list[EventEvidence] | EventEvidence) -> int:
    """Persist provenance rows, skipping ones already recorded.

    The `(event_id, provider, provider_event_id)` uniqueness means calling
    this repeatedly for the same merge is safe.
    """
    items = [evidence] if isinstance(evidence, EventEvidence) else list(evidence)
    inserted = 0
    for item in items:
        existing = session.execute(
            select(EventEvidenceORM.id)
            .where(EventEvidenceORM.event_id == item.event_id)
            .where(EventEvidenceORM.provider == item.provider)
            .where(EventEvidenceORM.provider_event_id == (item.provider_event_id or ""))
            .limit(1)
        ).first()
        if existing is not None:
            continue
        session.add(_evidence_to_orm(item))
        inserted += 1
    session.commit()
    return inserted


def get_evidence_for_event(session: Session, event_id: str) -> list[EventEvidence]:
    stmt = (
        select(EventEvidenceORM)
        .where(EventEvidenceORM.event_id == event_id)
        .order_by(EventEvidenceORM.observed_at)
    )
    return [_orm_to_evidence(r) for r in session.execute(stmt).scalars().all()]


def get_evidence_for_cluster(session: Session, event_cluster_id: str) -> list[EventEvidence]:
    """All evidence rows attached to any event in a dedup cluster."""
    event_ids = session.execute(
        select(WorldEventORM.id).where(WorldEventORM.event_cluster_id == event_cluster_id)
    ).scalars().all()
    if not event_ids:
        return []
    stmt = (
        select(EventEvidenceORM)
        .where(EventEvidenceORM.event_id.in_(list(event_ids)))
        .order_by(EventEvidenceORM.observed_at)
    )
    return [_orm_to_evidence(r) for r in session.execute(stmt).scalars().all()]


# --- Provider checkpoints --------------------------------------------------

def get_checkpoint(session: Session, provider: str) -> ProviderCheckpointORM | None:
    """Ingestion watermark for `provider`, or None if never run."""
    return session.get(ProviderCheckpointORM, provider)


def set_checkpoint(
    session: Session,
    provider: str,
    last_event_time: datetime | None = None,
    last_cursor: str | None = None,
) -> ProviderCheckpointORM:
    """Upsert `provider`'s watermark.

    `last_event_time` only ever moves forward: a backfill of an older
    window must not rewind the live watermark and cause the next live poll
    to re-download months of data.
    """
    row = session.get(ProviderCheckpointORM, provider)
    now = datetime.now(timezone.utc)
    if row is None:
        row = ProviderCheckpointORM(
            provider=provider, last_event_time=last_event_time,
            last_cursor=last_cursor, updated_at=now,
        )
        session.add(row)
    else:
        if last_event_time is not None and (
            row.last_event_time is None or last_event_time > row.last_event_time
        ):
            row.last_event_time = last_event_time
        if last_cursor is not None:
            row.last_cursor = last_cursor
        row.updated_at = now
    session.commit()
    return row


def get_events_as_of(session: Session, as_of: datetime, since: datetime | None = None) -> list[WorldEvent]:
    """Events with occurred_at <= as_of (and optionally >= since)."""
    stmt = select(WorldEventORM).where(WorldEventORM.occurred_at <= as_of)
    if since is not None:
        stmt = stmt.where(WorldEventORM.occurred_at >= since)
    stmt = stmt.order_by(WorldEventORM.occurred_at)
    rows = session.execute(stmt).scalars().all()
    return [_orm_to_event(r) for r in rows]


def get_event(session: Session, event_id: str) -> WorldEvent | None:
    row = session.get(WorldEventORM, event_id)
    return _orm_to_event(row) if row else None


# --- MarketBar persistence --------------------------------------------------

def save_bars(session: Session, bars: list[Bar]) -> None:
    for bar in bars:
        session.add(MarketBarORM(
            symbol=bar.symbol, timestamp=bar.timestamp, open=bar.open,
            high=bar.high, low=bar.low, close=bar.close, volume=bar.volume,
            source=bar.source,
        ))
    session.commit()


def get_bars_as_of(
    session: Session, symbol: str, start: datetime, as_of: datetime
) -> list[Bar]:
    """Bars for `symbol` with start <= timestamp <= as_of. Never returns a
    row with timestamp > as_of -- this is the causality enforcement point
    for market data."""
    stmt = (
        select(MarketBarORM)
        .where(MarketBarORM.symbol == symbol)
        .where(MarketBarORM.timestamp >= start)
        .where(MarketBarORM.timestamp <= as_of)
        .order_by(MarketBarORM.timestamp)
    )
    rows = session.execute(stmt).scalars().all()
    return [
        Bar(symbol=r.symbol, timestamp=r.timestamp, open=r.open, high=r.high,
            low=r.low, close=r.close, volume=r.volume, source=r.source)
        for r in rows
    ]


# --- Prediction persistence -------------------------------------------------

def save_prediction(session: Session, prediction: PredictionORM) -> None:
    session.add(prediction)
    session.commit()


def get_prediction(session: Session, prediction_id: str) -> PredictionORM | None:
    return session.get(PredictionORM, prediction_id)


def get_predictions_for_event(session: Session, event_id: str) -> list[PredictionORM]:
    stmt = select(PredictionORM).where(PredictionORM.event_id == event_id)
    return list(session.execute(stmt).scalars().all())


def get_unresolved_predictions(session: Session, as_of: datetime) -> list[PredictionORM]:
    """Predictions created strictly before `as_of` (obviously true for any
    real prediction) that have not yet been resolved."""
    stmt = (
        select(PredictionORM)
        .where(PredictionORM.resolved_at.is_(None))
        .where(PredictionORM.created_at <= as_of)
    )
    return list(session.execute(stmt).scalars().all())


def get_live_predictions(session: Session, limit: int = 100) -> list[PredictionORM]:
    stmt = select(PredictionORM).order_by(PredictionORM.created_at.desc()).limit(limit)
    return list(session.execute(stmt).scalars().all())


def get_all_predictions(session: Session) -> list[PredictionORM]:
    stmt = select(PredictionORM).order_by(PredictionORM.created_at)
    return list(session.execute(stmt).scalars().all())


def get_resolved_predictions(session: Session) -> list[PredictionORM]:
    stmt = select(PredictionORM).where(PredictionORM.resolved_at.is_not(None))
    return list(session.execute(stmt).scalars().all())
