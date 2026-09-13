"""Persona relevance: the "does this matter to me?" scoring."""
from __future__ import annotations

import pytest

from app.ranking.relevance import (
    _location_relevance,
    _role_overlap,
    _seniority_match,
    career_relevance,
    financial_relevance,
    skill_relevance,
)
from app.schemas.persona import DEMO_PERSONA


@pytest.fixture
def p():
    return DEMO_PERSONA


class TestFinancialRelevance:
    def test_watchlist_asset_beats_unrelated_asset(self, p):
        btc = financial_relevance(p, symbol="BTC", asset_class="crypto", sector="crypto")
        unrelated = financial_relevance(p, symbol="XOM", asset_class="equity",
                                        sector="energy")
        assert btc.score > unrelated.score
        assert btc.components["watchlist_membership"] == 1.0
        assert unrelated.components["watchlist_membership"] == 0.0

    def test_watchlist_hit_is_explained(self, p):
        result = financial_relevance(p, symbol="ETH", asset_class="crypto", sector="crypto")
        assert any("watchlist" in r for r in result.reasons)

    def test_tracked_sector_scores_without_watchlist_membership(self, p):
        """NVDA is not on the watchlist but AI is a tracked sector."""
        result = financial_relevance(p, symbol="NVDA", asset_class="equity", sector="AI")
        assert result.components["watchlist_membership"] == 0.0
        assert result.components["sector_preference"] == 1.0
        assert result.score > 0.2

    def test_entity_graph_connects_indirect_signals(self, p):
        """A CUDA headline should reach an 'AI infrastructure' persona."""
        result = financial_relevance(
            p, symbol="NVDA", asset_class="equity", sector="AI",
            signal_text="NVIDIA CUDA toolkit powers new AI infrastructure deployments",
        )
        assert result.components["entity_graph_overlap"] > 0.0

    def test_score_stays_in_unit_range(self, p):
        result = financial_relevance(p, symbol="BTC", asset_class="crypto", sector="crypto",
                                     signal_text="bitcoin crypto AI technology " * 20)
        assert 0.0 <= result.score <= 1.0


class TestCareerRelevance:
    def test_target_role_in_home_city_beats_unrelated_remote_role(self, p):
        good = career_relevance(p, title="Staff Data Engineer", skills=["spark", "kafka"],
                                location="Bengaluru, India", seniority="staff")
        bad = career_relevance(p, title="Frontend Designer", skills=["figma"],
                               location="San Francisco, CA", seniority="junior")
        assert good.score > bad.score

    def test_skill_overlap_is_fraction_of_required_skills(self, p):
        # persona has spark + kafka; 2 of 4 required -> 0.5
        result = career_relevance(p, title="Data Engineer",
                                  skills=["spark", "kafka", "rust", "scala"])
        assert result.components["skill_overlap"] == pytest.approx(0.5)

    def test_no_skills_listed_yields_zero_overlap_not_error(self, p):
        assert career_relevance(p, title="Data Engineer", skills=[]) \
            .components["skill_overlap"] == 0.0


class TestSubScores:
    def test_role_overlap_matches_target_roles(self, p):
        assert _role_overlap(p, "Staff Data Engineer") > _role_overlap(p, "Sales Manager")

    def test_location_ladder_is_ordered(self, p):
        home = _location_relevance(p, "Bengaluru, India", False)
        remote_in_country = _location_relevance(p, "Remote - India", True)
        remote_global = _location_relevance(p, "Remote - Global", True)
        other_city = _location_relevance(p, "Pune, India", False)
        abroad = _location_relevance(p, "Berlin, Germany", False)
        assert home > remote_in_country > remote_global > other_city > abroad

    def test_seniority_one_step_up_is_a_full_match(self, p):
        """A 10y Senior targeting Staff should see Staff roles at full strength."""
        assert _seniority_match(p, "staff") == pytest.approx(1.0)
        assert _seniority_match(p, "senior") == pytest.approx(1.0)

    def test_seniority_decays_with_distance(self, p):
        assert _seniority_match(p, "junior") < _seniority_match(p, "senior")

    def test_unknown_seniority_is_neutral(self, p):
        assert _seniority_match(p, "") == 0.5


class TestSkillRelevance:
    def test_held_skill_is_relevant(self, p):
        assert skill_relevance(p, skill_id="spark", skill_name="Spark") \
            .components["already_have"] == 1.0

    def test_unheld_skill_inside_a_learning_topic_is_a_gap(self, p):
        """LLM is not in the persona's skills but is in their learning topics."""
        result = skill_relevance(p, skill_id="llm", skill_name="LLM")
        assert result.components["already_have"] == 0.0
        assert result.components["learning_gap"] > 0.0

    def test_irrelevant_skill_scores_low(self, p):
        assert skill_relevance(p, skill_id="figma", skill_name="Figma").score < 0.3
