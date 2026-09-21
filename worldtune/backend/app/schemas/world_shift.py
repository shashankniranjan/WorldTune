"""API models for the GDELT-backed frontend World Shift contract."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class SnapshotMeta(ContractModel):
    snapshot_id: str = Field(alias="snapshotId")
    generated_at: str = Field(alias="generatedAt")
    valid_until: str = Field(alias="validUntil")


class WorldShiftListItem(ContractModel):
    id: str
    title: str
    rank: int
    status: str
    direction: str
    relationship_reason: str | None = Field(default=None, alias="relationshipReason")
    relationship_confidence: str | None = Field(default=None, alias="relationshipConfidence")


class Evidence(ContractModel):
    id: str
    type: str
    source: str
    title: str
    summary: str | None = None
    published_at: str = Field(alias="publishedAt")
    url: str
    image_url: str | None = Field(default=None, alias="imageUrl")
    entities: list[str]
    tags: list[str]
    relationship_role: str | None = Field(default=None, alias="relationshipRole")
    confidence: str
    supports: list[str]
    source_domain: str | None = Field(default=None, alias="sourceDomain")
    original_headline: str | None = Field(default=None, alias="originalHeadline")
    source_snippet: str | None = Field(default=None, alias="sourceSnippet")
    ai_summary: str | None = Field(default=None, alias="aiSummary")
    event_ids: list[str] = Field(default_factory=list, alias="eventIds")
    claim_ids: list[str] = Field(default_factory=list, alias="claimIds")
    entity_ids: list[str] = Field(default_factory=list, alias="entityIds")
    evidence_class: Literal["observed", "calculated", "inferred", "associated"] = Field(
        default="observed", alias="evidenceClass"
    )
    source_class: Literal["primary", "secondary", "aggregator", "unknown"] = Field(
        default="unknown", alias="sourceClass"
    )
    retrieval_status: Literal["complete", "metadata_only", "unavailable"] = Field(
        default="metadata_only", alias="retrievalStatus"
    )
    publisher_family: str | None = Field(default=None, alias="publisherFamily")
    independent_publisher_count: int = Field(default=1, ge=1, alias="independentPublisherCount")
    corroboration_status: Literal["single_source", "syndicated", "independently_corroborated", "contested"] = Field(
        default="single_source", alias="corroborationStatus"
    )


class IntelligencePoint(ContractModel):
    text: str
    evidence_class: Literal["observed", "calculated", "inferred", "associated"] = Field(alias="evidenceClass")
    evidence_ids: list[str] = Field(alias="evidenceIds", min_length=1)
    claim_ids: list[str] = Field(default_factory=list, alias="claimIds")


class ImpactItem(ContractModel):
    id: str
    title: str
    summary: str
    direction: str | None = None
    magnitude: str | None = None
    evidence_ids: list[str] = Field(alias="evidenceIds")
    claim_ids: list[str] = Field(default_factory=list, alias="claimIds")
    evidence_class: Literal["observed", "calculated", "inferred", "associated"] = Field(
        default="inferred", alias="evidenceClass"
    )
    mechanism: str | None = None
    horizon: Literal["immediate", "7d", "30d", "90d", "long_term"] | None = None
    confidence: Literal["low", "medium", "high"] = "low"
    counter_evidence_ids: list[str] = Field(default_factory=list, alias="counterEvidenceIds")
    invalidators: list[str] = Field(default_factory=list)


class Overview(ContractModel):
    what_happened: str = Field(alias="whatHappened")
    why_it_matters: str = Field(alias="whyItMatters")
    quick_take: str | None = Field(default=None, alias="quickTake")
    characteristics: list[str]
    themes: list[str]
    whats_happening: list[IntelligencePoint] = Field(default_factory=list, alias="whatsHappening")
    why_it_matters_points: list[IntelligencePoint] = Field(default_factory=list, alias="whyItMattersPoints")
    key_developments: list[IntelligencePoint] = Field(default_factory=list, alias="keyDevelopments")
    watch_next: list[IntelligencePoint] = Field(default_factory=list, alias="watchNext")
    drivers: list[IntelligencePoint] = Field(default_factory=list)
    contradictions: list[IntelligencePoint] = Field(default_factory=list)


class RelationshipNode(ContractModel):
    id: str
    label: str
    type: str
    category: str | None = None
    summary: str | None = None
    direction: str | None = None
    magnitude: str | None = None
    evidence_ids: list[str] = Field(alias="evidenceIds")


class RelationshipEdge(ContractModel):
    id: str
    source: str
    target: str
    relationship: str
    category: str | None = None
    explanation: str | None = None
    confidence: str
    evidence_ids: list[str] = Field(alias="evidenceIds")
    claim_ids: list[str] = Field(default_factory=list, alias="claimIds")
    evidence_class: Literal["observed", "calculated", "inferred", "associated"] = Field(
        default="associated", alias="evidenceClass"
    )
    mechanism: str | None = None
    temporal_order: str | None = Field(default=None, alias="temporalOrder")
    opposing_evidence_ids: list[str] = Field(default_factory=list, alias="opposingEvidenceIds")
    alternative_explanations: list[str] = Field(default_factory=list, alias="alternativeExplanations")
    first_observed_at: str | None = Field(default=None, alias="firstObservedAt")
    last_updated_at: str | None = Field(default=None, alias="lastUpdatedAt")


class CrossShiftLink(ContractModel):
    shift_id: str = Field(alias="shiftId")
    title: str
    relationship: str
    explanation: str
    confidence: Literal["low", "medium", "high"] = "low"
    evidence_class: Literal["inferred", "associated"] = Field(default="inferred", alias="evidenceClass")
    evidence_ids: list[str] = Field(default_factory=list, alias="evidenceIds")
    indicators: list[str] = Field(default_factory=list)


class PersonalPath(ContractModel):
    id: str
    title: str
    persona: str
    steps: list[str] = Field(min_length=2)
    explanation: str
    confidence: Literal["low", "medium", "high"] = "low"
    evidence_ids: list[str] = Field(default_factory=list, alias="evidenceIds")


class Relationships(ContractModel):
    nodes: list[RelationshipNode]
    edges: list[RelationshipEdge]
    story: dict[str, str] | None = None
    cross_shift_links: list[CrossShiftLink] = Field(default_factory=list, alias="crossShiftLinks")
    personal_paths: list[PersonalPath] = Field(default_factory=list, alias="personalPaths")


class Scenario(ContractModel):
    id: str
    label: Literal["base", "upside", "downside"]
    title: str
    summary: str
    horizon: Literal["7d", "30d", "90d"]
    confidence: Literal["low", "medium", "high"]
    triggers: list[str]
    indicators: list[str]
    invalidators: list[str]
    implications: list[str]
    evidence_ids: list[str] = Field(alias="evidenceIds")
    evidence_class: Literal["inferred"] = Field(default="inferred", alias="evidenceClass")


class WhatHappensNext(ContractModel):
    generated_at: str = Field(alias="generatedAt")
    evidence_cutoff: str = Field(alias="evidenceCutoff")
    model: str
    prompt_version: str = Field(alias="promptVersion")
    framing: str
    scenarios: list[Scenario]
    resolution_status: Literal["open", "resolved", "expired"] = Field(default="open", alias="resolutionStatus")


class Impact(ContractModel):
    summary: str
    direct_impacts: list[ImpactItem] = Field(alias="directImpacts")
    impact_chain: list[ImpactItem] = Field(alias="impactChain")
    second_order_effects: list[ImpactItem] = Field(alias="secondOrderEffects")
    opportunities: list[ImpactItem]
    risks: list[ImpactItem]
    watch_items: list[ImpactItem] = Field(alias="watchItems")


class DomainEntity(ContractModel):
    id: str
    name: str
    type: str
    direction: str | None = None
    magnitude: str | None = None
    summary: str
    evidence_ids: list[str] = Field(alias="evidenceIds")


class DomainGroup(ContractModel):
    id: str
    title: str
    entity_type: str = Field(default="domain", alias="entityType")
    items: list[DomainEntity]

    @field_validator("entity_type", mode="before")
    @classmethod
    def default_entity_type(cls, value):
        # Older snapshots and some AI responses used null. The FE contract
        # treats this as an optional string, so normalize null at the API edge.
        return value or "domain"


class PersonaContent(ContractModel):
    impact: Impact
    domain: dict[str, list[DomainGroup]]


class ShiftOverview(ContractModel):
    id: str
    title: str
    summary: str
    status: str
    direction: str
    signal_strength: float = Field(alias="signalStrength")
    updated_at: str = Field(alias="updatedAt")
    overview: Overview
    related_shifts: list[WorldShiftListItem] = Field(alias="relatedShifts")


class WorldShiftSnapshot(SnapshotMeta):
    schema_version: str = Field(default="2.0", alias="schemaVersion")
    persona: str
    shift: ShiftOverview
    content: PersonaContent
    relationships: Relationships
    evidence: list[Evidence]
    what_happens_next: WhatHappensNext = Field(alias="whatHappensNext")

    @model_validator(mode="before")
    @classmethod
    def upgrade_v1_snapshot(cls, value):
        """Keep already-published immutable v1 snapshots readable during v2 rollout."""
        if isinstance(value, dict) and "whatHappensNext" not in value and "what_happens_next" not in value:
            generated = value.get("generatedAt") or value.get("generated_at") or datetime.now(timezone.utc).isoformat()
            shift = value.get("shift") or {}
            value = {**value, "schemaVersion": "1.0-upgraded", "whatHappensNext": {
                "generatedAt": generated,
                "evidenceCutoff": shift.get("updatedAt") or generated,
                "model": "legacy-snapshot",
                "promptVersion": "world-shift-v1",
                "framing": "No scenarios were stored for this legacy snapshot. Refresh to generate v2 scenarios.",
                "scenarios": [],
                "resolutionStatus": "expired",
            }}
        return value


class WorldShiftListResponse(SnapshotMeta):
    entries: list[WorldShiftListItem]


class RelationshipsResponse(SnapshotMeta):
    relationships: Relationships


class EvidenceResponse(SnapshotMeta):
    evidence: list[Evidence]


class AIEvent(ContractModel):
    event_id: str = Field(alias="eventId")
    title: str
    summary: str
    evidence_ids: list[str] = Field(alias="evidenceIds", min_length=1)
    entity_ids: list[str] = Field(alias="entityIds")
    evidence_class: Literal["observed", "calculated", "inferred", "associated"] = Field(alias="evidenceClass")


class AIClaim(ContractModel):
    claim_id: str = Field(alias="claimId")
    text: str
    evidence_ids: list[str] = Field(alias="evidenceIds", min_length=1)
    entity_ids: list[str] = Field(alias="entityIds")
    evidence_class: Literal["observed", "calculated", "inferred", "associated"] = Field(alias="evidenceClass")


class AIEntity(ContractModel):
    entity_id: str = Field(alias="entityId")
    name: str
    normalized_name: str = Field(alias="normalizedName")
    entity_type: str = Field(alias="entityType")
    evidence_ids: list[str] = Field(alias="evidenceIds", min_length=1)


class AIRelationship(ContractModel):
    relationship_id: str = Field(alias="relationshipId")
    source_entity_id: str = Field(alias="sourceEntityId")
    target_entity_id: str = Field(alias="targetEntityId")
    relationship_type: Literal[
        "MENTIONED_WITH", "REGULATES", "INVESTS_IN", "FUNDS", "OPERATES", "SUPPLIES",
        "DEPENDS_ON", "COMPETES_WITH", "PART_OF", "ASSOCIATED_WITH"
    ] = Field(alias="relationshipType")
    label: str
    evidence_class: Literal["observed", "calculated", "inferred", "associated"] = Field(alias="evidenceClass")
    evidence_ids: list[str] = Field(alias="evidenceIds", min_length=1)
    claim_ids: list[str] = Field(default_factory=list, alias="claimIds")


class SemanticExtraction(ContractModel):
    events: list[AIEvent]
    claims: list[AIClaim]
    entities: list[AIEntity]
    relationships: list[AIRelationship]


class WorldShiftSynthesis(ContractModel):
    summary: str
    whats_happening: list[IntelligencePoint] = Field(alias="whatsHappening")
    why_it_matters: list[IntelligencePoint] = Field(alias="whyItMatters")
    key_developments: list[IntelligencePoint] = Field(alias="keyDevelopments")
    key_themes: list[str] = Field(alias="keyThemes")
    watch_next: list[IntelligencePoint] = Field(alias="watchNext")
    quick_take: str = Field(alias="quickTake")
    relationship_story: dict[str, str] = Field(alias="relationshipStory")
    drivers: list[IntelligencePoint] = Field(default_factory=list)
    contradictions: list[IntelligencePoint] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)


class PersonaSynthesis(ContractModel):
    summary: str
    direct_impacts: list[ImpactItem] = Field(alias="directImpacts")
    impact_chain: list[ImpactItem] = Field(default_factory=list, alias="impactChain")
    second_order_effects: list[ImpactItem] = Field(default_factory=list, alias="secondOrderEffects")
    risks: list[ImpactItem]
    opportunities: list[ImpactItem]
    watch_items: list[ImpactItem] = Field(alias="watchItems")
    domain_groups: list[DomainGroup] = Field(alias="domainGroups")


class RefreshProgress(ContractModel):
    completed: int
    total: int


class RefreshStatus(ContractModel):
    run_id: str = Field(alias="runId")
    status: Literal["queued", "running", "completed", "failed"]
    stage: str
    progress: RefreshProgress
    current_snapshot_id: str | None = Field(default=None, alias="currentSnapshotId")
    new_snapshot_id: str | None = Field(default=None, alias="newSnapshotId")
    error: str | None = None


class RefreshConfiguration(ContractModel):
    interval_seconds: int = Field(alias="intervalSeconds", ge=300, le=604800)
    web_research_enabled: bool = Field(alias="webResearchEnabled")
    web_results_per_shift: int = Field(alias="webResultsPerShift", ge=0, le=8)
    allowed_intervals: list[int] = Field(alias="allowedIntervals")
    next_refresh_at: str | None = Field(default=None, alias="nextRefreshAt")


class RefreshConfigurationUpdate(ContractModel):
    interval_seconds: int = Field(alias="intervalSeconds", ge=300, le=604800)
    web_research_enabled: bool = Field(alias="webResearchEnabled")
    web_results_per_shift: int = Field(default=3, alias="webResultsPerShift", ge=0, le=8)
