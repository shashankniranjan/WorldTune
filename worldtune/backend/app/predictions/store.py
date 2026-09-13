"""Immutable prediction storage and resolution.

The contract, enforced by this module being the only writer:

  * `record_prediction` INSERTs and never updates.
  * `resolve_prediction` INSERTs a `PredictionResultORM` and never touches
    the prediction row. If a prediction already has a result, resolving it
    again is a no-op returning the existing result.

That separation is what makes the evaluation numbers in `evaluate.py`
falsifiable. A pipeline that "updates the prediction with the outcome" can
always be accused of having updated the prediction *with* the outcome.

NON-GOAL: no profitability claim. See app/models/predictions.py DISCLAIMER.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PredictionORM, PredictionResultORM

# Outcome vocabularies, kept explicit so a typo becomes an error not a silent
# "never correct" class.
FINANCIAL_OUTCOMES = ("bullish", "neutral", "bearish")
CAREER_OUTCOMES = ("growing", "stable", "declining")


def record_prediction(
    session: Session,
    *,
    persona_id: str,
    domain: str,
    entity_type: str,
    entity_id: str,
    predicted_direction: str,
    predicted_probability: float,
    confidence: float,
    horizon_days: int,
    features: dict | None = None,
    rationale: str = "",
    created_at: datetime | None = None,
    prediction_type: str = "direction",
    is_demo: bool = False,
    model_version: str | None = None,
) -> PredictionORM:
    created = created_at or datetime.now(timezone.utc)
    row = PredictionORM(
        id=str(uuid.uuid4()),
        persona_id=persona_id,
        created_at=created,
        domain=domain,
        entity_type=entity_type,
        entity_id=entity_id,
        prediction_type=prediction_type,
        horizon_days=horizon_days,
        predicted_direction=predicted_direction,
        predicted_probability=float(predicted_probability),
        confidence=float(confidence),
        features=features or {},
        rationale=rationale,
        model_version=model_version or settings.model_version,
        resolves_at=created + timedelta(days=horizon_days),
        is_demo=is_demo,
    )
    session.add(row)
    session.flush()
    return row


def resolve_prediction(
    session: Session,
    prediction: PredictionORM,
    *,
    actual_outcome: str,
    actual_value: float | None = None,
    resolved_at: datetime | None = None,
    notes: str = "",
    is_demo: bool = False,
) -> PredictionResultORM:
    """Write the outcome as a separate row. Idempotent per prediction."""
    existing = session.scalar(
        select(PredictionResultORM).where(PredictionResultORM.prediction_id == prediction.id)
    )
    if existing is not None:
        return existing

    correct = actual_outcome == prediction.predicted_direction
    result = PredictionResultORM(
        id=str(uuid.uuid4()),
        prediction_id=prediction.id,
        resolved_at=resolved_at or datetime.now(timezone.utc),
        actual_outcome=actual_outcome,
        actual_value=actual_value,
        correct=correct,
        brier=brier_score(prediction.predicted_probability, correct),
        notes=notes,
        is_demo=is_demo,
    )
    session.add(result)
    session.flush()
    return result


def brier_score(probability: float, correct: bool) -> float:
    """(p - o)^2 on the binary "was the stated direction right?" framing.

    The stated probability is always the probability *of the direction the
    model called*, so the outcome indicator is 1 when correct. This keeps
    Brier comparable across bullish and bearish calls, which a naive
    "P(up) vs did-it-go-up" framing does not when the call was bearish.
    """
    outcome = 1.0 if correct else 0.0
    return float((float(probability) - outcome) ** 2)


def due_predictions(session: Session, *, as_of: datetime | None = None
                    ) -> list[PredictionORM]:
    """Unresolved predictions whose horizon has elapsed."""
    now = as_of or datetime.now(timezone.utc)
    resolved_ids = select(PredictionResultORM.prediction_id)
    return list(session.scalars(
        select(PredictionORM)
        .where(PredictionORM.resolves_at <= now)
        .where(PredictionORM.id.not_in(resolved_ids))
        .order_by(PredictionORM.resolves_at)
    ))


def resolved_pairs(session: Session, *, domain: str | None = None,
                   persona_id: str | None = None
                   ) -> list[tuple[PredictionORM, PredictionResultORM]]:
    """Every (prediction, result) pair -- the input to evaluation."""
    stmt = select(PredictionORM, PredictionResultORM).join(
        PredictionResultORM, PredictionResultORM.prediction_id == PredictionORM.id
    )
    if domain:
        stmt = stmt.where(PredictionORM.domain == domain)
    if persona_id:
        stmt = stmt.where(PredictionORM.persona_id == persona_id)
    return [(p, r) for p, r in session.execute(stmt).all()]
