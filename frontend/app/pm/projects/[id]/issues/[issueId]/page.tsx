"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
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
  const router = useRouter();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [subTitle, setSubTitle] = useState("");

  const { data: issue, isLoading } = useQuery({
    queryKey: ["pm-issue", issueId],
    queryFn: () => pmApi<PmIssue>(`/issues/${issueId}`),
  });
  const { data: comments = [] } = useQuery({
    queryKey: ["pm-comments", issueId],
    queryFn: () => pmApi<PmComment[]>(`/issues/${issueId}/comments`),
  });
  const { data: subs = [] } = useQuery({
    queryKey: ["pm-subs", issueId],
    queryFn: () => pmApi<PmIssue[]>(`/projects/${id}/issues?parent_id=${issueId}`),
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

  const addSub = useMutation({
    mutationFn: () =>
      pmApi<PmIssue>(`/projects/${id}/issues`, {
        method: "POST",
        body: JSON.stringify({ title: subTitle, kind: "subticket", parent_id: issueId, feature_id: issue?.feature_id }),
      }),
    onSuccess: () => {
      setSubTitle("");
      qc.invalidateQueries({ queryKey: ["pm-subs", issueId] });
      qc.invalidateQueries({ queryKey: ["pm-issue", issueId] });
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

  const editComment = useMutation({
    mutationFn: ({ commentId, body }: { commentId: string; body: string }) =>
      pmApi(`/comments/${commentId}`, { method: "PATCH", body: JSON.stringify({ body }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-comments", issueId] }),
  });

  const removeComment = useMutation({
    mutationFn: (commentId: string) => pmApi(`/comments/${commentId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-comments", issueId] }),
  });

  const remove = useMutation({
    mutationFn: () => pmApi(`/issues/${issueId}`, { method: "DELETE" }),
    onSuccess: () => router.push(`/pm/projects/${id}`),
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
      {isLoading && (
        <div className="mt-6">
          <WorkInline label="Loading issue" />
        </div>
      )}
      {issue && (
        <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_16rem]">
          <div>
            <p className="text-xs text-clay">
              {issue.key}
              {issue.feature_key ? ` · ${issue.feature_key}` : ""}
              {issue.parent_key ? ` · child of ${issue.parent_key}` : ""}
            </p>
            <input
              className="field mt-2 font-serif text-3xl"
              defaultValue={issue.title}
              onBlur={(e) => {
                if (e.target.value !== issue.title) save.mutate({ title: e.target.value });
              }}
            />
            <textarea
              className="field mt-4 min-h-40"
              defaultValue={issue.description}
              key={issue.updated_at}
              onBlur={(e) => {
                if (e.target.value !== issue.description) save.mutate({ description: e.target.value });
              }}
            />
            <h2 className="mt-8 font-serif text-2xl">Subtickets</h2>
            <div className="mt-3 space-y-2">
              {subs.map((s) => (
                <Link key={s.id} href={`/pm/projects/${id}/issues/${s.id}`} className="card flex items-center justify-between p-3">
                  <span>
                    {s.key} {s.title}
                  </span>
                  {pmPill(s.status)}
                </Link>
              ))}
            </div>
            <form
              className="mt-3 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (subTitle.trim()) addSub.mutate();
              }}
            >
              <input className="field" placeholder="New subticket" value={subTitle} onChange={(e) => setSubTitle(e.target.value)} />
              <button className="btn-ghost">Add</button>
            </form>
            <h2 className="mt-8 font-serif text-2xl">Comments</h2>
            <div className="mt-3 space-y-3">
              {comments.map((c) => (
                <div key={c.id} className="rounded-xl border border-line bg-white px-4 py-3">
                  <div className="flex items-center justify-between text-xs text-clay">
                    <span>
                      {c.author_name} · {new Date(c.created_at).toLocaleString()}
                    </span>
                    <button onClick={() => removeComment.mutate(c.id)}>Delete</button>
                  </div>
                  <textarea
                    className="field mt-2 min-h-16 text-sm"
                    defaultValue={c.body}
                    onBlur={(e) => {
                      if (e.target.value !== c.body) editComment.mutate({ commentId: c.id, body: e.target.value });
                    }}
                  />
                </div>
              ))}
            </div>
            <form onSubmit={onComment} className="mt-4 space-y-2">
              <textarea className="field" rows={3} placeholder="Add a comment" value={comment} onChange={(e) => setComment(e.target.value)} />
              <button className="btn-primary" disabled={postComment.isPending}>
                Comment
              </button>
            </form>
          </div>
          <aside className="card h-fit space-y-3 p-4">
            <label className="block text-xs uppercase tracking-wide text-clay">
              Status
              <select className="field mt-1" value={issue.status} onChange={(e) => save.mutate({ status: e.target.value })}>
                {ISSUE_COLUMNS.map((s) => (
                  <option key={s} value={s}>
                    {s.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Type
              <select className="field mt-1" value={issue.kind} onChange={(e) => save.mutate({ kind: e.target.value })}>
                {ISSUE_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Priority
              <select className="field mt-1" value={issue.priority} onChange={(e) => save.mutate({ priority: Number(e.target.value) })}>
                {[0, 1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    {priorityLabel(n)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Due date
              <input
                className="field mt-1"
                type="date"
                value={issue.due_date || ""}
                onChange={(e) => save.mutate({ due_date: e.target.value || null })}
              />
            </label>
            <label className="block text-xs uppercase tracking-wide text-clay">
              Epic
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
                    {m.display_name || m.email} {m.online ? "· online" : ""}
                  </option>
                ))}
              </select>
            </label>
            <div className="pt-2 text-xs text-clay">
              Reporter {issue.reporter_name || "—"}
              <div className="mt-2">
                {pmPill(issue.kind)} {pmPill(issue.status)}
                {issue.overdue && pmPill("overdue")}
              </div>
            </div>
            <button
              className="btn-ghost w-full text-violet"
              onClick={() => {
                if (confirm(`Delete ${issue.key}?`)) remove.mutate();
              }}
            >
              Delete ticket
            </button>
          </aside>
        </div>
      )}
    </PmShell>
  );
}
