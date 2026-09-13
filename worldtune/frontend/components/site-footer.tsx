"use client";

import { useQuery } from "@tanstack/react-query";
import { api, queryKeys } from "@/lib/api";

/**
 * The disclaimer is rendered VERBATIM from the API payload — it is a
 * non-negotiable spec requirement, not decoration.
 */
export function SiteFooter() {
  const { data } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => api.dashboard(),
  });

  return (
    <footer className="border-t border-hairline bg-elevated/40">
      <div className="mx-auto w-full max-w-6xl px-5 py-6">
        <div className="flex flex-wrap items-center gap-3 text-xs text-dim">
          <span className="eyebrow">
            {data?.demo_mode === undefined
              ? "Mode unknown"
              : data.demo_mode
                ? "Demo mode · on"
                : "Live mode"}
          </span>
          {data?.model_version ? <span>Model {data.model_version}</span> : null}
          {data?.generated_at ? (
            <span>Generated {new Date(data.generated_at).toLocaleString("en-GB")}</span>
          ) : null}
        </div>
        <p className="mt-3 max-w-3xl text-xs leading-relaxed text-muted">
          {data?.disclaimer ??
            "Research prototype. Directional accuracy and calibration are diagnostics only; WorldTune makes no profitability claim and this is not investment or career advice."}
        </p>
      </div>
    </footer>
  );
}
