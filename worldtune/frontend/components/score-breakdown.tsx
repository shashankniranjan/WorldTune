"use client";

import {
  COMPONENT_COLORS,
  COMPONENT_LABELS,
  COMPONENT_ORDER,
  subScoreLabel,
} from "@/lib/score";
import type { ScoreBreakdown, ScoreComponentKey } from "@/lib/api";

/**
 * Section 25: the score is never a black box. A segmented bar shows each
 * component's real point contribution, and the table shows raw value x weight,
 * plus PersonaRelevance's sub_scores (which differ by entity type: watchlist /
 * sector for assets, skill_overlap / role_overlap / location_relevance /
 * seniority_match for jobs, learning_gap / topical_overlap for skills).
 */
export function ScoreBreakdownPanel({ breakdown }: { breakdown: ScoreBreakdown }) {
  const entries = COMPONENT_ORDER.map((key) => ({ key, component: breakdown.components[key] }))
    .filter((e): e is { key: ScoreComponentKey; component: NonNullable<typeof e.component> } =>
      Boolean(e.component),
    );
  const total = entries.reduce((sum, e) => sum + e.component.contribution, 0) || 1;
  const personaSubs = breakdown.components.persona_relevance?.sub_scores;

  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-sm bg-elevated">
        {entries.map(({ key, component }) => (
          <div
            key={key}
            title={`${COMPONENT_LABELS[key]} — ${component.contribution.toFixed(2)} pts`}
            style={{
              width: `${(component.contribution / total) * 100}%`,
              backgroundColor: COMPONENT_COLORS[key],
            }}
          />
        ))}
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[460px] text-sm">
          <thead>
            <tr className="border-b border-hairline text-left">
              <th className="eyebrow pb-2">Component</th>
              <th className="eyebrow pb-2 text-right">Value</th>
              <th className="eyebrow pb-2 text-right">Weight</th>
              <th className="eyebrow pb-2 text-right">Points</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(({ key, component }) => (
              <tr key={key} className="border-b border-hairline/60">
                <td className="py-2">
                  <span className="flex items-center gap-2">
                    <span
                      className="inline-block h-2 w-2 rounded-[2px]"
                      style={{ backgroundColor: COMPONENT_COLORS[key] }}
                    />
                    {COMPONENT_LABELS[key]}
                  </span>
                </td>
                <td className="tabular py-2 text-right text-muted">
                  {component.value.toFixed(4)}
                </td>
                <td className="tabular py-2 text-right text-muted">
                  {component.weight.toFixed(2)}
                </td>
                <td className="tabular display py-2 text-right font-semibold">
                  {component.contribution.toFixed(2)}
                </td>
              </tr>
            ))}
            <tr>
              <td className="display py-2 font-semibold">WorldTune score</td>
              <td />
              <td />
              <td className="tabular display py-2 text-right text-lg font-bold text-accent">
                {breakdown.score.toFixed(1)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {personaSubs && Object.keys(personaSubs).length > 0 ? (
        <div className="mt-6">
          <p className="eyebrow">Inside PersonaRelevance</p>
          <div className="mt-3 space-y-2">
            {Object.entries(personaSubs).map(([key, value]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="w-44 shrink-0 text-xs text-muted">
                  {subScoreLabel(key)}
                </span>
                <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated">
                  <span
                    className="block h-full rounded-full bg-accent/70"
                    style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
                  />
                </span>
                <span className="tabular w-12 text-right text-xs text-muted">
                  {value.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <p className="mt-6 rounded border border-hairline bg-elevated px-3 py-2 font-mono text-[11px] leading-relaxed text-dim">
        {breakdown.formula}
      </p>

      {breakdown.reasons && breakdown.reasons.length > 0 ? (
        <ul className="mt-4 space-y-1 text-sm text-muted">
          {breakdown.reasons.map((r) => (
            <li key={r}>· {r}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
