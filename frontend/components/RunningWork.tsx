"use client";

import { useQuery } from "@tanstack/react-query";
import { WorkInline } from "@/components/WorkLoader";
import { api, Run } from "@/lib/api";

export function RunningWork({ brandId }: { brandId: string }) {
  const { data: runs = [] } = useQuery({
    queryKey: ["runs", brandId, "live"],
    queryFn: () => api<Run[]>(`/brands/${brandId}/runs`),
    refetchInterval: 4000,
  });
  const live = runs.filter((r) => r.status === "running");
  if (!live.length) return null;
  return (
    <div className="mb-6">
      <WorkInline label={`${live.length} agents running in parallel`} />
    </div>
  );
}
