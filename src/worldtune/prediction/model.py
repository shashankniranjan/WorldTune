"""Analogue distribution statistics.

Given a set of (similarity_weight, realized_return) pairs for historical
events that are analogous to the current one, compute the weighted
probability of an "up" move, weighted mean/median return, and the p25/p75
spread. This is the statistical core of the prediction: no ML training,
just a transparent weighted-empirical-distribution estimate.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnalogueOutcome:
    weight: float  # similarity-derived weight, > 0
    realized_return: float


@dataclass
class AnalogueDistributionStats:
    sample_size: int
    p_up: float  # weighted P(return > 0)
    mean_return: float
    median_return: float
    p25_return: float
    p75_return: float


def _weighted_median(sorted_pairs: list[tuple[float, float]]) -> float:
    """sorted_pairs: list of (value, weight) sorted by value ascending."""
    total_weight = sum(w for _, w in sorted_pairs)
    if total_weight == 0:
        return 0.0
    cumulative = 0.0
    for value, weight in sorted_pairs:
        cumulative += weight
        if cumulative >= total_weight / 2:
            return value
    return sorted_pairs[-1][0]


def _weighted_percentile(sorted_pairs: list[tuple[float, float]], pct: float) -> float:
    total_weight = sum(w for _, w in sorted_pairs)
    if total_weight == 0:
        return 0.0
    cumulative = 0.0
    target = total_weight * pct
    for value, weight in sorted_pairs:
        cumulative += weight
        if cumulative >= target:
            return value
    return sorted_pairs[-1][0]


def compute_distribution_stats(outcomes: list[AnalogueOutcome]) -> AnalogueDistributionStats | None:
    if not outcomes:
        return None
    total_weight = sum(o.weight for o in outcomes)
    if total_weight <= 0:
        return None

    up_weight = sum(o.weight for o in outcomes if o.realized_return > 0)
    p_up = up_weight / total_weight

    mean_return = sum(o.weight * o.realized_return for o in outcomes) / total_weight

    pairs = sorted([(o.realized_return, o.weight) for o in outcomes], key=lambda x: x[0])
    median_return = _weighted_median(pairs)
    p25_return = _weighted_percentile(pairs, 0.25)
    p75_return = _weighted_percentile(pairs, 0.75)

    return AnalogueDistributionStats(
        sample_size=len(outcomes),
        p_up=p_up,
        mean_return=mean_return,
        median_return=median_return,
        p25_return=p25_return,
        p75_return=p75_return,
    )
