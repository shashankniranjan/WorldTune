"""`predictions` and `prediction_results` (spec section 18 / section 16).

Immutability contract
---------------------
A `PredictionORM` row is written once and NEVER mutated. Resolution writes a
*separate* `PredictionResultORM` row. This is deliberate and is the same
discipline WorldPulse uses: if resolution were allowed to overwrite
`predicted_direction` or `predicted_probability`, every accuracy number the
evaluation module produces would be unfalsifiable.

NON-GOAL, stated in code so it cannot be quietly dropped: WorldTune makes no
profitability claim of any kind. Directional accuracy and calibration are
research diagnostics on a prototype, not trading performance, and nothing
here should be read as investment advice.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, UTCDateTime, utcnow

DISCLAIMER = (
    "Research prototype. Directional accuracy and calibration are diagnostics "
    "only; WorldTune makes no profitability claim and this is not investment "
    "or career advice."
)


class PredictionORM(Base):
    """Immutable. Nothing outside the creating transaction may update a row here."""

    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    domain: Mapped[str] = mapped_column(String, index=True)        # financial|career
    entity_type: Mapped[str] = mapped_column(String, index=True)   # asset|skill
    entity_id: Mapped[str] = mapped_column(String, index=True)     # "BTC" / "iceberg"
    prediction_type: Mapped[str] = mapped_column(String, default="direction")
    horizon_days: Mapped[int] = mapped_column(Float, default=7)

    # financial: bullish|neutral|bearish   career: growing|stable|declining
    predicted_direction: Mapped[str] = mapped_column(String, index=True)
    predicted_probability: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # The feature vector the model actually saw -- makes a prediction replayable.
    features: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    rationale: Mapped[str] = mapped_column(String, default="")
    model_version: Mapped[str] = mapped_column(String, index=True, default="")
    resolves_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (Index("ix_predictions_entity_created", "entity_id", "created_at"),)


class PredictionResultORM(Base):
    """Resolution of a prediction. Separate row; never edits the prediction."""

    __tablename__ = "prediction_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    prediction_id: Mapped[str] = mapped_column(ForeignKey("predictions.id"), index=True, unique=True)
    resolved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    actual_outcome: Mapped[str] = mapped_column(String, index=True)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)  # e.g. realized % move
    correct: Mapped[bool] = mapped_column(Boolean, index=True, default=False)
    # (probability - outcome)^2 on the binary framing; stored for fast aggregation.
    brier: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
