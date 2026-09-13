"""Core event schemas and the impact_candidate_score formula.

`WorldEvent` is the canonical structured record produced either by an
`EventClassifier` from a raw news/intel item, or directly by a
`WorldEventProvider` adapter (GDELT / USGS / EONET / GDACS / FIRMS /
ACLED / World Monitor). It is intentionally a plain pydantic model (not a
SQLAlchemy model) so that classification logic never depends on the
persistence layer; `database/models.py` defines the corresponding ORM
table and `database/repository.py` translates between the two.

Field-naming note (backward compatibility)
------------------------------------------
This model predates the multi-provider refactor and already used
`event_type` for the coarse *domain* (the `EventDomain` enum) and
`event_subtype` for the granular type. Downstream code (classifier,
embeddings, dedup, similarity, prediction, evaluation, API, dashboard,
ORM) reads those names, so they are preserved verbatim. The refactor adds
the newer canonical names as synced aliases instead of renaming:

  * `event_domain`  == `event_type`  (coarse domain, e.g. "natural_disaster")
  * `event_subtype`  = granular type (e.g. "earthquake")
  * `event_subtype_detail` = provider-specific finer detail
    (e.g. EONET category, GDACS alert level, magnitude band)
  * `event_id`      == `id`
  * `country_codes` == `countries`
  * `source_url`     = first entry of `source_urls`
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class EventDomain(str, enum.Enum):
    CONFLICT = "conflict_geopolitical"
    MILITARY = "military_activity"
    ENERGY = "energy_disruption"
    ECONOMIC = "economic_policy"
    DISASTER = "natural_disaster"


CLASSIFICATION_VERSION = "rules-v2"


class WorldEvent(BaseModel):
    """Structured, provider-agnostic record of a single real-world event."""

    id: Optional[str] = None
    source_id: str = Field(
        default="",
        description="ID of the raw source item this was extracted from",
    )
    occurred_at: datetime
    ingested_at: datetime
    # When WorldPulse first observed this event (may be later than
    # occurred_at for backfills). Defaults to ingested_at.
    first_seen_at: Optional[datetime] = None

    event_type: EventDomain
    event_subtype: str
    # Newer canonical alias of `event_type`; kept in sync by the validator
    # below so callers may read either name.
    event_domain: str = ""
    event_subtype_detail: str = ""

    countries: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    affected_channels: list[str] = Field(
        default_factory=list,
        description="e.g. 'energy_supply', 'shipping_lanes', 'monetary_policy'",
    )
    potential_assets: list[str] = Field(
        default_factory=list, description="Instrument symbols this event could move"
    )
    severity: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str = ""

    headline: str = ""
    summary: str = ""
    source_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    corroboration_count: int = Field(
        default=1, description="How many independent sources reported this event"
    )

    # --- Provenance (added by the multi-provider refactor) ---
    provider: str = Field(default="", description="Adapter that produced this record")
    provider_event_id: str = Field(
        default="", description="Stable ID of this event in the provider's own namespace"
    )
    source_urls: list[str] = Field(default_factory=list)
    source_name: str = ""
    raw_payload: Optional[dict[str, Any]] = Field(
        default=None, description="Verbatim provider payload, for audit/replay"
    )
    classification_version: str = CLASSIFICATION_VERSION

    # --- Geography ---
    locations: list[str] = Field(
        default_factory=list, description="Free-text place names (e.g. 'Hualien, Taiwan')"
    )
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # --- Impact-channel enrichment ---
    industries: list[str] = Field(default_factory=list)
    commodities: list[str] = Field(default_factory=list)
    novelty_score: Optional[float] = None

    event_cluster_id: Optional[str] = None
    embedding: Optional[list[float]] = None

    model_config = {"use_enum_values": True}

    # --- Alias / default synchronization -------------------------------

    @model_validator(mode="after")
    def _sync_aliases(self) -> "WorldEvent":
        et = self.event_type.value if hasattr(self.event_type, "value") else str(self.event_type)
        if not self.event_domain:
            object.__setattr__(self, "event_domain", et)
        if not self.source_id:
            # Prefer a provider-namespaced ID so cross-run upserts are stable.
            fallback = (
                f"{self.provider}:{self.provider_event_id}"
                if self.provider and self.provider_event_id
                else (self.provider_event_id or self.id or "")
            )
            object.__setattr__(self, "source_id", fallback)
        if self.first_seen_at is None:
            object.__setattr__(self, "first_seen_at", self.ingested_at)
        # Normalize all timestamps to tz-aware UTC.
        for attr in ("occurred_at", "ingested_at", "first_seen_at"):
            value = getattr(self, attr)
            if isinstance(value, datetime) and value.tzinfo is None:
                object.__setattr__(self, attr, value.replace(tzinfo=timezone.utc))
        return self

    # --- Read-only convenience aliases ---------------------------------

    @property
    def event_id(self) -> Optional[str]:
        """Alias of `id` (spec field name)."""
        return self.id

    @property
    def country_codes(self) -> list[str]:
        """Alias of `countries` (spec field name)."""
        return self.countries

    @property
    def source_url(self) -> Optional[str]:
        """Backward-compatible singular alias: first of `source_urls`."""
        return self.source_urls[0] if self.source_urls else None

    def has_point_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class EventEvidence(BaseModel):
    """One provider's contribution to a (possibly merged) WorldEvent.

    When cross-source dedup merges e.g. a USGS earthquake, a GDELT news
    article about it and an EONET entry for it into a single cluster, one
    `EventEvidence` row is written per contributing source so nothing is
    silently dropped and every merged event stays auditable.
    """

    event_id: str
    provider: str
    provider_event_id: str = ""
    source_url: Optional[str] = None
    source_name: str = ""
    observed_at: datetime
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"use_enum_values": True}

    @model_validator(mode="after")
    def _utc(self) -> "EventEvidence":
        if self.observed_at.tzinfo is None:
            object.__setattr__(self, "observed_at", self.observed_at.replace(tzinfo=timezone.utc))
        return self


class ImpactScoreInputs(BaseModel):
    """Inputs to the impact_candidate_score formula (spec section: scoring)."""

    severity: float
    corroboration: float  # normalized 0-1 (e.g. min(count/5, 1))
    novelty: float  # 1 - similarity to most similar recent event, 0-1
    historical_market_relevance: float  # 0-1, how often this event_type moved markets historically
    geographic_relevance: float  # 0-1, proximity/relevance to major economies/chokepoints
    source_confidence: float  # 0-1


def impact_candidate_score(inputs: ImpactScoreInputs) -> float:
    """Weighted impact score gating whether a prediction is attempted.

    score = 0.30*severity + 0.20*corroboration + 0.15*novelty
          + 0.15*historical_market_relevance + 0.10*geographic_relevance
          + 0.10*source_confidence

    All inputs and the output are clamped to [0, 1].
    """
    def c(x: float) -> float:
        return max(0.0, min(1.0, x))

    score = (
        0.30 * c(inputs.severity)
        + 0.20 * c(inputs.corroboration)
        + 0.15 * c(inputs.novelty)
        + 0.15 * c(inputs.historical_market_relevance)
        + 0.10 * c(inputs.geographic_relevance)
        + 0.10 * c(inputs.source_confidence)
    )
    return max(0.0, min(1.0, score))
