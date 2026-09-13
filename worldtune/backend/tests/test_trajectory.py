"""Trajectory engine: sane outputs and monotonic behaviour.

These tests assert *properties* (monotonicity, bounds, direction agreement)
rather than exact probabilities. Pinning exact outputs of a model whose
coefficients are expected to be tuned would make the suite an obstacle to
improving the model instead of a guard on its contract.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.analytics.trajectory import (
    BEARISH,
    BULLISH,
    DECLINING,
    GROWING,
    NEUTRAL,
    STABLE,
    career_trajectory,
    career_trajectory_multi,
    financial_trajectory,
    fit_direction_model,
    logistic,
)


def ramp(start: float, rate: float, n: int = 60) -> list[float]:
    """A clean exponential path -- no noise, so direction is unambiguous."""
    return [start * (1 + rate) ** i for i in range(n)]


class TestLogistic:
    def test_midpoint(self):
        assert logistic(0.0) == pytest.approx(0.5)

    def test_monotonic(self):
        values = [logistic(x) for x in (-3, -1, 0, 1, 3)]
        assert values == sorted(values)

    def test_extreme_inputs_do_not_overflow(self):
        assert 0.0 <= logistic(-1e9) <= 1.0
        assert 0.0 <= logistic(1e9) <= 1.0


class TestFinancialTrajectory:
    def test_strong_uptrend_is_bullish(self):
        result = financial_trajectory(ramp(100, 0.012))
        assert result.direction == BULLISH
        assert result.probability > 0.5

    def test_strong_downtrend_is_bearish(self):
        result = financial_trajectory(ramp(100, -0.012))
        assert result.direction == BEARISH
        assert result.probability > 0.5   # probability OF the stated direction

    def test_flat_series_is_neutral(self):
        assert financial_trajectory([100.0] * 60).direction == NEUTRAL

    def test_probability_is_a_valid_probability(self):
        for rate in (-0.02, -0.005, 0.0, 0.005, 0.02):
            result = financial_trajectory(ramp(100, rate))
            assert 0.0 <= result.probability <= 1.0
            assert 0.0 <= result.confidence <= 0.9

    def test_stronger_trend_gives_higher_bullish_probability(self):
        weak = financial_trajectory(ramp(100, 0.002))
        strong = financial_trajectory(ramp(100, 0.02))
        assert strong.features["composite"] > weak.features["composite"]

    def test_insufficient_history_refuses_to_call(self):
        result = financial_trajectory([100.0, 101.0])
        assert result.direction == NEUTRAL
        assert result.confidence == 0.0
        assert "insufficient" in result.rationale.lower()

    def test_positive_news_shifts_probability_up(self):
        prices = ramp(100, 0.001)
        neutral_news = financial_trajectory(prices, news_sentiment=0.0, news_intensity=0.0)
        good_news = financial_trajectory(prices, news_sentiment=0.9, news_intensity=1.0)
        assert good_news.features["composite"] > neutral_news.features["composite"]

    def test_never_emits_a_price_target(self):
        """Spec 12: direction + probability, explicitly NOT a price forecast."""
        result = financial_trajectory(ramp(100, 0.01))
        assert not hasattr(result, "predicted_price")
        assert "no price target" in result.rationale.lower()

    def test_features_are_recorded_for_replay(self):
        result = financial_trajectory(ramp(100, 0.01), [1e6] * 60)
        assert {"momentum", "composite", "realized_volatility"} <= set(result.features)

    def test_confidence_is_capped(self):
        """A V1 model over weeks of bars must not claim near-certainty."""
        result = financial_trajectory(ramp(100, 0.05, 200))
        assert result.confidence <= 0.9


class TestCareerTrajectory:
    def test_rising_demand_is_growing(self):
        assert career_trajectory(ramp(0.1, 0.02, 40)).direction == GROWING

    def test_falling_demand_is_declining(self):
        assert career_trajectory(ramp(0.4, -0.02, 40)).direction == DECLINING

    def test_flat_demand_is_stable(self):
        assert career_trajectory([0.25] * 40).direction == STABLE

    def test_insufficient_history_is_stable_with_zero_confidence(self):
        result = career_trajectory([0.1, 0.2, 0.3])
        assert result.direction == STABLE
        assert result.confidence == 0.0

    def test_technology_velocity_pushes_toward_growth(self):
        flat = [0.2] * 40
        without = career_trajectory(flat, tech_velocity=0.0)
        with_tech = career_trajectory(flat, tech_velocity=0.5)
        assert with_tech.features["composite"] > without.features["composite"]

    def test_multi_horizon_covers_spec_horizons(self):
        result = career_trajectory_multi(ramp(0.1, 0.02, 40))
        assert set(result) == {"7d", "30d", "90d"}

    def test_confidence_decays_with_horizon(self):
        """A 90-day call from 60 days of data is weaker than a 7-day one."""
        result = career_trajectory_multi(ramp(0.1, 0.02, 40))
        assert result["7d"]["confidence"] > result["30d"]["confidence"] > result["90d"]["confidence"]

    def test_all_horizons_agree_on_direction_for_a_clean_trend(self):
        result = career_trajectory_multi(ramp(0.1, 0.03, 40))
        assert {v["direction"] for v in result.values()} == {GROWING}


class TestFittedModel:
    def test_single_class_labels_return_none_rather_than_raising(self):
        """The normal state of a fresh prototype must degrade, not crash."""
        features = np.array([[0.1], [0.2], [0.3]])
        assert fit_direction_model(features, np.array([1, 1, 1])) is None

    def test_fits_when_both_classes_present(self):
        features = np.array([[-2.0], [-1.0], [1.0], [2.0]])
        model = fit_direction_model(features, np.array([0, 0, 1, 1]))
        assert model is not None
        assert model.predict(np.array([[3.0]]))[0] == 1

    def test_empty_input_returns_none(self):
        assert fit_direction_model(np.array([]), np.array([])) is None
