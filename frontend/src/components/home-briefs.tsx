"use client";
import Link from "next/link";
import { useState } from "react";
import { useWorldShift } from "@/hooks/useWorldShift";
import { useWorldShifts } from "@/hooks/useWorldShifts";
import type { WorldShiftListItem } from "@/types/worldShift";

// Twelve-column mosaic: each entry is a card's column span, so rows of
// unequal cards fill the width the way a magazine front page does.
const SPANS_9 = [7, 5, 4, 4, 4, 5, 7, 6, 6];
const SPANS_10 = [7, 5, 4, 4, 4, 5, 7, 4, 4, 4];
// Tints drawn from the landing page's teal / indigo palette.
const HUES = [172, 196, 232, 262, 158, 214, 284, 184, 244, 150];

function ago(iso: string) {
  const mins = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins}M AGO`;
  return mins < 1440 ? `${Math.round(mins / 60)}H AGO` : `${Math.round(mins / 1440)}D AGO`;
}

function BriefCard({ shift, index, span, snapshotId }: { shift: WorldShiftListItem; index: number; span: number; snapshotId: string }) {
  const { data } = useWorldShift(shift.id, "tech", snapshotId);
  const brief = data?.shift.overview.contextBrief?.latest ?? data?.shift.overview.whatHappened ?? "";
  const images = data ? [...new Set([...data.evidence].reverse().map((item) => item.imageUrl).filter((url): url is string => !!url))] : [];
  // Source images often 404 or block hotlinking; fall through to the next
  // candidate instead of showing the browser's broken-image icon.
  const [failed, setFailed] = useState(0);
  const image = images[failed];
  return <Link href={`/world-shifts/${shift.id}?persona=tech&tab=overview`} className="brief-card" style={{ gridColumn: `span ${span}`, "--hue": HUES[index % HUES.length] } as React.CSSProperties}>
    {image && <img key={image} src={image} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed((n) => n + 1)} onLoad={(e) => { if (e.currentTarget.naturalWidth < 2) setFailed((n) => n + 1); }} />}
    <div className="brief-body">
      <p className="brief-meta"><span>{data ? `${data.evidence.length} ARTICLES` : "…"}</span>{data && <span>{ago(data.generatedAt)}</span>}</p>
      <h3>{shift.title}</h3>
      {data ? <p className="brief-text">{brief}</p> : <p className="brief-skeleton" aria-hidden="true" />}
    </div>
  </Link>;
}

export function HomeBriefs() {
  const list = useWorldShifts();
  if (!list.data?.entries.length) return null;
  const { entries, snapshotId } = list.data;
  const shown = entries.slice(0, 10);
  const spans = shown.length >= 10 ? SPANS_10 : SPANS_9;
  return <section className="landing-briefs" aria-label="World shifts in brief">
    <div className="brief-grid">{shown.map((shift, index) => <BriefCard key={shift.id} shift={shift} index={index} span={spans[index] ?? 4} snapshotId={snapshotId} />)}</div>
  </section>;
}
