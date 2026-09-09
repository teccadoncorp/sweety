"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RunningWork } from "@/components/RunningWork";
import { Shell, pill } from "@/components/Shell";
import { WorkLoader } from "@/components/WorkLoader";
import { Agent, api, Artifact, Campaign, SwarmQueued, Task } from "@/lib/api";

const COLUMNS = ["backlog", "ready", "checked_out", "review", "done", "blocked"] as const;

export default function CampaignPage() {
  const { id, campaignId } = useParams<{ id: string; campaignId: string }>();
  const qc = useQueryClient();
  const { data: campaign } = useQuery({
    queryKey: ["campaign", id, campaignId],
    queryFn: () => api<Campaign>(`/brands/${id}/campaigns/${campaignId}`),
  });
  const { data: tasks = [] } = useQuery({
    queryKey: ["tasks", id, campaignId],
    queryFn: () => api<Task[]>(`/brands/${id}/tasks?campaign_id=${campaignId}`),
  });
  const { data: artifacts = [] } = useQuery({
    queryKey: ["artifacts", id, campaignId],
    queryFn: () => api<Artifact[]>(`/brands/${id}/artifacts?campaign_id=${campaignId}`),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ["agents", id],
    queryFn: () => api<Agent[]>(`/brands/${id}/agents`),
  });

  const act = useMutation({
    mutationFn: (action: "approve" | "pause") =>
      api(`/brands/${id}/campaigns/${campaignId}/${action}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaign", id, campaignId] }),
  });
  const runTeam = useMutation({
    mutationFn: () => api<SwarmQueued>(`/brands/${id}/campaigns/${campaignId}/run-team`, { method: "POST" }),
  });

  function agentName(agentId: string | null) {
    return agents.find((a) => a.id === agentId)?.title || "Unassigned";
  }

  return (
    <Shell brandId={id}>
      <RunningWork brandId={id} />
      {runTeam.isPending && <WorkLoader label="Waking campaign team" />}
      <Link href={`/brands/${id}`} className="text-sm text-ink/50">
        ← Org
      </Link>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl">{campaign?.name}</h1>
          <p className="mt-3 max-w-2xl text-ink/70">{campaign?.goal}</p>
        </div>
        <div className="flex items-center gap-2">
          {campaign && pill(campaign.status)}
          <button className="btn-primary" onClick={() => runTeam.mutate()}>
            Run team
          </button>
          <button className="btn-ghost" onClick={() => act.mutate("approve")}>
            Approve
          </button>
          <button className="btn-ghost" onClick={() => act.mutate("pause")}>
            Pause
          </button>
        </div>
      </div>
      {runTeam.data && <p className="mt-3 text-sm text-moss">{runTeam.data.queued} agents queued for this campaign</p>}

      {campaign?.brief && (
        <section className="card mt-8 p-6">
          <h2 className="font-serif text-2xl">Brief</h2>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-6 text-ink/80">{campaign.brief}</pre>
        </section>
      )}

      <section className="mt-10">
        <h2 className="font-serif text-3xl">Board</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {COLUMNS.map((col) => (
            <div key={col} className="rounded-2xl bg-ink/[0.03] p-3">
              <div className="mb-2 text-xs uppercase tracking-wide text-ink/50">{col.replaceAll("_", " ")}</div>
              <div className="space-y-2">
                {tasks
                  .filter((t) => t.status === col)
                  .map((t) => (
                    <Link
                      key={t.id}
                      href={`/brands/${id}/tasks/${t.id}`}
                      className="block rounded-xl bg-white p-3 text-sm shadow-sm"
                    >
                      <div className="font-medium">{t.title}</div>
                      <div className="mt-1 text-xs text-ink/50">{agentName(t.assignee_agent_id)}</div>
                    </Link>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="font-serif text-3xl">Artifacts</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {artifacts.map((art) => (
            <article key={art.id} className="card p-5">
              <div className="text-xs uppercase text-ink/50">{art.kind}</div>
              <h3 className="mt-1 font-serif text-2xl">{art.title}</h3>
              <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap font-sans text-sm text-ink/75">
                {art.content}
              </pre>
            </article>
          ))}
          {artifacts.length === 0 && <p className="text-sm text-ink/50">No artifacts yet. Wake the CMO.</p>}
        </div>
      </section>
    </Shell>
  );
}
