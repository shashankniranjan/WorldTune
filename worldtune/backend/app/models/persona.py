"""`users` and `personas` tables (spec section 18 / section 3).

A persona is a first-class row with its own id and a `user_id` FK. Nothing
downstream hardcodes "the one user": every service takes a `persona_id`.
Only one demo persona is seeded, but multi-persona is a data question, not a
code change.

Structured sub-objects (career, financial, preferences) are stored as JSON
columns rather than exploded into child tables. They are read and written as
whole documents and are never queried field-by-field in SQL, so a JSON bag is
the honest shape; the *validated* structure lives in app/schemas/persona.py.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, EmbeddingColumn, JSONColumn, UTCDateTime, utcnow


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class PersonaORM(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String, default="")

    # {"city": "Bengaluru", "country": "India", "timezone": "Asia/Kolkata"}
    location: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    # {"current_role", "years_experience", "target_roles", "skills", "industry"}
    career: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    # {"asset_classes", "watchlist", "holdings", "sectors", "risk_appetite"}
    financial: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    # {"learning_topics", "content_depth", "daily_time_budget_minutes"}
    preferences: Mapped[dict] = mapped_column(JSONColumn, default=dict)

    # Deterministic hashing-trick vector over the persona's text surface,
    # used as one input to PersonaRelevance. Recomputed on every update.
    embedding: Mapped[list | None] = mapped_column(EmbeddingColumn, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
