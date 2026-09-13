"""Event classification and enrichment.

Two entry points, because there are now two shapes of input:

  * `classify(item: RawNewsItem) -> WorldEvent` -- the original path, used
    by the World Monitor / synthetic sources which emit raw news items.
    Unchanged in behaviour.
  * `enrich(event: WorldEvent) -> WorldEvent` -- the multi-provider path.
    Provider adapters (GDELT, USGS, EONET, GDACS, FIRMS, ACLED) already
    produce a `WorldEvent` with provider-supplied structure (magnitude,
    EONET category, GDACS alert level, ACLED sub_event_type, ...). This
    method fills in the *derived* fields those adapters deliberately leave
    empty -- `potential_assets`, `industries`, `commodities`, refined
    `affected_channels` and `event_subtype` -- from the declarative
    mapping table in `config/impact_channels.yaml`.

`RuleBasedEventClassifier` is the default everywhere (`AI_CLASSIFIER=rules`,
no key needed). `LLMEventClassifier` is a pluggable skeleton that would
call an OpenAI-compatible structured-output endpoint; it is never used by
default and raises immediately if no key is configured.
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod

from worldpulse.config import settings
from worldpulse.events import impact_channels
from worldpulse.events.schemas import CLASSIFICATION_VERSION, EventDomain, WorldEvent
from worldpulse.ingestion.worldmonitor import RawNewsItem

logger = logging.getLogger(__name__)

# Category hint -> EventDomain
_CATEGORY_MAP: dict[str, EventDomain] = {
    "military": EventDomain.MILITARY,
    "conflict": EventDomain.CONFLICT,
    "energy": EventDomain.ENERGY,
    "economic": EventDomain.ECONOMIC,
    "disaster": EventDomain.DISASTER,
    # Aliases produced by the new providers' subtype/category vocabularies.
    "natural_disaster": EventDomain.DISASTER,
    "earthquake": EventDomain.DISASTER,
    "wildfire": EventDomain.DISASTER,
    "storm": EventDomain.DISASTER,
    "flood": EventDomain.DISASTER,
}

# Keyword -> subtype, used to refine event_subtype from the headline text.
# Extended from the original five-scenario vocabulary to cover the event
# types the new free providers actually emit (EONET categories, GDACS
# hazard codes, ACLED sub-event types, GDELT keyword sets).
_SUBTYPE_KEYWORDS: dict[str, list[str]] = {
    "troop_movement": ["masses troops", "troop deployment", "mobilis", "mobiliz", "border"],
    "naval_incident": ["naval", "tanker", "warship", "strait", "blockade"],
    "missile_strike": ["missile", "airstrike", "air strike", "drone strike", "shelling", "strike"],
    "armed_clash": ["armed clash", "clashes", "insurgen", "offensive", "coup", "firefight"],
    "civilian_violence": ["civilians killed", "violence against civilians", "massacre"],
    "protest": ["protest", "demonstration"],
    "riot": ["riot", "unrest"],
    "ceasefire_breakdown": ["ceasefire"],
    "state_of_emergency": ["state of emergency", "martial law"],
    "pipeline_disruption": ["pipeline"],
    "refinery_disruption": ["refinery", "refining outage"],
    "production_cut": ["production cut", "output cut", "opec", "quota"],
    "shipping_disruption": ["shipping", "port closed", "export terminal", "canal"],
    "rate_decision": ["rate decision", "central bank", "interest rate", "rate hike",
                      "rate cut", "federal reserve", "monetary policy"],
    "sanctions": ["sanction", "export ban", "embargo", "export control", "tariff"],
    "inflation_shock": ["inflation", "cpi print", " cpi"],
    "earthquake": ["earthquake", "quake", "seismic"],
    "tsunami": ["tsunami"],
    "volcanic_eruption": ["volcan", "eruption"],
    "tropical_cyclone": ["hurricane", "typhoon", "cyclone"],
    "storm": ["storm", "blizzard", "tornado"],
    "flooding": ["flood", "inundat"],
    "landslide": ["landslide", "mudslide"],
    "wildfire": ["wildfire", "bushfire", "forest fire", "active-fire"],
    "drought": ["drought"],
    "temperature_extreme": ["heatwave", "heat wave", "cold snap", "extreme cold"],
}

#: Subtypes the providers already assign authoritatively -- USGS *knows*
#: it is an earthquake, GDACS *knows* its hazard code. `enrich` must not
#: let a keyword heuristic overwrite those.
_AUTHORITATIVE_SUBTYPES = frozenset({
    "earthquake", "tsunami", "volcanic_eruption", "wildfire", "flooding",
    "landslide", "drought", "tropical_cyclone", "storm", "snowstorm",
    "dust_storm", "sea_ice", "temperature_extreme", "water_quality",
    "armed_clash", "civilian_violence", "protest", "riot",
    "strategic_development", "manmade_incident",
})

_MAJOR_ECONOMIES = {"USA", "China", "Russia", "Japan", "Saudi Arabia"}


def _table():
    return impact_channels.get_table()


class EventClassifier(ABC):
    @abstractmethod
    def classify(self, item: RawNewsItem) -> WorldEvent:
        ...


class RuleBasedEventClassifier(EventClassifier):
    """Deterministic keyword/entity-driven extraction (default classifier)."""

    # --- raw-news path (unchanged behaviour) ---------------------------

    def classify(self, item: RawNewsItem) -> WorldEvent:
        domain = _CATEGORY_MAP.get(item.category_hint, EventDomain.ECONOMIC)
        subtype = self._infer_subtype(item.headline)
        severity = self._infer_severity(item)
        geo_relevance = self._geo_relevance(item.countries)

        event = WorldEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-event:{item.id}")),
            source_id=item.id,
            occurred_at=item.published_at,
            ingested_at=item.published_at,
            event_type=domain,
            event_subtype=subtype,
            countries=item.countries,
            entities=item.entities,
            affected_channels=item.channels,
            potential_assets=[],
            severity=severity,
            headline=item.headline,
            source_confidence=min(1.0, 0.5 + 0.1 * item.corroboration_count),
            corroboration_count=item.corroboration_count,
            source_name=item.source_name,
            classification_version=CLASSIFICATION_VERSION,
        )

        mapping = _table().resolve(event)
        event.potential_assets = mapping.assets
        event.industries = mapping.industries
        event.commodities = mapping.commodities
        event.reasoning_summary = (
            f"Classified as {domain.value}/{subtype} based on keyword match in headline "
            f"'{item.headline}' and source category hint '{item.category_hint}'. "
            f"Countries involved: {', '.join(item.countries)}. Severity derived from "
            f"source severity hint ({item.severity_hint}) and corroboration count "
            f"({item.corroboration_count}). Impact channels from rules "
            f"[{', '.join(mapping.matched_rules)}] "
            f"(geo relevance {geo_relevance:.2f})."
        )
        return event

    # --- provider path -------------------------------------------------

    def enrich(self, event: WorldEvent) -> WorldEvent:
        """Fill derived fields on a provider-produced `WorldEvent`.

        Provider-supplied structure always wins: an authoritative
        `event_subtype` (USGS "earthquake", GDACS "tropical_cyclone") and a
        provider-computed `severity` (magnitude-derived, alert-level-derived)
        are never overwritten. Only genuinely empty/unknown fields are
        filled in.
        """
        if event.event_subtype in ("", "general", "natural_event") or \
                event.event_subtype not in _AUTHORITATIVE_SUBTYPES:
            inferred = self._infer_subtype(
                " ".join(filter(None, [event.headline, event.summary]))
            )
            if inferred != "general" or not event.event_subtype:
                event.event_subtype = inferred if inferred != "general" else (
                    event.event_subtype or "general"
                )

        mapping = _table().resolve(event)
        if not event.potential_assets:
            event.potential_assets = mapping.assets
        if not event.industries:
            event.industries = mapping.industries
        if not event.commodities:
            event.commodities = mapping.commodities
        for channel in mapping.channels:
            if channel not in event.affected_channels:
                event.affected_channels.append(channel)

        event.classification_version = CLASSIFICATION_VERSION
        provenance = f"provider={event.provider or 'unknown'}"
        if event.provider_event_id:
            provenance += f" id={event.provider_event_id}"
        extra = (
            f" Enriched by {CLASSIFICATION_VERSION} from impact-channel rules "
            f"[{', '.join(mapping.matched_rules) or 'none'}] "
            f"(market_relevance={mapping.market_relevance:.2f}, {provenance})."
        )
        event.reasoning_summary = (event.reasoning_summary or "") + extra
        return event

    def enrich_all(self, events: list[WorldEvent]) -> list[WorldEvent]:
        return [self.enrich(event) for event in events]

    # --- helpers -------------------------------------------------------

    @staticmethod
    def _infer_subtype(headline: str) -> str:
        lower = (headline or "").lower()
        for subtype, keywords in _SUBTYPE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return subtype
        return "general"

    @staticmethod
    def _infer_severity(item: RawNewsItem) -> float:
        corroboration_boost = min(0.15, 0.03 * (item.corroboration_count - 1))
        severity = item.severity_hint + corroboration_boost
        return max(0.0, min(1.0, round(severity, 3)))

    @staticmethod
    def _geo_relevance(countries: list[str]) -> float:
        if not countries:
            return 0.3
        major_hits = sum(1 for c in countries if c in _MAJOR_ECONOMIES)
        return min(1.0, 0.4 + 0.3 * major_hits)

    @staticmethod
    def market_relevance_prior(domain: EventDomain | str) -> float:
        """Per-domain prior, now sourced from `config/impact_channels.yaml`."""
        if isinstance(domain, str):
            try:
                domain = EventDomain(domain)
            except ValueError:
                return 0.5
        return _table().market_relevance(domain)

    def geo_relevance(self, countries: list[str]) -> float:
        return self._geo_relevance(countries)


class LLMEventClassifier(EventClassifier):
    """Structured-output LLM classifier skeleton -- NOT used by default.

    Would call an OpenAI-compatible chat-completions endpoint (OpenAI,
    Groq or OpenRouter) with a JSON schema matching `WorldEvent`.
    """

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini"):
        if not api_key:
            raise RuntimeError(
                "LLMEventClassifier requires an LLM API key (OPENAI_API_KEY / "
                "GROQ_API_KEY / OPENROUTER_API_KEY). Use RuleBasedEventClassifier "
                "(AI_CLASSIFIER=rules, the default) for local/dev/test -- it needs no key."
            )
        self._api_key = api_key
        self._model = model

    def classify(self, item: RawNewsItem) -> WorldEvent:
        raise NotImplementedError(
            "Real LLM-backed classification is not wired up in this prototype. "
            "Set an LLM key and implement the structured-output call, or use "
            "RuleBasedEventClassifier."
        )


def get_classifier() -> EventClassifier:
    """The configured classifier. Defaults to the rule-based one (no key).

    `AI_CLASSIFIER=llm` selects the LLM path; if no LLM key is configured
    that would raise, so this falls back to the rule-based classifier with
    a warning rather than breaking startup.
    """
    if (settings.ai_classifier or "rules").strip().lower() == "llm":
        key = settings.openai_api_key or settings.groq_api_key or settings.openrouter_api_key
        if key:
            return LLMEventClassifier(key)
        logger.warning(
            "AI_CLASSIFIER=llm but no OPENAI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY "
            "is set; falling back to RuleBasedEventClassifier."
        )
    return RuleBasedEventClassifier()
