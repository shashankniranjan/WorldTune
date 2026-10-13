"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getCurrentWorldShiftRefresh, getRefreshConfiguration, startWorldShiftRefresh, updateRefreshConfiguration } from "@/api/worldShifts";
import type { RefreshConfiguration } from "@/types/worldShift";

const CURRENT = ["world-shift-refresh", "current"];
const FINISHED_VISIBLE_MS = 10 * 60_000;

/**
 * Refreshes are platform-wide, so the backend is the only source of truth:
 * every page, tab and browser polls the same "current run" and shows the same
 * progress, whichever shift it is on and however long ago it was started.
 */
export function useWorldShiftRefresh(displayedSnapshotId?: string) {
  const client = useQueryClient();
  const configuration = useQuery({ queryKey: ["refresh-configuration"], queryFn: getRefreshConfiguration, staleTime: 30_000 });
  const configure = useMutation({
    mutationFn: (value: Pick<RefreshConfiguration, "intervalSeconds" | "webResearchEnabled" | "webResultsPerShift">) => updateRefreshConfiguration(value),
    onSuccess: (value) => client.setQueryData(["refresh-configuration"], value),
  });
  const current = useQuery({
    queryKey: CURRENT,
    queryFn: getCurrentWorldShiftRefresh,
    // Fast while a run is active; slow otherwise so a refresh started elsewhere still shows up.
    refetchInterval: (query) => ["queued", "running"].includes(query.state.data?.status ?? "") ? 1500 : 10_000,
  });
  const mutation = useMutation({
    mutationFn: (shiftId?: string) => startWorldShiftRefresh(shiftId),
    onSuccess: (status) => client.setQueryData(CURRENT, status),
  });
  const run = current.data ?? null;
  const active = run?.status === "queued" || run?.status === "running";
  // A finished run is only news until the page shows its snapshot (completed) or for a while (failed).
  const recentlyFinished = run?.status === "failed" && Date.now() - Date.parse(run.updatedAt ?? "") < FINISHED_VISIBLE_MS;
  const newSnapshotReady = run?.status === "completed" && Boolean(run.newSnapshotId) && run.newSnapshotId !== displayedSnapshotId;
  const status = active || newSnapshotReady || recentlyFinished ? run ?? undefined : undefined;
  const loadSnapshot = async () => {
    // Remove pinned detail queries before changing the list snapshot. This
    // prevents a stale detail request from briefly receiving SNAPSHOT_MISMATCH
    // while the new ACTIVE snapshot is being loaded.
    client.removeQueries({ queryKey: ["world-shift"] });
    client.removeQueries({ queryKey: ["relationships"] });
    client.removeQueries({ queryKey: ["evidence"] });
    await Promise.all([
      client.invalidateQueries({ queryKey: ["world-shifts"] }),
      client.invalidateQueries({ queryKey: ["world-shift"] }),
      client.invalidateQueries({ queryKey: ["relationships"] }),
      client.invalidateQueries({ queryKey: ["evidence"] }),
    ]);
  };
  return { start: mutation.mutate, starting: mutation.isPending, error: mutation.error, status, activeShiftId: active ? run?.shiftId ?? undefined : undefined, loadSnapshot, configuration: configuration.data, configure: configure.mutate, configuring: configure.isPending, configurationError: configure.error };
}
