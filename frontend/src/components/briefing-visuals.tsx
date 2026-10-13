"use client";
/* eslint-disable @next/next/no-img-element */
import { useState } from "react";
import { ArrowDown, ArrowRight, ImageOff, Newspaper, Lightbulb, TrendingUp, TriangleAlert } from "lucide-react";
import { briefingDate, hasEditorialImage, sourceTitle, wholeSentences } from "@/components/briefing-model";
import { overviewDevelopments } from "@/components/overview-model";
import type { Evidence, WorldShiftSnapshot } from "@/types/worldShift";

type EvidenceAction = (ids: string[], claim?: string) => void;

export function SourceImage({ item, compact = false }: { item: Evidence; compact?: boolean }) {
  const [failed, setFailed] = useState(false);
  if (!hasEditorialImage(item)) return null;
  return <figure className={compact ? "source-image source-image-compact" : "source-image"}>
    {failed ? <div className="source-image-unavailable"><ImageOff size={20} aria-hidden="true" /><span>Publisher image unavailable</span></div> : <img key={item.imageUrl} src={item.imageUrl ?? undefined} alt={`Image accompanying ${sourceTitle(item)}`} loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} />}
    <figcaption>{item.type === "illustration" ? "Illustration" : "Publisher image"} · <a href={item.url} target="_blank" rel="noreferrer">{item.source} ↗</a><span>{briefingDate(item.publishedAt)} · See source for image credit</span></figcaption>
  </figure>;
}

export function QuickBrief({ data, onEvidence }: { data: WorldShiftSnapshot; onEvidence: EvidenceAction }) {
  const { developments } = overviewDevelopments(data);
  const lead = developments[0];
  const why = lead?.consequence ?? data.shift.overview.whyItMattersPoints?.[0];
  const opportunity = data.content.impact.opportunities[0];
  const risk = data.content.impact.risks[0];
  const available = new Set(data.evidence.map(item => item.id));
  const cards = [
    { key: "reported", label: "What changed", Icon: Newspaper, text: lead?.change.text ?? data.shift.overview.whatHappened, title: null, ids: lead?.change.evidenceIds ?? [], kind: lead?.change.evidenceClass ?? "Reporting summary" },
    { key: "meaning", label: "Why it matters", Icon: Lightbulb, text: why?.text ?? data.shift.overview.whyItMatters, title: null, ids: why?.evidenceIds ?? [], kind: why?.evidenceClass ?? "Interpretation" },
    ...(opportunity ? [{ key: "opportunity", label: "Possible opportunity", Icon: TrendingUp, text: opportunity.summary, title: opportunity.title, ids: opportunity.evidenceIds, kind: "Possible upside" }] : []),
    ...(risk ? [{ key: "risk", label: "Risk to watch", Icon: TriangleAlert, text: risk.summary, title: risk.title, ids: risk.evidenceIds, kind: "Potential downside" }] : []),
  ].map(card => ({ ...card, ids: [...new Set(card.ids)].filter(id => available.has(id)), missing: card.ids.some(id => !available.has(id)) }));
  return <section className="quick-brief cognitive-brief" aria-labelledby="quick-brief-title">
    <div className="quick-brief-label"><span className="news-section-label" id="quick-brief-title">Understand at a glance</span><span>Change → meaning → implications</span></div>
    <div className="cognitive-grid">{cards.map(({ key, label, Icon, text, title, ids, kind }) => <article className={`cognitive-card tone-${key}`} key={key}><h2><Icon size={18} aria-hidden="true" />{label}</h2><span className="cognitive-kind">{kind}</span>{title && <h3>{title}</h3>}<p>{text ? wholeSentences(text, 190, 2) : "Not established in this briefing."}</p>{text && wholeSentences(text, 190, 2) !== text && <details><summary>Full context</summary><p>{text}</p></details>}{ids.length > 0 && <button onClick={() => onEvidence(ids, text)}>Sources ({ids.length}) ↗</button>}</article>)}</div>{cards.some(card => card.missing) && <p className="connection-evidence-gap">Some summary source references are unavailable in this briefing. Inspect Sources for the records currently available.</p>}
  </section>;
}

export function MechanismVisual({ data, onEvidence }: { data: WorldShiftSnapshot; onEvidence: EvidenceAction }) {
  const items = data.content.impact.impactChain.length ? data.content.impact.impactChain : data.content.impact.directImpacts;
  // These are separate stored pathways. Do not draw causal arrows between
  // unrelated items or promote an inference to an observed outcome.
  const item = items.find((entry) => entry.mechanism && entry.evidenceIds.length);
  if (!item) return null;
  return <section className="mechanism-visual" aria-labelledby="mechanism-title">
    <header><div><p className="news-section-label">A possible pathway</p><h2 id="mechanism-title">How the impact could unfold</h2></div><span className="inference-tag">Conditional inference</span></header>
    <div className="mechanism-flow">
      <div className="mechanism-step"><span>01 / Mechanism</span><p>{item.mechanism}</p></div>
      <div className="mechanism-arrow" aria-hidden="true"><ArrowRight className="flow-right" size={24} /><ArrowDown className="flow-down" size={24} /></div>
      <div className="mechanism-step"><span>02 / Possible effect</span><h3>{item.title}</h3><p>{item.verificationHint ?? item.invalidators?.[0] ?? "The effect is an interpretation; its outcome is not established by the linked reporting."}</p></div>
    </div>
    <footer><span>{data.persona === "finance" ? "Finance & Investing" : "Tech & Career"} perspective · {item.horizon ? ({ immediate: "Now", "7d": "Next week", "30d": "Next month", "90d": "Next 3 months", long_term: "Longer term" }[item.horizon]) : "Time horizon not specified"}</span><button onClick={() => onEvidence(item.evidenceIds, item.mechanism ?? item.summary)}>Inspect the underlying reporting ↗</button></footer>
  </section>;
}

export function TimelineVisual({ data, onEvidence }: { data: WorldShiftSnapshot; onEvidence: EvidenceAction }) {
  const events = [...(data.shift.overview.timeline ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  if (!events.length) return null;
  const render = (event: typeof events[number], index: number) => <li key={`${event.date}-${event.title}`}>
    <div className="timeline-marker" aria-hidden="true">{String(index + 1).padStart(2, "0")}</div>
    <div><div className="timeline-meta"><time dateTime={event.date}>{briefingDate(event.date)}</time><span>{event.status} · dataset label</span></div><h3>{event.title}</h3><p>{event.summary}</p>{event.evidenceIds.length > 0 && <button onClick={() => onEvidence(event.evidenceIds, event.summary)}>Sources ({event.evidenceIds.length}) ↗</button>}</div>
  </li>;
  return <section className="visual-timeline" aria-labelledby="timeline-title"><header><p className="news-section-label">The sequence</p><h2 id="timeline-title">How we got here</h2><p>Event dates supplied by the briefing. Source publication dates are shown separately in Sources.</p></header><ol>{events.slice(0, 3).map(render)}</ol>{events.length > 3 && <details className="overview-disclosure"><summary>Full chronology · {events.length} events</summary><ol>{events.slice(3).map((event, index) => render(event, index + 3))}</ol></details>}</section>;
}
