"""Signal-bearing tables: the generic `signals` spine plus the typed
`news_events` and `technology_events` tables (spec section 18).

Why both a generic table and typed tables?
------------------------------------------
The typed tables keep the columns each domain genuinely needs (a news event
has a url and a sentiment; a technology event has stars and a velocity).
The generic `signals` table is the *uniform* surface the ranking engine
consumes -- every ingester also writes a `SignalORM` row, so scoring,
trending and dedup operate on one shape and adding a fifth signal type later
does not touch the ranker.

`source` carries provenance and doubles as the demo tag: seeded rows are
written with `is_demo=True` and `source="demo:<provider>"`, so real ingestion
can coexist in the same database without ambiguity.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, EmbeddingColumn, JSONColumn, UTCDateTime, utcnow


class SignalORM(Base):
    """Generic signal spine -- the exact shape from the spec's section-18 example."""

    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    signal_type: Mapped[str] = mapped_column(String, index=True)  # news|market|job|technology
    entity_type: Mapped[str] = mapped_column(String, index=True)  # asset|skill|company|topic|role
    entity_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String, index=True)
    raw_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)  # [-1, 1]
    # JSONB on Postgres, TEXT-backed JSON on SQLite. Attribute is named
    # `meta` because `metadata` is reserved on a SQLAlchemy declarative class;
    # the *column* is still called `metadata` in the database.
    meta: Mapped[dict] = mapped_column("metadata", JSONColumn, default=dict)
    embedding: Mapped[list | None] = mapped_column(EmbeddingColumn, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        Index("ix_signals_type_time", "signal_type", "timestamp"),
        Index("ix_signals_entity_time", "entity_type", "entity_id", "timestamp"),
    )


class NewsEventORM(Base):
    __tablename__ = "news_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    published_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String, index=True)
    domain: Mapped[str] = mapped_column(String, default="")
    language: Mapped[str] = mapped_column(String, default="en")
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    # Resolved through the entity graph (config/entity_graph.yaml).
    entities: Mapped[list] = mapped_column(JSONColumn, default=list)
    sectors: Mapped[list] = mapped_column(JSONColumn, default=list)
    tickers: Mapped[list] = mapped_column(JSONColumn, default=list)
    # Stable content hash used for cross-source deduplication.
    dedup_hash: Mapped[str] = mapped_column(String, index=True, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class TechnologyEventORM(Base):
    __tablename__ = "technology_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    name: Mapped[str] = mapped_column(String, index=True)          # e.g. "Apache Iceberg"
    category: Mapped[str] = mapped_column(String, default="")       # e.g. "data-infrastructure"
    title: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String, index=True)         # github|hackernews|demo
    stars: Mapped[int] = mapped_column(Float, default=0)
    stars_7d_delta: Mapped[float] = mapped_column(Float, default=0.0)
    points: Mapped[float] = mapped_column(Float, default=0.0)       # HN points
    mentions: Mapped[float] = mapped_column(Float, default=0.0)
    related_skills: Mapped[list] = mapped_column(JSONColumn, default=list)
    dedup_hash: Mapped[str] = mapped_column(String, index=True, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
