"""`worldtune_scores` and `daily_recommendations` (spec sections 14, 18, 25).

A stored score is never a bare number: `breakdown` carries the six weighted
components and `evidence` carries the concrete facts behind them, so the API
can answer "why is this 82?" from storage without recomputation.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, UTCDateTime, utcnow


class WorldTuneScoreORM(Base):
    __tablename__ = "worldtune_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(String, index=True)
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    domain: Mapped[str] = mapped_column(String, index=True)       # financial|career
    entity_type: Mapped[str] = mapped_column(String, index=True)  # asset|skill|job|technology
    entity_id: Mapped[str] = mapped_column(String, index=True)

    score: Mapped[float] = mapped_column(Float, index=True)       # 0..100
    # {"persona_relevance": {...}, "trend_momentum": {...}, ...} -- the six
    # section-14 components, each with raw value, weight and contribution.
    breakdown: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    evidence: Mapped[list] = mapped_column(JSONColumn, default=list)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (Index("ix_scores_persona_domain_score", "persona_id", "domain", "score"),)


class DailyRecommendationORM(Base):
    """One "Daily Tune" item: learn / apply / watch / read."""

    __tablename__ = "daily_recommendations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(String, index=True)
    for_date: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    kind: Mapped[str] = mapped_column(String, index=True)   # learn|apply|watch|read
    title: Mapped[str] = mapped_column(Text)
    detail: Mapped[str] = mapped_column(Text, default="")
    why: Mapped[str] = mapped_column(Text, default="")
    entity_type: Mapped[str] = mapped_column(String, default="")
    entity_id: Mapped[str] = mapped_column(String, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
