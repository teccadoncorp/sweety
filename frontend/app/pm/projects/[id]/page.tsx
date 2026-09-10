"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useMemo, useState, type DragEvent } from "react";
import { PmShell, pmPill } from "@/components/pm/PmShell";
import { WorkInline } from "@/components/WorkLoader";
import {
  ISSUE_COLUMNS,
  ISSUE_KINDS,
  PmBoard,
  PmIssue,
  pmApi,
  presenceLabel,
  priorityLabel,
} from "@/lib/pm";

export default function PmBoardPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [featureFilter, setFeatureFilter] = useState("all");
  const [kindFilter, setKindFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [assigneeFilter, setAssigneeFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [dueFilter, setDueFilter] = useState("all");
  const [compose, setCompose] = useState(false);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("ticket");
  const [featureId, setFeatureId] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [priority, setPriority] = useState(2);

  const { data: board, isLoading } = useQuery({
    queryKey: ["pm-board", id],
    queryFn: () => pmApi<PmBoard>(`/projects/${id}/board`),
  });

  const create = useMutation({
    mutationFn: () =>
      pmApi<PmIssue>(`/projects/${id}/issues`, {
        method: "POST",
        body: JSON.stringify({
          title,
          kind,
          priority,
          feature_id: featureId || null,
          assignee_id: assigneeId || null,
          due_date: dueDate || null,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pm-board", id] });
      setTitle("");
      setCompose(false);
    },
  });

  const move = useMutation({
    mutationFn: ({ issueId, status }: { issueId: string; status: string }) =>
      pmApi(`/issues/${issueId}`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-board", id] }),
  });

  const remove = useMutation({
    mutationFn: (issueId: string) => pmApi(`/issues/${issueId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-board", id] }),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    create.mutate();
  }

  function drop(status: string, event: DragEvent) {
    event.preventDefault();
    const issueId = event.dataTransfer.getData("text/plain");
    if (issueId) move.mutate({ issueId, status });
  }

  const filtered = useMemo(() => {
    const columns: Record<string, PmIssue[]> = {};
    for (const col of ISSUE_COLUMNS) {
      columns[col] = (board?.columns[col] || []).filter((issue) => {
        if (statusFilter !== "all" && issue.status !== statusFilter) return false;
        if (featureFilter === "none" && issue.feature_id) return false;
        if (featureFilter !== "all" && featureFilter !== "none" && issue.feature_id !== featureFilter) return false;
        if (kindFilter !== "all" && issue.kind !== kindFilter) return false;
        if (assigneeFilter === "unassigned" && issue.assignee_id) return false;
        if (assigneeFilter !== "all" && assigneeFilter !== "unassigned" && issue.assignee_id !== assigneeFilter) return false;
        if (priorityFilter !== "all" && issue.priority !== Number(priorityFilter)) return false;
        if (dueFilter === "overdue" && !issue.overdue) return false;
        if (dueFilter === "dated" && !issue.due_date) return false;
        if (dueFilter === "none" && issue.due_date) return false;
        if (q.trim() && !`${issue.title} ${issue.key} ${issue.feature_key}`.toLowerCase().includes(q.trim().toLowerCase())) {
          return false;
        }
        return !issue.parent_id;
      });
    }
    return columns;
  }, [board, featureFilter, kindFilter, statusFilter, assigneeFilter, priorityFilter, dueFilter, q]);

  return (
    <PmShell projectId={id} full>
      <div className="flex h-full min-h-0 flex-col">
        <div className="shrink-0 border-b border-line bg-white px-4 py-4 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-cyan">{board?.project.key}</p>
              <h1 className="font-serif text-3xl">{board?.project.name || "Board"}</h1>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link href={`/pm/projects/${id}/features`} className="btn-ghost">
                Epics
              </Link>
              <Link href={`/pm/projects/${id}/report`} className="btn-ghost">
                Reports
              </Link>
              <button className="btn-primary" onClick={() => setCompose((v) => !v)}>
                Create
              </button>
            </div>
          </div>
          <div className="pm-filter-bar mt-4">
            <input className="field" placeholder="Search tickets" value={q} onChange={(e) => setQ(e.target.value)} />
            <select className="field" value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
              <option value="all">All types</option>
              {ISSUE_KINDS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
            <select className="field" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">All statuses</option>
              {ISSUE_COLUMNS.map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <select className="field" value={featureFilter} onChange={(e) => setFeatureFilter(e.target.value)}>
              <option value="all">All epics</option>
              <option value="none">No epic</option>
              {(board?.features || []).map((f) => (
                <option key={f.id} value={f.id}>
                  {f.key} {f.title}
                </option>
              ))}
            </select>
            <select className="field" value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)}>
              <option value="all">Anyone</option>
              <option value="unassigned">Unassigned</option>
              {(board?.members || []).map((m) => (
                <option key={m.user_id} value={m.user_id}>
                  {m.display_name || m.email}
                </option>
              ))}
            </select>
            <select className="field" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
              <option value="all">All priorities</option>
              {[0, 1, 2, 3, 4].map((n) => (
                <option key={n} value={n}>
                  {priorityLabel(n)}
                </option>
              ))}
            </select>
            <select className="field" value={dueFilter} onChange={(e) => setDueFilter(e.target.value)}>
              <option value="all">Any due date</option>
              <option value="overdue">Overdue</option>
              <option value="dated">Has due date</option>
              <option value="none">No due date</option>
            </select>
          </div>
          {compose && (
            <form onSubmit={onSubmit} className="pm-create mt-4">
              <input className="field sm:col-span-2" placeholder="Ticket title" value={title} onChange={(e) => setTitle(e.target.value)} />
              <select className="field" value={kind} onChange={(e) => setKind(e.target.value)}>
                {ISSUE_KINDS.filter((k) => k !== "subticket").map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <select className="field" value={featureId} onChange={(e) => setFeatureId(e.target.value)}>
                <option value="">No epic</option>
                {(board?.features || []).map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.key}
                  </option>
                ))}
              </select>
              <select className="field" value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
                <option value="">Unassigned</option>
                {(board?.members || []).map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.display_name || m.email}
                  </option>
                ))}
              </select>
              <input className="field" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              <select className="field" value={priority} onChange={(e) => setPriority(Number(e.target.value))}>
                {[0, 1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    {priorityLabel(n)}
                  </option>
                ))}
              </select>
              <button className="btn-primary" disabled={create.isPending}>
                Add ticket
              </button>
            </form>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden px-4 py-4 sm:px-6">
          {isLoading && <WorkInline label="Loading board" />}
          <div className="flex h-full min-h-[28rem] gap-3">
            {ISSUE_COLUMNS.map((col) => (
              <div
                key={col}
                className="pm-col"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => drop(col, e)}
              >
                <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wide text-ink/50">
                  <span>{col.replaceAll("_", " ")}</span>
                  <span>{filtered[col]?.length || 0}</span>
                </div>
                <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                  {(filtered[col] || []).map((issue) => (
                    <article
                      key={issue.id}
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData("text/plain", issue.id)}
                      className={`pm-card ${issue.overdue ? "is-overdue" : ""}`}
                    >
                      <Link href={`/pm/projects/${id}/issues/${issue.id}`} className="block">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] text-clay">{issue.key}</span>
                          {pmPill(issue.kind)}
                        </div>
                        <div className="mt-1 font-medium">{issue.title}</div>
                        {issue.feature_key && <div className="mt-1 text-xs text-violet">{issue.feature_key}</div>}
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-clay">
                          <span>{priorityLabel(issue.priority)}</span>
                          {issue.due_date && <span className={issue.overdue ? "text-violet" : ""}>Due {issue.due_date}</span>}
                          {issue.assignee_name && <span>{issue.assignee_name}</span>}
                          {issue.subticket_count > 0 && <span>{issue.subticket_count} sub</span>}
                        </div>
                      </Link>
                      <div className="mt-2 flex justify-between">
                        <button
                          type="button"
                          className="text-[11px] text-clay"
                          onClick={() => {
                            if (confirm(`Delete ${issue.key}?`)) remove.mutate(issue.id);
                          }}
                        >
                          Delete
                        </button>
                        <span className="text-[11px] text-clay">Drag to move</span>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        {board && board.members.length > 0 && (
          <div className="shrink-0 border-t border-line bg-white px-4 py-2 text-xs text-clay">
            {board.members.map((m) => (
              <span key={m.id} className="mr-4">
                <span className={`pm-dot ${m.online ? "is-on" : ""}`} /> {m.display_name || m.email} · {presenceLabel(m)}
              </span>
            ))}
          </div>
        )}
      </div>
    </PmShell>
  );
}
