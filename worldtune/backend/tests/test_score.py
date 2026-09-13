"""The WorldTune formula and its components (spec section 14)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.ranking.score import (
    WEIGHTS,
    compute_score,
    evidence_strength_score,
    novelty_score,
    prediction_confidence_score,
    recency_score,
    top_contributors,
    trend_momentum_score,
)

NOW = datetime(2025, 9, 13, 12, 0, tzinfo=timezone.utc)


class TestFormula:
    def test_weights_sum_to_one(self):
        assert sum(WEIGHTS.values()) == pytest.approx(1.0)

    def test_all_ones_scores_one_hundred(self):
        result = compute_score(persona_relevance=1, trend_momentum=1, evidence_strength=1,
                               novelty=1, recency=1, prediction_confidence=1)
        assert result.score == pytest.approx(100.0)

    def test_all_zeros_scores_zero(self):
        result = compute_score(persona_relevance=0, trend_momentum=0, evidence_strength=0,
                               novelty=0, recency=0, prediction_confidence=0)
        assert result.score == 0.0

    def test_hand_computed_mixed_score(self):
        # 0.30*1.0 + 0.20*0.5 + 0.15*0.0 + 0.15*0.0 + 0.10*1.0 + 0.10*0.0 = 0.50
        result = compute_score(persona_relevance=1.0, trend_momentum=0.5,
                               evidence_strength=0.0, novelty=0.0,
                               recency=1.0, prediction_confidence=0.0)
        assert result.score == pytest.approx(50.0)

    def test_contributions_sum_to_total(self):
        result = compute_score(persona_relevance=0.7, trend_momentum=0.4,
                               evidence_strength=0.9, novelty=0.2,
                               recency=0.6, prediction_confidence=0.5)
        total = sum(c["contribution"] for c in result.components.values())
        assert total == pytest.approx(result.score, abs=0.05)

    def test_out_of_range_inputs_are_clamped(self):
        result = compute_score(persona_relevance=5.0, trend_momentum=-3.0,
                               evidence_strength=0.5, novelty=0.5,
                               recency=0.5, prediction_confidence=0.5)
        assert result.components["persona_relevance"]["value"] == 1.0
        assert result.components["trend_momentum"]["value"] == 0.0
        assert 0.0 <= result.score <= 100.0

    def test_breakdown_is_always_present(self):
        """A score must never be a bare number -- this is the core contract."""
        result = compute_score(persona_relevance=0.5, trend_momentum=0.5,
                               evidence_strength=0.5, novelty=0.5,
                               recency=0.5, prediction_confidence=0.5,
                               relevance_components={"watchlist_membership": 1.0},
                               evidence=[{"type": "news", "detail": "x"}],
                               reasons=["BTC is on your watchlist"])
        payload = result.to_dict()
        assert set(payload["components"]) == set(WEIGHTS)
        for component in payload["components"].values():
            assert {"value", "weight", "contribution"} <= set(component)
        assert payload["evidence"] and payload["reasons"]
        assert "PersonaRelevance" in payload["formula"]
        assert payload["components"]["persona_relevance"]["sub_scores"]["watchlist_membership"] == 1.0

    def test_top_contributors_ranks_by_contribution(self):
        result = compute_score(persona_relevance=1.0, trend_momentum=0.0,
                               evidence_strength=0.0, novelty=0.0,
                               recency=1.0, prediction_confidence=0.0)
        assert "persona relevance" in top_contributors(result, limit=1)[0]


class TestComponents:
    def test_trend_momentum_is_direction_agnostic(self):
        """A -18% move is as *interesting* as +18%; direction lives elsewhere."""
        assert trend_momentum_score(0.18) == pytest.approx(trend_momentum_score(-0.18))

    def test_trend_momentum_saturates(self):
        assert trend_momentum_score(50.0) <= 1.0
        assert trend_momentum_score(0.0) == pytest.approx(0.0)

    def test_trend_momentum_is_monotonic_in_magnitude(self):
        values = [trend_momentum_score(c) for c in (0.0, 0.05, 0.1, 0.3, 1.0)]
        assert values == sorted(values)

    def test_evidence_prefers_independent_sources_over_repetition(self):
        many_sources = evidence_strength_score(n_sources=4, n_observations=10)
        one_source_repeated = evidence_strength_score(n_sources=1, n_observations=40)
        assert many_sources > one_source_repeated

    def test_evidence_with_nothing_is_zero(self):
        assert evidence_strength_score() == pytest.approx(0.0)

    def test_recency_half_life(self):
        older = NOW - timedelta(hours=36)
        assert recency_score(older, as_of=NOW, half_life_hours=36.0) == pytest.approx(0.5)

    def test_recency_now_is_one(self):
        assert recency_score(NOW, as_of=NOW) == pytest.approx(1.0)

    def test_recency_decays_monotonically(self):
        scores = [recency_score(NOW - timedelta(hours=h), as_of=NOW) for h in (0, 12, 48, 200)]
        assert scores == sorted(scores, reverse=True)

    def test_recency_handles_naive_datetime(self):
        naive = NOW.replace(tzinfo=None)
        assert 0.0 <= recency_score(naive, as_of=NOW) <= 1.0

    def test_novelty_damped_by_repeat_exposure(self):
        fresh = novelty_score(zscore=2.0, seen_before_count=0)
        stale = novelty_score(zscore=2.0, seen_before_count=9)
        assert fresh > stale

    def test_prediction_confidence_punishes_a_coin_flip(self):
        decisive = prediction_confidence_score(0.8, 0.9)
        shrug = prediction_confidence_score(0.8, 0.5)
        assert decisive > shrug

    def test_all_components_stay_in_unit_range(self):
        assert 0.0 <= trend_momentum_score(99.0, 99.0, 99.0) <= 1.0
        assert 0.0 <= novelty_score(zscore=99.0, is_new_entity=True) <= 1.0
        assert 0.0 <= evidence_strength_score(n_sources=999, n_observations=999) <= 1.0
        assert 0.0 <= prediction_confidence_score(9.0, 9.0) <= 1.0
