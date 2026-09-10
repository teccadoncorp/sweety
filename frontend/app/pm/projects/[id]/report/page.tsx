"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { PmShell, pmPill } from "@/components/pm/PmShell";
import { WorkInline } from "@/components/WorkLoader";
import { PmReport, pmApi } from "@/lib/pm";

export default function PmReportPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["pm-report", id],
    queryFn: () => pmApi<PmReport>(`/projects/${id}/report`),
  });

  return (
    <PmShell projectId={id}>
      <Link href={`/pm/projects/${id}`} className="text-sm text-ink/50">
        ← Board
      </Link>
      <h1 className="mt-2 font-serif text-3xl sm:text-4xl">Ticket report</h1>
      <p className="mt-2 text-clay">Epics, stories, tickets, bugs, and subtickets in one view.</p>
      {isLoading && (
        <div className="mt-6">
          <WorkInline label="Building report" />
        </div>
      )}
      {data && (
        <>
          <section className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Object.entries(data.totals).map(([k, v]) => (
              <div key={k} className="card p-4">
                <div className="text-[11px] uppercase tracking-wide text-clay">{k}</div>
                <div className="mt-1 font-serif text-3xl">{v}</div>
              </div>
            ))}
          </section>
          <section className="mt-8 grid gap-4 lg:grid-cols-2">
            <div className="card p-5">
              <h2 className="font-serif text-2xl">By status</h2>
              <div className="mt-3 space-y-2">
                {Object.entries(data.by_status).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-sm">
                    <span>{pmPill(k)}</span>
                    <span>{v}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card p-5">
              <h2 className="font-serif text-2xl">By type</h2>
              <div className="mt-3 space-y-2">
                {Object.entries(data.by_kind).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-sm">
                    <span>{pmPill(k)}</span>
                    <span>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
          <section className="mt-8 card p-5">
            <h2 className="font-serif text-2xl">Assignees</h2>
            <div className="mt-3 space-y-2">
              {data.by_assignee.map((row) => (
                <div key={row.name} className="flex items-center justify-between text-sm">
                  <span>{row.name}</span>
                  <span className="text-clay">
                    {row.open} open · {row.done} done
                  </span>
                </div>
              ))}
            </div>
          </section>
          <section className="mt-8 card p-5">
            <h2 className="font-serif text-2xl">Epics</h2>
            <div className="mt-4 space-y-3">
              {data.by_epic.map((epic) => (
                <div key={epic.id}>
                  <div className="flex items-center justify-between text-sm">
                    <span>
                      {epic.key} · {epic.title}
                    </span>
                    <span>{epic.pct}%</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-paper">
                    <div className="h-full bg-violet transition-all" style={{ width: `${epic.pct}%` }} />
                  </div>
                </div>
              ))}
              {data.by_epic.length === 0 && <p className="text-sm text-clay">No epics yet.</p>}
            </div>
          </section>
          <section className="mt-8">
            <h2 className="font-serif text-2xl">Overdue</h2>
            <div className="mt-3 space-y-2">
              {data.overdue.map((issue) => (
                <Link key={issue.id} href={`/pm/projects/${id}/issues/${issue.id}`} className="card block p-3 hover:border-violet/40">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {issue.key} {issue.title}
                    </span>
                    {pmPill("overdue")}
                  </div>
                  <p className="mt-1 text-xs text-clay">Due {issue.due_date} · {issue.assignee_name || "Unassigned"}</p>
                </Link>
              ))}
              {data.overdue.length === 0 && <p className="mt-2 text-sm text-clay">Nothing overdue.</p>}
            </div>
          </section>
        </>
      )}
    </PmShell>
  );
}
