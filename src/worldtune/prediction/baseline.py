"""Baseline predictors used to benchmark the analogue model in evaluation.

Baseline A (always UP): trivially predicts direction=UP with probability 1
  for every event/symbol/horizon.
Baseline B (momentum continuation): predicts the same direction as the
  preceding 1h price move (pre_1h return), with no opinion (0.5) if flat.
Baseline C (historical unconditional probability): P(up) for a given
  symbol/horizon computed from ALL resolved historical outcomes available
  strictly before the evaluation point (point-in-time causal, just like
  the main model).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaselinePrediction:
    name: str
    direction: str  # "UP" | "DOWN"
    probability: float


def baseline_always_up() -> BaselinePrediction:
    return BaselinePrediction(name="always_up", direction="UP", probability=1.0)


def baseline_momentum(pre_1h_return: float | None) -> BaselinePrediction:
    if pre_1h_return is None or pre_1h_return == 0:
        return BaselinePrediction(name="momentum", direction="UP", probability=0.5)
    direction = "UP" if pre_1h_return > 0 else "DOWN"
    return BaselinePrediction(name="momentum", direction=direction, probability=0.5)


def baseline_historical_unconditional(historical_returns: list[float]) -> BaselinePrediction:
    """historical_returns: realized returns for this symbol/horizon from all
    resolved outcomes available before the evaluation point."""
    if not historical_returns:
        return BaselinePrediction(name="historical_unconditional", direction="UP", probability=0.5)
    up_count = sum(1 for r in historical_returns if r > 0)
    p_up = up_count / len(historical_returns)
    direction = "UP" if p_up >= 0.5 else "DOWN"
    probability = p_up if direction == "UP" else 1 - p_up
    return BaselinePrediction(name="historical_unconditional", direction=direction, probability=probability)
