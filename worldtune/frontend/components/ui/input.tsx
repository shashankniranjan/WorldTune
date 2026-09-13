import * as React from "react";
import { cn } from "@/lib/utils";

const base =
  "w-full rounded border border-hairline bg-elevated px-3 py-2 text-sm text-foreground placeholder:text-dim outline-none transition-colors focus:border-accent/70";

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return <input className={cn(base, className)} {...props} />;
}

export function Select({ className, ...props }: React.ComponentProps<"select">) {
  return <select className={cn(base, className)} {...props} />;
}

export function Label({ className, ...props }: React.ComponentProps<"label">) {
  return (
    <label
      className={cn(
        "mb-1.5 block text-xs font-medium tracking-wide text-muted",
        className,
      )}
      {...props}
    />
  );
}
