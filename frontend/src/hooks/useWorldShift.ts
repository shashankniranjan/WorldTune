"use client";
import { useEffect } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { getWorldShift } from "@/api/worldShifts";
import { SnapshotMismatchError } from "@/api/worldShifts";
import type { PersonaId } from "@/types/worldShift";

export const useWorldShift = (id: string, persona: PersonaId, snapshotId?: string) => {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["world-shift", id, persona, snapshotId],
    queryFn: () => getWorldShift(id, persona, snapshotId),
    enabled: Boolean(id && snapshotId),
    staleTime: 60 * 60 * 1000,
    placeholderData: keepPreviousData,
    retry: false,
  });
  const mismatch = query.error instanceof SnapshotMismatchError;
  useEffect(() => {
    if (mismatch) {
      // A background publication can happen between list and detail requests.
      // Refresh the list snapshot; the changed query key then reloads detail.
      void client.invalidateQueries({ queryKey: ["world-shifts"] });
    }
  }, [client, mismatch]);
  return query;
};
