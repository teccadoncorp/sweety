"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { PmShell, pmPill } from "@/components/pm/PmShell";
import { WorkInline } from "@/components/WorkLoader";
import { FEATURE_STATUSES, PmBoard, PmFeature, pmApi } from "@/lib/pm";

export default function PmFeaturesPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [stories, setStories] = useState("");

  const { data: board, isLoading } = useQuery({
    queryKey: ["pm-board", id],
    queryFn: () => pmApi<PmBoard>(`/projects/${id}/board`),
  });

  const create = useMutation({
    mutationFn: () =>
      pmApi<PmFeature>(`/projects/${id}/features`, {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          stories: stories.split("\n").map((s) => s.trim()).filter(Boolean),
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pm-board", id] });
      setTitle("");
      setDescription("");
      setStories("");
      setOpen(false);
    },
  });

  const update = useMutation({
    mutationFn: ({ featureId, body }: { featureId: string; body: Record<string, unknown> }) =>
      pmApi(`/features/${featureId}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-board", id] }),
  });
  const remove = useMutation({
    mutationFn: (featureId: string) => pmApi(`/features/${featureId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-board", id] }),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    create.mutate();
  }

  return (
    <PmShell projectId={id}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link href={`/pm/projects/${id}`} className="text-sm text-ink/50">
            ← Board
          </Link>
          <h1 className="mt-2 font-serif text-3xl sm:text-4xl">Features</h1>
          <p className="mt-2 text-clay">Epics. God Mode and workspace admins create these.</p>
        </div>
        {board?.can_create_features && (
          <button className="btn-primary" onClick={() => setOpen((v) => !v)}>
            New feature
          </button>
        )}
      </div>

      {open && (
        <form onSubmit={onSubmit} className="card mt-6 space-y-3 p-5">
          <label className="block text-sm">
            Title
            <input className="field mt-1" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="block text-sm">
            Description
            <textarea className="field mt-1" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <label className="block text-sm">
            Stories (one per line)
            <textarea className="field mt-1" rows={4} value={stories} onChange={(e) => setStories(e.target.value)} />
          </label>
          {create.isError && <p className="text-sm text-violet">{create.error.message}</p>}
          <button className="btn-primary" disabled={create.isPending}>
            Create feature
          </button>
        </form>
      )}

      {isLoading && <div className="mt-8"><WorkInline label="Loading features" /></div>}

      <div className="mt-8 space-y-3">
        {(board?.features || []).map((f) => (
          <article key={f.id} className="card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs text-clay">
                  {f.key} · {pmPill(f.source)}
                </p>
                <input
                  className="field mt-1 font-serif text-2xl"
                  defaultValue={f.title}
                  onBlur={(e) => {
                    if (e.target.value !== f.title) update.mutate({ featureId: f.id, body: { title: e.target.value } });
                  }}
                />
              </div>
              <div className="flex items-center gap-2">
                {pmPill(f.status)}
                <select
                  className="field w-auto"
                  value={f.status}
                  onChange={(e) => update.mutate({ featureId: f.id, body: { status: e.target.value } })}
                >
                  {FEATURE_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <textarea
              className="field mt-2 text-sm"
              defaultValue={f.description}
              onBlur={(e) => {
                if (e.target.value !== f.description) update.mutate({ featureId: f.id, body: { description: e.target.value } });
              }}
            />
            <div className="mt-3 flex items-center justify-between text-xs text-clay">
              <span>{f.issue_count} issues on the board</span>
              {board?.can_create_features && (
                <button
                  onClick={() => {
                    if (confirm(`Delete ${f.key}?`)) remove.mutate(f.id);
                  }}
                >
                  Delete epic
                </button>
              )}
            </div>
          </article>
        ))}
      </div>

      {!isLoading && (board?.features || []).length === 0 && (
        <div className="card mt-8 p-8 text-center">
          <p className="font-serif text-2xl">No features yet</p>
          <p className="mt-2 text-sm text-clay">
            Open God Mode in marketing or here and ask for a product feature.
          </p>
        </div>
      )}
    </PmShell>
  );
}
