"""Prediction orchestration: analogue retrieval -> distribution -> tiering.

Two layers are exposed:
  - `generate_prediction`: a pure function over already-fetched, already
    causally-filtered in-memory data (target event, candidate analogue
    events, and their realized returns for a given symbol/horizon). This
    is what the leakage/no-lookahead tests exercise directly.
  - `create_predictions_for_event`: the DB/market-data-aware orchestrator
    used by jobs/create_predictions.py. It is responsible for ensuring
    every query it issues is bounded by `as_of` -- see the repository
    layer's get_bars_as_of/get_events_as_of, which are the actual
    enforcement points.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from worldpulse.database.models import PredictionORM
from worldpulse.database.repository import get_bars_as_of, get_events_as_of
from worldpulse.events.schemas import ImpactScoreInputs, WorldEvent, impact_candidate_score
from worldpulse.ingestion.markets import MarketDataProvider
from worldpulse.markets.returns import POST_HORIZONS_HOURS, compute_event_window_returns, sort_bars
from worldpulse.prediction.confidence import ConfidenceTier, assign_confidence_tier
from worldpulse.prediction.features import build_impact_inputs
from worldpulse.prediction.model import AnalogueOutcome, compute_distribution_stats
from worldpulse.similarity.retrieval import retrieve_analogues
from worldpulse.similarity.ranking import rerank
from worldpulse.config import settings


@dataclass
class PredictionResult:
    event_id: str
    symbol: str
    horizon_hours: int
    direction: str  # "UP" | "DOWN" | "NO_PREDICTION"
    probability: float
    expected_return: float
    median_return: float
    p25_return: float
    p75_return: float
    sample_size: int
    confidence_tier: str
    event_domain: str
    created_at: datetime
    explanation: dict = field(default_factory=dict)


def generate_prediction(
    target_event: WorldEvent,
    symbol: str,
    horizon_hours: int,
    analogue_events: list[WorldEvent],
    analogue_outcomes: dict[str, float],
    as_of: datetime,
    top_k: int = 50,
) -> PredictionResult:
    """Pure analogue-based prediction given pre-fetched, causally-eligible data.

    `analogue_events` must only contain events the caller has already
    verified are eligible (occurred strictly before the target and whose
    outcome at this horizon was resolvable by `as_of`). This function does
    not itself look at wall-clock time or query any store, which is what
    makes it safe to unit-test for lookahead leakage.
    """
    event_domain = target_event.event_type if isinstance(target_event.event_type, str) else target_event.event_type.value

    reranked = rerank(target_event, retrieve_analogues(target_event, analogue_events, top_k=top_k))
    outcomes: list[AnalogueOutcome] = []
    used_events: list[tuple[WorldEvent, float]] = []
    for candidate, score in reranked:
        if candidate.id not in analogue_outcomes:
            continue
        if score <= 0:
            continue
        outcomes.append(AnalogueOutcome(weight=score, realized_return=analogue_outcomes[candidate.id]))
        used_events.append((candidate, score))

    stats = compute_distribution_stats(outcomes)

    if stats is None:
        return PredictionResult(
            event_id=target_event.id or "", symbol=symbol, horizon_hours=horizon_hours,
            direction="NO_PREDICTION", probability=0.5, expected_return=0.0, median_return=0.0,
            p25_return=0.0, p75_return=0.0, sample_size=0, confidence_tier=ConfidenceTier.NO_PREDICTION.value,
            event_domain=event_domain, created_at=as_of,
            explanation={"observed_facts": ["No historical analogues found."]},
        )

    direction = "UP" if stats.p_up >= 0.5 else "DOWN"
    probability = stats.p_up if direction == "UP" else 1 - stats.p_up

    tier = assign_confidence_tier(
        sample_size=stats.sample_size,
        probability=probability,
        min_sample_size=settings.min_sample_size,
        no_signal_low=settings.no_signal_low,
        no_signal_high=settings.no_signal_high,
        high_n=settings.high_confidence_min_n,
        high_p=settings.high_confidence_min_p,
        medium_n=settings.medium_confidence_min_n,
        medium_p=settings.medium_confidence_min_p,
        low_n=settings.low_confidence_min_n,
        low_p=settings.low_confidence_min_p,
    )

    final_direction = direction if tier != ConfidenceTier.NO_PREDICTION else "NO_PREDICTION"

    top_examples = [
        {"event_id": c.id, "headline": c.headline, "similarity": round(s, 3),
         "realized_return": analogue_outcomes.get(c.id)}
        for c, s in used_events[:5]
    ]

    return PredictionResult(
        event_id=target_event.id or "",
        symbol=symbol,
        horizon_hours=horizon_hours,
        direction=final_direction,
        probability=round(probability, 4),
        expected_return=round(stats.mean_return, 6),
        median_return=round(stats.median_return, 6),
        p25_return=round(stats.p25_return, 6),
        p75_return=round(stats.p75_return, 6),
        sample_size=stats.sample_size,
        confidence_tier=tier.value,
        event_domain=event_domain,
        created_at=as_of,
        explanation={
            "top_analogues": top_examples,
            "p_up": round(stats.p_up, 4),
        },
    )


# --- DB/market-data-aware orchestration -------------------------------------

def _bars_for_symbol(
    session: Session, provider: MarketDataProvider, symbol: str, start: datetime, as_of: datetime,
) -> list:
    """Fetch (and sort once) all bars for `symbol` in [start, as_of].

    Fetched once per symbol per `create_predictions_for_event` call and
    reused across every historical analogue and horizon -- the single most
    important optimization for making analogue retrieval tractable, since
    otherwise every (symbol, horizon, historical-event) triple would issue
    its own DB round-trip.
    """
    bars = get_bars_as_of(session, symbol, start=start, as_of=as_of)
    if not bars:
        bars = [b for b in provider.get_bars(symbol, start, as_of, interval="1h") if b.timestamp <= as_of]
    return sort_bars(bars)


def _resolved_return_from_bars(
    sorted_bars: list, event: WorldEvent, horizon_hours: int, as_of: datetime,
) -> Optional[float]:
    """Realized return for `horizon_hours` after `event`, using a
    pre-sorted, already point-in-time-bounded bar list. Returns None if the
    horizon hasn't elapsed yet by `as_of` (checked BEFORE touching any bar
    data, so this never depends on what's in `sorted_bars` beyond that
    cutoff)."""
    resolve_time = event.occurred_at + timedelta(hours=horizon_hours)
    if resolve_time > as_of:
        return None
    window_returns = compute_event_window_returns(sorted_bars, event.occurred_at, presorted=True)
    return window_returns.get(f"post_{horizon_hours}h")


def create_predictions_for_event(
    session: Session,
    provider: MarketDataProvider,
    event: WorldEvent,
    as_of: datetime,
    lookback_days: int = 365,
) -> list[PredictionResult]:
    """Generate (and does NOT persist) predictions for every relevant
    symbol/horizon for `event`, gated by the impact_candidate_score.

    Persistence is left to the caller (jobs/create_predictions.py) so this
    function stays a pure orchestration step over point-in-time-safe reads.
    """
    if event.occurred_at > as_of:
        return []  # event hasn't happened yet as of this simulated time

    recent_window_start = as_of - timedelta(days=7)
    recent_events = get_events_as_of(session, as_of=as_of, since=recent_window_start)
    impact_inputs: ImpactScoreInputs = build_impact_inputs(event, recent_events)
    score = impact_candidate_score(impact_inputs)
    if score < settings.impact_threshold:
        return []

    candidate_pool_start = event.occurred_at - timedelta(days=lookback_days)
    historical_events = [
        e for e in get_events_as_of(session, as_of=event.occurred_at - timedelta(minutes=1), since=candidate_pool_start)
        if e.id != event.id
    ]

    results: list[PredictionResult] = []
    bars_start = candidate_pool_start - timedelta(hours=24 * 21)
    for symbol in event.potential_assets:
        sorted_bars = _bars_for_symbol(session, provider, symbol, bars_start, as_of)
        for horizon in POST_HORIZONS_HOURS:
            horizon_int = int(horizon)
            eligible_events = []
            outcomes: dict[str, float] = {}
            for hist_event in historical_events:
                ret = _resolved_return_from_bars(sorted_bars, hist_event, horizon_int, as_of)
                if ret is not None:
                    eligible_events.append(hist_event)
                    outcomes[hist_event.id] = ret
            result = generate_prediction(
                target_event=event, symbol=symbol, horizon_hours=horizon_int,
                analogue_events=eligible_events, analogue_outcomes=outcomes, as_of=as_of,
            )
            results.append(result)
    return results


def prediction_result_to_orm(result: PredictionResult) -> PredictionORM:
    return PredictionORM(
        id=str(uuid.uuid4()),
        event_id=result.event_id,
        symbol=result.symbol,
        horizon_hours=result.horizon_hours,
        direction=result.direction,
        probability=result.probability,
        expected_return=result.expected_return,
        median_return=result.median_return,
        p25_return=result.p25_return,
        p75_return=result.p75_return,
        sample_size=result.sample_size,
        confidence_tier=result.confidence_tier,
        event_domain=result.event_domain,
        explanation_json=json.dumps(result.explanation),
        created_at=result.created_at,
    )
