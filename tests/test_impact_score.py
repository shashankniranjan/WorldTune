from worldpulse.events.schemas import ImpactScoreInputs, impact_candidate_score


def test_impact_score_formula_hand_computed():
    inputs = ImpactScoreInputs(
        severity=0.8, corroboration=0.6, novelty=0.5,
        historical_market_relevance=0.7, geographic_relevance=0.4, source_confidence=0.9,
    )
    expected = 0.30 * 0.8 + 0.20 * 0.6 + 0.15 * 0.5 + 0.15 * 0.7 + 0.10 * 0.4 + 0.10 * 0.9
    assert abs(impact_candidate_score(inputs) - expected) < 1e-9


def test_impact_score_clamped_to_unit_interval():
    inputs = ImpactScoreInputs(
        severity=2.0, corroboration=2.0, novelty=2.0,
        historical_market_relevance=2.0, geographic_relevance=2.0, source_confidence=2.0,
    )
    assert impact_candidate_score(inputs) == 1.0

    inputs_low = ImpactScoreInputs(
        severity=-1.0, corroboration=-1.0, novelty=-1.0,
        historical_market_relevance=-1.0, geographic_relevance=-1.0, source_confidence=-1.0,
    )
    assert impact_candidate_score(inputs_low) == 0.0


def test_impact_score_zero_when_all_zero():
    inputs = ImpactScoreInputs(
        severity=0, corroboration=0, novelty=0,
        historical_market_relevance=0, geographic_relevance=0, source_confidence=0,
    )
    assert impact_candidate_score(inputs) == 0.0
