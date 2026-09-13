import Link from "next/link";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DirectionBadge, ScoreNumber, StateBadge } from "@/components/state-badge";
import { changeClass, pct, relativeTime, salary } from "@/lib/format";
import { signalHref } from "@/lib/score";
import type { AssetSignal, Evidence, JobSignal, SkillSignal } from "@/lib/api";

function EvidenceLines({ evidence, limit = 3 }: { evidence: Evidence[]; limit?: number }) {
  const items = evidence.slice(0, limit);
  if (items.length === 0) {
    return <p className="text-sm text-dim">No evidence recorded for this window.</p>;
  }
  return (
    <ul className="space-y-1.5">
      {items.map((e, i) => (
        <li key={`${e.type}-${i}`} className="flex gap-2 text-sm leading-snug text-muted">
          <span className="eyebrow mt-[3px] w-14 shrink-0 text-[9px]">{e.type}</span>
          <span className="min-w-0 flex-1">{e.detail}</span>
        </li>
      ))}
    </ul>
  );
}

function CardShell({
  href,
  children,
  footer,
}: {
  href: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <Card className="flex flex-col hover:border-hairline-strong">
      <CardContent className="flex-1 pt-5">{children}</CardContent>
      <CardFooter className="flex items-center justify-between text-dim">
        <span className="text-xs">{footer}</span>
        <Link
          href={href}
          className="display text-xs font-semibold tracking-wide text-accent hover:underline"
        >
          View evidence →
        </Link>
      </CardFooter>
    </Card>
  );
}

export function AssetCard({ signal }: { signal: AssetSignal }) {
  const m = signal.metrics ?? {};
  return (
    <CardShell
      href={signalHref(signal)}
      footer={`${signal.asset_class} · ${m.news_count ?? 0} headlines`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow">{signal.entity_id}</p>
          <h3 className="display truncate text-lg font-semibold">{signal.label}</h3>
        </div>
        <div className="flex flex-col items-end gap-2">
          <ScoreNumber score={signal.worldtune_score} />
          <StateBadge score={signal.worldtune_score} />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 border-y border-hairline py-3">
        <Metric label="24h" value={pct(m.change_24h)} tone={changeClass(m.change_24h)} />
        <Metric label="7d" value={pct(m.change_7d)} tone={changeClass(m.change_7d)} />
        <Metric label="30d" value={pct(m.change_30d)} tone={changeClass(m.change_30d)} />
      </div>

      <div className="mt-4">
        <EvidenceLines evidence={signal.evidence} />
      </div>

      {signal.trajectory ? (
        <div className="mt-4 flex items-center gap-2">
          <DirectionBadge direction={signal.trajectory.direction} />
          <span className="tabular text-xs text-dim">
            {(signal.trajectory.probability * 100).toFixed(0)}% over{" "}
            {signal.trajectory.horizon_days}d · confidence{" "}
            {signal.trajectory.confidence.toFixed(2)}
          </span>
        </div>
      ) : null}
    </CardShell>
  );
}

export function SkillCard({ signal }: { signal: SkillSignal }) {
  const m = signal.metrics ?? {};
  return (
    <CardShell
      href={signalHref(signal)}
      footer={`${signal.category} · ${m.skill_mentions ?? 0} of ${m.job_count ?? 0} postings`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow">Skill demand</p>
          <h3 className="display truncate text-lg font-semibold">{signal.label}</h3>
          <Badge
            className={
              signal.already_have
                ? "mt-2 border-teal-500/30 bg-teal-500/10 text-teal-300"
                : "mt-2 border-amber-400/30 bg-amber-400/10 text-amber-300"
            }
          >
            {signal.already_have ? "In your profile" : "Gap"}
          </Badge>
        </div>
        <div className="flex flex-col items-end gap-2">
          <ScoreNumber score={signal.worldtune_score} />
          <StateBadge score={signal.worldtune_score} />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 border-y border-hairline py-3">
        <Metric label="7d" value={pct(m.change_7d, 1)} tone={changeClass(m.change_7d)} />
        <Metric label="30d" value={pct(m.change_30d, 1)} tone={changeClass(m.change_30d)} />
        <Metric label="share" value={pct(m.skill_share, 0)} tone="text-foreground" />
      </div>

      <div className="mt-4">
        <EvidenceLines evidence={signal.evidence} />
      </div>

      {signal.explanation ? (
        <p className="mt-4 border-l-2 border-accent/50 pl-3 text-sm text-muted">
          {signal.explanation.why_it_matters}
        </p>
      ) : null}
    </CardShell>
  );
}

export function JobCard({ signal }: { signal: JobSignal }) {
  const pay = salary(signal.salary_min, signal.salary_max, signal.salary_currency);
  return (
    <CardShell
      href={signalHref(signal)}
      footer={`Posted ${relativeTime(signal.posted_at)}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow">{signal.company}</p>
          <h3 className="display truncate text-lg font-semibold">{signal.label}</h3>
          <p className="mt-1 text-sm text-muted">
            {signal.location}
            {signal.remote ? " · Remote" : ""} · {signal.seniority}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <ScoreNumber score={signal.worldtune_score} />
          <StateBadge score={signal.worldtune_score} />
        </div>
      </div>

      {pay ? (
        <p className="tabular mt-4 border-y border-hairline py-3 text-sm text-foreground">
          {pay}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-1.5">
        {signal.matched_skills.slice(0, 8).map((s) => (
          <Badge key={s} className="border-hairline bg-elevated text-muted">
            {s}
          </Badge>
        ))}
      </div>

      <div className="mt-4">
        <EvidenceLines evidence={signal.evidence} limit={2} />
      </div>
    </CardShell>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div>
      <p className="eyebrow text-[9px]">{label}</p>
      <p className={`tabular display mt-1 text-sm font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
