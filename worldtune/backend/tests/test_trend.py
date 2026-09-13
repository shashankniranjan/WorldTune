"""Trend engine: hand-computed fixtures.

Every expected value here was worked out by hand from the definition, not
captured from the implementation -- otherwise the test only asserts that the
code does what it currently does.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.analytics import trend as T


class TestPctChange:
    def test_seven_day_change_is_fractional(self):
        # index -8 is 100, latest is 110 -> 0.10
        values = [100, 101, 102, 103, 104, 105, 106, 107, 110]
        assert T.pct_change_over(values, 7) == pytest.approx((110 / 101) - 1)

    def test_exact_window_boundary(self):
        # len == window + 1 is the minimum computable case.
        assert T.pct_change_over([50.0, 75.0], 1) == pytest.approx(0.5)

    def test_too_short_returns_zero_not_nan(self):
        assert T.pct_change_over([100.0], 7) == 0.0

    def test_zero_reference_returns_zero(self):
        # An undefined ratio is not a 100% move.
        assert T.pct_change_over([0.0, 5.0], 1) == 0.0


class TestMovingAverage:
    def test_window_larger_than_series_uses_whole_series(self):
        assert T.moving_average([2.0, 4.0, 6.0], 30) == pytest.approx(4.0)

    def test_trailing_window(self):
        assert T.moving_average([1, 1, 1, 10, 20, 30], 3) == pytest.approx(20.0)


class TestAcceleration:
    def test_constant_growth_has_zero_acceleration(self):
        # +1/step throughout: recent delta == prior delta -> 0
        values = list(range(15))
        assert T.acceleration(values, 7) == pytest.approx(0.0)

    def test_accelerating_series_is_positive(self):
        # first 7 steps +1 each (delta 7), next 7 steps +3 each (delta 21)
        values = [0, 1, 2, 3, 4, 5, 6, 7] + [10, 13, 16, 19, 22, 25, 28]
        assert T.acceleration(values, 7) == pytest.approx(28 - 7 - 7)

    def test_insufficient_history_returns_zero(self):
        assert T.acceleration([1, 2, 3], 7) == 0.0


class TestZScore:
    def test_known_zscore(self):
        # window [1,2,3,4,5]: mean 3, sample sd sqrt(2.5); latest 5
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert T.zscore(values, 5) == pytest.approx((5 - 3) / (2.5 ** 0.5))

    def test_constant_series_returns_zero_not_division_error(self):
        assert T.zscore([4.0] * 10, 10) == 0.0


class TestSlopeAndMomentum:
    def test_perfect_line_slope(self):
        assert T.linear_slope([0, 2, 4, 6, 8, 10], 6) == pytest.approx(2.0)

    def test_rising_series_has_positive_momentum(self):
        assert T.ewma_momentum([float(i) for i in range(1, 40)]) > 0

    def test_falling_series_has_negative_momentum(self):
        assert T.ewma_momentum([float(i) for i in range(40, 1, -1)]) < 0

    def test_flat_series_momentum_is_zero(self):
        assert T.ewma_momentum([7.0] * 40) == pytest.approx(0.0, abs=1e-9)


class TestReturns:
    def test_simple_returns(self):
        rets = T.returns_from_prices([100.0, 110.0, 99.0])
        assert rets.tolist() == pytest.approx([0.1, -0.1])

    def test_zero_price_does_not_produce_inf(self):
        rets = T.returns_from_prices([0.0, 10.0, 20.0])
        assert all(abs(r) < 1e6 for r in rets)

    def test_realized_volatility_of_constant_series_is_zero(self):
        assert T.realized_volatility([100.0] * 40) == 0.0


class TestBucketing:
    def test_daily_counts_are_dense_including_empty_days(self):
        as_of = datetime(2025, 9, 13, tzinfo=timezone.utc)
        stamps = [as_of, as_of, as_of - timedelta(days=3)]
        counts = T.daily_counts(stamps, as_of=as_of, days=5)
        assert len(counts) == 5
        assert counts == [0.0, 1.0, 0.0, 0.0, 2.0]

    def test_daily_means_fill_empty_days_with_neutral(self):
        as_of = datetime(2025, 9, 13, tzinfo=timezone.utc)
        stamps = [as_of, as_of - timedelta(days=2)]
        means = T.daily_means(stamps, [1.0, -1.0], as_of=as_of, days=3)
        assert means == [-1.0, 0.0, 1.0]


class TestBundle:
    def test_direction_classification(self):
        assert T.classify_direction(0.10) == "rising"
        assert T.classify_direction(-0.10) == "falling"
        assert T.classify_direction(0.001) == "stable"

    def test_compute_trend_reports_observation_count(self):
        metrics = T.compute_trend([float(i) for i in range(1, 41)])
        assert metrics.n_observations == 40
        assert metrics.direction == "rising"
        assert metrics.latest == 40.0

    def test_empty_series_is_all_zero_not_nan(self):
        metrics = T.compute_trend([])
        assert metrics.to_dict()["change_7d"] == 0.0
        assert metrics.n_observations == 0
