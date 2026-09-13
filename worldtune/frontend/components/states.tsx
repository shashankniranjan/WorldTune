"use client";

import { Button } from "@/components/ui/button";

export function ErrorState({
  title = "Could not load this view",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-md border border-red-500/30 bg-red-500/5 p-6">
      <p className="display text-sm font-semibold text-red-300">{title}</p>
      <p className="mt-2 max-w-xl text-sm text-muted">{message}</p>
      {onRetry ? (
        <Button variant="outline" className="mt-4" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-dashed border-hairline-strong bg-panel/40 p-6 text-sm text-dim">
      {message}
    </div>
  );
}
