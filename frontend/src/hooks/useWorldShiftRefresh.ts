"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getRefreshConfiguration, getWorldShiftRefresh, startWorldShiftRefresh, updateRefreshConfiguration } from "@/api/worldShifts";
import type { RefreshConfiguration } from "@/types/worldShift";

export function useWorldShiftRefresh() {
  const client = useQueryClient();
  const mutation = useMutation({ mutationFn: startWorldShiftRefresh });
  const configuration = useQuery({ queryKey: ["refresh-configuration"], queryFn: getRefreshConfiguration, staleTime: 30_000 });
  const configure = useMutation({
    mutationFn: (value: Pick<RefreshConfiguration, "intervalSeconds" | "webResearchEnabled" | "webResultsPerShift">) => updateRefreshConfiguration(value),
    onSuccess: (value) => client.setQueryData(["refresh-configuration"], value),
  });
  const runId = mutation.data?.runId;
  const status = useQuery({
    queryKey: ["world-shift-refresh", runId],
    queryFn: () => getWorldShiftRefresh(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) => ["completed", "failed"].includes(query.state.data?.status ?? "") ? false : 1500,
  });
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
  return { start: mutation.mutate, starting: mutation.isPending, error: mutation.error, status: status.data ?? mutation.data, loadSnapshot, configuration: configuration.data, configure: configure.mutate, configuring: configure.isPending, configurationError: configure.error };
}
