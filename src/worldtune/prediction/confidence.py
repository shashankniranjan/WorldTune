"""Confidence tier assignment for analogue-based predictions.

Rules (checked in this order):
  1. sample_size < min_sample_size            -> NO_PREDICTION
  2. no_signal_low <= probability <= no_signal_high -> NO_PREDICTION
  3. sample_size >= high_n   and probability >= high_p   -> HIGH
  4. sample_size >= medium_n and probability >= medium_p -> MEDIUM
  5. sample_size >= low_n    and probability >= low_p    -> LOW
  6. otherwise                                 -> NO_PREDICTION

`probability` here is expected to be the probability of the *predicted*
direction (i.e. max(p_up, 1 - p_up)), so higher is always "more confident".
"""
from __future__ import annotations

import enum


class ConfidenceTier(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NO_PREDICTION = "NO_PREDICTION"


def assign_confidence_tier(
    sample_size: int,
    probability: float,
    *,
    min_sample_size: int = 10,
    no_signal_low: float = 0.45,
    no_signal_high: float = 0.55,
    high_n: int = 30,
    high_p: float = 0.70,
    medium_n: int = 15,
    medium_p: float = 0.62,
    low_n: int = 10,
    low_p: float = 0.57,
) -> ConfidenceTier:
    if sample_size < min_sample_size:
        return ConfidenceTier.NO_PREDICTION
    if no_signal_low <= probability <= no_signal_high:
        return ConfidenceTier.NO_PREDICTION
    if sample_size >= high_n and probability >= high_p:
        return ConfidenceTier.HIGH
    if sample_size >= medium_n and probability >= medium_p:
        return ConfidenceTier.MEDIUM
    if sample_size >= low_n and probability >= low_p:
        return ConfidenceTier.LOW
    return ConfidenceTier.NO_PREDICTION
