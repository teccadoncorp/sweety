"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { RunningWork } from "@/components/RunningWork";
import { Shell, money, pill } from "@/components/Shell";
import { WorkInline, WorkLoader } from "@/components/WorkLoader";
import { Agent, api, Approval, Brand, Campaign } from "@/lib/api";

export default function BrandPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { data: brand, isLoading } = useQuery({
    queryKey: ["brand", id],
    queryFn: () => api<Brand>(`/brands/${id}`),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ["agents", id],
    queryFn: () => api<Agent[]>(`/brands/${id}/agents`),
  });
  const { data: campaigns = [] } = useQuery({
    queryKey: ["campaigns", id],
    queryFn: () => api<Campaign[]>(`/brands/${id}/campaigns`),
  });
  const { data: approvals = [] } = useQuery({
    queryKey: ["approvals", id],
    queryFn: () => api<Approval[]>(`/brands/${id}/approvals`),
  });

  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [memory, setMemory] = useState({ mission: "", voice_notes: "", audience: "", guidelines: "" });

  useEffect(() => {
    if (!brand) return;
    setMemory({
      mission: brand.mission || "",
      voice_notes: brand.voice_notes || "",
      audience: brand.audience || "",
      guidelines: brand.guidelines || "",
    });
  }, [brand]);

  const createCampaign = useMutation({
    mutationFn: () =>
      api<Campaign>(`/brands/${id}/campaigns`, {
        method: "POST",
        body: JSON.stringify({ name, goal }),
      }),
    onSuccess: () => {
      setName("");
      setGoal("");
      qc.invalidateQueries({ queryKey: ["campaigns", id] });
    },
  });

  const saveMemory = useMutation({
    mutationFn: () =>
      api(`/brands/${id}`, {
        method: "PATCH",
        body: JSON.stringify(memory),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brand", id] }),
  });

  const decide = useMutation({
    mutationFn: ({ approvalId, status }: { approvalId: string; status: string }) =>
      api(`/brands/${id}/approvals/${approvalId}/decide`, {
        method: "POST",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals", id] });
      qc.invalidateQueries({ queryKey: ["campaigns", id] });
    },
  });

  const wake = useMutation({
    mutationFn: (agentId: string) =>
      api(`/brands/${id}/agents/${agentId}/heartbeat`, { method: "POST" }),
  });
  const swarm = useMutation({
    mutationFn: () => api<{ queued: number }>(`/brands/${id}/agents/wake-all`, { method: "POST" }),
  });
  const expand = useMutation({
    mutationFn: () => api<Agent[]>(`/brands/${id}/agents/expand`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents", id] }),
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    if (name.trim() && goal.trim()) createCampaign.mutate();
  }

  const cmo = agents.find((a) => a.role === "cmo");

  return (
    <Shell brandId={id}>
      {isLoading && <WorkInline label="Loading brand" />}
      <RunningWork brandId={id} />
      {(wake.isPending || createCampaign.isPending || swarm.isPending || expand.isPending) && (
        <WorkLoader
          label={
            swarm.isPending ? "Waking swarm" : expand.isPending ? "Expanding org" : wake.isPending ? "Waking agent" : "Creating campaign"
          }
        />
      )}
      <div className="mb-8 flex flex-wrap gap-3">
        <Link href={`/brands/${id}/godmode`} className="btn-primary">
          CMO God Mode
        </Link>
        <Link href={`/brands/${id}/approvals`} className="btn-ghost">
          Approvals
        </Link>
        <Link href={`/brands/${id}/calendar`} className="btn-ghost">
          Calendar
        </Link>
        <Link href={`/brands/${id}/crm`} className="btn-ghost">
          Neural CRM
        </Link>
        <Link href={`/brands/${id}/command`} className="btn-ghost">
          Command radar
        </Link>
        <Link href={`/brands/${id}/studio`} className="btn-ghost">
          Agent studio
        </Link>
        <Link href={`/brands/${id}/connect`} className="btn-ghost">
          Connectors
        </Link>
        <button className="btn-ghost" onClick={() => swarm.mutate()}>
          Wake all agents
        </button>
        <button className="btn-ghost" onClick={() => expand.mutate()}>
          Expand org
        </button>
        {swarm.data && <span className="self-center text-sm text-moss">{swarm.data.queued} queued</span>}
      </div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm uppercase tracking-[0.18em] text-clay">Brand</p>
          <h1 className="mt-1 break-words font-serif text-3xl sm:text-4xl lg:text-5xl">{brand?.name || "…"}</h1>
          <p className="mt-3 max-w-2xl text-ink/70">{brand?.mission}</p>
        </div>
        {brand && (
          <div className="w-full min-w-0 sm:w-auto sm:text-right">
            <Link href={`/brands/${id}/connect`} className="mb-2 block text-sm text-cyan">
              Social connectors
            </Link>
            <div className="text-sm text-ink/50">Monthly burn</div>
            <div className="font-serif text-2xl sm:text-3xl">
              {money(brand.spent_usd)}
              <span className="text-lg text-ink/40"> / {money(brand.monthly_budget_usd)}</span>
            </div>
          </div>
        )}
      </div>

      {brand && (
        <form
          className="card mt-8 space-y-3 p-5"
          onSubmit={(e) => {
            e.preventDefault();
            saveMemory.mutate();
          }}
        >
          <h2 className="font-serif text-2xl">Brand memory</h2>
          <p className="text-sm text-ink/60">Feeds every agent prompt. Keep this current.</p>
          <textarea
            className="field min-h-16"
            placeholder="Mission"
            value={memory.mission}
            onChange={(e) => setMemory((m) => ({ ...m, mission: e.target.value }))}
          />
          <textarea
            className="field min-h-16"
            placeholder="Voice / tone"
            value={memory.voice_notes}
            onChange={(e) => setMemory((m) => ({ ...m, voice_notes: e.target.value }))}
          />
          <textarea
            className="field min-h-16"
            placeholder="Audience"
            value={memory.audience}
            onChange={(e) => setMemory((m) => ({ ...m, audience: e.target.value }))}
          />
          <textarea
            className="field min-h-16"
            placeholder="Do's / don'ts"
            value={memory.guidelines}
            onChange={(e) => setMemory((m) => ({ ...m, guidelines: e.target.value }))}
          />
          <button className="btn-primary" type="submit" disabled={saveMemory.isPending}>
            Save brand memory
          </button>
        </form>
      )}

      {brand && (
        <section className="card mt-4 grid gap-4 p-5 md:grid-cols-3">
          <div>
            <div className="text-xs uppercase tracking-wide text-clay">Website</div>
            <div className="mt-1 break-all text-sm">{brand.website_url || "Optional — not set"}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-clay">App</div>
            <div className="mt-1 break-all text-sm">{brand.app_url || "Optional — not set"}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-clay">Logo</div>
            <div className="mt-1 text-sm">{brand.logo_url ? "Uploaded" : "Optional — not set"}</div>
          </div>
        </section>
      )}

      <section className="mt-10">
        <h2 className="font-serif text-2xl sm:text-3xl">Org chart · {agents.length} agents</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {agents.map((agent) => (
            <div key={agent.id} className="card min-w-0 p-5">
              <div className="flex items-start justify-between gap-2">
                <Link href={`/brands/${id}/agents/${agent.id}`} className="min-w-0 break-words font-serif text-xl sm:text-2xl">
                  {agent.title}
                </Link>
                {pill(agent.status)}
              </div>
              <p className="mt-1 text-xs uppercase tracking-wide text-ink/50">{agent.role}</p>
              <p className="mt-2 text-sm text-ink/60">
                {agent.adapter} · {agent.model}
              </p>
              <p className="mt-1 text-sm text-ink/50">
                {money(agent.spent_usd)} / {money(agent.monthly_budget_usd)}
              </p>
              <button className="btn-ghost mt-4" onClick={() => wake.mutate(agent.id)} disabled={wake.isPending}>
                Wake agent
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12 grid gap-6 md:grid-cols-2">
        <div className="min-w-0">
          <h2 className="font-serif text-2xl sm:text-3xl">Campaigns</h2>
          <div className="mt-4 space-y-3">
            {campaigns.map((c) => (
              <Link key={c.id} href={`/brands/${id}/campaigns/${c.id}`} className="card block min-w-0 p-5 hover:bg-paper">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="min-w-0 break-words font-serif text-xl sm:text-2xl">{c.name}</h3>
                  {pill(c.status)}
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-ink/70">{c.goal}</p>
              </Link>
            ))}
          </div>
          <form onSubmit={onCreate} className="card mt-4 space-y-3 p-5">
            <h3 className="font-medium">New campaign</h3>
            <input className="field" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <textarea className="field min-h-20" placeholder="Goal" value={goal} onChange={(e) => setGoal(e.target.value)} />
            <div className="flex gap-2">
              <button className="btn-primary" type="submit">
                Create
              </button>
              {cmo && (
                <button type="button" className="btn-ghost" onClick={() => wake.mutate(cmo.id)}>
                  Then wake CMO
                </button>
              )}
            </div>
          </form>
        </div>
        <div className="min-w-0">
          <div className="flex items-end justify-between gap-3">
            <h2 className="font-serif text-2xl sm:text-3xl">Approvals</h2>
            <Link href={`/brands/${id}/approvals`} className="text-sm text-cyan">
              Open queue →
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {approvals.length === 0 && <p className="text-sm text-ink/50">Nothing waiting on the board.</p>}
            {approvals.map((a) => (
              <div key={a.id} className="card p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{a.kind.replaceAll("_", " ")}</span>
                  {pill(a.status)}
                </div>
                <p className="mt-2 text-sm text-ink/70">{a.payload?.summary || "—"}</p>
                {a.status === "pending" && (
                  <div className="mt-3 flex gap-2">
                    <button className="btn-primary" onClick={() => decide.mutate({ approvalId: a.id, status: "approved" })}>
                      Approve
                    </button>
                    <button className="btn-ghost" onClick={() => decide.mutate({ approvalId: a.id, status: "rejected" })}>
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    </Shell>
  );
}
