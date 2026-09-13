/**
 * The ONE place in the frontend that knows the WorldTune backend's JSON shape.
 *
 * Every interface below was written by hand against a live
 * `GET /api/dashboard` response from the FastAPI backend (model
 * worldtune-v0.1.0, DEMO_MODE on). Components consume these types; no component
 * calls fetch() directly and nothing outside this file uses `any`.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8090";

/* ------------------------------------------------------------------ persona */

export interface PersonaLocation {
  city: string;
  country: string;
  timezone: string;
}

export interface CareerProfile {
  current_role: string;
  years_experience: number;
  target_roles: string[];
  skills: string[];
  industry: string;
}

export type RiskAppetite = "low" | "medium" | "high";
export type ContentDepth = "skim" | "balanced" | "deep";

export interface FinancialProfile {
  asset_classes: string[];
  watchlist: string[];
  sectors: string[];
  risk_appetite: RiskAppetite;
}

export interface Preferences {
  learning_topics: string[];
  content_depth: ContentDepth;
  daily_time_budget_minutes: number;
}

/** Body of `PUT /api/persona` — a whole-document replace of editable fields. */
export interface PersonaUpdate {
  name: string;
  location: PersonaLocation;
  career: CareerProfile;
  financial: FinancialProfile;
  preferences: Preferences;
}

export interface Persona extends PersonaUpdate {
  id: string;
  user_id: string;
  created_at: string | null;
  updated_at: string | null;
}

/* ------------------------------------------------------------- score / signal */

export interface ScoreComponent {
  value: number;
  weight: number;
  contribution: number;
  /** Present on persona_relevance only; keys differ per entity type. */
  sub_scores?: Record<string, number>;
}

export type ScoreComponentKey =
  | "persona_relevance"
  | "trend_momentum"
  | "evidence_strength"
  | "novelty"
  | "recency"
  | "prediction_confidence";

export type ScoreComponents = Partial<Record<ScoreComponentKey, ScoreComponent>>;

export interface Evidence {
  type: string; // "price" | "trend" | "news" | "job" | "technology" | ...
  source: string;
  detail: string;
  url?: string;
  observed_at: string;
  sentiment?: number;
}

export interface ScoreBreakdown {
  score: number;
  components: ScoreComponents;
  evidence: Evidence[];
  reasons?: string[];
  formula: string;
}

export type TrajectoryDirection =
  | "bullish"
  | "bearish"
  | "neutral"
  | "growing"
  | "stable"
  | "declining";

export interface Trajectory {
  direction: TrajectoryDirection;
  probability: number;
  confidence: number;
  horizon_days: number;
  rationale: string;
  features?: Record<string, number>;
}

export type HorizonKey = "7d" | "30d" | "90d";
export type TrajectoryByHorizon = Partial<Record<HorizonKey, Trajectory>>;

export interface Explanation {
  summary: string;
  why_it_matters: string;
  drivers: string[];
  risks: string[];
  recommended_action: string;
  generated_by: string;
}

interface SignalBase {
  entity_id: string;
  label: string;
  worldtune_score: number;
  score_breakdown: ScoreBreakdown;
  top_contributors: string[];
  evidence: Evidence[];
  trajectory?: Trajectory | null;
  trajectory_by_horizon?: TrajectoryByHorizon | null;
  explanation?: Explanation | null;
  metrics?: Record<string, number | string | undefined> | null;
}

export interface AssetMetrics {
  price?: number;
  change_24h?: number;
  change_7d?: number;
  change_30d?: number;
  momentum?: number;
  volume_zscore?: number;
  realized_volatility?: number;
  news_count?: number;
  news_sentiment?: number;
  direction?: string;
  probability?: number;
  confidence?: number;
  horizon_days?: number;
  [key: string]: number | string | undefined;
}

export interface AssetSignal extends SignalBase {
  entity_type: "asset";
  asset_class: string;
  sector: string;
  metrics: AssetMetrics;
}

export interface SkillMetrics {
  skill_mentions?: number;
  job_count?: number;
  skill_share?: number;
  change_7d?: number;
  change_30d?: number;
  acceleration?: number;
  zscore?: number;
  tech_velocity?: number;
  direction?: string;
  probability?: number;
  confidence?: number;
  [key: string]: number | string | undefined;
}

export interface SkillSignal extends SignalBase {
  entity_type: "skill";
  category: string;
  already_have: boolean;
  metrics: SkillMetrics;
}

export interface JobSignal extends SignalBase {
  entity_type: "job";
  company: string;
  location: string;
  remote: boolean;
  seniority: string;
  role_family: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  url: string;
  posted_at: string;
  matched_skills: string[];
}

export type AnySignal = AssetSignal | SkillSignal | JobSignal;

/* ---------------------------------------------------------------- dashboard */

export type DailyTuneKind = "learn" | "apply" | "watch" | "read";

export interface DailyTuneItem {
  kind: DailyTuneKind;
  title: string;
  detail: string;
  why: string;
  entity_type: string;
  entity_id: string;
  url: string;
  score: number;
}

export interface DashboardSummary {
  headline: string;
  top_score: number;
  assets_tracked: number;
  assets_moving: number;
  skills_tracked: number;
  skills_rising: number;
  skills_cooling: number;
  job_matches: number;
  persona_name: string;
  location: string;
}

export interface Dashboard {
  persona: Persona;
  summary: DashboardSummary;
  financial_pulse: AssetSignal[];
  career_pulse: {
    skill_signals: SkillSignal[];
    job_matches: JobSignal[];
  };
  daily_tune: DailyTuneItem[];
  generated_at: string;
  model_version: string;
  demo_mode: boolean;
  disclaimer: string;
}

export interface DataSourceStatus {
  mode?: string;
  live?: boolean;
  [key: string]: unknown;
}

/* ------------------------------------------------------------------ client */

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Cannot reach the WorldTune API at ${API_BASE_URL}. Is the backend running?`,
      0,
    );
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body — keep the status text */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  dashboard: (limit = 6) => request<Dashboard>(`/api/dashboard?limit=${limit}`),
  persona: () => request<Persona>("/api/persona"),
  updatePersona: (body: PersonaUpdate) =>
    request<Persona>("/api/persona", { method: "PUT", body: JSON.stringify(body) }),
  /** Real per-asset detail endpoint: GET /api/financial/assets/{symbol}. */
  asset: (symbol: string) =>
    request<AssetSignal>(`/api/financial/assets/${encodeURIComponent(symbol)}`),
  /** Real per-skill detail endpoint: GET /api/career/skills/{skill_id}. */
  skill: (skillId: string) =>
    request<SkillSignal>(`/api/career/skills/${encodeURIComponent(skillId)}`),
  dataSources: () => request<Record<string, DataSourceStatus>>("/api/system/data-sources"),
};

/* ------------------------------------------------------------ query helpers */

export const queryKeys = {
  dashboard: ["dashboard"] as const,
  persona: ["persona"] as const,
  asset: (symbol: string) => ["asset", symbol] as const,
  skill: (id: string) => ["skill", id] as const,
};
