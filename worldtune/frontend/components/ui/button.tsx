import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "ghost" | "outline";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-accent text-[#04211d] hover:bg-teal-300 font-semibold disabled:opacity-50",
  outline:
    "border border-hairline-strong bg-transparent text-foreground hover:border-accent/60 hover:text-accent",
  ghost: "bg-transparent text-muted hover:text-foreground",
};

export function Button({
  className,
  variant = "primary",
  ...props
}: React.ComponentProps<"button"> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded px-4 py-2 text-sm transition-colors disabled:cursor-not-allowed",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
