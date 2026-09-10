"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RunningWork } from "@/components/RunningWork";
import { Shell, money, pill } from "@/components/Shell";
import { WorkLoader } from "@/components/WorkLoader";
import { api, CommandSnapshot, SwarmQueued } from "@/lib/api";

export default function CommandPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["command", id],
    queryFn: () => api<CommandSnapshot>(`/brands/${id}/command`),
    refetchInterval: 8000,
    refetchIntervalInBackground: false,
  });
  const swarm = useMutation({
    mutationFn: () => api<SwarmQueued>(`/brands/${id}/agents/wake-all`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["command", id] }),
  });
  const wake = useMutation({
    mutationFn: (agentId: string) => api(`/brands/${id}/agents/${agentId}/heartbeat`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["command", id] }),
  });
  const expand = useMutation({
    mutationFn: () => api(`/brands/${id}/agents/expand`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["command", id] }),
  });

  const agents = data?.agents || [];

  return (
    <Shell brandId={id}>
      <RunningWork brandId={id} />
      {(swarm.isPending || wake.isPending || expand.isPending) && (
        <WorkLoader label={swarm.isPending ? "Dispatching swarm" : "Sending pulse"} />
      )}
      <p className="text-xs uppercase tracking-[0.28em] text-cyan">Console</p>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl">Command</h1>
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" onClick={() => swarm.mutate()} disabled={Boolean(data?.agents_paused)}>
            Wake all
          </button>
          <button className="btn-ghost" onClick={() => expand.mutate()}>
            Expand org
          </button>
        </div>
      </div>
      {data?.agents_paused && (
        <p className="mt-3 rounded-lg bg-violet/10 px-3 py-2 text-sm text-violet">
          Kill switch is on. Every agent is paused until you resume.
        </p>
      )}
      {swarm.data && <p className="mt-3 text-sm text-moss">{swarm.data.queued} agents queued{swarm.data.reason ? ` — ${swarm.data.reason}` : ""}</p>}

      <section className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "Live runs", value: data?.live_runs ?? 0, href: `/brands/${id}/command` },
          { label: "Open tasks", value: data?.ready_tasks ?? 0, href: `/brands/${id}` },
          { label: "Approvals", value: data?.pending_approvals ?? 0, href: `/brands/${id}/approvals` },
          { label: "Hot CRM", value: data?.crm_hot ?? 0, href: `/brands/${id}/crm?tab=contacts&temp=hot` },
        ].map((tile) => (
          <Link key={tile.label} href={tile.href} className="hud-glow card min-w-0 p-4 hover:bg-paper">
            <div className="text-[11px] uppercase tracking-[0.18em] text-clay">{tile.label}</div>
            <div className="mt-2 font-serif text-3xl text-cyan sm:text-4xl">{tile.value}</div>
            <div className="signal-bar mt-3" />
          </Link>
        ))}
      </section>

      <section className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent) => (
          <article key={agent.id} className={`card min-w-0 p-5 ${agent.live ? "border-cyan/40" : ""}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <Link href={`/brands/${id}/agents/${agent.id}`} className="break-words font-serif text-xl sm:text-2xl">
                  {agent.title}
                </Link>
                <p className="text-xs uppercase tracking-wide text-clay">{agent.role}</p>
              </div>
              <div className="flex items-center gap-2">
                {agent.live && <span className="h-2 w-2 animate-pulse rounded-full bg-cyan" />}
                {pill(agent.live ? "running" : agent.status)}
              </div>
            </div>
            <p className="mt-3 text-xs text-clay">
              inbox {agent.inbox} · {agent.skill_count} skills · {agent.model}
            </p>
            <p className="mt-1 text-xs text-ink/50">
              {money(agent.spent_usd)}
              {agent.last_heartbeat_at ? ` · last ${new Date(agent.last_heartbeat_at).toLocaleTimeString()}` : " · never woke"}
            </p>
            {agent.last_summary && (
              <p className="mt-3 line-clamp-3 text-sm text-ink/70">{agent.last_summary}</p>
            )}
            <button className="btn-ghost mt-4" onClick={() => wake.mutate(agent.id)} disabled={wake.isPending || Boolean(data?.agents_paused)}>
              Pulse
            </button>
          </article>
        ))}
      </section>
    </Shell>
  );
}
