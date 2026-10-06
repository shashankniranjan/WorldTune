"""SQLAlchemy ORM models.

Written to be Postgres+pgvector-compatible: the `embedding` column uses a
plain JSON/Text column here (SQLite has no vector type), but in Postgres it
would be declared as `pgvector.sqlalchemy.Vector(128)` instead -- see the
comment on `WorldEventORM.embedding` below. Everything else (schema shapes,
indexes) is written to work unchanged against Postgres.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class UTCDateTime(TypeDecorator):
    """Timezone-safe DateTime.

    SQLite's DateTime type silently drops tzinfo on round-trip, which
    causes naive/aware comparison errors throughout the causal-ordering
    logic. This decorator always stores a naive UTC datetime and always
    returns a tz-aware (UTC) datetime, so every datetime flowing through
    the ORM is aware and comparable, on both SQLite and Postgres.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    pass


class WorldEventORM(Base):
    __tablename__ = "world_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, index=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)

    event_type: Mapped[str] = mapped_column(String, index=True)
    event_subtype: Mapped[str] = mapped_column(String)
    countries: Mapped[str] = mapped_column(Text)  # JSON-encoded list[str]
    entities: Mapped[str] = mapped_column(Text)  # JSON-encoded list[str]
    affected_channels: Mapped[str] = mapped_column(Text)  # JSON-encoded list[str]
    potential_assets: Mapped[str] = mapped_column(Text)  # JSON-encoded list[str]
    severity: Mapped[float] = mapped_column(Float)
    reasoning_summary: Mapped[str] = mapped_column(Text, default="")

    headline: Mapped[str] = mapped_column(Text, default="")
    source_confidence: Mapped[float] = mapped_column(Float, default=0.7)
    corroboration_count: Mapped[int] = mapped_column(Integer, default=1)

    event_cluster_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # In Postgres: mapped_column(Vector(128)) from pgvector.sqlalchemy.
    # Here (SQLite-friendly default): JSON-encoded list[float] as text.
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)

    impact_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Provenance / multi-provider fields (added by the provider
    # abstraction refactor). All nullable-with-default so rows written by
    # the pre-refactor code path remain valid. ---
    provider: Mapped[str] = mapped_column(String, default="", index=True)
    provider_event_id: Mapped[str] = mapped_column(String, default="", index=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    event_domain: Mapped[str] = mapped_column(String, default="", index=True)
    event_subtype_detail: Mapped[str] = mapped_column(String, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    source_urls: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    source_name: Mapped[str] = mapped_column(String, default="")
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object
    classification_version: Mapped[str] = mapped_column(String, default="")
    locations: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    industries: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    commodities: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    predictions: Mapped[list["PredictionORM"]] = relationship(back_populates="event")
    evidence: Mapped[list["EventEvidenceORM"]] = relationship(back_populates="event")

    __table_args__ = (
        # Makes re-ingesting the same window idempotent: one row per
        # (provider, provider_event_id). Left non-unique because
        # pre-refactor rows share the empty-string default for both.
        Index("ix_world_events_provider_pair", "provider", "provider_event_id"),
    )


class EventEvidenceORM(Base):
    """One provider's contribution to a (possibly merged) world event.

    Cross-source dedup merges records from different providers about the
    same real-world event into a single `event_cluster_id`; rather than
    discarding the non-winning records, one evidence row is written per
    contributing source so every merge stays auditable.
    """

    __tablename__ = "event_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("world_events.id"), index=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    provider_event_id: Mapped[str] = mapped_column(String, default="", index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String, default="")
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object

    event: Mapped["WorldEventORM"] = relationship(back_populates="evidence")

    __table_args__ = (
        UniqueConstraint("event_id", "provider", "provider_event_id",
                         name="uq_event_evidence_source"),
    )


class ProviderCheckpointORM(Base):
    """Per-provider ingestion watermark.

    Lets a re-run of ingestion resume from where the last one stopped
    instead of re-downloading the same window. Combined with the
    `(provider, provider_event_id)` upsert on `world_events`, this makes
    ingestion idempotent.
    """

    __tablename__ = "provider_checkpoint"

    provider: Mapped[str] = mapped_column(String, primary_key=True)
    last_event_time: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_cursor: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class MarketBarORM(Base):
    __tablename__ = "market_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String, default="synthetic")


class PredictionORM(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("world_events.id"), index=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    horizon_hours: Mapped[int] = mapped_column(Integer, index=True)

    # --- Immutable fields, fixed at creation time (never touched by the
    # outcome resolver) ---
    direction: Mapped[str] = mapped_column(String)  # "UP" | "DOWN" | "NO_PREDICTION"
    probability: Mapped[float] = mapped_column(Float)
    expected_return: Mapped[float] = mapped_column(Float)
    median_return: Mapped[float] = mapped_column(Float)
    p25_return: Mapped[float] = mapped_column(Float)
    p75_return: Mapped[float] = mapped_column(Float)
    sample_size: Mapped[int] = mapped_column(Integer)
    confidence_tier: Mapped[str] = mapped_column(String)  # HIGH|MEDIUM|LOW|NO_PREDICTION
    event_domain: Mapped[str] = mapped_column(String, index=True)
    explanation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)

    # --- Resolution fields, set later by evaluation/outcome_resolver.py ---
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, index=True)
    actual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction_correct: Mapped[bool | None] = mapped_column(nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)  # "correct"|"incorrect"|None

    event: Mapped["WorldEventORM"] = relationship(back_populates="predictions")
