"""Persistent semantic intelligence, generation cache, and snapshot lifecycle."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, UTCDateTime, utcnow


class WorldShiftEvidenceORM(Base):
    __tablename__ = "world_shift_evidence"
    evidence_id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, default="GDELT")
    source_domain: Mapped[str] = mapped_column(String, default="", index=True)
    original_headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONColumn, default=list)
    first_run_id: Mapped[str] = mapped_column(String, index=True)
    last_run_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class WorldShiftEventORM(Base):
    __tablename__ = "world_shift_events"
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    shift_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    evidence_class: Mapped[str] = mapped_column(String)
    evidence_ids: Mapped[list] = mapped_column(JSONColumn, default=list)
    entity_ids: Mapped[list] = mapped_column(JSONColumn, default=list)
    generation_run_id: Mapped[str] = mapped_column(String, index=True)


class WorldShiftClaimORM(Base):
    __tablename__ = "world_shift_claims"
    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    shift_id: Mapped[str] = mapped_column(String, index=True)
    text: Mapped[str] = mapped_column(Text)
    evidence_class: Mapped[str] = mapped_column(String)
    evidence_ids: Mapped[list] = mapped_column(JSONColumn, default=list)
    entity_ids: Mapped[list] = mapped_column(JSONColumn, default=list)
    generation_run_id: Mapped[str] = mapped_column(String, index=True)


class WorldShiftEntityORM(Base):
    __tablename__ = "world_shift_entities"
    entity_id: Mapped[str] = mapped_column(String, primary_key=True)
    shift_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    normalized_name: Mapped[str] = mapped_column(String, index=True)
    entity_type: Mapped[str] = mapped_column(String)
    evidence_ids: Mapped[list] = mapped_column(JSONColumn, default=list)
    generation_run_id: Mapped[str] = mapped_column(String, index=True)


class WorldShiftRelationshipORM(Base):
    __tablename__ = "world_shift_relationships"
    relationship_id: Mapped[str] = mapped_column(String, primary_key=True)
    shift_id: Mapped[str] = mapped_column(String, index=True)
    source_entity_id: Mapped[str] = mapped_column(String, index=True)
    target_entity_id: Mapped[str] = mapped_column(String, index=True)
    relationship_type: Mapped[str] = mapped_column(String)
    label: Mapped[str] = mapped_column(Text)
    evidence_class: Mapped[str] = mapped_column(String)
    evidence_ids: Mapped[list] = mapped_column(JSONColumn, default=list)
    claim_ids: Mapped[list] = mapped_column(JSONColumn, default=list)
    generation_run_id: Mapped[str] = mapped_column(String, index=True)


class AIGenerationORM(Base):
    __tablename__ = "world_shift_ai_generations"
    cache_key: Mapped[str] = mapped_column(String, primary_key=True)
    shift_id: Mapped[str] = mapped_column(String, index=True)
    stage: Mapped[str] = mapped_column(String, index=True)
    persona: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[str] = mapped_column(String)
    schema_version: Mapped[str] = mapped_column(String)
    input_digest: Mapped[str] = mapped_column(String)
    generation_run_id: Mapped[str] = mapped_column(String, index=True)
    output: Mapped[dict] = mapped_column(JSONColumn)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class WorldShiftSnapshotORM(Base):
    __tablename__ = "world_shift_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(String, index=True)
    shift_id: Mapped[str] = mapped_column(String, index=True)
    persona: Mapped[str] = mapped_column(String, index=True)
    lifecycle: Mapped[str] = mapped_column(String, index=True)  # ACTIVE|BUILDING|FAILED|HISTORICAL
    rank: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSONColumn)
    generation_run_id: Mapped[str] = mapped_column(String, index=True)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    valid_until: Mapped[datetime] = mapped_column(UTCDateTime)
    __table_args__ = (UniqueConstraint("snapshot_id", "shift_id", "persona", name="uq_snapshot_shift_persona"),)


class WorldShiftRefreshRunORM(Base):
    __tablename__ = "world_shift_refresh_runs"
    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, index=True)
    stage: Mapped[str] = mapped_column(String)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=10)
    current_snapshot_id: Mapped[str | None] = mapped_column(String, nullable=True)
    new_snapshot_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_deduplicated: Mapped[int] = mapped_column(Integer, default=0)
    shifts_generated: Mapped[int] = mapped_column(Integer, default=0)
    ai_generations_attempted: Mapped[int] = mapped_column(Integer, default=0)
    ai_generations_reused: Mapped[int] = mapped_column(Integer, default=0)
    validation_failures: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (Index("ix_refresh_active", "status", "created_at"),)


class WorldShiftRuntimeConfigORM(Base):
    __tablename__ = "world_shift_runtime_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    web_research_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    web_results_per_shift: Mapped[int] = mapped_column(Integer, default=3)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
