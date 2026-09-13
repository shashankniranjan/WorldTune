import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  STATE_CLASSES,
  STATE_SCORE_CLASSES,
  directionClasses,
  scoreState,
} from "@/lib/score";
import type { TrajectoryDirection } from "@/lib/api";

export function StateBadge({ score, className }: { score: number; className?: string }) {
  const state = scoreState(score);
  return <Badge className={cn(STATE_CLASSES[state], className)}>{state}</Badge>;
}

export function DirectionBadge({
  direction,
  className,
}: {
  direction?: TrajectoryDirection | string | null;
  className?: string;
}) {
  if (!direction) return null;
  return (
    <Badge className={cn(directionClasses(direction), className)}>{direction}</Badge>
  );
}

export function ScoreNumber({
  score,
  size = "md",
  className,
}: {
  score: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const state = scoreState(score);
  const sizes = {
    sm: "text-2xl",
    md: "text-4xl",
    lg: "text-6xl",
  } as const;
  return (
    <span
      className={cn(
        "display tabular font-bold leading-none",
        sizes[size],
        STATE_SCORE_CLASSES[state],
        className,
      )}
    >
      {score.toFixed(1)}
    </span>
  );
}
