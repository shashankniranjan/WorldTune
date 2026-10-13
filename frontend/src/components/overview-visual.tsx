"use client";
/* eslint-disable @next/next/no-img-element */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowRight, ChevronLeft, ChevronRight, Eye, Lightbulb, Newspaper, Quote, TriangleAlert, X } from "lucide-react";
import { getPersonaConfig } from "@/config/personas";
import { hasEditorialImage, readableText as baseReadable, sentences, wholeSentences } from "@/components/briefing-model";

// Drop inline citations such as "(example.com, 2026-09-19)" so their dots never split a sentence.
const readableText = (value?: string | null) => baseReadable(value).replace(/\s*\([^)]*\.(?:com|org|net|io|gov|edu|co|in|uk)\b[^)]*\)/gi, "").replace(/\s+([.,;])/g, "$1").trim();
import type { Evidence, IntelligencePoint, SemanticTab, StoryCard, WorldShiftSnapshot } from "@/types/worldShift";

type StoryCardKey = StoryCard["key"];

type EvidenceAction = (ids: string[]) => void;

/** Split prose into a headline (the first complete sentence) and a subhead (the next complete sentence). Text is never cut mid-sentence. */
export function headlineParts(raw: string | undefined | null) {
  const text = readableText(raw);
  if (!text) return { head: "", sub: "", full: "" };
  const [first, second] = sentences(text);
  const trim = (value: string) => value.replace(/[,;:\s.]+$/, "");
  return { head: trim(first), sub: second ? trim(second) : "", full: text };
}

function Sources({ ids, onEvidence }: { ids: string[]; onEvidence: EvidenceAction }) {
  return ids.length ? <button className="ov-src" onClick={() => onEvidence(ids)}>{ids.length} source{ids.length > 1 ? "s" : ""} ↗</button> : null;
}

/** Headline + subhead card; the paragraph only opens on request. */
function StoryCard({ tone, Icon, label, point, onEvidence, index }: { tone: string; Icon: typeof Newspaper; label: string; point: IntelligencePoint | { text: string; evidenceIds: string[] }; onEvidence: EvidenceAction; index?: number }) {
  const { head, sub, full } = headlineParts(point.text);
  if (!head) return null;
  const hasMore = full.length > head.length + sub.length + 8;
  return <article className={`ov-card ov-${tone}`}>
    <div className="ov-card-top"><span className="ov-icon"><Icon size={18} aria-hidden="true" /></span><span className="ov-label">{index ? `${String(index).padStart(2, "0")} · ` : ""}{label}</span></div>
    <h3>{head}</h3>
    {sub && <p className="ov-sub">{sub}</p>}
    <div className="ov-card-foot">
      {hasMore && <details><summary>Read more</summary><p>{full}</p></details>}
      <Sources ids={point.evidenceIds} onEvidence={onEvidence} />
    </div>
  </article>;
}

function Timeline({ data, onEvidence }: { data: WorldShiftSnapshot; onEvidence: EvidenceAction }) {
  const events = [...(data.shift.overview.timeline ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const [open, setOpen] = useState<number | null>(null);
  if (!events.length) return null;
  const active = open === null ? null : events[open];
  return <section className="ov-section" aria-labelledby="ov-tl">
    <h2 id="ov-tl" className="ov-h2">How it unfolded <small>Tap a date</small></h2>
    <ol className="ov-rail">{events.map((event, i) => <li key={event.date + event.title}>
      <button aria-pressed={open === i} data-status={event.status} onClick={() => setOpen(open === i ? null : i)}>
        <i aria-hidden="true" /><time>{event.date}</time><strong>{event.title}</strong><span>{event.status}</span>
      </button>
    </li>)}</ol>
    {active && <div className="ov-rail-detail"><h3>{active.title}</h3><p>{active.summary}</p><Sources ids={active.evidenceIds} onEvidence={onEvidence} /></div>}
  </section>;
}


type Story = { key: string; kicker: string; head: string; body: string; image?: Evidence; deep: { title: string; text: string; ids: string[] }[] };

/** Whole sentences only, so a card never ends in "…". */
function crisp(raw: string | undefined | null, n = 3, max = 260) {
  return wholeSentences(readableText(raw), max, n);
}

/** Distinct publishers only, so the cards do not repeat one outlet's picture. */
function distinctImages(data: WorldShiftSnapshot) {
  const seen = new Set<string>();
  return [...data.evidence].reverse().filter((item) => {
    if (!hasEditorialImage(item)) return false;
    const key = (item.sourceDomain ?? item.source).toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function buildStories(data: WorldShiftSnapshot, images: Evidence[]): Story[] {
  const o = data.shift.overview;
  const impact = data.content.impact;
  const persona = getPersonaConfig(data.persona).label;
  const pts = (list?: IntelligencePoint[]) => (list ?? []).map((p) => ({ title: headlineParts(p.text).head, text: readableText(p.text), ids: p.evidenceIds }));
  const happened = o.whatsHappening?.[0];
  const driver = o.drivers?.[0] ?? o.whyItMattersPoints?.[0];
  const next = data.whatHappensNext;
  const base = next.scenarios.find((sc) => sc.label === "base") ?? next.scenarios[0];
  const mine = [...impact.opportunities, ...impact.risks, ...impact.directImpacts];
  const stories: Story[] = [
    { key: "happened", kicker: "The story",
      head: headlineParts(happened?.text ?? o.whatHappened).head || data.shift.title,
      body: crisp(o.contextBrief?.latest ?? o.whatHappened ?? happened?.text) || "The research has not confirmed a recent update for this topic yet. It will appear here after the next refresh.", image: images[0],
      deep: [...pts(o.whatsHappening), ...pts(o.keyDevelopments)] },
    { key: "why", kicker: "Why it happened",
      head: headlineParts(driver?.text ?? o.whyItMatters).head || "The cause is not clear yet",
      body: crisp(o.contextBrief?.howItStarted ?? driver?.text ?? o.whyItMatters) || "The sources do not yet explain what set this off. It will appear here after the next refresh.", image: images[1] ?? images[0],
      deep: [...pts(o.drivers), ...pts(o.whyItMattersPoints), ...(o.contextBrief ? [{ title: "How it started", text: o.contextBrief.howItStarted, ids: o.contextBrief.howItStartedEvidenceIds ?? [] }] : [])] },
    { key: "you", kicker: `What it means for you · ${persona}`,
      head: headlineParts(impact.headline ?? mine[0]?.title ?? impact.summary).head || "No clear impact on you yet",
      body: crisp(impact.summary || mine[0]?.summary) || `The research has not found a well-supported ${persona} impact for this topic yet. It will appear here after the next refresh.`,
      image: images[2] ?? images[0],
      deep: mine.map((item) => ({ title: item.title, text: item.summary, ids: item.evidenceIds })) },
    { key: "next", kicker: "What happens next",
      head: headlineParts(base?.title ?? next.framing).head || "No forecast yet",
      body: crisp(base ? `${base.summary} ${next.framing}` : next.framing) || "No scenarios have been generated for this topic yet.",
      image: images[3] ?? images[0],
      deep: next.scenarios.map((sc) => ({ title: `${sc.label[0].toUpperCase()}${sc.label.slice(1)} case · ${sc.horizon}: ${sc.title}`, text: sc.summary, ids: sc.evidenceIds })) },
  ];
  // Prefer the cards the model wrote for each question; the derived text above is the fallback for older snapshots.
  const written = new Map([...(o.storyCards ?? []), ...(impact.storyCard ? [impact.storyCard] : [])].map((card) => [card.key, card]));
  return stories.map((story) => {
    const card = written.get(story.key as StoryCardKey);
    const head = readableText(card?.headline), text = readableText(card?.body);
    return head && text ? { ...story, head, body: text } : story;
  });  // always four cards: a missing one shows an honest placeholder rather than disappearing
}

function StoryCarousel({ data, images, onEvidence, slots, onSection }: { data: WorldShiftSnapshot; images: Evidence[]; onEvidence: EvidenceAction; slots?: Record<string, { tab: SemanticTab; title: string; node: ReactNode }>; onSection?: (tab: SemanticTab | null) => void }) {
  const stories = buildStories(data, images);
  const track = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  const [deep, setDeep] = useState<number | null>(null);
  const slot = deep !== null ? slots?.[stories[deep]?.key] : undefined;
  const slotTab = slot?.tab;
  // Light up the persona's impact tab while its section is on screen; fall back to Overview when scrolling back up.
  useEffect(() => {
    if (!slotTab || !onSection) return;
    const el = document.getElementById("ov-slot");
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => onSection(entry.isIntersecting || entry.boundingClientRect.top < 0 ? slotTab : null), { rootMargin: "-25% 0px -55% 0px" });
    io.observe(el);
    return () => { io.disconnect(); onSection(null); };
  }, [slotTab, onSection]);
  if (!stories.length) return null;
  const go = (i: number) => { const el = track.current; if (!el) return; const next = Math.max(0, Math.min(stories.length - 1, i)); el.scrollTo({ left: next * el.clientWidth, behavior: "smooth" }); setActive(next); };
  const open = deep === null ? null : stories[deep];
  return <section className="ov-section" aria-label="The story in four cards">
    <div className="ov-carousel">
      <div className="ov-track" ref={track} onScroll={(e) => { const el = e.currentTarget; setActive(Math.round(el.scrollLeft / el.clientWidth)); }}>
        {stories.map((story, i) => <article className="ov-slide" key={story.key} aria-roledescription="slide" aria-label={`${i + 1} of ${stories.length}`}>
          {story.image?.imageUrl && <img src={story.image.imageUrl} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(e) => { e.currentTarget.style.display = "none"; }} />}
          <div className="ov-slide-copy">
            <span className="ov-chip">{story.kicker}</span>
            <h2>{story.head}</h2>
            <p>{story.body}</p>
            <div className="ov-slide-foot">
              <button className="ov-know" onClick={() => { setDeep(i); requestAnimationFrame(() => document.getElementById("ov-deep")?.scrollIntoView({ behavior: "smooth", block: "start" })); }}>Know more <ArrowRight size={15} aria-hidden="true" /></button>
              {story.image && <small>Image: {story.image.source}</small>}
            </div>
          </div>
        </article>)}
      </div>
      <button className="ov-nav ov-prev" aria-label="Previous card" disabled={active === 0} onClick={() => go(active - 1)}><ChevronLeft size={20} /></button>
      <button className="ov-nav ov-next" aria-label="Next card" disabled={active === stories.length - 1} onClick={() => go(active + 1)}><ChevronRight size={20} /></button>
      <div className="ov-dots">{stories.map((story, i) => <button key={story.key} aria-label={`Go to card ${i + 1}`} aria-current={i === active} onClick={() => go(i)} />)}</div>
    </div>
    {open && <div className="ov-deep" id="ov-deep" tabIndex={-1}>
      <header><div><span className="ov-label">{open.kicker}</span><h3>{open.head}</h3></div><button aria-label="Close" onClick={() => setDeep(null)}><X size={18} /></button></header>
      {open.deep.length ? <ol>{open.deep.map((item, i) => <li key={item.title + i}><strong>{item.title}</strong>{(() => { const rest = item.text.startsWith(item.title) ? item.text.slice(item.title.length).replace(/^[.\s]+/, "") : item.text; return rest && rest !== item.title ? <p>{rest}</p> : null; })()}<Sources ids={item.ids} onEvidence={onEvidence} /></li>)}</ol> : <p className="ov-sub">No further detail is available for this card.</p>}
    </div>}
    {slot && <div className="ov-continue" id="ov-slot">
      <h2 className="ov-h2">{slot.title}<small>Continues from your card</small></h2>
      {slot.node}
    </div>}
  </section>;
}

export function VisualOverview({ data, onEvidence, slots, onSection }: { data: WorldShiftSnapshot; onEvidence: EvidenceAction; slots?: Record<string, { tab: SemanticTab; title: string; node: ReactNode }>; onSection?: (tab: SemanticTab | null) => void }) {
  const o = data.shift.overview;
  const images = distinctImages(data);
  const watch = o.watchNext?.[0];
  const unsure = o.contradictions?.[0];
  const more = [...(o.keyDevelopments ?? []), ...(o.drivers ?? [])];
  return <div className="ov">
    <StoryCarousel data={data} images={images} onEvidence={onEvidence} slots={slots} onSection={onSection} />

    {Boolean(o.factsAndFigures?.length) && <section className="ov-stats" aria-label="Key numbers">{o.factsAndFigures!.slice(0, 6).map((fact) => <button key={fact.value + fact.label} onClick={() => onEvidence(fact.evidenceIds)} title={fact.context}><strong>{fact.value}</strong><span>{fact.label}</span></button>)}</section>}

    {(watch || unsure) && <section className="ov-section" aria-labelledby="ov-eye">
      <h2 id="ov-eye" className="ov-h2">Keep an eye on</h2>
      <div className="ov-grid">
        {watch && <StoryCard tone="watch" Icon={Eye} label="Watch next" point={watch} onEvidence={onEvidence} />}
        {unsure && <StoryCard tone="risk" Icon={TriangleAlert} label="Still unclear" point={unsure} onEvidence={onEvidence} />}
      </div>
    </section>}

    <Timeline data={data} onEvidence={onEvidence} />

    {Boolean(o.actors?.length) && <section className="ov-section" aria-labelledby="ov-who">
      <h2 id="ov-who" className="ov-h2">Who&apos;s involved <small>Positions are attributed, not verified</small></h2>
      <div className="ov-actors">{o.actors!.map((actor) => <article key={actor.name} data-status={actor.status}>
        <div><strong>{actor.name}</strong><span>{actor.role}</span></div>
        <p><Quote size={13} aria-hidden="true" />{headlineParts(actor.position).head}</p>
        <footer><em>{actor.status}</em><Sources ids={actor.evidenceIds} onEvidence={onEvidence} /></footer>
      </article>)}</div>
    </section>}

    {more.length > 0 && <section className="ov-section" aria-labelledby="ov-more">
      <h2 id="ov-more" className="ov-h2">More to know</h2>
      <div className="ov-grid">{more.slice(0, 6).map((point, i) => <StoryCard key={point.text} tone={i < (o.keyDevelopments?.length ?? 0) ? "change" : "meaning"} Icon={i < (o.keyDevelopments?.length ?? 0) ? Newspaper : Lightbulb} label={i < (o.keyDevelopments?.length ?? 0) ? "Development" : "Driver"} point={point} index={i + 1} onEvidence={onEvidence} />)}</div>
    </section>}

    {o.contextBrief && <details className="ov-background"><summary>Background: what this is and how it started</summary>
      <p><strong>What it is.</strong> {o.contextBrief.whatItIs}</p><p><strong>How it started.</strong> {o.contextBrief.howItStarted}</p><p><strong>Latest.</strong> {o.contextBrief.latest}</p>
    </details>}

    {o.themes.length > 0 && <footer className="ov-themes">{o.themes.map((theme) => <span key={theme}>{theme}</span>)}</footer>}
  </div>;
}
