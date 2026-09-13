"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, queryKeys } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Today" },
  { href: "/persona", label: "Your profile" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const { data } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => api.dashboard(),
  });

  return (
    <header className="sticky top-0 z-20 border-b border-hairline bg-background/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="display text-lg font-bold tracking-tight">
            World<span className="text-accent">Tune</span>
          </span>
          {data?.demo_mode ? (
            <Badge className="border-amber-400/30 bg-amber-400/10 text-amber-300">
              Demo data
            </Badge>
          ) : null}
        </Link>
        <nav className="flex items-center gap-1">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded px-3 py-1.5 text-sm transition-colors",
                pathname === item.href
                  ? "bg-elevated text-foreground"
                  : "text-muted hover:text-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
