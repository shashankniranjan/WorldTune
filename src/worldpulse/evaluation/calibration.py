"""Calibration: does "70% probability" resolve correct ~70% of the time?

Buckets resolved directional predictions by their stated probability and
compares the bucket's average stated probability to its realized
(empirical) accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass

from worldpulse.database.models import PredictionORM

DEFAULT_BUCKETS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]


@dataclass
class CalibrationBucket:
    bucket_low: float
    bucket_high: float
    n: int
    mean_predicted_probability: float
    realized_accuracy: float


def compute_calibration_table(
    predictions: list[PredictionORM], buckets: list[tuple[float, float]] = None
) -> list[CalibrationBucket]:
    buckets = buckets or DEFAULT_BUCKETS
    eligible = [
        p for p in predictions
        if p.resolved_at is not None and p.direction in ("UP", "DOWN") and p.direction_correct is not None
    ]

    table: list[CalibrationBucket] = []
    for lo, hi in buckets:
        in_bucket = [p for p in eligible if lo <= p.probability < hi or (hi == 1.0 and p.probability == 1.0)]
        if not in_bucket:
            continue
        mean_p = sum(p.probability for p in in_bucket) / len(in_bucket)
        correct = sum(1 for p in in_bucket if p.direction_correct)
        accuracy = correct / len(in_bucket)
        table.append(CalibrationBucket(
            bucket_low=lo, bucket_high=hi, n=len(in_bucket),
            mean_predicted_probability=mean_p, realized_accuracy=accuracy,
        ))
    return table


def calibration_error(table: list[CalibrationBucket]) -> float | None:
    """Mean absolute difference between predicted probability and realized
    accuracy across buckets, weighted by bucket size (a simple ECE-style
    metric)."""
    total_n = sum(b.n for b in table)
    if total_n == 0:
        return None
    weighted_error = sum(b.n * abs(b.mean_predicted_probability - b.realized_accuracy) for b in table)
    return weighted_error / total_n
