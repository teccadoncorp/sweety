"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { PmShell, pmPill } from "@/components/pm/PmShell";
import { WorkInline } from "@/components/WorkLoader";
import { getPmWorkspaceId, pmApi, PmMe, PmProject, setPmWorkspaceId } from "@/lib/pm";

export default function PmHomePage() {
  const qc = useQueryClient();
  const { data: me } = useQuery({
    queryKey: ["pm-me"],
    queryFn: () => pmApi<PmMe>("/auth/me"),
  });
  const workspace = me?.workspaces.find((w) => w.id === getPmWorkspaceId()) || me?.workspaces[0];
  useEffect(() => {
    if (workspace) setPmWorkspaceId(workspace.id);
  }, [workspace]);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["pm-projects", workspace?.id],
    queryFn: () => pmApi<PmProject[]>(`/workspaces/${workspace!.id}/projects`),
    enabled: Boolean(workspace?.id),
  });

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");

  const invite = useMutation({
    mutationFn: () =>
      pmApi(`/workspaces/${workspace!.id}/members`, {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail, role: "member" }),
      }),
    onSuccess: () => {
      setInviteEmail("");
      qc.invalidateQueries({ queryKey: ["pm-me"] });
    },
  });

  const create = useMutation({
    mutationFn: () =>
      pmApi<PmProject>(`/workspaces/${workspace!.id}/projects`, {
        method: "POST",
        body: JSON.stringify({ name, key, description }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pm-projects", workspace?.id] });
      setOpen(false);
      setName("");
      setKey("");
      setDescription("");
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate();
  }

  return (
    <PmShell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-cyan">Task console</p>
          <h1 className="mt-1 font-serif text-3xl sm:text-4xl">{workspace?.name || "Projects"}</h1>
          <p className="mt-2 max-w-xl text-clay">
            Features come from God Mode. The board is where the team ships them.
          </p>
        </div>
        {workspace?.can_create_features && (
          <button className="btn-primary" onClick={() => setOpen((v) => !v)}>
            New project
          </button>
        )}
      </div>

      {open && (
        <form onSubmit={onSubmit} className="card mt-6 grid gap-3 p-5 sm:grid-cols-2">
          <label className="text-sm sm:col-span-1">
            Name
            <input className="field mt-1" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="text-sm">
            Key
            <input
              className="field mt-1 uppercase"
              placeholder="CORE"
              value={key}
              onChange={(e) => setKey(e.target.value.toUpperCase())}
            />
          </label>
          <label className="text-sm sm:col-span-2">
            Description
            <textarea className="field mt-1" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          {create.isError && <p className="text-sm text-violet sm:col-span-2">{create.error.message}</p>}
          <div className="sm:col-span-2">
            <button className="btn-primary" disabled={create.isPending}>
              Create project
            </button>
          </div>
        </form>
      )}

      {isLoading && <div className="mt-8"><WorkInline label="Loading projects" /></div>}

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {projects.map((p) => (
          <Link key={p.id} href={`/pm/projects/${p.id}`} className="card block p-5 hover:border-violet/40">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-serif text-2xl">{p.name}</h2>
              {pmPill(p.key)}
            </div>
            <p className="mt-2 line-clamp-2 text-sm text-clay">{p.description || "No description"}</p>
            <p className="mt-4 text-xs text-clay">
              {p.feature_count} features · {p.issue_count} issues
              {p.sweety_brand_id ? " · linked from God Mode" : ""}
            </p>
          </Link>
        ))}
      </div>

      {workspace?.can_create_features && (
        <form
          className="mt-8 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (inviteEmail.trim()) invite.mutate();
          }}
        >
          <label className="text-sm">
            Invite member
            <input
              className="field mt-1 w-64"
              type="email"
              placeholder="they@team.com (must register first)"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
            />
          </label>
          <button className="btn-ghost" disabled={invite.isPending}>
            Add to workspace
          </button>
          {invite.isError && <p className="text-sm text-violet">{invite.error.message}</p>}
        </form>
      )}

      {!isLoading && projects.length === 0 && (
        <div className="card mt-8 p-8 text-center">
          <p className="font-serif text-2xl">No projects yet</p>
          <p className="mt-2 text-sm text-clay">
            Ask God Mode for a feature, or create a project if you are an admin.
          </p>
          {workspace?.can_create_features && (
            <Link href="/pm/godmode" className="btn-primary mt-4 inline-flex">
              Open God Mode
            </Link>
          )}
        </div>
      )}
    </PmShell>
  );
}
