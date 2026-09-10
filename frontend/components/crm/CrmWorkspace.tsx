"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Markdown } from "@/components/Markdown";
import { money, pill } from "@/components/Shell";
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

export const STAGES = ["signal", "qualify", "propose", "commit", "won", "lost"] as const;
const TEMPS = ["all", "ice", "cool", "warm", "hot", "star"] as const;
const KINDS = ["note", "call", "email", "meeting", "task"] as const;
type Tab = "pipeline" | "contacts" | "accounts" | "activity" | "ai";

function stageValue(deals: CrmDeal[]) {
  return deals.reduce((sum, d) => sum + (parseFloat(d.value_usd) || 0), 0);
}

export function CrmWorkspace({ brandId }: { brandId: string }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("pipeline");
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [temp, setTemp] = useState("all");
  const [dealId, setDealId] = useState<string | null>(null);
  const [contactId, setContactId] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const dragging = useRef(false);

  const [cName, setCName] = useState("");
  const [cEmail, setCEmail] = useState("");
  const [cCompany, setCCompany] = useState("");
  const [cTitle, setCTitle] = useState("");
  const [cPhone, setCPhone] = useState("");

  const [aName, setAName] = useState("");
  const [aDomain, setADomain] = useState("");
  const [aIndustry, setAIndustry] = useState("");

  const [dName, setDName] = useState("");
  const [dValue, setDValue] = useState("5000");
  const [dStage, setDStage] = useState("signal");
  const [dClose, setDClose] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q), 280);
    return () => clearTimeout(t);
  }, [q]);

  const { data: board, isLoading } = useQuery({
    queryKey: ["crm-board", brandId],
    queryFn: () => api<CrmBoard>(`/brands/${brandId}/crm/board`),
  });
  const { data: contacts = [] } = useQuery({
    queryKey: ["crm-contacts", brandId, qDebounced, temp],
    queryFn: () =>
      api<CrmContact[]>(
        `/brands/${brandId}/crm/contacts?q=${encodeURIComponent(qDebounced)}&temperature=${temp}`,
      ),
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
  const activityFilter = dealId ? `?deal_id=${dealId}` : contactId ? `?contact_id=${contactId}` : "";
  const { data: activities = [] } = useQuery({
    queryKey: ["crm-activities", brandId, contactId, dealId, tab],
    queryFn: () => api<CrmActivity[]>(`/brands/${brandId}/crm/activities${tab === "activity" ? "" : activityFilter}`),
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["crm-board", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-contacts", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-deals", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-activities", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-accounts", brandId] });
    qc.invalidateQueries({ queryKey: ["crm-overdue", brandId] });
  };

  const patch = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) =>
      api(`/brands/${brandId}/crm/${path}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });
  const create = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) =>
      api(`/brands/${brandId}/crm/${path}`, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (path: string) => api(`/brands/${brandId}/crm/${path}`, { method: "DELETE" }),
    onSuccess: () => {
      setDealId(null);
      setContactId(null);
      refresh();
    },
  });
  const seed = useMutation({
    mutationFn: () => api(`/brands/${brandId}/crm/seed`, { method: "POST" }),
    onSuccess: refresh,
  });
  const wakeCrm = useMutation({
    mutationFn: async () => {
      const steward = agents.find((a) => a.role === "crm");
      if (!steward) throw new Error("Expand the org first so a CRM steward exists.");
      return api(`/brands/${brandId}/agents/${steward.id}/heartbeat`, { method: "POST" });
    },
  });
  const score = useMutation({
    mutationFn: (id: string) =>
      api(`/brands/${brandId}/crm/contacts/${id}/score`, {
        method: "POST",
        signal: AbortSignal.timeout(60_000),
      }),
    onSuccess: refresh,
  });
  const coach = useMutation({
    mutationFn: (id: string) =>
      api<{ next_action: string; risk: string; talking_points: string[]; source: string }>(
        `/brands/${brandId}/crm/deals/${id}/coach`,
        { method: "POST", signal: AbortSignal.timeout(60_000) },
      ),
    onSuccess: refresh,
  });
  const brief = useMutation({
    mutationFn: () =>
      api<{ brief: string; source: string }>(`/brands/${brandId}/crm/ai/brief`, {
        method: "POST",
        signal: AbortSignal.timeout(60_000),
      }),
  });

  const byStage = useMemo(() => {
    const map: Record<string, CrmDeal[]> = {};
    for (const stage of STAGES) map[stage] = [];
    for (const deal of deals) (map[deal.stage] || (map[deal.stage] = [])).push(deal);
    return map;
  }, [deals]);

  const deal = deals.find((d) => d.id === dealId) || null;
  const person = contacts.find((c) => c.id === contactId) || null;
  const busy =
    patch.isPending ||
    create.isPending ||
    remove.isPending ||
    seed.isPending ||
    score.isPending ||
    coach.isPending ||
    brief.isPending ||
    wakeCrm.isPending;

  function onDrop(stage: string, dealKey?: string) {
    const id = dealKey || dragId;
    if (!id) return;
    const current = deals.find((d) => d.id === id);
    setDragId(null);
    if (!current || current.stage === stage) return;
    patch.mutate({ path: `deals/${id}`, body: { stage } });
  }

  function addContact(e: FormEvent) {
    e.preventDefault();
    if (!cName.trim()) return;
    create.mutate({
      path: "contacts",
      body: { name: cName, email: cEmail, company: cCompany, title: cTitle, phone: cPhone, source: "manual", temperature: "warm" },
    });
    setCName("");
    setCEmail("");
    setCCompany("");
    setCTitle("");
    setCPhone("");
  }

  function addAccount(e: FormEvent) {
    e.preventDefault();
    if (!aName.trim()) return;
    create.mutate({ path: "accounts", body: { name: aName, domain: aDomain, industry: aIndustry } });
    setAName("");
    setADomain("");
    setAIndustry("");
  }

  function addDeal(e: FormEvent) {
    e.preventDefault();
    if (!dName.trim()) return;
    create.mutate({
      path: "deals",
      body: {
        name: dName,
        value_usd: dValue,
        stage: dStage,
        close_date: dClose,
        contact_id: contactId,
      },
    });
    setDName("");
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "pipeline", label: "Pipeline" },
    { id: "contacts", label: "Contacts" },
    { id: "accounts", label: "Accounts" },
    { id: "activity", label: "Activity" },
    { id: "ai", label: "AI desk" },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {busy && <WorkLoader label={brief.isPending ? "Writing pipeline brief" : score.isPending ? "Scoring lead" : "Updating CRM"} />}
      <div className="shrink-0 border-b border-line bg-white px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-violet">Customer platform</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">CRM</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" onClick={() => wakeCrm.mutate()}>
              Wake CRM agent
            </button>
            <button className="btn-ghost" onClick={() => seed.mutate()}>
              Load sample pipeline
            </button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-6">
          {[
            ["Pipeline", money(board?.pipeline_usd || "0")],
            ["Weighted", money(board?.weighted_pipeline_usd || "0")],
            ["Won", money(board?.won_usd || "0")],
            ["Open deals", board?.open_deals ?? 0],
            ["Hot leads", board?.hot_leads ?? 0],
            ["Overdue", board?.overdue ?? 0],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-xl border border-line bg-paper px-3 py-3">
              <div className="text-[11px] uppercase tracking-wide text-clay">{label}</div>
              <div className="mt-1 text-xl font-semibold text-violet">{value}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex gap-1 overflow-x-auto">
          {tabs.map((item) => (
            <button
              key={item.id}
              className={`rounded-lg px-3 py-1.5 text-sm ${tab === item.id ? "bg-violet text-white" : "text-clay hover:bg-paper"}`}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-4 py-4 sm:px-6">
        {isLoading && <WorkInline label="Loading CRM" />}

        {tab === "pipeline" && (
          <div>
            <form className="mb-4 flex flex-wrap gap-2" onSubmit={addDeal}>
              <input className="field max-w-xs flex-1" placeholder="New deal" value={dName} onChange={(e) => setDName(e.target.value)} />
              <input className="field w-28" placeholder="Value" value={dValue} onChange={(e) => setDValue(e.target.value)} />
              <input className="field w-36" type="date" value={dClose} onChange={(e) => setDClose(e.target.value)} />
              <select className="field w-36" value={dStage} onChange={(e) => setDStage(e.target.value)}>
                {STAGES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <button className="btn-primary" type="submit">
                Add deal
              </button>
            </form>
            <div className="flex min-h-[28rem] gap-3 overflow-x-auto pb-4">
              {STAGES.map((stage) => {
                const col = byStage[stage] || [];
                return (
                  <section
                    key={stage}
                    onDragOver={(e) => {
                      e.preventDefault();
                      e.dataTransfer.dropEffect = "move";
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      onDrop(stage, e.dataTransfer.getData("text/plain"));
                    }}
                    className={`crm-kanban flex w-64 shrink-0 flex-col rounded-xl border bg-paper p-3 ${
                      dragId ? "border-violet/40" : "border-line"
                    }`}
                  >
                    <div className="mb-3 flex items-start justify-between gap-2">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-violet">{stage}</div>
                        <div className="text-[11px] text-clay">
                          {col.length} · {money(stageValue(col))}
                        </div>
                      </div>
                    </div>
                    <div className="flex min-h-[12rem] flex-1 flex-col gap-2">
                      {col.map((item) => (
                        <article
                          key={item.id}
                          draggable
                          onDragStart={(e) => {
                            dragging.current = true;
                            e.dataTransfer.setData("text/plain", item.id);
                            e.dataTransfer.effectAllowed = "move";
                            setDragId(item.id);
                          }}
                          onDragEnd={() => {
                            setDragId(null);
                            window.setTimeout(() => {
                              dragging.current = false;
                            }, 0);
                          }}
                          onClick={() => {
                            if (dragging.current) return;
                            setDealId(item.id);
                            setContactId(item.contact_id);
                          }}
                          className="cursor-grab rounded-lg border border-line bg-white p-3 shadow-sm active:cursor-grabbing"
                        >
                          <div className="text-sm font-medium">{item.name}</div>
                          <div className="mt-1 text-sm text-violet">{money(item.value_usd)}</div>
                          <div className="mt-1 text-[11px] text-clay">
                            {item.probability}% · {item.contact_name || item.account_name || "Unassigned"}
                          </div>
                          {item.close_date && <div className="mt-1 text-[11px] text-clay">Close {item.close_date}</div>}
                        </article>
                      ))}
                    </div>
                  </section>
                );
              })}
            </div>
            <p className="text-xs text-clay">Drag a card onto another column to move stage. Probability updates automatically.</p>
          </div>
        )}

        {tab === "contacts" && (
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            <form className="card h-fit space-y-2 p-4" onSubmit={addContact}>
              <h2 className="font-semibold">New contact</h2>
              <input className="field" placeholder="Name" value={cName} onChange={(e) => setCName(e.target.value)} />
              <input className="field" placeholder="Email" value={cEmail} onChange={(e) => setCEmail(e.target.value)} />
              <input className="field" placeholder="Title" value={cTitle} onChange={(e) => setCTitle(e.target.value)} />
              <input className="field" placeholder="Company" value={cCompany} onChange={(e) => setCCompany(e.target.value)} />
              <input className="field" placeholder="Phone" value={cPhone} onChange={(e) => setCPhone(e.target.value)} />
              <button className="btn-primary w-full" type="submit">
                Save contact
              </button>
            </form>
            <div>
              <div className="mb-3 flex flex-wrap gap-2">
                <input className="field max-w-sm" placeholder="Search name, email, company" value={q} onChange={(e) => setQ(e.target.value)} />
                {TEMPS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`rounded-full px-3 py-1 text-xs ${temp === t ? "bg-violet text-white" : "bg-paper text-clay"}`}
                    onClick={() => setTemp(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="overflow-x-auto rounded-xl border border-line bg-white">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="border-b border-line bg-paper text-xs uppercase tracking-wide text-clay">
                    <tr>
                      <th className="px-3 py-2">Contact</th>
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
                        className="cursor-pointer border-b border-line hover:bg-paper"
                        onClick={() => setContactId(c.id)}
                      >
                        <td className="px-3 py-2">
                          <div className="font-medium">{c.name}</div>
                          <div className="text-xs text-clay">{c.email || c.phone || "—"}</div>
                        </td>
                        <td className="px-3 py-2">{c.company || c.account_name || "—"}</td>
                        <td className="px-3 py-2">{pill(c.temperature)}</td>
                        <td className="px-3 py-2">{c.signal_score}</td>
                        <td className="px-3 py-2 text-xs text-clay">{c.next_action || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {contacts.length === 0 && <p className="p-6 text-sm text-clay">No contacts yet. Add one or load the sample pipeline.</p>}
              </div>
            </div>
          </div>
        )}

        {tab === "accounts" && (
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            <form className="card h-fit space-y-2 p-4" onSubmit={addAccount}>
              <h2 className="font-semibold">New account</h2>
              <input className="field" placeholder="Company name" value={aName} onChange={(e) => setAName(e.target.value)} />
              <input className="field" placeholder="Domain" value={aDomain} onChange={(e) => setADomain(e.target.value)} />
              <input className="field" placeholder="Industry" value={aIndustry} onChange={(e) => setAIndustry(e.target.value)} />
              <button className="btn-primary w-full" type="submit">
                Save account
              </button>
            </form>
            <div className="grid gap-3 md:grid-cols-2">
              {accounts.map((a) => (
                <article key={a.id} className="card p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-semibold">{a.name}</div>
                      <div className="text-xs text-clay">{a.industry || "—"} · {a.domain || a.website || "no domain"}</div>
                    </div>
                    <button
                      className="text-xs text-violet"
                      onClick={() => {
                        if (confirm(`Delete ${a.name}?`)) remove.mutate(`accounts/${a.id}`);
                      }}
                    >
                      Delete
                    </button>
                  </div>
                  <div className="mt-2 text-sm text-violet">Score {a.signal_score}</div>
                  <p className="mt-2 text-sm text-clay">{a.notes || "No notes"}</p>
                </article>
              ))}
              {accounts.length === 0 && <p className="text-sm text-clay">No accounts yet.</p>}
            </div>
          </div>
        )}

        {tab === "activity" && (
          <div className="mx-auto max-w-3xl space-y-4">
            {activities.map((a) => (
              <div key={a.id} className="border-l-2 border-violet/30 pl-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{a.title}</span>
                  {pill(a.kind)}
                  <span className="text-xs text-clay">{new Date(a.created_at).toLocaleString()}</span>
                </div>
                <p className="mt-1 text-sm text-ink/80">{a.body}</p>
              </div>
            ))}
            {activities.length === 0 && <p className="text-sm text-clay">No activity yet.</p>}
          </div>
        )}

        {tab === "ai" && (
          <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-2">
            <section className="card p-5">
              <h2 className="font-semibold">Weekly pipeline brief</h2>
              <p className="mt-1 text-sm text-clay">Uses your live board. Falls back to a heuristic brief if the model is offline.</p>
              <button className="btn-primary mt-4" onClick={() => brief.mutate()}>
                Generate brief
              </button>
              {brief.data && (
                <div className="mt-4">
                  <p className="mb-2 text-xs uppercase tracking-wide text-clay">{brief.data.source}</p>
                  <Markdown>{brief.data.brief}</Markdown>
                </div>
              )}
            </section>
            <section className="card p-5">
              <h2 className="font-semibold">Overdue follow-ups</h2>
              <p className="mt-1 text-sm text-clay">Next action set, no touch in 7 days.</p>
              <div className="mt-4 space-y-3">
                {overdue.map((c) => (
                  <div key={c.id} className="rounded-lg border border-line p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-medium">{c.name}</div>
                        <div className="text-xs text-clay">{c.next_action}</div>
                      </div>
                      <button className="btn-ghost px-3 py-1 text-xs" onClick={() => score.mutate(c.id)}>
                        Score
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

      {deal && (
        <Drawer title={deal.name} onClose={() => setDealId(null)}>
          <DealEditor
            deal={deal}
            contacts={contacts}
            accounts={accounts}
            activities={activities.filter((a) => a.deal_id === deal.id || (!dealId && a.contact_id === deal.contact_id))}
            coaching={coach.data && coach.variables === deal.id ? coach.data : undefined}
            onSave={(body) => patch.mutate({ path: `deals/${deal.id}`, body })}
            onCoach={() => coach.mutate(deal.id)}
            onDelete={() => {
              if (confirm("Delete this deal?")) remove.mutate(`deals/${deal.id}`);
            }}
            onActivity={(body) =>
              create.mutate({
                path: "activities",
                body: { ...body, deal_id: deal.id, contact_id: deal.contact_id, account_id: deal.account_id },
              })
            }
          />
        </Drawer>
      )}

      {person && !deal && (
        <Drawer title={person.name} onClose={() => setContactId(null)}>
          <ContactEditor
            contact={person}
            accounts={accounts}
            activities={activities.filter((a) => a.contact_id === person.id)}
            onSave={(body) => patch.mutate({ path: `contacts/${person.id}`, body })}
            onScore={() => score.mutate(person.id)}
            onDelete={() => {
              if (confirm("Delete this contact?")) remove.mutate(`contacts/${person.id}`);
            }}
            onActivity={(body) => create.mutate({ path: "activities", body: { ...body, contact_id: person.id, account_id: person.account_id } })}
          />
        </Drawer>
      )}
    </div>
  );
}

function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-ink/20">
      <button className="h-full flex-1" onClick={onClose} aria-label="Close" />
      <aside className="flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-line bg-white p-5 shadow-card">
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button className="text-sm text-clay" onClick={onClose}>
            Close
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}

function DealEditor({
  deal,
  contacts,
  accounts,
  activities,
  coaching,
  onSave,
  onCoach,
  onDelete,
  onActivity,
}: {
  deal: CrmDeal;
  contacts: CrmContact[];
  accounts: CrmAccount[];
  activities: CrmActivity[];
  coaching?: { next_action: string; risk: string; talking_points: string[]; source: string };
  onSave: (body: Record<string, unknown>) => void;
  onCoach: () => void;
  onDelete: () => void;
  onActivity: (body: Record<string, unknown>) => void;
}) {
  const [name, setName] = useState(deal.name);
  const [value, setValue] = useState(String(deal.value_usd));
  const [close, setClose] = useState(deal.close_date);
  const [notes, setNotes] = useState(deal.notes);
  const [lost, setLost] = useState(deal.lost_reason || "");
  const [kind, setKind] = useState("note");
  const [log, setLog] = useState("");

  useEffect(() => {
    setName(deal.name);
    setValue(String(deal.value_usd));
    setClose(deal.close_date);
    setNotes(deal.notes);
    setLost(deal.lost_reason || "");
  }, [deal.id, deal.name, deal.value_usd, deal.close_date, deal.notes, deal.lost_reason]);

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap gap-2">
        {pill(deal.stage)}
        <span>{deal.probability}% likely</span>
      </div>
      <input className="field" value={name} onChange={(e) => setName(e.target.value)} />
      <input className="field" value={value} onChange={(e) => setValue(e.target.value)} />
      <input className="field" type="date" value={close} onChange={(e) => setClose(e.target.value)} />
      <select
        className="field"
        value={deal.contact_id || ""}
        onChange={(e) => onSave({ contact_id: e.target.value || null })}
      >
        <option value="">No contact</option>
        {contacts.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <select
        className="field"
        value={deal.account_id || ""}
        onChange={(e) => onSave({ account_id: e.target.value || null })}
      >
        <option value="">No account</option>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <select className="field" value={deal.stage} onChange={(e) => onSave({ stage: e.target.value, lost_reason: lost })}>
        {STAGES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      {deal.stage === "lost" && (
        <input className="field" placeholder="Lost reason" value={lost} onChange={(e) => setLost(e.target.value)} />
      )}
      <textarea className="field min-h-24" value={notes} onChange={(e) => setNotes(e.target.value)} />
      <button
        className="btn-primary w-full"
        onClick={() => onSave({ name, value_usd: value, close_date: close, notes, lost_reason: lost })}
      >
        Save deal
      </button>
      <button className="btn-ghost w-full" onClick={onCoach}>
        AI coach this deal
      </button>
      {coaching && (
        <div className="rounded-lg bg-paper p-3">
          <div className="text-xs uppercase text-clay">{coaching.source}</div>
          <p className="mt-1 font-medium">{coaching.next_action}</p>
          <p className="mt-1 text-clay">{coaching.risk}</p>
          <ul className="mt-2 list-disc pl-4">
            {(coaching.talking_points || []).map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      )}
      <form
        className="space-y-2 border-t border-line pt-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!log.trim()) return;
          onActivity({ kind, title: kind[0].toUpperCase() + kind.slice(1), body: log });
          setLog("");
        }}
      >
        <div className="font-medium">Log activity</div>
        <select className="field" value={kind} onChange={(e) => setKind(e.target.value)}>
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
        <textarea className="field min-h-16" placeholder="What happened?" value={log} onChange={(e) => setLog(e.target.value)} />
        <button className="btn-ghost w-full" type="submit">
          Log
        </button>
      </form>
      <div className="space-y-2">
        {activities.map((a) => (
          <div key={a.id} className="border-l border-violet/30 pl-3">
            <div className="text-xs text-clay">
              {a.kind} · {new Date(a.created_at).toLocaleString()}
            </div>
            <div>{a.title}</div>
            <p className="text-clay">{a.body}</p>
          </div>
        ))}
      </div>
      <button className="text-sm text-violet" onClick={onDelete}>
        Delete deal
      </button>
    </div>
  );
}

function ContactEditor({
  contact,
  accounts,
  activities,
  onSave,
  onScore,
  onDelete,
  onActivity,
}: {
  contact: CrmContact;
  accounts: CrmAccount[];
  activities: CrmActivity[];
  onSave: (body: Record<string, unknown>) => void;
  onScore: () => void;
  onDelete: () => void;
  onActivity: (body: Record<string, unknown>) => void;
}) {
  const [form, setForm] = useState({
    name: contact.name,
    email: contact.email,
    phone: contact.phone,
    title: contact.title,
    company: contact.company,
    next_action: contact.next_action,
    notes: contact.notes,
  });
  const [log, setLog] = useState("");
  const [kind, setKind] = useState("note");

  useEffect(() => {
    setForm({
      name: contact.name,
      email: contact.email,
      phone: contact.phone,
      title: contact.title,
      company: contact.company,
      next_action: contact.next_action,
      notes: contact.notes,
    });
  }, [contact.id, contact.name, contact.email, contact.phone, contact.title, contact.company, contact.next_action, contact.notes]);

  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        {pill(contact.temperature)}
        <span>Score {contact.signal_score}</span>
      </div>
      {Object.entries({ name: "Name", email: "Email", phone: "Phone", title: "Title", company: "Company", next_action: "Next action" }).map(
        ([key, label]) => (
          <label key={key} className="block text-xs text-clay">
            {label}
            <input
              className="field mt-1"
              value={(form as Record<string, string>)[key]}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          </label>
        ),
      )}
      <select
        className="field"
        value={contact.account_id || ""}
        onChange={(e) => onSave({ account_id: e.target.value || null })}
      >
        <option value="">No account</option>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <select
        className="field"
        value={contact.temperature}
        onChange={(e) => onSave({ temperature: e.target.value })}
      >
        {TEMPS.filter((t) => t !== "all").map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <textarea className="field min-h-20" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      <button className="btn-primary w-full" onClick={() => onSave(form)}>
        Save contact
      </button>
      <button className="btn-ghost w-full" onClick={onScore}>
        AI score this lead
      </button>
      <form
        className="space-y-2 border-t border-line pt-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!log.trim()) return;
          onActivity({ kind, title: kind[0].toUpperCase() + kind.slice(1), body: log });
          setLog("");
        }}
      >
        <select className="field" value={kind} onChange={(e) => setKind(e.target.value)}>
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
        <textarea className="field min-h-16" placeholder="Log a call, email, or note" value={log} onChange={(e) => setLog(e.target.value)} />
        <button className="btn-ghost w-full" type="submit">
          Log activity
        </button>
      </form>
      <div className="space-y-2">
        {activities.map((a) => (
          <div key={a.id} className="border-l border-violet/30 pl-3">
            <div className="text-xs text-clay">
              {a.kind} · {new Date(a.created_at).toLocaleString()}
            </div>
            <p>{a.body}</p>
          </div>
        ))}
      </div>
      <button className="text-sm text-violet" onClick={onDelete}>
        Delete contact
      </button>
    </div>
  );
}
