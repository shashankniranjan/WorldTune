import type { Evidence, IntelligencePoint, WorldShiftSnapshot } from "@/types/worldShift";

export function briefingDate(value: string, withTime = false) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", year: "numeric", ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}) }).format(date) + (withTime ? " IST" : "");
}

export function readableText(value?: string | null) {
  return (value ?? "").replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").replace(/<[^>]*>/g, "")
    .replace(/https?:\/\/\S+/g, "").replace(/[#*_`]+/g, "").replace(/\s+/g, " ").trim();
}

export function sentences(text: string) {
  return text.match(/[^.!?]+(?:[.!?]+(?=\s|$)|$)/g)?.map((s) => s.trim()).filter(Boolean) ?? (text ? [text] : []);
}

/** Whole sentences up to `max` characters (at most `n`). Always keeps the first sentence complete; never cuts mid-sentence or adds an ellipsis. */
export function wholeSentences(text: string, max = 260, n = 3) {
  let out = "";
  for (const sentence of sentences(text).slice(0, n)) {
    const next = out ? `${out} ${sentence}` : sentence;
    if (out && next.length > max) break;
    out = next;
  }
  return out;
}

export function sourceTitle(item: Evidence) {
  for (const value of [item.originalHeadline, item.title]) {
    const title = readableText(value);
    if (title && !/^\d+$/.test(title) && !/^reporting related to/i.test(title)) return title;
  }
  return "Title unavailable";
}

export function hasEditorialImage(item: Evidence) {
  return Boolean(item.imageUrl && !/(?:logo|favicon|placeholder|default[-_]?image|avatar)/i.test(item.imageUrl));
}

export function sourceGroups(evidence: Evidence[]) {
  const groups: Evidence[][] = [];
  const keys = new Map<string, Evidence[]>();
  for (const item of evidence) {
    const title = sourceTitle(item);
    // Group identical headlines without assuming that different publishers
    // constitute independent corroboration. Every original record is retained.
    const key = title === "Title unavailable" ? `id:${item.id}` : title.toLowerCase().replace(/\s+-\s+(?:abc(?:\d+| news)\b[^-]*|khbs)$/i, "").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
    const group = keys.get(key);
    if (group) group.push(item);
    else { const next = [item]; keys.set(key, next); groups.push(next); }
  }
  return groups.sort((a, b) => Number(b.some((item) => item.sourceClass === "primary")) - Number(a.some((item) => item.sourceClass === "primary")) || (Date.parse(b[0].publishedAt) || 0) - (Date.parse(a[0].publishedAt) || 0));
}

export function developmentContext(data: WorldShiftSnapshot, change: IntelligencePoint) {
  const records = data.evidence.filter((item) => change.evidenceIds.includes(item.id));
  const events = (data.shift.overview.timeline ?? []).map((event) => ({ event, overlap: event.evidenceIds.filter((id) => change.evidenceIds.includes(id)).length }))
    .filter(({ overlap }) => overlap > 0).sort((a, b) => b.overlap - a.overlap);
  // Only label a development with a stored event title when the linked source
  // sets match; shared sources alone do not prove the same event or date.
  const exact = events.filter(({ event }) => event.evidenceIds.length === change.evidenceIds.length && event.evidenceIds.every((id) => change.evidenceIds.includes(id)));
  const event = exact.length === 1 ? exact[0].event : undefined;
  return { records, event };
}
