import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded bg-white/5", className)} />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-md border border-hairline bg-panel p-5">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-8 w-40" />
      <Skeleton className="mt-4 h-3 w-full" />
      <Skeleton className="mt-2 h-3 w-5/6" />
      <Skeleton className="mt-2 h-3 w-3/5" />
    </div>
  );
}
