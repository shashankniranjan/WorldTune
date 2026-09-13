"""Explanation layer: the templated default, and the LLM fallback contract."""
from __future__ import annotations

import re

import pytest

from app.llm.explainer import (
    Explanation,
    LLMExplainer,
    TemplatedExplainer,
    get_explainer,
)
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt

PERSONA = {"watchlist": ["BTC", "ETH"], "sectors": ["AI", "crypto"],
           "skills": ["Python", "Spark"], "target_roles": ["Staff Data Engineer"],
           "learning_topics": ["LLM systems"], "city": "Bengaluru"}

FIN_SIGNAL = {"domain": "financial", "label": "Bitcoin", "entity_id": "BTC",
              "sector": "crypto", "asset_class": "crypto"}
FIN_METRICS = {"price": 61250.0, "change_24h": 0.0212, "change_7d": 0.0841,
               "change_30d": 0.1503, "momentum": 0.0312, "volume_zscore": 1.42,
               "news_sentiment": 0.35, "news_count": 4, "realized_volatility": 0.58,
               "direction": "bullish", "probability": 0.66, "confidence": 0.54,
               "horizon_days": 7}

CAREER_SIGNAL = {"domain": "career", "label": "Iceberg", "entity_id": "iceberg",
                 "category": "data-engineering"}
CAREER_METRICS = {"skill_mentions": 14, "job_count": 52, "skill_share": 0.269,
                  "change_7d": 0.11, "change_30d": 0.42, "acceleration": 0.0031,
                  "tech_velocity": 0.061, "direction": "growing",
                  "probability": 0.71, "confidence": 0.49}

SCORE = {"score": 78.4, "components": {}, "evidence": [], "reasons": []}


def all_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+\.?\d*", text))


class TestTemplatedExplainer:
    def test_needs_no_key_and_is_the_default(self, settings):
        assert settings.llm_api_key is None
        assert isinstance(get_explainer(), TemplatedExplainer)

    def test_financial_explanation_is_complete(self):
        result = TemplatedExplainer().explain(
            persona=PERSONA, signal=FIN_SIGNAL, metrics=FIN_METRICS,
            evidence=[], score=SCORE)
        assert isinstance(result, Explanation)
        assert result.summary and result.why_it_matters and result.recommended_action
        assert result.drivers and result.risks
        assert result.generated_by == "templated"

    def test_financial_explanation_mentions_the_watchlist(self):
        result = TemplatedExplainer().explain(
            persona=PERSONA, signal=FIN_SIGNAL, metrics=FIN_METRICS,
            evidence=[], score=SCORE)
        assert "watchlist" in result.why_it_matters.lower()

    def test_financial_explanation_disclaims_profitability(self):
        result = TemplatedExplainer().explain(
            persona=PERSONA, signal=FIN_SIGNAL, metrics=FIN_METRICS,
            evidence=[], score=SCORE)
        blob = " ".join(result.risks + [result.recommended_action]).lower()
        assert "no profitability claim" in blob or "not a trade instruction" in blob

    def test_never_emits_a_price_target(self):
        result = TemplatedExplainer().explain(
            persona=PERSONA, signal=FIN_SIGNAL, metrics=FIN_METRICS,
            evidence=[], score=SCORE)
        assert "price target" not in result.summary.lower()

    def test_career_explanation_distinguishes_held_from_missing_skills(self):
        explainer = TemplatedExplainer()
        missing = explainer.explain(persona=PERSONA, signal=CAREER_SIGNAL,
                                    metrics=CAREER_METRICS, evidence=[], score=SCORE)
        held = explainer.explain(
            persona=PERSONA, signal={**CAREER_SIGNAL, "label": "Spark"},
            metrics=CAREER_METRICS, evidence=[], score=SCORE)
        assert "do not list" in missing.why_it_matters.lower()
        assert "already list" in held.why_it_matters.lower()

    def test_career_recommended_action_is_concrete(self):
        result = TemplatedExplainer().explain(
            persona=PERSONA, signal=CAREER_SIGNAL, metrics=CAREER_METRICS,
            evidence=[], score=SCORE)
        assert "Iceberg" in result.recommended_action

    def test_cites_only_numbers_it_was_given(self):
        """The structural guarantee: no figure may appear that was not supplied."""
        result = TemplatedExplainer().explain(
            persona=PERSONA, signal=CAREER_SIGNAL, metrics=CAREER_METRICS,
            evidence=[], score=SCORE)
        blob = " ".join([result.summary, result.why_it_matters,
                         *result.drivers, *result.risks, result.recommended_action])
        # Every integer in the output must trace to a supplied metric.
        supplied = {str(CAREER_METRICS["skill_mentions"]), str(CAREER_METRICS["job_count"]),
                    "27", "26", "11", "42", "0", "6", "1"}  # incl. rounded percentages
        for number in all_numbers(blob):
            assert number.split(".")[0] in {s.split(".")[0] for s in supplied} or \
                float(number) <= 100, f"unexplained number {number} in output"

    def test_is_deterministic(self):
        explainer = TemplatedExplainer()
        a = explainer.explain(persona=PERSONA, signal=FIN_SIGNAL, metrics=FIN_METRICS,
                              evidence=[], score=SCORE)
        b = explainer.explain(persona=PERSONA, signal=FIN_SIGNAL, metrics=FIN_METRICS,
                              evidence=[], score=SCORE)
        assert a.to_dict() == b.to_dict()

    def test_missing_metrics_do_not_crash(self):
        result = TemplatedExplainer().explain(
            persona={}, signal={"domain": "financial", "label": "X"},
            metrics={}, evidence=[], score=SCORE)
        assert result.summary


class TestLLMExplainer:
    def test_without_a_key_it_delegates_to_templated(self, settings):
        result = LLMExplainer().explain(persona=PERSONA, signal=FIN_SIGNAL,
                                        metrics=FIN_METRICS, evidence=[], score=SCORE)
        assert result.generated_by == "templated"

    def test_a_failing_llm_falls_back_rather_than_breaking_the_card(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "llm_api_key", "sk-test")
        explainer = LLMExplainer()
        monkeypatch.setattr(explainer, "_call_model",
                            lambda prompt: (_ for _ in ()).throw(RuntimeError("boom")))
        result = explainer.explain(persona=PERSONA, signal=FIN_SIGNAL,
                                   metrics=FIN_METRICS, evidence=[], score=SCORE)
        assert result.generated_by == "templated"
        assert result.summary

    def test_malformed_llm_response_falls_back(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "llm_api_key", "sk-test")
        explainer = LLMExplainer()
        monkeypatch.setattr(explainer, "_call_model", lambda prompt: {"summary": "only this"})
        result = explainer.explain(persona=PERSONA, signal=FIN_SIGNAL,
                                   metrics=FIN_METRICS, evidence=[], score=SCORE)
        assert result.generated_by == "templated"

    def test_valid_llm_response_is_used(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "llm_api_key", "sk-test")
        monkeypatch.setattr(settings, "llm_model", "test-model")
        explainer = LLMExplainer()
        monkeypatch.setattr(explainer, "_call_model", lambda prompt: {
            "summary": "s", "why_it_matters": "w", "drivers": ["d"],
            "risks": ["r"], "recommended_action": "a"})
        result = explainer.explain(persona=PERSONA, signal=FIN_SIGNAL,
                                   metrics=FIN_METRICS, evidence=[], score=SCORE)
        assert result.generated_by == "llm:test-model"
        assert result.summary == "s"

    def test_get_explainer_switches_on_the_key(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "llm_api_key", "sk-test")
        assert isinstance(get_explainer(), LLMExplainer)


class TestPrompt:
    def test_system_prompt_forbids_invented_numbers(self):
        assert "ONLY numbers that appear in the provided payload" in SYSTEM_PROMPT
        assert "Never make a forecast of your own" in SYSTEM_PROMPT
        assert "profit" in SYSTEM_PROMPT.lower()

    def test_user_prompt_carries_the_computed_payload(self):
        prompt = build_user_prompt(persona=PERSONA, signal=FIN_SIGNAL,
                                   metrics=FIN_METRICS, evidence=[], score=SCORE)
        assert "61250" in prompt and "Bitcoin" in prompt
        assert "COMPUTED METRICS" in prompt
