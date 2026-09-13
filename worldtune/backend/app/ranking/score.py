"""The WorldTune score (spec section 14).

    WorldTuneScore = 0.30 * PersonaRelevance
                   + 0.20 * TrendMomentum
                   + 0.15 * EvidenceStrength
                   + 0.15 * Novelty
                   + 0.10 * Recency
                   + 0.10 * PredictionConfidence
    normalized to 0-100.

Design commitments that are not negotiable in this module:

  * **No bare numbers.** `compute_score` always returns the full breakdown --
    each component's raw value, its weight and its contribution in points --
    plus the concrete evidence behind it. A score the user cannot interrogate
    is indistinguishable from a made-up one.
  * **Every component is in [0, 1] before weighting**, so the weights mean
    what they appear to mean and the total is in [0, 100] by construction.
  * **Signed inputs are folded, not clipped.** A -18% move is as
    *interesting* as a +18% move, so TrendMomentum uses magnitude; the
    direction lives in the trajectory, not in the ranking.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

WEIGHTS: dict[str, float] = {
    "persona_relevance": 0.30,
    "trend_momentum": 0.20,
    "evidence_strength": 0.15,
    "novelty": 0.15,
    "recency": 0.10,
    "prediction_confidence": 0.10,
}


@dataclass
class ScoreBreakdown:
    score: float                               # 0..100
    components: dict[str, dict] = field(default_factory=dict)
    evidence: list[dict] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 2),
            "components": self.components,
            "evidence": self.evidence,
            "reasons": self.reasons,
            "formula": (
                "0.30*PersonaRelevance + 0.20*TrendMomentum + 0.15*EvidenceStrength "
                "+ 0.15*Novelty + 0.10*Recency + 0.10*PredictionConfidence, scaled to 0-100"
            ),
        }


def _clamp01(value: float) -> float:
    if value is None or not math.isfinite(value):
        return 0.0
    return float(max(0.0, min(1.0, value)))


# --- component builders ------------------------------------------------------

def trend_momentum_score(change_7d: float, acceleration: float = 0.0,
                         zscore: float = 0.0) -> float:
    """Magnitude of movement, saturating -- in [0, 1].

    `tanh` rather than a linear ramp with a cutoff: a 40% move and a 400% move
    should both read as "extreme", and a linear scale would let one outlier
    flatten every other item in the ranking to nothing.
    """
    magnitude = math.tanh(abs(change_7d) * 6.0)
    accel_term = math.tanh(abs(acceleration) * 2.0)
    z_term = math.tanh(abs(zscore) / 2.5)
    return _clamp01(0.55 * magnitude + 0.25 * accel_term + 0.20 * z_term)


def evidence_strength_score(*, n_sources: int = 0, n_observations: int = 0,
                            corroborating_signals: int = 0) -> float:
    """How much data stands behind the claim -- in [0, 1].

    Independent *sources* are weighted above sheer observation count: three
    outlets reporting a thing is stronger evidence than one outlet reporting
    it thirty times, which is the failure mode of raw article counts.
    """
    source_term = 1.0 - math.exp(-max(0, n_sources) / 1.5)
    obs_term = 1.0 - math.exp(-max(0, n_observations) / 25.0)
    corrob_term = 1.0 - math.exp(-max(0, corroborating_signals) / 4.0)
    return _clamp01(0.45 * source_term + 0.30 * obs_term + 0.25 * corrob_term)


def novelty_score(*, is_new_entity: bool = False, zscore: float = 0.0,
                  seen_before_count: int = 0) -> float:
    """How much this departs from the persona's normal feed -- in [0, 1].

    Novelty is what stops a personalization product collapsing into a filter
    bubble that shows the same five things forever. A high |z| means the
    entity is behaving unlike itself; a high `seen_before_count` damps it,
    because the fourth day of the same story is not news.
    """
    z_term = math.tanh(abs(zscore) / 2.0)
    fatigue = math.exp(-max(0, seen_before_count) / 3.0)
    base = 0.65 * z_term + 0.35 * (1.0 if is_new_entity else 0.0)
    return _clamp01(base * fatigue + (0.15 if is_new_entity else 0.0))


def recency_score(timestamp: datetime, *, as_of: datetime | None = None,
                  half_life_hours: float = 36.0) -> float:
    """Exponential decay with a 36h half-life -- in [0, 1].

    Half-life rather than a hard cutoff so a 49-hour-old item degrades
    gracefully instead of vanishing. 36h is tuned for a daily-use product:
    yesterday still counts, last week mostly does not.
    """
    now = as_of or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (now - timestamp).total_seconds() / 3600.0)
    return _clamp01(0.5 ** (age_hours / half_life_hours))


def prediction_confidence_score(confidence: float, probability: float = 0.5) -> float:
    """Blend of the model's self-reported confidence and its decisiveness.

    `|p - 0.5| * 2` is the decisiveness term: a 50/50 call contributes
    nothing here no matter how confident the model claims to be, which stops
    a shrug from being ranked as an insight.
    """
    decisiveness = _clamp01(abs(probability - 0.5) * 2.0)
    return _clamp01(0.65 * _clamp01(confidence) + 0.35 * decisiveness)


# --- the formula -------------------------------------------------------------

def compute_score(
    *,
    persona_relevance: float,
    trend_momentum: float,
    evidence_strength: float,
    novelty: float,
    recency: float,
    prediction_confidence: float,
    relevance_components: dict | None = None,
    evidence: list[dict] | None = None,
    reasons: list[str] | None = None,
) -> ScoreBreakdown:
    """Apply the section-14 formula and return the explainable breakdown."""
    raw = {
        "persona_relevance": _clamp01(persona_relevance),
        "trend_momentum": _clamp01(trend_momentum),
        "evidence_strength": _clamp01(evidence_strength),
        "novelty": _clamp01(novelty),
        "recency": _clamp01(recency),
        "prediction_confidence": _clamp01(prediction_confidence),
    }
    components: dict[str, dict] = {}
    total = 0.0
    for key, value in raw.items():
        weight = WEIGHTS[key]
        contribution = value * weight * 100.0
        total += contribution
        components[key] = {
            "value": round(value, 4),
            "weight": weight,
            "contribution": round(contribution, 2),
        }
    if relevance_components:
        components["persona_relevance"]["sub_scores"] = {
            k: round(v, 4) for k, v in relevance_components.items()
        }
    return ScoreBreakdown(
        score=round(min(100.0, max(0.0, total)), 2),
        components=components,
        evidence=list(evidence or []),
        reasons=list(reasons or []),
    )


def top_contributors(breakdown: ScoreBreakdown, limit: int = 3) -> list[str]:
    """The components that actually drove this score -- used in explanations."""
    ranked = sorted(
        breakdown.components.items(),
        key=lambda kv: -kv[1].get("contribution", 0.0),
    )
    return [f"{name.replace('_', ' ')} ({data['contribution']:.1f} pts)"
            for name, data in ranked[:limit]]
