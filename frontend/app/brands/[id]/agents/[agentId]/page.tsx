"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RunningWork } from "@/components/RunningWork";
import { Shell, money, pill } from "@/components/Shell";
import { WorkLoader } from "@/components/WorkLoader";
import { Agent, api, Run, Skill } from "@/lib/api";

export default function AgentPage() {
  const { id, agentId } = useParams<{ id: string; agentId: string }>();
  const qc = useQueryClient();
  const { data: agent } = useQuery({
    queryKey: ["agent", id, agentId],
    queryFn: () => api<Agent>(`/brands/${id}/agents/${agentId}`),
  });
  const { data: runs = [] } = useQuery({
    queryKey: ["runs", id, agentId],
    queryFn: () => api<Run[]>(`/brands/${id}/runs?agent_id=${agentId}&include_heavy=true`),
    refetchInterval: 8000,
    refetchIntervalInBackground: false,
  });
  const { data: skills = [] } = useQuery({
    queryKey: ["skills"],
    queryFn: () => api<Skill[]>("/skills"),
  });

  const action = useMutation({
    mutationFn: (path: string) => api(`/brands/${id}/agents/${agentId}/${path}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agent", id, agentId] });
      qc.invalidateQueries({ queryKey: ["runs", id, agentId] });
    },
  });

  return (
    <Shell brandId={id}>
      <RunningWork brandId={id} />
      {action.isPending && <WorkLoader label="Sending command" />}
      <Link href={`/brands/${id}`} className="text-sm text-clay">
        ← Org
      </Link>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl">{agent?.title}</h1>
          <p className="mt-2 text-ink/60">
            {agent?.role} · {agent?.adapter} · {agent?.model}
          </p>
        </div>
        {agent && (
          <div className="text-right">
            {pill(agent.status)}
            <div className="mt-2 font-serif text-2xl">
              {money(agent.spent_usd)}
              <span className="text-base text-ink/40"> / {money(agent.monthly_budget_usd)}</span>
            </div>
          </div>
        )}
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        <button className="btn-primary" onClick={() => action.mutate("heartbeat")}>
          Wake now
        </button>
        <button className="btn-ghost" onClick={() => action.mutate("pause")}>
          Pause
        </button>
        <button className="btn-ghost" onClick={() => action.mutate("resume")}>
          Resume
        </button>
        <button className="btn-ghost" onClick={() => action.mutate("terminate")}>
          Terminate
        </button>
      </div>

      <div className="mt-10 grid gap-6 md:grid-cols-2">
        <section className="card p-6">
          <h2 className="font-serif text-2xl">Briefing</h2>
          <p className="mt-3 text-sm leading-6 text-ink/75">{agent?.system_prompt}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {agent?.skill_slugs.map((slug) => {
              const skill = skills.find((s) => s.slug === slug);
              return (
                <span key={slug} className="rounded-full bg-rose/10 px-3 py-1 text-xs text-rose">
                  {skill?.name || slug}
                </span>
              );
            })}
          </div>
        </section>
        <section>
          <h2 className="font-serif text-2xl">Heartbeat log</h2>
          <div className="mt-4 space-y-3">
            {runs.map((run) => (
              <article key={run.id} className="card p-5 text-sm">
                <div className="flex items-center justify-between">
                  {pill(run.status)}
                  <span className="text-ink/40">{new Date(run.created_at).toLocaleString()}</span>
                </div>
                <p className="mt-2">{run.result_summary}</p>
                <p className="mt-2 text-xs text-ink/45">
                  {run.trigger} · {run.tokens_in}/{run.tokens_out} · ${run.cost_usd}
                </p>
                {!!run.trace?.length && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-ink/50">Trace</summary>
                    <pre className="mt-2 max-h-48 overflow-auto text-xs">
                      {JSON.stringify(run.trace, null, 2)}
                    </pre>
                  </details>
                )}
              </article>
            ))}
            {runs.length === 0 && <p className="text-sm text-ink/50">No runs yet.</p>}
          </div>
        </section>
      </div>
    </Shell>
  );
}
