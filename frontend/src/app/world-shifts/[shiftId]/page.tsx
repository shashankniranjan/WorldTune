"use client";
/* eslint-disable @next/next/no-img-element */
import { useRouter, useSearchParams } from "next/navigation";
import { use, useState } from "react";
import { AppHeader, LeftSidebar, RightSidebar, ShiftTabs, WorldShiftStrip } from "@/components/layout";
import { ErrorState, LoadingSkeleton, StatusBadge } from "@/components/common";
import { DomainRenderer, EvidenceRenderer, ForecastRenderer, ImpactRenderer, OverviewRenderer, RelationshipRenderer } from "@/components/renderers";
import { RefreshControl } from "@/components/refresh-control";
import { useWorldShift } from "@/hooks/useWorldShift";
import { useWorldShifts } from "@/hooks/useWorldShifts";
import { SnapshotMismatchError } from "@/api/worldShifts";
import type { PersonaId, SemanticTab } from "@/types/worldShift";
import { InwardStarField } from "@/components/inward-star-field";

const validTabs = new Set<SemanticTab>(["overview", "impact", "domain", "relationships", "forecast", "evidence"]);

export default function WorldShiftPage({ params }: { params: Promise<{ shiftId: string }> }) {
  const [evidenceIds, setEvidenceIds] = useState<string[]>([]);
  const route = useRouter();
  const search = useSearchParams();
  const { shiftId } = use(params);
  const persona = (search.get("persona") === "finance" ? "finance" : "tech") as PersonaId;
  const tab = validTabs.has(search.get("tab") as SemanticTab) ? search.get("tab") as SemanticTab : "overview";
  const list = useWorldShifts();
  const world = useWorldShift(shiftId, persona, list.data?.snapshotId);
  const changeTab = (next: SemanticTab, preserveEvidence = false) => {
    if (!preserveEvidence) setEvidenceIds([]);
    route.push(`/world-shifts/${shiftId}?persona=${persona}&tab=${next}`);
  };
  if (list.isError) return <main className="mx-auto max-w-7xl p-5"><ErrorState error={list.error} /></main>;
  if (world.isLoading || list.isLoading || !list.data) return <main className="mx-auto max-w-7xl p-5"><LoadingSkeleton /></main>;
  if (world.error instanceof SnapshotMismatchError) return <main className="mx-auto max-w-7xl p-5"><LoadingSkeleton /></main>;
  if (world.isError) return <main className="mx-auto max-w-7xl p-5"><ErrorState error={world.error} /></main>;
  if (!world.data) return null;
  const data = world.data;
  const personaLabel = persona === "finance" ? "Finance & Investing" : "Tech & Career";
  const personaTab = tab === "impact" || tab === "domain";
  const articleDeck = personaTab ? data.content.impact.summary : data.shift.overview.whatHappened;
  const showEvidence = (ids: string[]) => { setEvidenceIds(ids); changeTab("evidence", true); };
  const content = tab === "overview" ? <OverviewRenderer data={data} onEvidence={showEvidence} /> : tab === "impact" ? <ImpactRenderer data={data} onEvidence={showEvidence} /> : tab === "domain" ? <DomainRenderer data={data} onEvidence={showEvidence} /> : tab === "relationships" ? <RelationshipRenderer relationships={data.relationships} persona={persona} onEvidence={showEvidence} /> : tab === "forecast" ? <ForecastRenderer data={data} onEvidence={showEvidence} /> : <EvidenceRenderer evidence={data.evidence} activeIds={evidenceIds} onClear={() => setEvidenceIds([])} />;
  // Best-available lead image: whichever evidence record happens to carry
  // one (GDELT socialimage, or a scraped og:image -- see world_shift_refresh.py).
  const leadImage = data.evidence.find((item) => item.imageUrl)?.imageUrl ?? null;
  return <><InwardStarField className="briefing-star-field" density={130} velocity={0.95} /><AppHeader /><WorldShiftStrip title={data.shift.title} strength={data.shift.signalStrength} snapshotId={data.snapshotId} /><main className="news-shell mx-auto grid max-w-[1540px] gap-10 px-5 py-8 sm:px-8 xl:grid-cols-[210px_minmax(0,1fr)_270px]"><LeftSidebar shifts={list.data.entries} currentId={shiftId} persona={persona} tab={tab} /><section className="order-1 min-w-0 xl:order-none"><header className="news-article-header"><div className="flex flex-wrap items-center gap-3"><p className="news-kicker">{personaTab ? `${personaLabel} briefing` : "World briefing"}</p><StatusBadge status={data.shift.status} />{data.shift.isTrending && <span className="rounded bg-fuchsia-900/60 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-fuchsia-200">Trending</span>}<span className="text-xs text-slate-500">{new Date(data.generatedAt).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}</span></div><h1>{data.shift.title}</h1><p className="news-deck">{articleDeck}</p>{leadImage && <img src={leadImage} alt="" loading="lazy" referrerPolicy="no-referrer" className="mt-4 aspect-[16/7] w-full rounded-lg object-cover" />}<div className="news-byline"><span>WorldTune intelligence desk</span><span>{personaLabel} lens</span><span>Evidence-linked analysis</span><span>{data.evidence.length} source records</span></div></header><ShiftTabs persona={persona} selected={tab} onTab={changeTab} /><div className="pt-7">{content}</div><details className="news-settings"><summary>Update frequency and research settings</summary><RefreshControl generatedAt={data.generatedAt} /></details></section><RightSidebar data={data} tab={tab} /></main></>;
}
