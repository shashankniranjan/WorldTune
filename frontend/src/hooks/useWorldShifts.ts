"use client";
import { useQuery } from "@tanstack/react-query";
import { getWorldShifts } from "@/api/worldShifts";
import { getRefreshConfiguration } from "@/api/worldShifts";
export const useWorldShifts = () => {
  const config = useQuery({ queryKey: ["refresh-configuration"], queryFn: getRefreshConfiguration, staleTime: 30_000 });
  return useQuery({
    queryKey: ["world-shifts"],
    queryFn: getWorldShifts,
    staleTime: Math.min(5 * 60 * 1000, (config.data?.intervalSeconds ?? 300) * 1000),
    refetchInterval: (config.data?.intervalSeconds ?? 300) * 1000,
    refetchOnWindowFocus: true,
  });
};
