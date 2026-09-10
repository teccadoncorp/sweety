"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { PmShell, pmPill } from "@/components/pm/PmShell";
import { WorkInline } from "@/components/WorkLoader";
import {
  ISSUE_COLUMNS,
  ISSUE_KINDS,
  PmBoard,
  PmComment,
  PmIssue,
  pmApi,
  priorityLabel,
} from "@/lib/pm";

export default function PmIssuePage() {
  const { id, issueId } = useParams<{ id: string; issueId: string }>();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");

  const { data: issue, isLoading } = useQuery({
    queryKey: ["pm-issue", issueId],
    queryFn: () => pmApi<PmIssue>(`/issues/${issueId}`),
  });
  const { data: comments = [] } = useQuery({
    queryKey: ["pm-comments", issueId],
    queryFn: () => pmApi<PmComment[]>(`/issues/${issueId}/comments`),
  });
  const { data: board } = useQuery({
    queryKey: ["pm-board", id],
    queryFn: () => pmApi<PmBoard>(`/projects/${id}/board`),
  });

  const save = useMutation({
    mutationFn: (payload: Partial<PmIssue>) =>
      pmApi<PmIssue>(`/issues/${issueId}`, { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pm-issue", issueId] });
      qc.invalidateQueries({ queryKey: ["pm-board", id] });
    },
  });

  const postComment = useMutation({
    mutationFn: () =>
      pmApi<PmComment>(`/issues/${issueId}/comments`, {
        method: "POST",
        body: JSON.stringify({ body: comment }),
      }),
    onSuccess: () => {
      setComment("");
      qc.invalidateQueries({ queryKey: ["pm-comments", issueId] });
    },
  });

  function onComment(e: FormEvent) {
    e.preventDefault();
    if (!comment.trim()) return;
    postComment.mutate();
  }

  return (
    <PmShell projectId={id}>
      <Link href={`/pm/projects/${id}`} className="text-sm text-ink/50">
        ← Board
      </Link>
      {isLoading && <div className="mt-6"><WorkInline label="Loading issue" /></div>}
      {issue && (
        <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_16rem]">
          <div>
            <p className="text-xs text-clay">
              {issue.key}
              {issue.feature_key ? ` · ${issue.feature_key}` : ""}
            </p>
            <h1 className="mt-1 font-serif text-3xl sm:text-4xl">{issue.title}</h1>
            <textarea
              className="field mt-4 min-h-40"
              defaultValue={issue.description}
              key={issue.updated_at}
              onBlur={(e) => {
                if (e.target.value !== issue.description) save.mutate({ description: e.target.value });
              }}
            />
            <h2 className="mt-8 font-serif text-2xl">Comments</h2>
            <div className="mt-3 space-y-3">
              {comments.map((c) => (
                <div key={c.id} className="rounded-xl border border-line bg-white px-4 py-3">
                  <div className="text-xs text-clay">
                    {c.author_name} · {new Date(c.created_at).toLocaleString()}
                  </div>
                  <div className="mt-1 whitespace-pre-wrap text-sm">{c.body}</div>
                </div>
              ))}
            </div>
            <form onSubmit={onComment} className="mt-4 space-y-2">
              <textarea
                className="field"
                rows={3}
                placeholder="Add a comment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <button className="btn-primary" disabled={postComment.isPending}>
                Comment
              </button>
            </form>
          </div>
          <aside className="card h-fit space-y-3 p-4">
            <label className="block text-xs uppercase tracking-wide text-clay">
              Status
              <select
                className="field mt-1"
                value={issue.status}
                onChange={(e) => save.mutate({ status: e.target.value })}
              >
                {ISSUE_COLUMNS.map((s) => (
                  <option key={s} value={s}>
                    {s.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Type
              <select
                className="field mt-1"
                value={issue.kind}
                onChange={(e) => save.mutate({ kind: e.target.value })}
              >
                {ISSUE_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Priority
              <select
                className="field mt-1"
                value={issue.priority}
                onChange={(e) => save.mutate({ priority: Number(e.target.value) })}
              >
                {[0, 1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    {priorityLabel(n)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Feature
              <select
                className="field mt-1"
                value={issue.feature_id || ""}
                onChange={(e) => save.mutate({ feature_id: e.target.value || null })}
              >
                <option value="">None</option>
                {(board?.features || []).map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.key} {f.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Assignee
              <select
                className="field mt-1"
                value={issue.assignee_id || ""}
                onChange={(e) => save.mutate({ assignee_id: e.target.value || null })}
              >
                <option value="">Unassigned</option>
                {(board?.members || []).map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.display_name || m.email}
                  </option>
                ))}
              </select>
            </label>
            <div className="pt-2 text-xs text-clay">
              Reporter {issue.reporter_name || "—"}
              <div className="mt-2">{pmPill(issue.kind)} {pmPill(issue.status)}</div>
            </div>
          </aside>
        </div>
      )}
    </PmShell>
  );
}
