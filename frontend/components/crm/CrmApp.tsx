"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useMemo, useState, type DragEvent } from "react";
import { Markdown } from "@/components/Markdown";
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

const STAGES = ["signal", "qualify", "propose", "commit", "won", "lost"] as const;
const TEMPS = ["all", "ice", "cool", "warm", "hot", "star"] as const;
const KINDS = ["note", "call", "email", "meeting", "task"];

type Tab = "pipeline" | "contacts" | "accounts" | "activity" | "ai";

function fmtDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export function CrmApp({ brandId }: { brandId: string }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>(() => {
    if (typeof window === "undefined") return "pipeline";
    const t = new URLSearchParams(window.location.search).get("tab");
    return t === "contacts" || t === "accounts" || t === "activity" || t === "ai" ? t : "pipeline";
  });
  const [q, setQ] = useState("");
  const [temp, setTemp] = useState(() => {
    if (typeof window === "undefined") return "all";
    return new URLSearchParams(window.location.search).get("temp") || "all";
  });
  const [dealId, setDealId] = useState<string | null>(null);
  const [contactId, setContactId] = useState<string | null>(null);
  const [dealForm, setDealForm] = useState({ name: "", value: "5000", stage: "signal", contact_id: "" });
  const [contactForm, setContactForm] = useState({
    name: "",
    email: "",
    phone: "",
    title: "",
    company: "",
    next_action: "",
  });
  const [accountForm, setAccountForm] = useState({ name: "", domain: "", industry: "" });
  const [note, setNote] = useState("");
  const [kind, setKind] = useState("note");
  const [lostReason, setLostReason] = useState("");
  const [brief, setBrief] = useState("");

  const { data: board, isLoading } = useQuery({
    queryKey: ["crm-board", brandId],
    queryFn: () => api<CrmBoard>(`/brands/${brandId}/crm/board`),
  });
  const { data: contacts = [] } = useQuery({
    queryKey: ["crm-contacts", brandId, q, temp],
    queryFn: () => {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      if (temp !== "all") params.set("temperature", temp);
      const qs = params.toString();
      return api<CrmContact[]>(`/brands/${brandId}/crm/contacts${qs ? `?${qs}` : ""}`);
    },
  });
  const { data: deals = [] } = useQuery({
    queryKey: ["crm-deals", brandId],
    queryFn: () => api<CrmDeal[]>(`/brands/${brandId}/crm/deals`),
  });
  const { data: accounts = [] } = useQuery({
    queryKey: ["crm-accounts", brandId],
    queryFn: () => api<CrmAccount[]>(`/brands/${brandId}/crm/accounts`),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ["agents", brandId],
    queryFn: () => api<Agent[]>(`/brands/${brandId}/agents`),
  });
  const { data: overdue = [] } = useQuery({
    queryKey: ["crm-overdue", brandId],
    queryFn: () => api<CrmContact[]>(`/brands/${brandId}/crm/overdue`),
  });
  const activityKey = dealId || contactId;
  const { data: activities = [] } = useQuery({
    queryKey: ["crm-activities", brandId, activityKey, tab],
    queryFn: () => {
      if (tab === "activity") return api<CrmActivity[]>(`/brands/${brandId}/crm/activities`);
      const params = new URLSearchParams();
      if (dealId) params.set("deal_id", dealId);
      else if (contactId) params.set("contact_id", contactId);
      const qs = params.toString();
      return api<CrmActivity[]>(`/brands/${brandId}/crm/activities${qs ? `?${qs}` : ""}`);
    },
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["crm-board", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-contacts", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-deals", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-accounts", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-activities", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-overdue", brandId] });
  };

  const seed = useMutation({
    mutationFn: () => api(`/brands/${brandId}/crm/seed`, { method: "POST" }),
    onSuccess: refresh,
  });
  const addContact = useMutation({
    mutationFn: () =>
      api<CrmContact>(`/brands/${brandId}/crm/contacts`, {
        method: "POST",
        body: JSON.stringify({ ...contactForm, source: "manual", temperature: "warm", signal_score: 55 }),
      }),
    onSuccess: (row) => {
      setContactForm({ name: "", email: "", phone: "", title: "", company: "", next_action: "" });
      setContactId(row.id);
      refresh();
    },
  });
  const addAccount = useMutation({
    mutationFn: () =>
      api(`/brands/${brandId}/crm/accounts`, { method: "POST", body: JSON.stringify(accountForm) }),
    onSuccess: () => {
      setAccountForm({ name: "", domain: "", industry: "" });
      refresh();
    },
  });
  const addDeal = useMutation({
    mutationFn: () =>
      api<CrmDeal>(`/brands/${brandId}/crm/deals`, {
        method: "POST",
        body: JSON.stringify({
          name: dealForm.name,
          value_usd: dealForm.value,
          stage: dealForm.stage,
          contact_id: dealForm.contact_id || contactId || null,
        }),
      }),
    onSuccess: (row) => {
      setDealForm({ name: "", value: "5000", stage: "signal", contact_id: "" });
      setDealId(row.id);
      refresh();
    },
  });
  const patchDeal = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api(`/brands/${brandId}/crm/deals/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });
  const patchContact = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api(`/brands/${brandId}/crm/contacts/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: ({ kind, id }: { kind: "deals" | "contacts" | "accounts"; id: string }) =>
      api(`/brands/${brandId}/crm/${kind}/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      setDealId(null);
      setContactId(null);
      refresh();
    },
  });
  const logNote = useMutation({
    mutationFn: () =>
      api(`/brands/${brandId}/crm/activities`, {
        method: "POST",
        body: JSON.stringify({
          kind,
          title: kind === "task" ? "Follow-up" : kind[0].toUpperCase() + kind.slice(1),
          body: note,
          contact_id: contactId,
          deal_id: dealId,
        }),
      }),
    onSuccess: () => {
      setNote("");
      refresh();
    },
  });
  const score = useMutation({
    mutationFn: (id: string) =>
      api(`/brands/${brandId}/crm/contacts/${id}/score`, { method: "POST", signal: AbortSignal.timeout(60_000) }),
    onSuccess: refresh,
  });
  const coach = useMutation({
    mutationFn: (id: string) =>
      api<{ next_action: string; risk: string; talking_points: string[] }>(
        `/brands/${brandId}/crm/deals/${id}/coach`,
        { method: "POST", signal: AbortSignal.timeout(60_000) },
      ),
    onSuccess: refresh,
  });
  const briefAi = useMutation({
    mutationFn: () =>
      api<{ brief: string }>(`/brands/${brandId}/crm/ai/brief`, {
        method: "POST",
        signal: AbortSignal.timeout(60_000),
      }),
    onSuccess: (data) => setBrief(data.brief),
  });
  const wakeCrm = useMutation({
    mutationFn: async () => {
      const steward = agents.find((a) => a.role === "crm");
      if (!steward) throw new Error("No CRM steward yet — expand the org first");
      return api(`/brands/${brandId}/agents/${steward.id}/heartbeat`, { method: "POST" });
    },
  });

  const deal = deals.find((d) => d.id === dealId) || null;
  const person = contacts.find((c) => c.id === contactId) || null;
  const byStage = useMemo(() => {
    const map: Record<string, CrmDeal[]> = {};
    for (const stage of STAGES) map[stage] = [];
    for (const row of deals) (map[row.stage] || (map[row.stage] = [])).push(row);
    return map;
  }, [deals]);

  const busy =
    seed.isPending ||
    addContact.isPending ||
    addDeal.isPending ||
    addAccount.isPending ||
    patchDeal.isPending ||
    patchContact.isPending ||
    remove.isPending ||
    logNote.isPending ||
    score.isPending ||
    coach.isPending ||
    briefAi.isPending ||
    wakeCrm.isPending;

  function dropDeal(stage: string, event: DragEvent) {
    event.preventDefault();
    const id = event.dataTransfer.getData("text/plain");
    if (!id) return;
    const extra = stage === "lost" && lostReason ? { lost_reason: lostReason } : {};
    patchDeal.mutate({ id, body: { stage, ...extra } });
  }

  function onCreateContact(e: FormEvent) {
    e.preventDefault();
    if (contactForm.name.trim()) addContact.mutate();
  }

  return (
    <Shell brandId={brandId} full>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-paper">
        <div className="shrink-0 border-b border-line bg-white px-4 py-4 sm:px-6">
          <RunningWork brandId={brandId} />
          {isLoading && <WorkInline label="Loading CRM" />}
          {busy && <WorkLoader label="Updating CRM" />}
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-violet">Revenue</p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight">CRM</h1>
              <p className="mt-1 max-w-xl text-sm text-clay">
                Pipeline, contacts, accounts, activity, and AI coaching. Drag deals across stages.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" onClick={() => briefAi.mutate()}>
                AI pipeline brief
              </button>
              <button className="btn-ghost" onClick={() => wakeCrm.mutate()}>
                Wake CRM agent
              </button>
              <button className="btn-ghost" onClick={() => seed.mutate()}>
                Load sample data
              </button>
            </div>
          </div>
          <section className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-8">
            {[
              ["Pipeline", money(board?.pipeline_usd || "0")],
              ["Weighted", money(board?.weighted_pipeline_usd || "0")],
              ["Won", money(board?.won_usd || "0")],
              ["Avg deal", money(board?.avg_deal_usd || "0")],
              ["Open", board?.open_deals ?? 0],
              ["Contacts", board?.contacts ?? 0],
              ["Hot", board?.hot_leads ?? 0],
              ["Overdue", board?.overdue ?? 0],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-xl border border-line bg-paper px-3 py-3">
                <div className="text-[11px] uppercase tracking-wide text-clay">{label}</div>
                <div className="mt-1 text-xl font-semibold text-violet">{value}</div>
              </div>
            ))}
          </section>
          <nav className="mt-5 flex flex-wrap gap-1">
            {(["pipeline", "contacts", "accounts", "activity", "ai"] as Tab[]).map((item) => (
              <button
                key={item}
                className={`rounded-lg px-3 py-1.5 text-sm capitalize ${
                  tab === item ? "bg-violet text-white" : "text-clay hover:bg-paper"
                }`}
                onClick={() => setTab(item)}
              >
                {item}
              </button>
            ))}
          </nav>
        </div>

        <div className="min-h-0 flex-1 overflow-auto px-4 py-4 sm:px-6">
          {tab === "pipeline" && (
            <div>
              <form
                className="mb-4 flex flex-wrap gap-2 rounded-xl border border-line bg-white p-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (dealForm.name.trim()) addDeal.mutate();
                }}
              >
                <input
                  className="field min-w-48 flex-1"
                  placeholder="New deal name"
                  value={dealForm.name}
                  onChange={(e) => setDealForm({ ...dealForm, name: e.target.value })}
                />
                <input
                  className="field w-28"
                  placeholder="Value"
                  value={dealForm.value}
                  onChange={(e) => setDealForm({ ...dealForm, value: e.target.value })}
                />
                <select
                  className="field w-36"
                  value={dealForm.stage}
                  onChange={(e) => setDealForm({ ...dealForm, stage: e.target.value })}
                >
                  {STAGES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <select
                  className="field w-48"
                  value={dealForm.contact_id}
                  onChange={(e) => setDealForm({ ...dealForm, contact_id: e.target.value })}
                >
                  <option value="">Contact (optional)</option>
                  {contacts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <button className="btn-primary" type="submit">
                  Create deal
                </button>
              </form>
              <div className="flex min-h-[28rem] gap-3 overflow-x-auto pb-4">
                {STAGES.map((stage) => {
                  const col = byStage[stage] || [];
                  const total = col.reduce((sum, d) => sum + (parseFloat(d.value_usd) || 0), 0);
                  return (
                    <div
                      key={stage}
                      className="flex w-64 shrink-0 flex-col rounded-xl border border-line bg-white"
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => dropDeal(stage, e)}
                    >
                      <div className="flex items-center justify-between border-b border-line px-3 py-2">
                        <span className="text-xs font-semibold uppercase tracking-wide text-violet">{stage}</span>
                        <span className="text-xs text-clay">
                          {col.length} · {money(total)}
                        </span>
                      </div>
                      <div className="min-h-40 flex-1 space-y-2 overflow-y-auto p-2">
                        {col.map((row) => (
                          <article
                            key={row.id}
                            draggable
                            onDragStart={(e) => e.dataTransfer.setData("text/plain", row.id)}
                            onClick={() => {
                              setDealId(row.id);
                              setContactId(row.contact_id);
                            }}
                            className={`cursor-grab rounded-lg border p-3 text-left hover:border-violet/40 ${
                              dealId === row.id ? "border-violet bg-violet/5" : "border-line bg-paper"
                            }`}
                          >
                            <div className="text-sm font-medium">{row.name}</div>
                            <div className="mt-1 text-sm text-violet">{money(row.value_usd)}</div>
                            <div className="mt-1 text-[11px] text-clay">
                              {row.probability}% · {row.contact_name || row.account_name || "Unassigned"}
                            </div>
                            {row.close_date && <div className="mt-1 text-[11px] text-clay">Close {row.close_date}</div>}
                          </article>
                        ))}
                        {col.length === 0 && <p className="px-1 py-6 text-center text-xs text-clay">Drop deals here</p>}
                      </div>
                    </div>
                  );
                })}
              </div>
              {STAGES.includes("lost") && (
                <label className="mt-2 block text-xs text-clay">
                  Lost reason (used when you drop a deal on Lost)
                  <input
                    className="field mt-1 max-w-md"
                    value={lostReason}
                    onChange={(e) => setLostReason(e.target.value)}
                    placeholder="Budget, timing, competitor…"
                  />
                </label>
              )}
            </div>
          )}

          {tab === "contacts" && (
            <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
              <form className="card h-fit space-y-2 p-4" onSubmit={onCreateContact}>
                <h2 className="font-semibold">New contact</h2>
                {["name", "email", "phone", "title", "company", "next_action"].map((key) => (
                  <input
                    key={key}
                    className="field"
                    placeholder={key.replace("_", " ")}
                    value={contactForm[key as keyof typeof contactForm]}
                    onChange={(e) => setContactForm({ ...contactForm, [key]: e.target.value })}
                  />
                ))}
                <button className="btn-primary w-full" type="submit">
                  Add contact
                </button>
              </form>
              <div>
                <div className="mb-3 flex flex-wrap gap-2">
                  <input className="field max-w-xs" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
                  {TEMPS.map((t) => (
                    <button
                      key={t}
                      className={`rounded-full px-3 py-1 text-xs ${temp === t ? "bg-violet text-white" : "bg-white text-clay"}`}
                      onClick={() => setTemp(t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>
                <div className="overflow-x-auto rounded-xl border border-line bg-white">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-line text-xs uppercase text-clay">
                      <tr>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Company</th>
                        <th className="px-3 py-2">Heat</th>
                        <th className="px-3 py-2">Score</th>
                        <th className="px-3 py-2">Next action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contacts.map((c) => (
                        <tr
                          key={c.id}
                          className="cursor-pointer border-b border-line last:border-0 hover:bg-paper"
                          onClick={() => setContactId(c.id)}
                        >
                          <td className="px-3 py-2 font-medium">{c.name}</td>
                          <td className="px-3 py-2 text-clay">{c.company || c.account_name || "—"}</td>
                          <td className="px-3 py-2">{pill(c.temperature)}</td>
                          <td className="px-3 py-2">{c.signal_score}</td>
                          <td className="max-w-xs truncate px-3 py-2 text-clay">{c.next_action || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {contacts.length === 0 && <p className="p-6 text-sm text-clay">No contacts yet.</p>}
                </div>
              </div>
            </div>
          )}

          {tab === "accounts" && (
            <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
              <form
                className="card h-fit space-y-2 p-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (accountForm.name.trim()) addAccount.mutate();
                }}
              >
                <h2 className="font-semibold">New account</h2>
                <input className="field" placeholder="Name" value={accountForm.name} onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })} />
                <input className="field" placeholder="Domain" value={accountForm.domain} onChange={(e) => setAccountForm({ ...accountForm, domain: e.target.value })} />
                <input className="field" placeholder="Industry" value={accountForm.industry} onChange={(e) => setAccountForm({ ...accountForm, industry: e.target.value })} />
                <button className="btn-primary w-full" type="submit">
                  Add account
                </button>
              </form>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {accounts.map((a) => (
                  <article key={a.id} className="card p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold">{a.name}</h3>
                      <button
                        className="text-xs text-clay"
                        onClick={() => {
                          if (confirm(`Delete ${a.name}?`)) remove.mutate({ kind: "accounts", id: a.id });
                        }}
                      >
                        Delete
                      </button>
                    </div>
                    <p className="mt-1 text-xs text-clay">{a.industry || a.domain || "—"}</p>
                    <p className="mt-2 text-sm text-violet">Signal {a.signal_score}</p>
                    <p className="mt-2 line-clamp-3 text-sm text-ink/70">{a.notes || "No notes."}</p>
                  </article>
                ))}
                {accounts.length === 0 && <p className="text-sm text-clay">No accounts yet.</p>}
              </div>
            </div>
          )}

          {tab === "activity" && (
            <div className="mx-auto max-w-3xl space-y-3">
              {activities.map((a) => (
                <div key={a.id} className="card p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium">{a.title}</div>
                    {pill(a.kind)}
                  </div>
                  <div className="mt-1 text-xs text-clay">{fmtDate(a.created_at)}</div>
                  <p className="mt-2 text-sm text-ink/80">{a.body}</p>
                </div>
              ))}
              {activities.length === 0 && <p className="text-sm text-clay">No activity yet.</p>}
            </div>
          )}

          {tab === "ai" && (
            <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-2">
              <section className="card p-5">
                <h2 className="font-semibold">Weekly briefing</h2>
                <p className="mt-1 text-sm text-clay">Uses OpenRouter when configured, otherwise a rules-based snapshot.</p>
                <button className="btn-primary mt-4" onClick={() => briefAi.mutate()}>
                  Generate brief
                </button>
                <div className="mt-4 text-sm">
                  {brief ? <Markdown>{brief}</Markdown> : <p className="text-clay">No brief yet.</p>}
                </div>
              </section>
              <section className="card p-5">
                <h2 className="font-semibold">Overdue follow-ups</h2>
                <p className="mt-1 text-sm text-clay">Next action set, no touch in 7 days.</p>
                <div className="mt-4 space-y-2">
                  {overdue.map((c) => (
                    <div key={c.id} className="flex items-center justify-between gap-2 rounded-lg border border-line px-3 py-2">
                      <div>
                        <div className="text-sm font-medium">{c.name}</div>
                        <div className="text-xs text-clay">{c.next_action}</div>
                      </div>
                      <div className="flex gap-2">
                        <button className="btn-ghost px-3 py-1 text-xs" onClick={() => score.mutate(c.id)}>
                          Score
                        </button>
                        <button className="btn-ghost px-3 py-1 text-xs" onClick={() => { setContactId(c.id); setTab("contacts"); }}>
                          Open
                        </button>
                      </div>
                    </div>
                  ))}
                  {overdue.length === 0 && <p className="text-sm text-clay">Nothing overdue.</p>}
                </div>
              </section>
            </div>
          )}
        </div>
      </div>

      {(deal || person) && (
        <aside className="absolute inset-y-0 right-0 z-30 flex w-full max-w-md flex-col border-l border-line bg-white shadow-card">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <div className="text-xs uppercase tracking-wide text-clay">{deal ? "Deal" : "Contact"}</div>
              <h2 className="text-lg font-semibold">{deal?.name || person?.name}</h2>
            </div>
            <button className="btn-ghost px-3 py-1 text-xs" onClick={() => { setDealId(null); setContactId(null); }}>
              Close
            </button>
          </div>
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
            {deal && (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <label className="text-xs text-clay">
                    Value
                    <input
                      className="field mt-1"
                      defaultValue={deal.value_usd}
                      onBlur={(e) => patchDeal.mutate({ id: deal.id, body: { value_usd: e.target.value } })}
                    />
                  </label>
                  <label className="text-xs text-clay">
                    Close date
                    <input
                      className="field mt-1"
                      type="date"
                      defaultValue={deal.close_date}
                      onBlur={(e) => patchDeal.mutate({ id: deal.id, body: { close_date: e.target.value } })}
                    />
                  </label>
                </div>
                <label className="text-xs text-clay">
                  Stage
                  <select
                    className="field mt-1"
                    value={deal.stage}
                    onChange={(e) => patchDeal.mutate({ id: deal.id, body: { stage: e.target.value } })}
                  >
                    {STAGES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="text-sm text-clay">{deal.probability}% probability · {deal.contact_name || "No contact"}</p>
                {deal.lost_reason && <p className="text-sm text-clay">Lost: {deal.lost_reason}</p>}
                <textarea
                  className="field min-h-20"
                  defaultValue={deal.notes}
                  onBlur={(e) => patchDeal.mutate({ id: deal.id, body: { notes: e.target.value } })}
                />
                <button className="btn-primary w-full" onClick={() => coach.mutate(deal.id)}>
                  AI coach this deal
                </button>
                {coach.data && (
                  <div className="rounded-lg bg-paper p-3 text-sm">
                    <div className="font-medium">{coach.data.next_action}</div>
                    <p className="mt-1 text-clay">{coach.data.risk}</p>
                    <ul className="mt-2 list-disc pl-4 text-clay">
                      {(coach.data.talking_points || []).map((p) => (
                        <li key={p}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <button
                  className="btn-ghost w-full text-violet"
                  onClick={() => {
                    if (confirm("Delete this deal?")) remove.mutate({ kind: "deals", id: deal.id });
                  }}
                >
                  Delete deal
                </button>
              </>
            )}
            {person && (
              <>
                <div className="text-sm text-clay">
                  {person.title} {person.company ? `· ${person.company}` : ""}
                </div>
                <div className="text-sm">{person.email || "No email"} {person.phone ? `· ${person.phone}` : ""}</div>
                <div className="flex flex-wrap gap-2">{pill(person.temperature)} <span className="text-sm">Score {person.signal_score}</span></div>
                <label className="text-xs text-clay">
                  Next action
                  <input
                    className="field mt-1"
                    defaultValue={person.next_action}
                    onBlur={(e) => patchContact.mutate({ id: person.id, body: { next_action: e.target.value } })}
                  />
                </label>
                <textarea
                  className="field min-h-20"
                  defaultValue={person.notes}
                  onBlur={(e) => patchContact.mutate({ id: person.id, body: { notes: e.target.value } })}
                />
                <div className="flex flex-wrap gap-1">
                  {["cool", "warm", "hot", "star"].map((t) => (
                    <button
                      key={t}
                      className="btn-ghost px-3 py-1 text-xs"
                      onClick={() =>
                        patchContact.mutate({
                          id: person.id,
                          body: { temperature: t, signal_score: t === "star" ? 92 : t === "hot" ? 80 : t === "warm" ? 62 : 40 },
                        })
                      }
                    >
                      {t}
                    </button>
                  ))}
                </div>
                <button className="btn-primary w-full" onClick={() => score.mutate(person.id)}>
                  AI score lead
                </button>
                <button
                  className="btn-ghost w-full"
                  onClick={() => {
                    if (confirm(`Delete ${person.name}?`)) remove.mutate({ kind: "contacts", id: person.id });
                  }}
                >
                  Delete contact
                </button>
              </>
            )}
            <div className="border-t border-line pt-3">
              <div className="text-xs uppercase tracking-wide text-clay">Log activity</div>
              <form
                className="mt-2 space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (note.trim()) logNote.mutate();
                }}
              >
                <select className="field" value={kind} onChange={(e) => setKind(e.target.value)}>
                  {KINDS.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
                <textarea className="field min-h-16" placeholder="What happened?" value={note} onChange={(e) => setNote(e.target.value)} />
                <button className="btn-ghost w-full" type="submit">
                  Log
                </button>
              </form>
              <div className="mt-3 space-y-3">
                {activities.map((a) => (
                  <div key={a.id} className="border-l-2 border-violet/30 pl-3">
                    <div className="text-sm font-medium">{a.title}</div>
                    <div className="text-xs text-clay">{a.kind} · {fmtDate(a.created_at)}</div>
                    <p className="mt-1 text-xs text-ink/70">{a.body}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      )}
    </Shell>
  );
}
