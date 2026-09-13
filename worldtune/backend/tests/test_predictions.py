"""Prediction storage (immutability) and evaluation maths (hand-computed)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db import session_scope
from app.predictions.evaluate import (
    calibration_curve,
    direction_accuracy,
    evaluate_classification,
    mean_absolute_error,
    mean_brier,
    precision_recall_f1,
    ranking_stability,
    roc_auc,
    trend_correlation,
)
from app.predictions.store import (
    FINANCIAL_OUTCOMES,
    brier_score,
    due_predictions,
    record_prediction,
    resolve_prediction,
    resolved_pairs,
)

NOW = datetime(2025, 9, 13, 12, 0, tzinfo=timezone.utc)


def make_prediction(session, **overrides):
    kwargs = dict(
        persona_id="p1", domain="financial", entity_type="asset", entity_id="BTC",
        predicted_direction="bullish", predicted_probability=0.7, confidence=0.6,
        horizon_days=7, created_at=NOW,
    )
    kwargs.update(overrides)
    return record_prediction(session, **kwargs)


class TestImmutability:
    def test_resolution_does_not_mutate_the_prediction(self, session):
        """The core falsifiability contract."""
        prediction = make_prediction(session)
        original = (prediction.predicted_direction, prediction.predicted_probability,
                    prediction.created_at, prediction.horizon_days)

        resolve_prediction(session, prediction, actual_outcome="bearish")
        session.flush()

        assert (prediction.predicted_direction, prediction.predicted_probability,
                prediction.created_at, prediction.horizon_days) == original

    def test_result_is_a_separate_row(self, session):
        prediction = make_prediction(session)
        result = resolve_prediction(session, prediction, actual_outcome="bullish")
        assert result.prediction_id == prediction.id
        assert result.id != prediction.id

    def test_resolution_is_idempotent(self, session):
        prediction = make_prediction(session)
        first = resolve_prediction(session, prediction, actual_outcome="bullish")
        second = resolve_prediction(session, prediction, actual_outcome="bearish")
        assert first.id == second.id
        assert second.actual_outcome == "bullish"   # the first resolution stands

    def test_correct_flag_and_brier_are_derived(self, session):
        prediction = make_prediction(session, predicted_probability=0.8)
        result = resolve_prediction(session, prediction, actual_outcome="bullish")
        assert result.correct is True
        assert result.brier == pytest.approx((0.8 - 1.0) ** 2)

    def test_resolves_at_is_created_plus_horizon(self, session):
        prediction = make_prediction(session, horizon_days=7)
        assert prediction.resolves_at == NOW + timedelta(days=7)

    def test_due_predictions_excludes_already_resolved(self, session):
        due = make_prediction(session, created_at=NOW - timedelta(days=30))
        make_prediction(session, entity_id="ETH", created_at=NOW)   # not yet due
        assert [p.id for p in due_predictions(session, as_of=NOW)] == [due.id]

        resolve_prediction(session, due, actual_outcome="bullish")
        assert due_predictions(session, as_of=NOW) == []

    def test_model_version_is_stamped(self, session, settings):
        assert make_prediction(session).model_version == settings.model_version

    def test_resolved_pairs_filters_by_domain(self, session):
        fin = make_prediction(session)
        career = make_prediction(session, domain="career", entity_type="skill",
                                 entity_id="llm", predicted_direction="growing")
        resolve_prediction(session, fin, actual_outcome="bullish")
        resolve_prediction(session, career, actual_outcome="growing")
        assert len(resolved_pairs(session, domain="financial")) == 1
        assert len(resolved_pairs(session, domain="career")) == 1


class TestBrier:
    def test_perfect_confident_call(self):
        assert brier_score(1.0, True) == 0.0

    def test_confident_and_wrong_is_worst(self):
        assert brier_score(1.0, False) == 1.0

    def test_coin_flip_is_a_quarter_either_way(self):
        assert brier_score(0.5, True) == pytest.approx(0.25)
        assert brier_score(0.5, False) == pytest.approx(0.25)


class TestClassificationMetrics:
    def test_direction_accuracy(self):
        assert direction_accuracy(["a", "b", "c"], ["a", "b", "x"]) == pytest.approx(2 / 3)

    def test_accuracy_of_empty_is_none(self):
        assert direction_accuracy([], []) is None

    def test_precision_recall_f1_hand_computed(self):
        # predicted bullish 3x, of which 2 correct -> precision 2/3
        # actual bullish 4x, of which 2 caught      -> recall 2/4
        predicted = ["bullish", "bullish", "bullish", "bearish", "bearish"]
        actual = ["bullish", "bullish", "bearish", "bullish", "bullish"]
        result = precision_recall_f1(predicted, actual, "bullish")
        assert result["precision"] == pytest.approx(2 / 3)
        assert result["recall"] == pytest.approx(0.5)
        assert result["f1"] == pytest.approx(2 * (2 / 3) * 0.5 / ((2 / 3) + 0.5))
        assert result["support"] == 4

    def test_undefined_precision_is_none_not_zero(self):
        """Reporting 0.0 when no positive call was made is a lie that reads as a result."""
        result = precision_recall_f1(["bearish"], ["bearish"], "bullish")
        assert result["precision"] is None
        assert result["f1"] is None

    def test_mean_brier(self):
        assert mean_brier([1.0, 0.0], [True, True]) == pytest.approx(0.5)

    def test_calibration_bins_cover_unit_interval(self):
        curve = calibration_curve([0.1, 0.9], [False, True], bins=5)
        assert len(curve) == 5
        assert curve[0]["bin_lower"] == 0.0
        assert curve[-1]["bin_upper"] == 1.0

    def test_calibration_reports_observed_rate(self):
        # four predictions all at 0.9, three of which were right
        curve = calibration_curve([0.9] * 4, [True, True, True, False], bins=5)
        top = [b for b in curve if b["n"] > 0][0]
        assert top["observed_rate"] == pytest.approx(0.75)
        assert top["mean_predicted"] == pytest.approx(0.9)

    def test_empty_bins_report_none_not_zero(self):
        curve = calibration_curve([0.9], [True], bins=5)
        assert curve[0]["n"] == 0 and curve[0]["observed_rate"] is None

    def test_roc_auc_perfect_separation(self):
        assert roc_auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == pytest.approx(1.0)

    def test_roc_auc_inverted(self):
        assert roc_auc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) == pytest.approx(0.0)

    def test_roc_auc_all_ties_is_half(self):
        assert roc_auc([0.5] * 4, [0, 1, 0, 1]) == pytest.approx(0.5)

    def test_roc_auc_single_class_is_none(self):
        """Common early on, when every resolved prediction happened to be right."""
        assert roc_auc([0.5, 0.7], [1, 1]) is None

    def test_evaluate_classification_bundle(self):
        predicted = ["bullish", "bearish", "bullish", "neutral"]
        actual = ["bullish", "bearish", "bearish", "neutral"]
        metrics = evaluate_classification(predicted, actual, [0.8, 0.7, 0.6, 0.55],
                                          FINANCIAL_OUTCOMES)
        assert metrics.n == 4
        assert metrics.accuracy == pytest.approx(0.75)
        assert set(metrics.per_class) == set(FINANCIAL_OUTCOMES)
        assert metrics.brier is not None
        assert len(metrics.calibration) == 5


class TestRegressionAndRanking:
    def test_mae(self):
        assert mean_absolute_error([1.0, 2.0], [1.5, 1.0]) == pytest.approx(0.75)

    def test_trend_correlation_perfect(self):
        assert trend_correlation([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)

    def test_trend_correlation_constant_series_is_none(self):
        assert trend_correlation([1, 1, 1, 1], [1, 2, 3, 4]) is None

    def test_ranking_stability_identical_is_one(self):
        assert ranking_stability(["a", "b", "c"], ["a", "b", "c"], k=3) == pytest.approx(1.0)

    def test_ranking_stability_disjoint_is_zero(self):
        assert ranking_stability(["a", "b"], ["c", "d"], k=2) == pytest.approx(0.0)

    def test_ranking_stability_partial(self):
        assert ranking_stability(["a", "b", "c"], ["a", "x", "y"], k=3) == pytest.approx(1 / 3)

    def test_ranking_stability_empty_is_none(self):
        assert ranking_stability([], ["a"]) is None


class TestSeededEvaluation:
    def test_seed_produces_resolved_predictions_to_evaluate(self, seeded):
        with session_scope() as s:
            pairs = resolved_pairs(s, domain="financial")
        assert len(pairs) >= 20, "evaluation framework needs resolved history to report on"

    def test_seeded_outcomes_are_read_from_price_history(self, seeded):
        """Outcomes must be derived, not invented."""
        with session_scope() as s:
            pairs = resolved_pairs(s, domain="financial")
        assert all(r.actual_value is not None for _, r in pairs)
        assert {r.actual_outcome for _, r in pairs} <= set(FINANCIAL_OUTCOMES)

    def test_seeded_accuracy_is_reportable(self, seeded):
        with session_scope() as s:
            pairs = resolved_pairs(s, domain="financial")
        metrics = evaluate_classification(
            [p.predicted_direction for p, _ in pairs],
            [r.actual_outcome for _, r in pairs],
            [p.predicted_probability for p, _ in pairs],
            FINANCIAL_OUTCOMES,
        )
        assert metrics.accuracy is not None
        assert 0.0 <= metrics.accuracy <= 1.0
        assert metrics.brier is not None
