"""Outcome resolution: fill in what actually happened after a prediction.

Finds predictions whose horizon has elapsed relative to a supplied `now`,
fetches the realized return (using only bars with timestamp <= now), and
sets resolution fields (`resolved_at`, `actual_return`, `direction_correct`,
`result`). Critically, this NEVER touches the immutable fields set at
prediction time (direction, probability, expected_return, etc.) -- see
tests/test_outcome_resolver.py::test_resolution_does_not_mutate_prediction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from worldpulse.database.models import PredictionORM
from worldpulse.database.repository import get_bars_as_of, get_event, get_unresolved_predictions
from worldpulse.ingestion.markets import MarketDataProvider
from worldpulse.markets.returns import compute_event_window_returns, sort_bars


@dataclass
class ResolutionOutcome:
    prediction_id: str
    actual_return: float
    direction_correct: bool
    result: str  # "correct" | "incorrect"


def resolve_predictions(session: Session, provider: MarketDataProvider, now) -> list[ResolutionOutcome]:
    """Resolve every eligible unresolved prediction as of `now`.

    Only sets resolution fields; direction/probability/expected_return/etc.
    set at creation time are read but never written here. Bars are fetched
    and sorted once per (event, symbol) and reused across every horizon
    that shares them, since several predictions for the same event/symbol
    (one per horizon) would otherwise repeat the same DB round-trip.
    """
    resolved: list[ResolutionOutcome] = []
    bars_cache: dict[tuple[str, str], list] = {}
    event_cache: dict[str, object] = {}

    for prediction in get_unresolved_predictions(session, as_of=now):
        if prediction.event_id not in event_cache:
            event_cache[prediction.event_id] = get_event(session, prediction.event_id)
        event = event_cache[prediction.event_id]
        if event is None:
            continue

        resolve_time = event.occurred_at + timedelta(hours=prediction.horizon_hours)
        if resolve_time > now:
            continue  # horizon hasn't elapsed yet

        cache_key = (prediction.event_id, prediction.symbol)
        if cache_key not in bars_cache:
            start = event.occurred_at - timedelta(hours=24 * 21)
            bars = get_bars_as_of(session, prediction.symbol, start=start, as_of=now)
            if not bars:
                bars = [b for b in provider.get_bars(prediction.symbol, start, now, interval="1h") if b.timestamp <= now]
            bars_cache[cache_key] = sort_bars(bars)
        sorted_bars = bars_cache[cache_key]

        window_returns = compute_event_window_returns(sorted_bars, event.occurred_at, presorted=True)
        actual_return = window_returns.get(f"post_{prediction.horizon_hours}h")
        if actual_return is None:
            continue  # insufficient bar coverage

        if prediction.direction == "NO_PREDICTION":
            # No directional call was made; nothing to score, but we still
            # record that we looked at it and what happened, for audit.
            prediction.actual_return = actual_return
            prediction.direction_correct = None
            prediction.result = None
            prediction.resolved_at = now
            session.add(prediction)
            continue

        predicted_up = prediction.direction == "UP"
        actual_up = actual_return > 0
        direction_correct = predicted_up == actual_up
        result = "correct" if direction_correct else "incorrect"

        prediction.actual_return = actual_return
        prediction.direction_correct = direction_correct
        prediction.result = result
        prediction.resolved_at = now
        session.add(prediction)

        resolved.append(ResolutionOutcome(
            prediction_id=prediction.id, actual_return=actual_return,
            direction_correct=direction_correct, result=result,
        ))
    session.commit()
    return resolved
