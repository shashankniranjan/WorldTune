export function pct(value: number | undefined | null, digits = 2): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  const v = value * 100;
  return `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

export function num(value: number | undefined | null, digits = 2): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function signedNum(value: number | undefined | null, digits = 2): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value > 0 ? "+" : ""}${num(value, digits)}`;
}

export function changeClass(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "text-slate-400";
  if (value > 0) return "text-emerald-400";
  if (value < 0) return "text-red-400";
  return "text-slate-400";
}

export function salary(
  min: number | null,
  max: number | null,
  currency: string | null,
): string | null {
  if (!min && !max) return null;
  const fmt = (v: number) =>
    v >= 100000 ? `${(v / 100000).toFixed(1)}L` : v.toLocaleString("en-IN");
  const cur = currency ?? "";
  if (min && max) return `${cur} ${fmt(min)} – ${fmt(max)}`;
  return `${cur} ${fmt((min ?? max) as number)}`;
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diff = Date.now() - then;
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function longDate(date: Date): string {
  return date.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function greeting(date: Date): string {
  const h = date.getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}
