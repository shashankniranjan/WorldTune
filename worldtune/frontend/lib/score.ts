/**
 * Frontend-only convenience: map the backend's 0-100 `worldtune_score` to a
 * state label. The backend does NOT return a state field — thresholds are
 * calibrated against real demo scores (observed range ~42-68, top score 68.1),
 * so they spread the demo data across the band instead of parking everything
 * in "COLD".
 */
import type {
  AnySignal,
  ScoreComponentKey,
  TrajectoryDirection,
} from "./api";

export type SignalState = "VERY HOT" | "HOT" | "NEUTRAL" | "COOLING" | "COLD";

export const STATE_THRESHOLDS: { min: number; state: SignalState }[] = [
  { min: 65, state: "VERY HOT" },
  { min: 55, state: "HOT" },
  { min: 45, state: "NEUTRAL" },
  { min: 35, state: "COOLING" },
  { min: -Infinity, state: "COLD" },
];

export function scoreState(score: number): SignalState {
  return (
    STATE_THRESHOLDS.find((t) => score >= t.min)?.state ?? "COLD"
  );
}

export function isHeating(score: number): boolean {
  const s = scoreState(score);
  return s === "HOT" || s === "VERY HOT";
}

export function isCooling(score: number): boolean {
  const s = scoreState(score);
  return s === "COOLING" || s === "COLD";
}

/** Tailwind classes per state. Warm = hot, cool blue = cooling, muted = neutral. */
export const STATE_CLASSES: Record<SignalState, string> = {
  "VERY HOT": "border-amber-400/40 bg-amber-400/10 text-amber-300",
  HOT: "border-orange-400/35 bg-orange-400/10 text-orange-300",
  NEUTRAL: "border-slate-500/40 bg-slate-500/10 text-slate-300",
  COOLING: "border-sky-500/35 bg-sky-500/10 text-sky-300",
  COLD: "border-blue-500/30 bg-blue-500/10 text-blue-300",
};

/** The score number itself: teal accent, warmed when the signal is hot. */
export const STATE_SCORE_CLASSES: Record<SignalState, string> = {
  "VERY HOT": "text-amber-300",
  HOT: "text-orange-300",
  NEUTRAL: "text-teal-300",
  COOLING: "text-sky-300",
  COLD: "text-slate-400",
};

/** Red is reserved for genuinely bearish/declining reads — never for "exciting". */
export function directionClasses(direction?: TrajectoryDirection | string) {
  switch (direction) {
    case "bullish":
    case "growing":
      return "border-emerald-500/35 bg-emerald-500/10 text-emerald-300";
    case "bearish":
    case "declining":
      return "border-red-500/40 bg-red-500/10 text-red-300";
    default:
      return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }
}

export const COMPONENT_LABELS: Record<ScoreComponentKey, string> = {
  persona_relevance: "PersonaRelevance",
  trend_momentum: "TrendMomentum",
  evidence_strength: "EvidenceStrength",
  novelty: "Novelty",
  recency: "Recency",
  prediction_confidence: "PredictionConfidence",
};

export const COMPONENT_ORDER: ScoreComponentKey[] = [
  "persona_relevance",
  "trend_momentum",
  "evidence_strength",
  "novelty",
  "recency",
  "prediction_confidence",
];

/** Distinct hues for the stacked contribution bar (kept off the state palette). */
export const COMPONENT_COLORS: Record<ScoreComponentKey, string> = {
  persona_relevance: "#2dd4bf",
  trend_momentum: "#818cf8",
  evidence_strength: "#38bdf8",
  novelty: "#f0abfc",
  recency: "#fbbf24",
  prediction_confidence: "#94a3b8",
};

export function signalHref(signal: Pick<AnySignal, "entity_type" | "entity_id">) {
  return `/signal/${signal.entity_type}/${encodeURIComponent(signal.entity_id)}`;
}

export function subScoreLabel(key: string) {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
