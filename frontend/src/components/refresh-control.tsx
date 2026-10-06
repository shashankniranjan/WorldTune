"use client";
import { Check, Circle, LoaderCircle, RefreshCw, Search, XCircle } from "lucide-react";
import { useWorldShiftRefresh } from "@/hooks/useWorldShiftRefresh";

const stages = [
  ["fetching_gdelt", "Loading stored World Shift data"], ["building_evidence", "Processing evidence"],
  ["researching_web", "Researching primary and independent sources"],
  ["extracting_semantics", "Analysing World Shifts"], ["generating_finance", "Generating Finance perspective"],
  ["generating_tech", "Generating Tech perspective"], ["validating", "Validating evidence"],
  ["publishing", "Publishing snapshot"],
] as const;
const order = ["fetching_gdelt", "normalizing", "calculating_signals", "building_evidence", "researching_web", "extracting_semantics", "generating_overview", "generating_finance", "generating_tech", "validating", "publishing", "complete"];
const labels: Record<number, string> = { 300: "Every 5 minutes", 3600: "Every hour", 43200: "Every 12 hours", 86400: "Once daily" };

export function RefreshControl({ generatedAt }: { generatedAt: string }) {
  const refresh = useWorldShiftRefresh();
  const status = refresh.status;
  const activeIndex = order.indexOf(status?.stage ?? "fetching_gdelt");
  const running = status?.status === "queued" || status?.status === "running" || refresh.starting;
  return <section className="mb-5 rounded-lg border border-slate-800 bg-slate-950/30 p-3">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Last updated</p><p className="mt-1 text-sm text-slate-300">{new Date(generatedAt).toLocaleString()}</p></div>
      {!running && status?.status !== "completed" && <button className="inline-flex items-center gap-2 rounded border border-sky-700 px-3 py-2 text-xs text-sky-200 hover:bg-sky-950" onClick={() => refresh.start()}><RefreshCw size={14} />Refresh intelligence</button>}
      {status?.status === "completed" && <button className="rounded bg-emerald-500/15 px-3 py-2 text-xs text-emerald-200" onClick={() => refresh.loadSnapshot()}>Load new snapshot</button>}
    </div>
    {refresh.configuration && <div className="mt-3 grid gap-3 border-t border-slate-800 pt-3 md:grid-cols-[minmax(180px,240px)_1fr]"><label className="text-xs text-slate-400"><span className="mb-1 block font-medium text-slate-300">AI intelligence refresh</span><select className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-2 text-slate-200" value={refresh.configuration.intervalSeconds} disabled={refresh.configuring} onChange={(event) => refresh.configure({ ...refresh.configuration!, intervalSeconds: Number(event.target.value) })}>{refresh.configuration.allowedIntervals.map((seconds) => <option key={seconds} value={seconds}>{labels[seconds] ?? `${seconds} seconds`}</option>)}</select></label><div className="flex flex-wrap items-center gap-4 text-xs text-slate-400"><label className="inline-flex items-center gap-2"><input type="checkbox" checked={refresh.configuration.webResearchEnabled} disabled={refresh.configuring} onChange={(event) => refresh.configure({ ...refresh.configuration!, webResearchEnabled: event.target.checked })} /><Search size={14} className="text-sky-300" />Bounded web research</label><span>Maximum {refresh.configuration.webResultsPerShift} sources per changed shift</span><span>Research is cached for six hours; changed evidence may create fresh AI and search usage.</span>{refresh.configuration.nextRefreshAt && <span>Next scheduled: {new Date(refresh.configuration.nextRefreshAt).toLocaleString()}</span>}</div></div>}
    {running && <div className="mt-4 border-t border-slate-800 pt-3"><p className="mb-2 text-sm font-medium text-slate-200">Updating intelligence…</p><div className="grid gap-1 sm:grid-cols-2">{stages.map(([key, label]) => { const index = order.indexOf(key); const done = activeIndex > index; const current = activeIndex === index; return <p key={key} className={`flex items-center gap-2 text-xs ${done ? "text-emerald-300" : current ? "text-sky-300" : "text-slate-600"}`}>{done ? <Check size={13} /> : current ? <LoaderCircle className="animate-spin" size={13} /> : <Circle size={13} />}{label}</p>; })}</div></div>}
    {status?.status === "completed" && <p className="mt-3 flex items-center gap-2 text-xs text-emerald-300"><Check size={14} />New intelligence available</p>}
    {refresh.error && <p className="mt-3 flex items-center gap-2 text-xs text-rose-300"><XCircle size={14} />Could not start refresh: {refresh.error.message}</p>}
    {refresh.configurationError && <p className="mt-3 flex items-center gap-2 text-xs text-rose-300"><XCircle size={14} />Could not save refresh configuration: {refresh.configurationError.message}</p>}
    {status?.status === "failed" && <p className="mt-3 flex items-center gap-2 text-xs text-rose-300"><XCircle size={14} />Refresh failed. The current snapshot remains active. {status.error}</p>}
  </section>;
}
