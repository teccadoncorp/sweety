"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Shell, pill } from "@/components/Shell";
import { Agent, api, Artifact, Run, Task } from "@/lib/api";

export default function TaskPage() {
  const { id, taskId } = useParams<{ id: string; taskId: string }>();
  const qc = useQueryClient();
  const { data: task } = useQuery({
    queryKey: ["task", id, taskId],
    queryFn: () => api<Task>(`/brands/${id}/tasks/${taskId}`),
  });
  const { data: artifacts = [] } = useQuery({
    queryKey: ["artifacts", id, "task", taskId],
    queryFn: () => api<Artifact[]>(`/brands/${id}/artifacts?task_id=${taskId}`),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ["agents", id],
    queryFn: () => api<Agent[]>(`/brands/${id}/agents`),
  });
  const { data: runs = [] } = useQuery({
    queryKey: ["runs", id],
    queryFn: () => api<Run[]>(`/brands/${id}/runs`),
  });

  const move = useMutation({
    mutationFn: (status: string) =>
      api(`/brands/${id}/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["task", id, taskId] }),
  });
  const release = useMutation({
    mutationFn: () => api(`/brands/${id}/tasks/${taskId}/release`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["task", id, taskId] }),
  });

  const assignee = agents.find((a) => a.id === task?.assignee_agent_id);
  const relatedRuns = runs.filter((r) => r.agent_id === task?.assignee_agent_id).slice(0, 5);

  return (
    <Shell brandId={id}>
      {task && (
        <Link href={`/brands/${id}/campaigns/${task.campaign_id}`} className="text-sm text-ink/50">
          ← Campaign
        </Link>
      )}
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-serif text-5xl">{task?.title}</h1>
          <p className="mt-3 max-w-2xl text-ink/70">{task?.description}</p>
          <p className="mt-2 text-sm text-ink/50">Assignee: {assignee?.title || "—"}</p>
        </div>
        {task && pill(task.status)}
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        {["ready", "review", "done", "blocked"].map((s) => (
          <button key={s} className="btn-ghost" onClick={() => move.mutate(s)}>
            Mark {s}
          </button>
        ))}
        <button className="btn-ghost" onClick={() => release.mutate()}>
          Release
        </button>
        {assignee && (
          <Link className="btn-primary" href={`/brands/${id}/agents/${assignee.id}`}>
            Open agent
          </Link>
        )}
      </div>

      <div className="mt-10 grid gap-6 md:grid-cols-2">
        <section>
          <h2 className="font-serif text-3xl">Artifacts</h2>
          <div className="mt-4 space-y-4">
            {artifacts.map((art) => (
              <article key={art.id} className="card p-5">
                <div className="text-xs uppercase text-ink/50">{art.kind}</div>
                <h3 className="font-serif text-2xl">{art.title}</h3>
                <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-6">{art.content}</pre>
              </article>
            ))}
            {artifacts.length === 0 && <p className="text-sm text-ink/50">No artifacts on this task yet.</p>}
          </div>
        </section>
        <section>
          <h2 className="font-serif text-3xl">Recent runs</h2>
          <div className="mt-4 space-y-3">
            {relatedRuns.map((run) => (
              <article key={run.id} className="card p-5 text-sm">
                <div className="flex justify-between">
                  {pill(run.status)}
                  <span className="text-ink/40">{new Date(run.created_at).toLocaleString()}</span>
                </div>
                <p className="mt-2 text-ink/80">{run.result_summary}</p>
                <p className="mt-2 text-xs text-ink/45">
                  {run.tokens_in}+{run.tokens_out} tokens · ${run.cost_usd} · {run.adapter}
                </p>
              </article>
            ))}
            {relatedRuns.length === 0 && <p className="text-sm text-ink/50">No heartbeat traces yet.</p>}
          </div>
        </section>
      </div>
    </Shell>
  );
}
