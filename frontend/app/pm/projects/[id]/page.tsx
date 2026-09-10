"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { PmShell, pmPill } from "@/components/pm/PmShell";
import { WorkInline } from "@/components/WorkLoader";
import {
  ISSUE_COLUMNS,
  ISSUE_KINDS,
  PmBoard,
  PmIssue,
  pmApi,
  priorityLabel,
} from "@/lib/pm";

export default function PmBoardPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [featureFilter, setFeatureFilter] = useState("all");
  const [compose, setCompose] = useState(false);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("task");
  const [featureId, setFeatureId] = useState("");
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

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    create.mutate();
  }

  const filtered = useMemo(() => {
    const columns: Record<string, PmIssue[]> = {};
    for (const col of ISSUE_COLUMNS) {
      const list = board?.columns[col] || [];
      columns[col] =
        featureFilter === "all"
          ? list
          : featureFilter === "none"
            ? list.filter((i) => !i.feature_id)
            : list.filter((i) => i.feature_id === featureFilter);
    }
    return columns;
  }, [board, featureFilter]);

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
              <select className="field w-auto" value={featureFilter} onChange={(e) => setFeatureFilter(e.target.value)}>
                <option value="all">All features</option>
                <option value="none">No feature</option>
                {(board?.features || []).map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.key} {f.title}
                  </option>
                ))}
              </select>
              <Link href={`/pm/projects/${id}/features`} className="btn-ghost">
                Features
              </Link>
              <button className="btn-primary" onClick={() => setCompose((v) => !v)}>
                New issue
              </button>
            </div>
          </div>
          {compose && (
            <form onSubmit={onSubmit} className="mt-4 grid gap-3 rounded-xl border border-line bg-paper p-4 sm:grid-cols-4">
              <input
                className="field sm:col-span-2"
                placeholder="Issue title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <select className="field" value={kind} onChange={(e) => setKind(e.target.value)}>
                {ISSUE_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <select className="field" value={featureId} onChange={(e) => setFeatureId(e.target.value)}>
                <option value="">No feature</option>
                {(board?.features || []).map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.key}
                  </option>
                ))}
              </select>
              <select
                className="field sm:col-span-2"
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
              >
                {[0, 1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    {priorityLabel(n)}
                  </option>
                ))}
              </select>
              <button className="btn-primary sm:col-span-2" disabled={create.isPending}>
                Add to backlog
              </button>
            </form>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden px-4 py-4 sm:px-6">
          {isLoading && <WorkInline label="Loading board" />}
          <div className="flex h-full min-h-[28rem] gap-3">
            {ISSUE_COLUMNS.map((col) => (
              <div key={col} className="flex w-64 shrink-0 flex-col rounded-2xl bg-ink/[0.03] p-3">
                <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wide text-ink/50">
                  <span>{col.replaceAll("_", " ")}</span>
                  <span>{filtered[col]?.length || 0}</span>
                </div>
                <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                  {(filtered[col] || []).map((issue) => (
                    <article key={issue.id} className="rounded-xl bg-white p-3 text-sm shadow-sm">
                      <Link href={`/pm/projects/${id}/issues/${issue.id}`} className="block">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] text-clay">{issue.key}</span>
                          {pmPill(issue.kind)}
                        </div>
                        <div className="mt-1 font-medium">{issue.title}</div>
                        {issue.feature_key && (
                          <div className="mt-1 text-xs text-violet">{issue.feature_key}</div>
                        )}
                        <div className="mt-2 text-xs text-clay">
                          {priorityLabel(issue.priority)}
                          {issue.assignee_name ? ` · ${issue.assignee_name}` : ""}
                        </div>
                      </Link>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {ISSUE_COLUMNS.filter((s) => s !== issue.status).slice(0, 2).map((s) => (
                          <button
                            key={s}
                            type="button"
                            className="rounded-md px-2 py-0.5 text-[11px] text-violet hover:bg-paper"
                            onClick={() => move.mutate({ issueId: issue.id, status: s })}
                          >
                            → {s.replaceAll("_", " ")}
                          </button>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PmShell>
  );
}
