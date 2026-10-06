import { AlertCircle, ArrowDownRight, ArrowUpRight, CircleHelp } from "lucide-react";
import { directionClass, statusClass } from "@/config/statuses";
import type { Direction, ShiftStatus } from "@/types/worldShift";
export function StatusBadge({ status }: { status: ShiftStatus }) { return <span className={`rounded-sm px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClass[status]}`}>{status}</span>; }
export function DirectionIndicator({ direction }: { direction?: Direction | null }) { if (!direction) return null; const Icon = direction === "negative" || direction === "down" ? ArrowDownRight : direction === "positive" || direction === "up" ? ArrowUpRight : CircleHelp; return <span className={`inline-flex items-center gap-1 text-xs capitalize ${directionClass[direction]}`}><Icon size={13} />{direction}</span>; }
export function EmptyState({ children }: { children: React.ReactNode }) { return <div className="card text-center muted">{children}</div>; }
export function ErrorState({ error }: { error: Error }) { return <div className="card flex gap-2 text-rose-300"><AlertCircle size={18} />{error.message}</div>; }
export function LoadingSkeleton() { return <div className="card animate-pulse space-y-3"><div className="h-5 w-1/3 rounded bg-slate-700" /><div className="h-3 rounded bg-slate-700" /><div className="h-3 w-2/3 rounded bg-slate-700" /></div>; }
