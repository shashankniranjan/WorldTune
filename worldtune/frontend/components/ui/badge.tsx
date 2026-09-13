import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "display inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] whitespace-nowrap",
        "border-hairline-strong bg-elevated text-muted",
        className,
      )}
      {...props}
    />
  );
}
