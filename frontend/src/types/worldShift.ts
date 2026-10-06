export type PersonaId = "tech" | "finance" | (string & {});
export type SemanticTab = "overview" | "impact" | "domain" | "relationships" | "forecast" | "evidence";
export type Direction = "positive" | "negative" | "up" | "down" | "mixed" | "neutral" | "uncertain";
export type ShiftStatus = "surging" | "rising" | "changing" | "watching" | "stable" | "declining" | "elevated";
export type Magnitude = "low" | "moderate" | "medium" | "high" | "critical" | "significant";
export type Confidence = "low" | "medium" | "high";

export interface SnapshotMeta { snapshotId: string; generatedAt: string; validUntil: string }
// "reasoned" = an explicit, labelled inference connecting an observed event
// to a plausible consequence using world knowledge (e.g. which companies may
// be exposed). It is never corpus-grounded the way the other four classes
// are, and the UI MUST render it with a visibly distinct treatment.
export type EvidenceClass = "observed" | "calculated" | "inferred" | "associated" | "reasoned";
export interface IntelligencePoint { text: string; evidenceClass: EvidenceClass; evidenceIds: string[]; claimIds: string[] }
export interface ContextBrief { whatItIs: string; howItStarted: string; latest: string; whatItIsEvidenceIds?: string[]; howItStartedEvidenceIds?: string[]; latestEvidenceIds?: string[] }
export interface TimelineEvent { date: string; title: string; summary: string; status: "confirmed" | "reported" | "claimed" | "disputed"; evidenceIds: string[] }
export interface ActorBrief { name: string; role: string; position: string; status: "confirmed" | "reported" | "claimed" | "disputed"; evidenceIds: string[] }
export interface FactFigure { value: string; label: string; context: string; evidenceIds: string[] }
export interface Evidence { id: string; type: string; source: string; title: string; summary?: string; publishedAt: string; url: string; imageUrl?: string | null; entities: string[]; tags: string[]; relationshipRole?: string; confidence: Confidence; supports: string[]; sourceDomain?: string | null; originalHeadline?: string | null; sourceSnippet?: string | null; aiSummary?: string | null; eventIds?: string[]; claimIds?: string[]; entityIds?: string[]; evidenceClass?: EvidenceClass; sourceClass: "primary" | "secondary" | "aggregator" | "unknown"; retrievalStatus: "complete" | "metadata_only" | "unavailable"; publisherFamily?: string | null; independentPublisherCount: number; corroborationStatus: "single_source" | "syndicated" | "independently_corroborated" | "contested" }
export interface Overview { whatHappened: string; whyItMatters: string; quickTake?: string; characteristics: string[]; themes: string[]; whatsHappening?: IntelligencePoint[]; whyItMattersPoints?: IntelligencePoint[]; keyDevelopments?: IntelligencePoint[]; watchNext?: IntelligencePoint[]; drivers?: IntelligencePoint[]; contradictions?: IntelligencePoint[]; contextBrief?: ContextBrief | null; timeline?: TimelineEvent[]; actors?: ActorBrief[]; factsAndFigures?: FactFigure[]; timelineKicker?: string | null; timelineHeading?: string | null }
export interface ImpactItem { id: string; title: string; summary: string; direction?: Direction | null; magnitude?: Magnitude | null; evidenceIds: string[]; claimIds?: string[]; evidenceClass?: EvidenceClass; mechanism?: string | null; horizon?: "immediate" | "7d" | "30d" | "90d" | "long_term" | null; confidence?: Confidence; counterEvidenceIds?: string[]; invalidators?: string[]; reasoning?: string[]; derivedFrom?: string[]; verificationHint?: string | null }
// A reasoned company-level exposure: the answer to "which companies get
// impacted, and how". entityName is frequently NOT in the evidence corpus --
// that is the point, not a grounding failure. Always render as inference,
// never as a recommendation.
export interface ExposureItem { id: string; entityName: string; ticker?: string | null; direction: "positive" | "negative" | "mixed"; ring: "direct" | "supply_chain" | "second_order"; mechanism: string; reasoning: string[]; confidence: Confidence; derivedFrom: string[]; verificationHint?: string | null; horizons: Array<"near_term" | "long_term">; countries: string[]; opportunityType?: string | null; evidenceIds: string[]; evidenceClass: "reasoned" }
export interface Impact { summary: string; directImpacts: ImpactItem[]; impactChain: ImpactItem[]; secondOrderEffects: ImpactItem[]; opportunities: ImpactItem[]; risks: ImpactItem[]; watchItems: ImpactItem[]; exposureMap?: ExposureItem[]; kicker?: string | null; headline?: string | null; exposureHeadline?: string | null; exposureBlurb?: string | null; lensTitle?: string | null; lensBlurb?: string | null }
export interface DomainEntity { id: string; name: string; type: string; direction?: Direction | null; magnitude?: Magnitude | null; summary: string; evidenceIds: string[] }
export interface DomainGroup { id: string; title: string; entityType?: string; items: DomainEntity[] }
export interface RelationshipNode { id: string; label: string; type: string; category?: string | null; summary?: string | null; direction?: Direction | null; magnitude?: Magnitude | null; evidenceIds: string[] }
export interface RelationshipEdge { id: string; source: string; target: string; relationship: string; category?: string | null; explanation?: string | null; confidence: Confidence; evidenceIds: string[]; claimIds?: string[]; evidenceClass?: EvidenceClass; mechanism?: string | null; temporalOrder?: string | null; opposingEvidenceIds?: string[]; alternativeExplanations?: string[]; firstObservedAt?: string | null; lastUpdatedAt?: string | null }
export interface CrossShiftLink { shiftId: string; title: string; relationship: string; explanation: string; confidence: Confidence; evidenceClass: "inferred" | "associated"; evidenceIds: string[]; indicators: string[] }
export interface PersonalPath { id: string; title: string; persona: string; steps: string[]; explanation: string; confidence: Confidence; evidenceIds: string[] }
export interface Relationships { nodes: RelationshipNode[]; edges: RelationshipEdge[]; story?: Record<string, string | null>; crossShiftLinks: CrossShiftLink[]; personalPaths: PersonalPath[] }
export interface Scenario { id: string; label: "base" | "upside" | "downside"; title: string; summary: string; horizon: "7d" | "30d" | "90d"; confidence: Confidence; triggers: string[]; indicators: string[]; invalidators: string[]; implications: string[]; evidenceIds: string[]; evidenceClass: "inferred" }
export interface WhatHappensNext { generatedAt: string; evidenceCutoff: string; model: string; promptVersion: string; framing: string; scenarios: Scenario[]; resolutionStatus: "open" | "resolved" | "expired" }
export interface PersonaContent { impact: Impact; domain: { groups: DomainGroup[] } }
export interface WorldShiftListItem { id: string; title: string; rank: number; status: ShiftStatus; direction: Direction; relationshipReason?: string | null; relationshipConfidence?: Confidence | null; isTrending?: boolean }
export interface WorldShiftListResponse extends SnapshotMeta { entries: WorldShiftListItem[] }
export interface RelationshipsResponse extends SnapshotMeta { relationships: Relationships }
export interface EvidenceResponse extends SnapshotMeta { evidence: Evidence[] }
export interface WorldShiftSnapshot extends SnapshotMeta { schemaVersion: string; shift: { id: string; title: string; summary: string; status: ShiftStatus; direction: Direction; signalStrength: number; updatedAt: string; overview: Overview; relatedShifts: WorldShiftListItem[]; isTrending?: boolean }; persona: PersonaId; content: PersonaContent; relationships: Relationships; evidence: Evidence[]; whatHappensNext: WhatHappensNext }
export type RefreshStage = "fetching_gdelt" | "normalizing" | "calculating_signals" | "building_evidence" | "researching_web" | "extracting_semantics" | "generating_overview" | "generating_finance" | "generating_tech" | "validating" | "publishing" | "complete" | "failed";
export interface RefreshStatus { runId: string; status: "queued" | "running" | "completed" | "failed"; stage: RefreshStage | string; progress: { completed: number; total: number }; currentSnapshotId?: string | null; newSnapshotId?: string | null; error?: string | null }
export interface RefreshConfiguration { intervalSeconds: number; webResearchEnabled: boolean; webResultsPerShift: number; allowedIntervals: number[]; nextRefreshAt?: string | null }
