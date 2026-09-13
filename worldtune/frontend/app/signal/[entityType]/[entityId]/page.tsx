"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  api,
  queryKeys,
  type AnySignal,
  type AssetSignal,
  type Dashboard,
  type Evidence,
  type HorizonKey,
  type JobSignal,
  type SkillSignal,
  type Trajectory,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/states";
import { DirectionBadge, ScoreNumber, StateBadge } from "@/components/state-badge";
import { ScoreBreakdownPanel } from "@/components/score-breakdown";
import { TrendChart, type TrendPoint } from "@/components/trend-chart";
import { num, pct, relativeTime, salary } from "@/lib/format";
import { scoreState, signalHref } from "@/lib/score";

export default function SignalDetailPage() {
  const params = useParams<{ entityType: string; entityId: string }>();
  const entityType = params?.entityType ?? "";
  const entityId = decodeURIComponent(params?.entityId ?? "");

  const dashboard = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => api.dashboard(),
  });

  /* Real per-entity endpoints exist for assets and skills; jobs have none, so
     the job view is built from the (already cached) dashboard payload. */
  const asset = useQuery({
    queryKey: queryKeys.asset(entityId),
    queryFn: () => api.asset(entityId),
    enabled: entityType === "asset" && Boolean(entityId),
  });
  const skill = useQuery({
    queryKey: queryKeys.skill(entityId),
    queryFn: () => api.skill(entityId),
    enabled: entityType === "skill" && Boolean(entityId),
  });

  const fromDashboard = findInDashboard(dashboard.data, entityType, entityId);
  const signal: AnySignal | undefined =
    (entityType === "asset" ? asset.data : entityType === "skill" ? skill.data : undefined) ??
    fromDashboard;

  const isPending =
    dashboard.isPending ||
    (entityType === "asset" && asset.isPending) ||
    (entityType === "skill" && skill.isPending);

  const error =
    (dashboard.error as Error | null) ??
    (entityType === "asset" ? (asset.error as Error | null) : null) ??
    (entityType === "skill" ? (skill.error as Error | null) : null);

  if (isPending) {
    return (
      <div className="space-y-6 pt-10">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error && !signal) {
    return (
      <div className="pt-10">
        <ErrorState
          title="Could not load this signal"
          message={error.message}
          onRetry={() => {
            dashboard.refetch();
            if (entityType === "asset") asset.refetch();
            if (entityType === "skill") skill.refetch();
          }}
        />
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="pt-10">
        <EmptyState
          message={`No signal found for ${entityType}/${entityId} in the current dashboard window.`}
        />
        <Link href="/" className="mt-4 inline-block text-sm text-accent hover:underline">
          ← Back to today
        </Link>
      </div>
    );
  }

  return (
    <SignalDetail signal={signal} dashboard={dashboard.data} />
  );
}

function SignalDetail({
  signal,
  dashboard,
}: {
  signal: AnySignal;
  dashboard?: Dashboard;
}) {
  const news = signal.evidence.filter((e) => e.type === "news");
  const nonNews = signal.evidence.filter((e) => e.type !== "news");
  const related = relatedSignals(dashboard, signal);
  const trend = buildTrend(signal);
  const horizons = horizonList(signal);

  return (
    <div className="pt-8">
      <Link href="/" className="text-sm text-accent hover:underline">
        ← Back to today
      </Link>

      {/* ---------------------------------------------------- Overview */}
      <header className="mt-6 flex flex-wrap items-start justify-between gap-6 border-b border-hairline pb-8">
        <div className="min-w-0">
          <p className="eyebrow">{overviewEyebrow(signal)}</p>
          <h1 className="display mt-2 text-4xl font-bold tracking-tight">{signal.label}</h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
            {signal.explanation?.summary ?? overviewFallback(signal)}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <StateBadge score={signal.worldtune_score} />
            <DirectionBadge direction={signal.trajectory?.direction} />
            {signal.top_contributors.map((c) => (
              <Badge key={c}>{c}</Badge>
            ))}
          </div>
        </div>
        <div className="text-right">
          <p className="eyebrow">WorldTune score</p>
          <ScoreNumber score={signal.worldtune_score} size="lg" className="mt-2 block" />
          <p className="mt-2 text-xs text-dim">{scoreState(signal.worldtune_score)}</p>
        </div>
      </header>

      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-10">
          {/* ------------------------------------- Why it matters to you */}
          <Section title="Why it matters to you">
            <Card>
              <CardContent className="pt-5">
                <p className="text-base leading-relaxed">
                  {signal.explanation?.why_it_matters ?? whyFallback(signal)}
                </p>
                {signal.explanation && signal.explanation.drivers.length > 0 ? (
                  <>
                    <p className="eyebrow mt-6">Drivers</p>
                    <ul className="mt-2 space-y-1 text-sm text-muted">
                      {signal.explanation.drivers.map((d) => (
                        <li key={d}>· {d}</li>
                      ))}
                    </ul>
                  </>
                ) : null}
              </CardContent>
            </Card>
          </Section>

          {/* ------------------------------------------ Score breakdown */}
          <Section title="How this score was built">
            <Card>
              <CardContent className="pt-5">
                <ScoreBreakdownPanel breakdown={signal.score_breakdown} />
              </CardContent>
            </Card>
          </Section>

          {/* ------------------------------------------------- Evidence */}
          <Section title="Evidence">
            {nonNews.length === 0 ? (
              <EmptyState message="No non-news evidence recorded." />
            ) : (
              <Card>
                <CardContent className="pt-5">
                  <ul className="divide-y divide-hairline">
                    {nonNews.map((e, i) => (
                      <EvidenceRow key={`${e.type}-${i}`} evidence={e} />
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </Section>

          {/* --------------------------------------------- Trend history */}
          <Section title="Trend history">
            <Card>
              <CardContent className="pt-5">
                {trend ? (
                  <TrendChart points={trend.points} note={trend.note} unit={trend.unit} />
                ) : (
                  <p className="text-sm text-dim">
                    This entity type carries no change metrics in the API payload, so no
                    trend line can be drawn honestly.
                  </p>
                )}
              </CardContent>
            </Card>
          </Section>

          {/* ------------------------------------------- Relevant news */}
          <Section title="Relevant news">
            {news.length === 0 ? (
              <EmptyState message="No related headlines in this window." />
            ) : (
              <Card>
                <CardContent className="pt-5">
                  <ul className="divide-y divide-hairline">
                    {news.map((e, i) => (
                      <EvidenceRow key={`news-${i}`} evidence={e} />
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </Section>
        </div>

        {/* ------------------------------------------------- Right rail */}
        <aside className="space-y-8">
          <Section title="Trajectory">
            {horizons.length === 0 ? (
              <EmptyState message="No trajectory computed for this entity." />
            ) : (
              <div className="space-y-3">
                {horizons.map(([key, t]) => (
                  <Card key={key}>
                    <CardContent className="pt-4">
                      <div className="flex items-center justify-between">
                        <span className="eyebrow">{key}</span>
                        <DirectionBadge direction={t.direction} />
                      </div>
                      <p className="tabular display mt-3 text-3xl font-bold">
                        {(t.probability * 100).toFixed(0)}%
                      </p>
                      <p className="mt-1 text-xs text-dim">
                        probability · confidence{" "}
                        <span className="tabular">{t.confidence.toFixed(2)}</span>
                      </p>
                      <p className="mt-3 text-xs leading-relaxed text-muted">
                        {t.rationale}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </Section>

          <Section title="Confidence">
            <Card>
              <CardContent className="pt-4">
                {signal.trajectory ? (
                  <>
                    <div className="flex items-baseline justify-between">
                      <span className="text-sm text-muted">Model confidence</span>
                      <span className="tabular display text-xl font-bold text-accent">
                        {signal.trajectory.confidence.toFixed(2)}
                      </span>
                    </div>
                    <span className="mt-3 block h-1.5 overflow-hidden rounded-full bg-elevated">
                      <span
                        className="block h-full rounded-full bg-accent"
                        style={{
                          width: `${Math.min(1, Math.max(0, signal.trajectory.confidence)) * 100}%`,
                        }}
                      />
                    </span>
                  </>
                ) : (
                  <p className="text-sm text-dim">No confidence estimate for this entity.</p>
                )}
                {signal.score_breakdown.components.prediction_confidence ? (
                  <p className="mt-4 text-xs leading-relaxed text-dim">
                    PredictionConfidence contributes{" "}
                    <span className="tabular">
                      {signal.score_breakdown.components.prediction_confidence.contribution.toFixed(
                        2,
                      )}
                    </span>{" "}
                    points to the score.
                  </p>
                ) : null}
              </CardContent>
            </Card>
          </Section>

          <Section title="Risks">
            {signal.explanation && signal.explanation.risks.length > 0 ? (
              <Card className="border-red-500/25">
                <CardContent className="pt-4">
                  <ul className="space-y-2 text-sm leading-relaxed text-muted">
                    {signal.explanation.risks.map((r) => (
                      <li key={r} className="flex gap-2">
                        <span className="text-red-400">·</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ) : (
              <EmptyState message="No risks listed for this signal." />
            )}
          </Section>

          <Section title="Recommended action">
            <Card className="border-accent/30 bg-accent/5">
              <CardContent className="pt-4">
                <p className="text-sm leading-relaxed">
                  {signal.explanation?.recommended_action ??
                    "No templated action for this entity type — use the evidence above as one input."}
                </p>
                {signal.entity_type === "job" && signal.url ? (
                  <a
                    href={signal.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="display mt-4 inline-block text-xs font-semibold text-accent hover:underline"
                  >
                    Open posting →
                  </a>
                ) : null}
              </CardContent>
            </Card>
          </Section>

          <Section title="Related signals">
            {related.length === 0 ? (
              <EmptyState message="Nothing else shares this sector or category today." />
            ) : (
              <ul className="space-y-2">
                {related.map((r) => (
                  <li key={`${r.entity_type}-${r.entity_id}`}>
                    <Link
                      href={signalHref(r)}
                      className="flex items-center justify-between rounded border border-hairline bg-panel px-3 py-2 text-sm transition-colors hover:border-hairline-strong"
                    >
                      <span className="truncate">{r.label}</span>
                      <span className="tabular display ml-3 font-semibold text-accent">
                        {r.worldtune_score.toFixed(1)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          {signal.entity_type === "job" ? <JobFacts signal={signal} /> : null}
          {signal.entity_type === "asset" ? <AssetFacts signal={signal} /> : null}
          {signal.entity_type === "skill" ? <SkillFacts signal={signal} /> : null}
        </aside>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- fragments */

function EvidenceRow({ evidence }: { evidence: Evidence }) {
  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{evidence.type}</Badge>
        <span className="text-xs text-dim">{evidence.source}</span>
        <span className="text-xs text-dim">· {relativeTime(evidence.observed_at)}</span>
        {evidence.sentiment !== undefined ? (
          <span className="tabular text-xs text-dim">
            · sentiment {evidence.sentiment.toFixed(2)}
          </span>
        ) : null}
      </div>
      <p className="mt-1.5 text-sm leading-snug">{evidence.detail}</p>
      {evidence.url ? (
        <a
          href={evidence.url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-1 inline-block text-xs text-accent hover:underline"
        >
          {hostname(evidence.url)} →
        </a>
      ) : null}
    </li>
  );
}

function hostname(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return "source";
  }
}

function Facts({ rows }: { rows: [string, string][] }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <dl className="space-y-2 text-sm">
          {rows.map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between gap-3">
              <dt className="text-muted">{k}</dt>
              <dd className="tabular text-right">{v}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function AssetFacts({ signal }: { signal: AssetSignal }) {
  const m = signal.metrics ?? {};
  return (
    <Section title="Market facts">
      <Facts
        rows={[
          ["Price", num(m.price)],
          ["24h", pct(m.change_24h)],
          ["7d", pct(m.change_7d)],
          ["30d", pct(m.change_30d)],
          ["Volume z-score", num(m.volume_zscore)],
          ["Realized vol", pct(m.realized_volatility, 0)],
          ["Headlines", String(m.news_count ?? 0)],
          ["Asset class", signal.asset_class],
        ]}
      />
    </Section>
  );
}

function SkillFacts({ signal }: { signal: SkillSignal }) {
  const m = signal.metrics ?? {};
  return (
    <Section title="Demand facts">
      <Facts
        rows={[
          ["Postings mentioning", `${m.skill_mentions ?? 0} / ${m.job_count ?? 0}`],
          ["Share", pct(m.skill_share, 0)],
          ["7d", pct(m.change_7d, 1)],
          ["30d", pct(m.change_30d, 1)],
          ["Z-score", num(m.zscore)],
          ["Tech velocity", pct(m.tech_velocity, 1)],
          ["In your profile", signal.already_have ? "yes" : "no"],
          ["Category", signal.category],
        ]}
      />
    </Section>
  );
}

function JobFacts({ signal }: { signal: JobSignal }) {
  const pay = salary(signal.salary_min, signal.salary_max, signal.salary_currency);
  return (
    <Section title="Posting facts">
      <Facts
        rows={[
          ["Company", signal.company],
          ["Location", signal.location],
          ["Remote", signal.remote ? "yes" : "no"],
          ["Seniority", signal.seniority],
          ["Role family", signal.role_family],
          ["Salary", pay ?? "not disclosed"],
          ["Posted", relativeTime(signal.posted_at)],
          ["Matched skills", String(signal.matched_skills.length)],
        ]}
      />
    </Section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="display mb-3 text-sm font-bold tracking-[0.14em] uppercase text-dim">
        {title}
      </h2>
      {children}
    </section>
  );
}

/* ----------------------------------------------------------------- helpers */

function findInDashboard(
  data: Dashboard | undefined,
  entityType: string,
  entityId: string,
): AnySignal | undefined {
  if (!data) return undefined;
  const pool: AnySignal[] = [
    ...data.financial_pulse,
    ...data.career_pulse.skill_signals,
    ...data.career_pulse.job_matches,
  ];
  return pool.find((s) => s.entity_type === entityType && s.entity_id === entityId);
}

function relatedSignals(data: Dashboard | undefined, signal: AnySignal): AnySignal[] {
  if (!data) return [];
  const pool: AnySignal[] = [
    ...data.financial_pulse,
    ...data.career_pulse.skill_signals,
    ...data.career_pulse.job_matches,
  ];
  const key = groupKey(signal);
  return pool
    .filter((s) => !(s.entity_type === signal.entity_type && s.entity_id === signal.entity_id))
    .filter((s) => (key ? groupKey(s) === key : s.entity_type === signal.entity_type))
    .sort((a, b) => b.worldtune_score - a.worldtune_score)
    .slice(0, 5);
}

function groupKey(signal: AnySignal): string | null {
  if (signal.entity_type === "asset") return `sector:${signal.sector}`;
  if (signal.entity_type === "skill") return `category:${signal.category}`;
  return `role:${signal.role_family}`;
}

function horizonList(signal: AnySignal): [string, Trajectory][] {
  const byHorizon = signal.trajectory_by_horizon;
  if (byHorizon) {
    const keys: HorizonKey[] = ["7d", "30d", "90d"];
    const rows = keys
      .map((k) => [k, byHorizon[k]] as const)
      .filter((entry): entry is readonly [HorizonKey, Trajectory] => Boolean(entry[1]));
    if (rows.length > 0) return rows.map(([k, t]) => [k, t]);
  }
  if (signal.trajectory) {
    return [[`${signal.trajectory.horizon_days}d`, signal.trajectory]];
  }
  return [];
}

/**
 * The API exposes no historical series — only point-in-time change figures.
 * We reconstruct an indexed line by walking the known 30d / 7d / 24h changes
 * backwards from the current level, and say so under the chart.
 */
function buildTrend(
  signal: AnySignal,
): { points: TrendPoint[]; note: string; unit: string } | null {
  if (signal.entity_type === "asset") {
    const m = signal.metrics ?? {};
    const now = typeof m.price === "number" ? m.price : undefined;
    if (now === undefined) return null;
    const back = (change?: number) =>
      typeof change === "number" ? now / (1 + change) : undefined;
    const points: TrendPoint[] = [
      { label: "30d ago", value: back(m.change_30d) },
      { label: "7d ago", value: back(m.change_7d) },
      { label: "24h ago", value: back(m.change_24h) },
      { label: "now", value: now },
    ]
      .filter((p): p is TrendPoint => typeof p.value === "number")
      .map((p) => ({ ...p, value: Number(p.value.toFixed(2)) }));
    if (points.length < 2) return null;
    return {
      points,
      unit: "price",
      note: `Derived, not a full price history: the API returns no time series, so these ${points.length} points are back-computed from the current price and the reported 30d/7d/24h changes. Straight segments between anchors, not real intraday path.`,
    };
  }

  if (signal.entity_type === "skill") {
    const m = signal.metrics ?? {};
    const now = typeof m.skill_mentions === "number" ? m.skill_mentions : undefined;
    if (now === undefined) return null;
    const back = (change?: number) =>
      typeof change === "number" ? now / (1 + change) : undefined;
    const points: TrendPoint[] = [
      { label: "30d ago", value: back(m.change_30d) },
      { label: "7d ago", value: back(m.change_7d) },
      { label: "now", value: now },
    ]
      .filter((p): p is TrendPoint => typeof p.value === "number")
      .map((p) => ({ ...p, value: Number(p.value.toFixed(2)) }));
    if (points.length < 2) return null;
    return {
      points,
      unit: "postings",
      note: `Derived from the two known change figures (30d ${pct(m.change_30d, 1)}, 7d ${pct(m.change_7d, 1)}) and the current mention count — the payload contains no posting-count history, so treat this as a shape, not a measured series.`,
    };
  }

  return null;
}

function overviewEyebrow(signal: AnySignal): string {
  if (signal.entity_type === "asset") return `${signal.entity_id} · ${signal.asset_class}`;
  if (signal.entity_type === "skill") return `Skill · ${signal.category}`;
  return `${signal.company} · ${signal.role_family}`;
}

function overviewFallback(signal: AnySignal): string {
  if (signal.entity_type === "job") {
    return `${signal.label} at ${signal.company}, ${signal.location}${
      signal.remote ? " (remote)" : ""
    } — ${signal.matched_skills.length} of your skills appear in this posting.`;
  }
  return "No templated summary for this entity.";
}

function whyFallback(signal: AnySignal): string {
  if (signal.entity_type === "job") {
    const pr = signal.score_breakdown.components.persona_relevance?.sub_scores;
    const bits: string[] = [];
    if (pr?.skill_overlap !== undefined)
      bits.push(`skill overlap ${(pr.skill_overlap * 100).toFixed(0)}%`);
    if (pr?.role_overlap !== undefined)
      bits.push(`role overlap ${(pr.role_overlap * 100).toFixed(0)}%`);
    if (pr?.location_relevance !== undefined)
      bits.push(`location relevance ${(pr.location_relevance * 100).toFixed(0)}%`);
    if (pr?.seniority_match !== undefined)
      bits.push(`seniority match ${(pr.seniority_match * 100).toFixed(0)}%`);
    return `This posting scores against your profile on ${bits.join(", ")}.`;
  }
  return "No explanation returned for this entity.";
}
