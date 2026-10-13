import type { IntelligencePoint, WorldShiftSnapshot } from "@/types/worldShift";

export function overviewDevelopments(data: WorldShiftSnapshot) {
  const overview = data.shift.overview;
  const consequences = overview.whyItMattersPoints ?? [];
  const overlap = (a: string[], b: string[]) => a.filter((id) => b.includes(id)).length;
  const candidates = (overview.whatsHappening ?? []).map((change, index) => {
    const matches = consequences.map((consequence) => ({ consequence, claims: overlap(change.claimIds, consequence.claimIds), sources: overlap(change.evidenceIds, consequence.evidenceIds) }))
      .filter((match) => match.claims || match.sources).sort((a, b) => b.claims - a.claims || b.sources - a.sources);
    const records = data.evidence.filter((record) => change.evidenceIds.includes(record.id));
    return { change, index, matches, primary: records.some((record) => record.sourceClass === "primary"), publishedAt: Math.max(0, ...records.map((record) => Date.parse(record.publishedAt) || 0)) };
  });
  // Prefer developments with an explicit supported consequence, then primary
  // records and recent reporting. This is not a measure of geopolitical impact.
  candidates.sort((a, b) => Number(Boolean(b.matches.length)) - Number(Boolean(a.matches.length)) || Number(Boolean(b.matches[0]?.claims)) - Number(Boolean(a.matches[0]?.claims)) || Number(b.primary) - Number(a.primary) || b.publishedAt - a.publishedAt || a.index - b.index);
  const used = new Set<IntelligencePoint>();
  const developments = candidates.map(({ change, matches }) => {
    const consequence = matches.find((match) => !used.has(match.consequence))?.consequence;
    if (consequence) used.add(consequence);
    return { change, consequence };
  });
  return { developments, remainingConsequences: consequences.filter((point) => !used.has(point)) };
}
