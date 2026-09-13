"""AI investigator: turns a prediction + analogues into a structured,
plain-language explanation.

`Investigator` is the port. `TemplatedInvestigator` (default, used
everywhere in this prototype including tests) builds the explanation from
templated, rule-based text over the deterministic prediction output -- no
LLM call. `LLMInvestigator` is a pluggable skeleton that would call an
OpenAI-compatible endpoint using the prompts in `prompts.py` when
OPENAI_API_KEY is set; not used by default.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from worldpulse.events.schemas import WorldEvent
from worldpulse.prediction.predictor import PredictionResult


@dataclass
class InvestigatorExplanation:
    observed_facts: list[str]
    historical_association: str
    ai_hypothesis: str
    prediction: str
    what_would_invalidate: list[str]


class Investigator(ABC):
    @abstractmethod
    def explain(self, event: WorldEvent, prediction: PredictionResult) -> InvestigatorExplanation:
        ...


_INVALIDATORS_BY_DOMAIN: dict[str, list[str]] = {
    "conflict_geopolitical": [
        "A ceasefire or de-escalation is announced within the prediction horizon",
        "Major powers publicly signal non-intervention",
    ],
    "military_activity": [
        "The reported movement turns out to be a routine exercise, not a real deployment",
        "A rapid diplomatic resolution is reached",
    ],
    "energy_disruption": [
        "Alternate supply (strategic reserves, other producers) is announced quickly",
        "The disruption is confirmed to be shorter/smaller than initially reported",
    ],
    "economic_policy": [
        "The policy announcement is walked back or clarified as less impactful",
        "Markets had already priced in the announcement (no surprise)",
    ],
    "natural_disaster": [
        "Damage assessments come in lower than initial reports",
        "Affected infrastructure/production resumes faster than historical analogues",
    ],
}


class TemplatedInvestigator(Investigator):
    def explain(self, event: WorldEvent, prediction: PredictionResult) -> InvestigatorExplanation:
        event_type = event.event_type if isinstance(event.event_type, str) else event.event_type.value

        observed_facts = [
            f"Headline: {event.headline}",
            f"Event type: {event_type} / {event.event_subtype}",
            f"Countries involved: {', '.join(event.countries) if event.countries else 'unspecified'}",
            f"Reported severity: {event.severity:.2f} (0-1 scale)",
            f"Corroborating sources: {event.corroboration_count}",
        ]

        top_analogues = prediction.explanation.get("top_analogues", [])
        if prediction.sample_size > 0:
            historical_association = (
                f"Across {prediction.sample_size} similar historical events, {prediction.symbol} moved "
                f"{'up' if prediction.direction == 'UP' else 'down' if prediction.direction == 'DOWN' else 'in a mixed direction'} "
                f"over the following {prediction.horizon_hours}h in roughly "
                f"{prediction.explanation.get('p_up', 0.5):.0%} of cases, with a median return of "
                f"{prediction.median_return:.3%}."
            )
        else:
            historical_association = (
                f"No sufficiently similar historical events with resolved outcomes were found for "
                f"{prediction.symbol} at the {prediction.horizon_hours}h horizon."
            )

        ai_hypothesis = (
            f"HYPOTHESIS (not fact): given this is a {event_type.replace('_', ' ')} event affecting "
            f"{', '.join(event.affected_channels) if event.affected_channels else 'multiple channels'}, "
            f"the same risk-pricing mechanism that moved {prediction.symbol} after similar past events "
            f"may apply again -- but each event has unique circumstances, and this pattern is "
            f"correlational, not causal."
        )

        prediction_text = (
            f"Prediction for {prediction.symbol} at +{prediction.horizon_hours}h: {prediction.direction} "
            f"(probability={prediction.probability:.0%}, confidence tier={prediction.confidence_tier}, "
            f"sample_size={prediction.sample_size})."
        )

        invalidators = list(_INVALIDATORS_BY_DOMAIN.get(event_type, []))
        invalidators.append("The event cluster is revised/retracted by additional corroborating sources")

        return InvestigatorExplanation(
            observed_facts=observed_facts,
            historical_association=historical_association,
            ai_hypothesis=ai_hypothesis,
            prediction=prediction_text,
            what_would_invalidate=invalidators,
        )


class LLMInvestigator(Investigator):
    """LLM-backed investigator skeleton -- NOT used by default.

    Would call an OpenAI-compatible chat-completions endpoint using
    `agents/prompts.py`, requiring OPENAI_API_KEY.
    """

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini"):
        if not api_key:
            raise RuntimeError(
                "LLMInvestigator requires OPENAI_API_KEY. Use TemplatedInvestigator for local/dev/test."
            )
        self._api_key = api_key
        self._model = model

    def explain(self, event: WorldEvent, prediction: PredictionResult) -> InvestigatorExplanation:
        raise NotImplementedError(
            "Real LLM-backed investigation is not wired up in this prototype. "
            "Set OPENAI_API_KEY and implement the API call, or use TemplatedInvestigator."
        )
