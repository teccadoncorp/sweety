"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { RunningWork } from "@/components/RunningWork";
import { Shell, pill } from "@/components/Shell";
import { WorkLoader } from "@/components/WorkLoader";
import { Agent, api, Skill, SwarmQueued } from "@/lib/api";

export default function StudioPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { data: agents = [] } = useQuery({
    queryKey: ["agents", id],
    queryFn: () => api<Agent[]>(`/brands/${id}/agents`),
  });
  const { data: skills = [] } = useQuery({
    queryKey: ["skills"],
    queryFn: () => api<Skill[]>("/skills"),
  });
  const [draft, setDraft] = useState<Record<string, { skills: string[]; interval: number; model: string }>>({});
  const [saved, setSaved] = useState<string | null>(null);
  const [sharedModel, setSharedModel] = useState("");

  useEffect(() => {
    const next: Record<string, { skills: string[]; interval: number; model: string }> = {};
    for (const agent of agents) {
      next[agent.id] = {
        skills: [...agent.skill_slugs],
        interval: agent.heartbeat_interval_minutes,
        model: agent.model,
      };
    }
    setDraft(next);
  }, [agents]);

  const expand = useMutation({
    mutationFn: () => api<Agent[]>(`/brands/${id}/agents/expand`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents", id] }),
  });
  const swarm = useMutation({
    mutationFn: () => api<SwarmQueued>(`/brands/${id}/agents/wake-all`, { method: "POST" }),
  });
  const presets = useMutation({
    mutationFn: () => api<Agent[]>(`/brands/${id}/agents/apply-presets`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents", id] }),
  });
  const broadcast = useMutation({
    mutationFn: () =>
      api<Agent[]>(`/brands/${id}/agents/broadcast-model`, {
        method: "POST",
        body: JSON.stringify({ model: sharedModel }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents", id] }),
  });
  const save = useMutation({
    mutationFn: async (agentId: string) => {
      const row = draft[agentId];
      return api(`/brands/${id}/agents/${agentId}`, {
        method: "PATCH",
        body: JSON.stringify({
          skill_slugs: row.skills,
          heartbeat_interval_minutes: row.interval,
          model: row.model,
        }),
      });
    },
    onSuccess: (_, agentId) => {
      setSaved(agentId);
      qc.invalidateQueries({ queryKey: ["agents", id] });
    },
  });

  function toggle(agentId: string, slug: string) {
    setDraft((cur) => {
      const row = cur[agentId] || { skills: [], interval: 10, model: "" };
      const skills = row.skills.includes(slug) ? row.skills.filter((s) => s !== slug) : [...row.skills, slug];
      return { ...cur, [agentId]: { ...row, skills } };
    });
  }

  return (
    <Shell brandId={id}>
      <RunningWork brandId={id} />
      {(expand.isPending || swarm.isPending || save.isPending || presets.isPending || broadcast.isPending) && (
        <WorkLoader label={swarm.isPending ? "Waking swarm" : "Saving studio"} />
      )}
      <p className="text-xs uppercase tracking-[0.24em] text-cyan">Configure</p>
      <h1 className="mt-1 font-serif text-5xl">Agent studio</h1>
      <p className="mt-3 max-w-2xl text-sm text-ink/65">
        Toggle skills per role. Cyan = on. Violet outline = recommended for that role. Apply presets to load the default pack in one click.
      </p>
      <div className="mt-6 flex flex-wrap items-end gap-2">
        <button className="btn-primary" onClick={() => expand.mutate()}>
          Expand to full org
        </button>
        <button className="btn-ghost" onClick={() => presets.mutate()}>
          Apply recommended skills
        </button>
        <button className="btn-ghost" onClick={() => swarm.mutate()}>
          Wake all agents
        </button>
        <label className="text-xs text-clay">
          Model for all
          <input
            className="field mt-1 w-64"
            placeholder="openai/gpt-4o-mini"
            value={sharedModel}
            onChange={(e) => setSharedModel(e.target.value)}
          />
        </label>
        <button className="btn-ghost" onClick={() => broadcast.mutate()} disabled={!sharedModel.trim()}>
          Broadcast model
        </button>
        {swarm.data && <span className="self-center text-sm text-moss">{swarm.data.queued} queued</span>}
      </div>

      <div className="mt-10 space-y-6">
        {agents.map((agent) => {
          const row = draft[agent.id];
          if (!row) return null;
          return (
            <section key={agent.id} className="card p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-serif text-3xl">{agent.title}</h2>
                  <p className="text-xs uppercase tracking-wide text-clay">{agent.role}</p>
                </div>
                <div className="flex items-center gap-2">
                  {pill(agent.status)}
                  <button className="btn-primary" onClick={() => save.mutate(agent.id)}>
                    {saved === agent.id ? "Saved" : "Save"}
                  </button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <label className="text-xs text-clay">
                  Model
                  <input
                    className="field mt-1"
                    value={row.model}
                    onChange={(e) => setDraft((c) => ({ ...c, [agent.id]: { ...row, model: e.target.value } }))}
                  />
                </label>
                <label className="text-xs text-clay">
                  Heartbeat minutes
                  <input
                    className="field mt-1"
                    type="number"
                    min={1}
                    value={row.interval}
                    onChange={(e) =>
                      setDraft((c) => ({ ...c, [agent.id]: { ...row, interval: Number(e.target.value) || 10 } }))
                    }
                  />
                </label>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {skills.map((skill) => {
                  const on = row.skills.includes(skill.slug);
                  const rec = skill.allowed_roles.includes(agent.role);
                  return (
                    <button
                      key={skill.slug}
                      type="button"
                      title={skill.description}
                      onClick={() => toggle(agent.id, skill.slug)}
                      className={`rounded-full border px-3 py-1 text-xs ${
                        on
                          ? "border-cyan/50 bg-cyan/15 text-cyan"
                          : rec
                            ? "border-violet/40 text-violet"
                            : "border-white/10 text-clay"
                      }`}
                    >
                      {skill.name}
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </Shell>
  );
}
