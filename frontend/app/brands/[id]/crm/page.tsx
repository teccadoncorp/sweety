"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { RunningWork } from "@/components/RunningWork";
import { Shell, money, pill } from "@/components/Shell";
import { WorkInline, WorkLoader } from "@/components/WorkLoader";
import {
  api,
  Agent,
  CrmAccount,
  CrmActivity,
  CrmBoard,
  CrmContact,
  CrmDeal,
} from "@/lib/api";

const STAGES = ["signal", "qualify", "propose", "commit", "won", "lost"];

function ring(score: number) {
  const deg = Math.max(0, Math.min(100, score)) * 3.6;
  return {
    background: `conic-gradient(#4cc9f0 ${deg}deg, rgba(255,255,255,0.08) ${deg}deg)`,
  };
}

export default function CrmPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [temp, setTemp] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [dealName, setDealName] = useState("");
  const [dealValue, setDealValue] = useState("5000");
  const [note, setNote] = useState("");
  const [nextAction, setNextAction] = useState("");

  const { data: board, isLoading } = useQuery({
    queryKey: ["crm-board", id],
    queryFn: () => api<CrmBoard>(`/brands/${id}/crm/board`),
  });
  const { data: contacts = [] } = useQuery({
    queryKey: ["crm-contacts", id, q],
    queryFn: () => api<CrmContact[]>(`/brands/${id}/crm/contacts${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  });
  const { data: deals = [] } = useQuery({
    queryKey: ["crm-deals", id],
    queryFn: () => api<CrmDeal[]>(`/brands/${id}/crm/deals`),
  });
  const { data: accounts = [] } = useQuery({
    queryKey: ["crm-accounts", id],
    queryFn: () => api<CrmAccount[]>(`/brands/${id}/crm/accounts`),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ["agents", id],
    queryFn: () => api<Agent[]>(`/brands/${id}/agents`),
  });
  const { data: activities = [] } = useQuery({
    queryKey: ["crm-activities", id, selected],
    queryFn: () =>
      api<CrmActivity[]>(
        `/brands/${id}/crm/activities${selected ? `?contact_id=${selected}` : ""}`,
      ),
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["crm-board", id] });
    qc.invalidateQueries({ queryKey: ["crm-contacts", id] });
    qc.invalidateQueries({ queryKey: ["crm-deals", id] });
    qc.invalidateQueries({ queryKey: ["crm-activities", id] });
    qc.invalidateQueries({ queryKey: ["crm-accounts", id] });
  };

  const seed = useMutation({
    mutationFn: () => api(`/brands/${id}/crm/seed`, { method: "POST" }),
    onSuccess: refresh,
  });
  const addContact = useMutation({
    mutationFn: () =>
      api(`/brands/${id}/crm/contacts`, {
        method: "POST",
        body: JSON.stringify({
          name,
          email,
          company,
          temperature: "warm",
          signal_score: 55,
          source: "manual",
        }),
      }),
    onSuccess: () => {
      setName("");
      setEmail("");
      setCompany("");
      refresh();
    },
  });
  const addDeal = useMutation({
    mutationFn: () =>
      api(`/brands/${id}/crm/deals`, {
        method: "POST",
        body: JSON.stringify({
          name: dealName,
          value_usd: dealValue,
          stage: "signal",
          contact_id: selected,
        }),
      }),
    onSuccess: () => {
      setDealName("");
      refresh();
    },
  });
  const moveDeal = useMutation({
    mutationFn: ({ dealId, stage }: { dealId: string; stage: string }) =>
      api(`/brands/${id}/crm/deals/${dealId}`, {
        method: "PATCH",
        body: JSON.stringify({ stage }),
      }),
    onSuccess: refresh,
  });
  const heat = useMutation({
    mutationFn: ({ contactId, temperature, signal_score }: { contactId: string; temperature: string; signal_score: number }) =>
      api(`/brands/${id}/crm/contacts/${contactId}`, {
        method: "PATCH",
        body: JSON.stringify({ temperature, signal_score }),
      }),
    onSuccess: refresh,
  });
  const saveAction = useMutation({
    mutationFn: () =>
      api(`/brands/${id}/crm/contacts/${selected}`, {
        method: "PATCH",
        body: JSON.stringify({ next_action: nextAction }),
      }),
    onSuccess: refresh,
  });
  const logNote = useMutation({
    mutationFn: () =>
      api(`/brands/${id}/crm/activities`, {
        method: "POST",
        body: JSON.stringify({ kind: "note", title: "Board note", body: note, contact_id: selected }),
      }),
    onSuccess: () => {
      setNote("");
      refresh();
    },
  });
  const wakeCrm = useMutation({
    mutationFn: async () => {
      const steward = agents.find((a) => a.role === "crm");
      if (!steward) throw new Error("No CRM steward yet — expand the org first");
      return api(`/brands/${id}/agents/${steward.id}/heartbeat`, { method: "POST" });
    },
  });

  function onContact(e: FormEvent) {
    e.preventDefault();
    if (name.trim()) addContact.mutate();
  }

  const person = contacts.find((c) => c.id === selected) || null;
  const visible = contacts.filter((c) => temp === "all" || c.temperature === temp);

  useEffect(() => {
    setNextAction(person?.next_action || "");
  }, [person?.id, person?.next_action]);
  const byStage = useMemo(() => {
    const map: Record<string, CrmDeal[]> = {};
    for (const stage of STAGES) map[stage] = [];
    for (const deal of deals) {
      (map[deal.stage] || (map[deal.stage] = [])).push(deal);
    }
    return map;
  }, [deals]);

  const busy =
    seed.isPending ||
    addContact.isPending ||
    addDeal.isPending ||
    moveDeal.isPending ||
    logNote.isPending ||
    saveAction.isPending ||
    wakeCrm.isPending;

  return (
    <Shell brandId={id} full>
      <div className="scanline h-full overflow-auto px-6 py-8">
        <RunningWork brandId={id} />
        {isLoading && <WorkInline label="Booting signal lattice" />}
        {busy && <WorkLoader label="Updating lattice" />}

        <div className="mx-auto max-w-[1400px]">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-cyan">Neural CRM</p>
              <h1 className="mt-1 font-serif text-5xl">Signal lattice</h1>
              <p className="mt-2 max-w-xl text-sm text-ink/60">
                Live pipeline, heat, and next actions. Agents write here too — wake the CRM steward from Org.
              </p>
            </div>
            <div className="flex gap-2">
              <button className="btn-ghost" onClick={() => wakeCrm.mutate()}>
                Wake CRM steward
              </button>
              <button className="btn-ghost" onClick={() => seed.mutate()}>
                Load demo signals
              </button>
            </div>
          </div>

          <section className="mt-8 grid gap-3 md:grid-cols-6">
            {[
              ["Contacts", board?.contacts ?? 0],
              ["Accounts", board?.accounts ?? 0],
              ["Open deals", board?.open_deals ?? 0],
              ["Pipeline", money(board?.pipeline_usd || "0")],
              ["Won", money(board?.won_usd || "0")],
              ["Hot / star", board?.hot_leads ?? 0],
            ].map(([label, value]) => (
              <div key={String(label)} className="hud-glow card p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-clay">{label}</div>
                <div className="mt-2 font-serif text-3xl text-cyan">{value}</div>
                <div className="signal-bar mt-3" />
              </div>
            ))}
          </section>

          {accounts.length > 0 && (
            <section className="mt-8">
              <h2 className="font-serif text-2xl">Account nodes</h2>
              <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
                {accounts.map((a) => (
                  <div key={a.id} className="hud-glow card min-w-[200px] p-4">
                    <div className="font-medium">{a.name}</div>
                    <div className="text-xs text-clay">{a.industry || a.domain || "unclassified"}</div>
                    <div className="mt-2 text-sm text-cyan">signal {a.signal_score}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="mt-10 grid gap-6 lg:grid-cols-[340px_1fr_280px]">
            <section className="card p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-serif text-2xl">Constellation</h2>
                <span className="text-xs text-clay">avg {Math.round(board?.avg_signal || 0)}</span>
              </div>
              <input
                className="field mt-4"
                placeholder="Search signals"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <div className="mt-3 flex flex-wrap gap-1">
                {["all", "cool", "warm", "hot", "star"].map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`rounded-full px-2.5 py-0.5 text-[11px] ${
                      temp === t ? "bg-cyan/20 text-cyan" : "bg-white/5 text-clay"
                    }`}
                    onClick={() => setTemp(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="mt-4 max-h-[520px] space-y-2 overflow-auto">
                {visible.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setSelected(c.id)}
                    className={`flex w-full items-center gap-3 rounded-xl border px-3 py-3 text-left ${
                      selected === c.id ? "border-cyan/50 bg-cyan/10" : "border-white/10 hover:bg-white/5"
                    }`}
                  >
                    <div className="grid h-11 w-11 place-items-center rounded-full p-[3px]" style={ring(c.signal_score)}>
                      <div className="grid h-full w-full place-items-center rounded-full bg-void text-xs">
                        {c.signal_score}
                      </div>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">{c.name}</div>
                      <div className="truncate text-xs text-clay">
                        {c.title ? `${c.title} · ` : ""}
                        {c.company || c.email || "unlinked"}
                      </div>
                    </div>
                    {pill(c.temperature)}
                  </button>
                ))}
                {visible.length === 0 && (
                  <p className="text-sm text-clay">No contacts yet. Capture one or load demo signals.</p>
                )}
              </div>
              <form onSubmit={onContact} className="mt-4 space-y-2 border-t border-white/10 pt-4">
                <div className="text-xs uppercase tracking-wide text-clay">Capture</div>
                <input className="field" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
                <input className="field" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
                <input className="field" placeholder="Company" value={company} onChange={(e) => setCompany(e.target.value)} />
                <button className="btn-primary w-full" type="submit">
                  Drop into lattice
                </button>
              </form>
            </section>

            <section>
              <h2 className="font-serif text-2xl">Pipeline warp</h2>
              <div className="mt-4 flex gap-3 overflow-x-auto pb-3">
                {STAGES.map((stage) => (
                  <div key={stage} className="crm-kanban card flex-1 p-3">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-xs uppercase tracking-[0.16em] text-cyan">{stage}</span>
                      <span className="text-xs text-clay">{byStage[stage]?.length || 0}</span>
                    </div>
                    <div className="space-y-2">
                      {(byStage[stage] || []).map((deal) => (
                        <article key={deal.id} className="rounded-xl border border-white/10 bg-void/50 p-3">
                          <div className="text-sm font-medium">{deal.name}</div>
                          <div className="mt-1 text-xs text-cyan">{money(deal.value_usd)}</div>
                          <div className="mt-1 text-[11px] text-clay">{deal.probability}% close</div>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {STAGES.filter((s) => s !== stage).slice(0, 3).map((next) => (
                              <button
                                key={next}
                                className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] text-clay hover:border-cyan/40 hover:text-cyan"
                                onClick={() => moveDeal.mutate({ dealId: deal.id, stage: next })}
                              >
                                {next}
                              </button>
                            ))}
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <form
                className="card mt-4 flex flex-wrap gap-2 p-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (dealName.trim()) addDeal.mutate();
                }}
              >
                <input
                  className="field flex-1"
                  placeholder="New deal name"
                  value={dealName}
                  onChange={(e) => setDealName(e.target.value)}
                />
                <input
                  className="field w-32"
                  placeholder="Value"
                  value={dealValue}
                  onChange={(e) => setDealValue(e.target.value)}
                />
                <button className="btn-primary" type="submit">
                  Open deal
                </button>
              </form>
            </section>

            <aside className="card p-5">
              <h2 className="font-serif text-2xl">{person ? person.name : "Trace"}</h2>
              {person ? (
                <div className="mt-3 space-y-2 text-sm">
                  <div className="text-clay">{person.title}</div>
                  <div>{person.email || "no email"}</div>
                  <div className="text-cyan">{person.next_action || "No next action"}</div>
                  <p className="text-ink/70">{person.notes}</p>
                  <input
                    className="field"
                    placeholder="Next action"
                    value={nextAction}
                    onChange={(e) => setNextAction(e.target.value)}
                  />
                  <button className="btn-ghost w-full" onClick={() => saveAction.mutate()} disabled={!nextAction.trim()}>
                    Save next action
                  </button>
                  <div className="flex flex-wrap gap-1">
                    {["cool", "warm", "hot", "star"].map((t) => (
                      <button
                        key={t}
                        className="btn-ghost px-3 py-1 text-xs"
                        onClick={() =>
                          heat.mutate({
                            contactId: person.id,
                            temperature: t,
                            signal_score: t === "star" ? 92 : t === "hot" ? 80 : t === "warm" ? 62 : 40,
                          })
                        }
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mt-3 text-sm text-clay">Select a contact to inspect the trace.</p>
              )}
              <div className="mt-6 text-xs uppercase tracking-[0.18em] text-clay">Activity</div>
              {person && (
                <form
                  className="mt-3 space-y-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (note.trim()) logNote.mutate();
                  }}
                >
                  <textarea
                    className="field min-h-16"
                    placeholder="Log a touch"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                  />
                  <button className="btn-ghost w-full" type="submit">
                    Write to trace
                  </button>
                </form>
              )}
              <div className="mt-3 max-h-[360px] space-y-3 overflow-auto">
                {activities.map((a) => (
                  <div key={a.id} className="border-l border-cyan/30 pl-3">
                    <div className="text-sm">{a.title}</div>
                    <div className="text-xs text-clay">{a.kind} · {new Date(a.created_at).toLocaleString()}</div>
                    <p className="mt-1 text-xs text-ink/70">{a.body}</p>
                  </div>
                ))}
                {activities.length === 0 && <p className="text-sm text-clay">Quiet lattice.</p>}
              </div>
            </aside>
          </div>
        </div>
      </div>
    </Shell>
  );
}
