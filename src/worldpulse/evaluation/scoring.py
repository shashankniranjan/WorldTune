"""Scoring: directional accuracy, coverage, precision by tier, accuracy by
horizon/category, compared against baselines.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from worldpulse.database.models import PredictionORM


@dataclass
class ScoreboardReport:
    total_predictions: int
    total_resolved: int
    coverage: float  # fraction of predictions that were directional (not NO_PREDICTION) AND resolved
    directional_accuracy: float | None
    precision_by_tier: dict[str, float]
    accuracy_by_horizon: dict[int, float]
    accuracy_by_domain: dict[str, float]
    baseline_accuracy: dict[str, float]


def _directional(preds: list[PredictionORM]) -> list[PredictionORM]:
    return [p for p in preds if p.direction in ("UP", "DOWN")]


def _resolved(preds: list[PredictionORM]) -> list[PredictionORM]:
    return [p for p in preds if p.resolved_at is not None]


def _accuracy(preds: list[PredictionORM]) -> float | None:
    resolved_directional = [p for p in preds if p.resolved_at is not None and p.direction_correct is not None]
    if not resolved_directional:
        return None
    correct = sum(1 for p in resolved_directional if p.direction_correct)
    return correct / len(resolved_directional)


def compute_scoreboard(predictions: list[PredictionORM]) -> ScoreboardReport:
    total = len(predictions)
    resolved = _resolved(predictions)
    directional_resolved = [p for p in resolved if p.direction in ("UP", "DOWN")]

    coverage = len(directional_resolved) / total if total else 0.0
    directional_accuracy = _accuracy(predictions)

    precision_by_tier: dict[str, float] = {}
    for tier in ("HIGH", "MEDIUM", "LOW"):
        tier_preds = [p for p in directional_resolved if p.confidence_tier == tier]
        acc = _accuracy(tier_preds)
        if acc is not None:
            precision_by_tier[tier] = acc

    accuracy_by_horizon: dict[int, float] = {}
    horizons = sorted({p.horizon_hours for p in directional_resolved})
    for h in horizons:
        acc = _accuracy([p for p in directional_resolved if p.horizon_hours == h])
        if acc is not None:
            accuracy_by_horizon[h] = acc

    accuracy_by_domain: dict[str, float] = {}
    domains = sorted({p.event_domain for p in directional_resolved})
    for d in domains:
        acc = _accuracy([p for p in directional_resolved if p.event_domain == d])
        if acc is not None:
            accuracy_by_domain[d] = acc

    # Baselines, computed against the same resolved set.
    baseline_accuracy = compute_baseline_accuracies(directional_resolved)

    return ScoreboardReport(
        total_predictions=total,
        total_resolved=len(resolved),
        coverage=coverage,
        directional_accuracy=directional_accuracy,
        precision_by_tier=precision_by_tier,
        accuracy_by_horizon=accuracy_by_horizon,
        accuracy_by_domain=accuracy_by_domain,
        baseline_accuracy=baseline_accuracy,
    )


def compute_baseline_accuracies(resolved_directional: list[PredictionORM]) -> dict[str, float]:
    """Baseline A/B/C accuracy against the same resolved outcomes.

    Baseline A (always UP): correct whenever actual_return > 0.
    Baseline B (momentum continuation): we don't have pre_1h stored on the
      prediction row in this simplified schema, so we approximate using the
      model's own historical_unconditional as a stand-in is inappropriate;
      instead we report always-UP and unconditional-from-sample as A and C,
      and treat B as unavailable (documented limitation).
    Baseline C (historical unconditional P(up) for symbol/horizon, computed
      from this same resolved sample, mirroring the "all prior data" idea).
    """
    if not resolved_directional:
        return {"always_up": 0.0, "historical_unconditional": 0.0}

    always_up_correct = sum(1 for p in resolved_directional if p.actual_return is not None and p.actual_return > 0)
    always_up_acc = always_up_correct / len(resolved_directional)

    # Historical unconditional: P(up) overall in this sample; baseline
    # "predicts" UP if that overall P(up) >= 0.5, else DOWN, applied
    # uniformly -- i.e. it's just whichever class is more frequent.
    up_count = sum(1 for p in resolved_directional if p.actual_return is not None and p.actual_return > 0)
    p_up = up_count / len(resolved_directional)
    majority_direction_acc = max(p_up, 1 - p_up)

    return {
        "always_up": always_up_acc,
        "historical_unconditional": majority_direction_acc,
    }
