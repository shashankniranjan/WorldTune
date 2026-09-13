"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, queryKeys, type Dashboard, type DailyTuneItem } from "@/lib/api";
import { AssetCard, JobCard, SkillCard } from "@/components/signal-card";
import { CardSkeleton, Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/states";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { greeting, longDate } from "@/lib/format";
import { isCooling, isHeating } from "@/lib/score";

export default function HomePage() {
  const query = useQuery({ queryKey: queryKeys.dashboard, queryFn: () => api.dashboard() });

  return (
    <div className="pt-8">
      <Header data={query.data} />

      {query.isPending ? <HomeSkeleton /> : null}

      {query.isError ? (
        <div className="mt-8">
          <ErrorState
            title="WorldTune could not load your dashboard"
            message={(query.error as Error).message}
            onRetry={() => query.refetch()}
          />
        </div>
      ) : null}

      {query.data ? <HomeBody data={query.data} /> : null}
    </div>
  );
}

function Header({ data }: { data?: Dashboard }) {
  const now = new Date();
  const persona = data?.persona;
  const personaLine = persona
    ? [
        persona.career.current_role,
        [persona.location.city, persona.location.country].filter(Boolean).join(", "),
        persona.financial.sectors.slice(0, 3).join(" + "),
      ]
        .filter(Boolean)
        .join(" · ")
    : null;

  return (
    <header>
      <p className="eyebrow">{longDate(now)}</p>
      <h1 className="display mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
        {greeting(now)}.
      </h1>
      <p className="display mt-1 text-2xl font-medium text-muted sm:text-3xl">
        What matters to you today.
      </p>
      <p className="mt-4 text-sm text-muted">
        {personaLine ?? <Skeleton className="inline-block h-4 w-72 align-middle" />}
        {persona ? (
          <Link href="/persona" className="ml-3 text-accent hover:underline">
            Edit profile
          </Link>
        ) : null}
      </p>
    </header>
  );
}

function HomeBody({ data }: { data: Dashboard }) {
  const allSignals = [
    ...data.financial_pulse,
    ...data.career_pulse.skill_signals,
    ...data.career_pulse.job_matches,
  ];
  const heating = allSignals.filter((s) => isHeating(s.worldtune_score)).length;
  const cooling = allSignals.filter((s) => isCooling(s.worldtune_score)).length;
  const careerChanges =
    data.career_pulse.skill_signals.filter((s) => isHeating(s.worldtune_score)).length +
    data.career_pulse.job_matches.filter((j) => isHeating(j.worldtune_score)).length;

  return (
    <div className="mt-10 space-y-14">
      {/* --- YOUR WORLD TODAY ------------------------------------------- */}
      <section>
        <p className="eyebrow">Your world today</p>
        <Card className="mt-3 border-hairline-strong bg-elevated">
          <CardContent className="pt-5">
            <p className="display text-xl leading-snug font-medium sm:text-2xl">
              <span className="tabular text-accent">{heating}</span> signals heating up,{" "}
              <span className="tabular text-sky-300">{cooling}</span> cooling,{" "}
              <span className="tabular text-amber-300">{careerChanges}</span> important
              career changes.
            </p>
            <p className="mt-3 text-sm text-muted">{data.summary.headline}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge>{data.summary.assets_tracked} assets tracked</Badge>
              <Badge>{data.summary.assets_moving} moving</Badge>
              <Badge>{data.summary.skills_rising} skills rising</Badge>
              <Badge>{data.summary.skills_cooling} skills cooling</Badge>
              <Badge>{data.summary.job_matches} job matches</Badge>
              <Badge className="border-accent/30 bg-accent/10 text-accent">
                top score {data.summary.top_score.toFixed(1)}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* --- FINANCIAL PULSE -------------------------------------------- */}
      <Section
        title="Financial pulse"
        subtitle={`Watchlist ${data.persona.financial.watchlist.join(", ")} · sectors ${data.persona.financial.sectors.join(", ")}`}
      >
        {data.financial_pulse.length === 0 ? (
          <EmptyState message="No assets scored for this persona yet." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.financial_pulse.map((s) => (
              <AssetCard key={s.entity_id} signal={s} />
            ))}
          </div>
        )}
      </Section>

      {/* --- CAREER PULSE ------------------------------------------------ */}
      <Section
        title="Career pulse"
        subtitle={`Toward ${data.persona.career.target_roles.slice(0, 3).join(", ")}`}
      >
        <h3 className="eyebrow mb-3">Skill demand</h3>
        {data.career_pulse.skill_signals.length === 0 ? (
          <EmptyState message="No skill signals in this window." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.career_pulse.skill_signals.map((s) => (
              <SkillCard key={s.entity_id} signal={s} />
            ))}
          </div>
        )}

        <h3 className="eyebrow mt-10 mb-3">Job matches</h3>
        {data.career_pulse.job_matches.length === 0 ? (
          <EmptyState message="No matching postings in the last 30 days." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.career_pulse.job_matches.map((j) => (
              <JobCard key={j.entity_id} signal={j} />
            ))}
          </div>
        )}
      </Section>

      {/* --- TODAY'S TUNE ------------------------------------------------ */}
      <Section
        title="Today's tune"
        subtitle={`${data.persona.preferences.daily_time_budget_minutes} minutes, four things`}
      >
        {data.daily_tune.length === 0 ? (
          <EmptyState message="Nothing recommended for today." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {data.daily_tune.map((item, i) => (
              <TuneCard key={`${item.kind}-${item.entity_id}-${i}`} item={item} />
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

const TUNE_KIND_CLASSES: Record<string, string> = {
  learn: "border-amber-400/35 bg-amber-400/10 text-amber-300",
  apply: "border-teal-400/35 bg-teal-400/10 text-teal-300",
  watch: "border-sky-400/35 bg-sky-400/10 text-sky-300",
  read: "border-indigo-400/35 bg-indigo-400/10 text-indigo-300",
};

function TuneCard({ item }: { item: DailyTuneItem }) {
  const linkable = ["asset", "skill", "job"].includes(item.entity_type) && item.entity_id;
  return (
    <Card className="flex flex-col">
      <CardContent className="flex flex-1 flex-col pt-5">
        <div className="flex items-center justify-between">
          <Badge className={TUNE_KIND_CLASSES[item.kind] ?? ""}>{item.kind}</Badge>
          <span className="tabular display text-sm font-semibold text-muted">
            {item.score.toFixed(1)}
          </span>
        </div>
        <h3 className="display mt-3 text-base leading-snug font-semibold">{item.title}</h3>
        <p className="mt-2 text-sm text-muted">{item.detail}</p>
        <p className="mt-3 border-l-2 border-accent/50 pl-3 text-xs leading-relaxed text-dim">
          {item.why}
        </p>
        <div className="mt-4 flex-1" />
        {linkable ? (
          <Link
            href={`/signal/${item.entity_type}/${encodeURIComponent(item.entity_id)}`}
            className="display text-xs font-semibold text-accent hover:underline"
          >
            View evidence →
          </Link>
        ) : item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer noopener"
            className="display text-xs font-semibold text-accent hover:underline"
          >
            Open source →
          </a>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-5 flex items-baseline justify-between gap-4 border-b border-hairline pb-3">
        <h2 className="display text-xl font-bold tracking-tight uppercase">{title}</h2>
        {subtitle ? (
          <p className="hidden truncate text-xs text-dim sm:block">{subtitle}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function HomeSkeleton() {
  return (
    <div className="mt-10 space-y-10">
      <Skeleton className="h-32 w-full" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
