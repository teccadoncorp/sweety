"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Brand } from "@/lib/api";

export function KillSwitch({ brandId, compact = false }: { brandId: string; compact?: boolean }) {
  const qc = useQueryClient();
  const { data: brand } = useQuery({
    queryKey: ["brand", brandId],
    queryFn: () => api<Brand>(`/brands/${brandId}`),
  });
  const paused = Boolean(brand?.agents_paused);
  const toggle = useMutation({
    mutationFn: (next: boolean) =>
      api<Brand>(`/brands/${brandId}/kill-switch`, {
        method: "POST",
        body: JSON.stringify({ paused: next }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["brand", brandId] });
      qc.invalidateQueries({ queryKey: ["command", brandId] });
    },
  });
  if (!brand) return null;
  return (
    <button
      type="button"
      className={paused ? "btn-primary" : compact ? "text-violet hover:text-ink" : "btn-ghost text-violet"}
      onClick={() => toggle.mutate(!paused)}
      disabled={toggle.isPending}
    >
      {paused ? (compact ? "Resume" : "Resume all agents") : compact ? "Kill" : "Kill switch"}
    </button>
  );
}
