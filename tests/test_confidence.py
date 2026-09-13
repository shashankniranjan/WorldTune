import pytest

from worldpulse.prediction.confidence import ConfidenceTier, assign_confidence_tier

CASES = [
    # sample_size, probability, expected_tier
    (5, 0.9, ConfidenceTier.NO_PREDICTION),       # below min_sample_size
    (9, 0.99, ConfidenceTier.NO_PREDICTION),      # below min_sample_size
    (50, 0.50, ConfidenceTier.NO_PREDICTION),     # inside no-signal band
    (50, 0.45, ConfidenceTier.NO_PREDICTION),     # boundary of no-signal band
    (50, 0.55, ConfidenceTier.NO_PREDICTION),     # boundary of no-signal band
    (30, 0.70, ConfidenceTier.HIGH),              # exactly at HIGH thresholds
    (40, 0.85, ConfidenceTier.HIGH),
    (29, 0.90, ConfidenceTier.MEDIUM),            # n just below HIGH's n, but clears MEDIUM
    (15, 0.62, ConfidenceTier.MEDIUM),            # exactly at MEDIUM thresholds
    (20, 0.65, ConfidenceTier.MEDIUM),
    (14, 0.90, ConfidenceTier.LOW),               # n just below MEDIUM's n, but clears LOW
    (10, 0.57, ConfidenceTier.LOW),               # exactly at LOW thresholds
    (10, 0.56, ConfidenceTier.NO_PREDICTION),     # n ok, probability just below LOW's p
    (9, 0.99, ConfidenceTier.NO_PREDICTION),      # sample size below absolute minimum
]


@pytest.mark.parametrize("sample_size,probability,expected", CASES)
def test_confidence_tier_thresholds(sample_size, probability, expected):
    tier = assign_confidence_tier(sample_size, probability)
    assert tier == expected


def test_no_signal_band_is_checked_before_sample_size_tiers():
    # A huge sample with a coin-flip probability is still NO_PREDICTION.
    assert assign_confidence_tier(1000, 0.50) == ConfidenceTier.NO_PREDICTION
