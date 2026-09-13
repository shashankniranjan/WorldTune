"""Trajectory engine -- "where might this be heading?"

Explicitly NOT an LLM. An LLM is a language model; asked for a probability it
produces a plausible-sounding number with no relationship to the data, and
that number cannot be calibrated, back-tested or explained. Everything here
is an interpretable model over real computed features:

  * momentum / EWMA trend and z-scores from `app.analytics.trend`;
  * a **logistic link** mapping a signed, scale-free trend score to a
    probability -- monotone by construction, one coefficient, inspectable;
  * scikit-learn's LogisticRegression is used where a *fitted* model is
    wanted (`fit_direction_model`), so the upgrade path from the V1 link
    function to a trained model is one call, not a rewrite.

What it outputs, per spec sections 12-13:
  * Financial: Bullish / Neutral / Bearish + probability + confidence +
    horizon. **Never a price target** -- a point forecast would imply a
    precision this model does not have.
  * Career: Growing / Stable / Declining over 7 / 30 / 90 days.

NON-GOAL (stated here so it survives refactors): no profitability claim is
made or implied. These are calibrated-ish directional probabilities on a
prototype, not trading signals and not career guarantees.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np

from app.analytics.trend import (
    ewma_momentum,
    realized_volatility,
    returns_from_prices,
    zscore,
)

BULLISH, NEUTRAL, BEARISH = "bullish", "neutral", "bearish"
GROWING, STABLE, DECLINING = "growing", "stable", "declining"

# Probability band that counts as "no directional call". A 52% bullish read is
# not a view, and presenting it as one is the main way a prototype like this
# misleads someone.
NEUTRAL_BAND = 0.06


@dataclass
class Trajectory:
    direction: str
    probability: float          # P(the stated non-neutral direction), 0..1
    confidence: float           # 0..1, how much to trust the call
    horizon_days: int
    features: dict
    rationale: str

    def to_dict(self) -> dict:
        return asdict(self)


def logistic(x: float, *, k: float = 1.0) -> float:
    """Numerically safe logistic link."""
    z = max(-40.0, min(40.0, k * x))
    return 1.0 / (1.0 + math.exp(-z))


# --- Financial ---------------------------------------------------------------

def financial_trajectory(
    closes: Sequence[float],
    volumes: Sequence[float] | None = None,
    *,
    news_sentiment: float = 0.0,
    news_intensity: float = 0.0,
    horizon_days: int = 7,
) -> Trajectory:
    """Direction + probability for one asset over `horizon_days`.

    Feature blend (weights are the model; they are constants on purpose so a
    reader can audit them):
        0.50  EWMA momentum, volatility-scaled
        0.20  return z-score (mean-reversion-aware: large positive z is
              *less* bullish, hence the negative coefficient)
        0.20  news sentiment weighted by how much news there is
        0.10  volume z-score as a conviction proxy

    The composite is passed through a logistic link with k=1.6, chosen so a
    strong-but-not-extreme composite (~1.0) maps to ~83%, not ~99%. A model
    this simple emitting 99% would be lying about its own precision.
    """
    closes = list(closes)
    rets = returns_from_prices(closes)
    if rets.size < 5:
        return Trajectory(NEUTRAL, 0.5, 0.0, horizon_days, {},
                          "Insufficient price history for a directional view.")

    vol = realized_volatility(closes) or 1e-6
    momentum = ewma_momentum(closes, span=10)
    # Scale momentum by volatility: a 3% drift in a quiet asset is a bigger
    # statement than a 3% drift in one that moves 3% daily.
    momentum_scaled = float(np.clip(momentum / max(vol, 0.05) * 3.0, -3.0, 3.0))
    ret_z = float(np.clip(zscore(rets, 30), -3.0, 3.0))
    vol_z = 0.0
    if volumes is not None and len(volumes) >= 5:
        vol_z = float(np.clip(zscore(list(volumes), 30), -3.0, 3.0))
    sentiment_term = float(np.clip(news_sentiment, -1.0, 1.0)) * float(np.clip(news_intensity, 0.0, 1.0))

    composite = (
        0.50 * momentum_scaled
        - 0.20 * ret_z          # stretched moves mean-revert more often than not
        + 0.20 * sentiment_term * 2.0
        + 0.10 * vol_z
    )
    p_up = logistic(composite, k=1.6)

    features = {
        "momentum": round(momentum, 6),
        "momentum_scaled": round(momentum_scaled, 4),
        "return_zscore": round(ret_z, 4),
        "volume_zscore": round(vol_z, 4),
        "news_sentiment": round(news_sentiment, 4),
        "news_intensity": round(news_intensity, 4),
        "realized_volatility": round(vol, 4),
        "composite": round(composite, 4),
    }

    if abs(p_up - 0.5) < NEUTRAL_BAND:
        return Trajectory(
            NEUTRAL, round(p_up, 4),
            round(_confidence(rets.size, abs(composite), vol), 4),
            horizon_days, features,
            "Momentum, sentiment and volume are mutually offsetting; no directional call.",
        )
    direction = BULLISH if p_up > 0.5 else BEARISH
    stated = p_up if direction == BULLISH else 1.0 - p_up
    return Trajectory(
        direction,
        round(stated, 4),
        round(_confidence(rets.size, abs(composite), vol), 4),
        horizon_days,
        features,
        _financial_rationale(direction, momentum_scaled, ret_z, sentiment_term, vol_z),
    )


def _financial_rationale(direction: str, momentum: float, ret_z: float,
                         sentiment: float, vol_z: float) -> str:
    parts = []
    if abs(momentum) > 0.2:
        parts.append(f"{'positive' if momentum > 0 else 'negative'} volatility-scaled momentum")
    if abs(ret_z) > 1.0:
        parts.append(f"returns {abs(ret_z):.1f} sd {'above' if ret_z > 0 else 'below'} their 30d mean")
    if abs(sentiment) > 0.05:
        parts.append(f"{'supportive' if sentiment > 0 else 'negative'} news tone")
    if vol_z > 1.0:
        parts.append("elevated volume")
    reason = "; ".join(parts) or "weak but non-zero directional evidence"
    return f"{direction.capitalize()} on {reason}. Directional view only; no price target."


def _confidence(n_obs: int, strength: float, vol: float) -> float:
    """Confidence rises with history length and signal strength, falls with vol.

    Capped at 0.9: a V1 model over a few weeks of daily bars has no business
    reporting near-certainty.
    """
    data_term = min(1.0, n_obs / 60.0)
    strength_term = min(1.0, strength / 1.5)
    vol_penalty = 1.0 / (1.0 + max(0.0, vol - 0.4))
    return float(min(0.9, 0.55 * data_term + 0.30 * strength_term + 0.15 * vol_penalty))


# --- Career ------------------------------------------------------------------

def career_trajectory(
    demand_series: Sequence[float],
    *,
    horizon_days: int = 30,
    tech_velocity: float = 0.0,
) -> Trajectory:
    """Growing / Stable / Declining for a skill's demand series.

    `demand_series` is typically daily `skill_share` (mentions / postings),
    which is already normalized against board size -- so a quiet hiring week
    does not read as a skill going out of fashion.

    `tech_velocity` (GitHub/HN star and discussion growth for technologies
    implying this skill) is a *leading* term: code activity moves months
    before job descriptions do, so it is blended in at a deliberately modest
    weight rather than allowed to dominate observed hiring.
    """
    values = [float(v) for v in demand_series]
    if len(values) < 8:
        return Trajectory(STABLE, 0.5, 0.0, horizon_days, {},
                          "Insufficient demand history for a trajectory.")

    momentum = ewma_momentum(values, span=7)
    z = float(np.clip(zscore(values, 30), -3.0, 3.0))
    composite = 0.55 * float(np.clip(momentum * 4.0, -3.0, 3.0)) + 0.25 * z \
        + 0.20 * float(np.clip(tech_velocity * 3.0, -3.0, 3.0))
    p_growth = logistic(composite, k=1.4)

    features = {
        "demand_momentum": round(momentum, 6),
        "demand_zscore": round(z, 4),
        "tech_velocity": round(tech_velocity, 6),
        "composite": round(composite, 4),
        "n_observations": len(values),
    }
    if abs(p_growth - 0.5) < NEUTRAL_BAND:
        direction, stated = STABLE, p_growth
    elif p_growth > 0.5:
        direction, stated = GROWING, p_growth
    else:
        direction, stated = DECLINING, 1.0 - p_growth

    return Trajectory(
        direction,
        round(stated, 4),
        round(_confidence(len(values), abs(composite), 0.2), 4),
        horizon_days,
        features,
        f"{direction.capitalize()} demand: EWMA momentum {momentum:+.1%}, "
        f"z-score {z:+.2f}, technology-activity term {tech_velocity:+.1%}.",
    )


def career_trajectory_multi(demand_series: Sequence[float], *,
                            tech_velocity: float = 0.0,
                            horizons: tuple[int, ...] = (7, 30, 90)) -> dict[str, dict]:
    """Spec section 13: the same skill judged over 7 / 30 / 90 days.

    Longer horizons get a shorter effective look-back on the *momentum* term
    relative to their horizon, so confidence decays with horizon -- which is
    the honest behaviour: a 90-day call from 60 days of data is weaker than a
    7-day one.
    """
    out: dict[str, dict] = {}
    for horizon in horizons:
        traj = career_trajectory(demand_series, horizon_days=horizon,
                                 tech_velocity=tech_velocity)
        decay = 1.0 / (1.0 + horizon / 60.0)
        traj.confidence = round(traj.confidence * decay, 4)
        out[f"{horizon}d"] = traj.to_dict()
    return out


# --- Optional fitted model ---------------------------------------------------

def fit_direction_model(features: np.ndarray, labels: np.ndarray):
    """Fit a LogisticRegression on (features, binary labels).

    Present so the upgrade from the hand-weighted link function above to a
    model fitted on resolved predictions is a data problem, not a rewrite:
    `prediction_results` accumulates exactly the (features, correct) pairs
    this needs. Returns None when the labels are single-class, which is the
    normal state of a fresh prototype -- an unfittable model must degrade to
    the link function, not raise.
    """
    from sklearn.linear_model import LogisticRegression

    if features.size == 0 or len(np.unique(labels)) < 2:
        return None
    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(features, labels)
    return model
