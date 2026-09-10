"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { PmShell, pmPill } from "@/components/pm/PmShell";
import { getPmWorkspaceId, pmApi, PmMe, PmMember, PmWorkspace, presenceLabel, setPmWorkspaceId } from "@/lib/pm";

export default function PmPeoplePage() {
  const qc = useQueryClient();
  const { data: me } = useQuery({ queryKey: ["pm-me"], queryFn: () => pmApi<PmMe>("/auth/me") });
  const workspaceMeta = me?.workspaces.find((w) => w.id === getPmWorkspaceId()) || me?.workspaces[0];
  useEffect(() => {
    if (workspaceMeta) setPmWorkspaceId(workspaceMeta.id);
  }, [workspaceMeta]);

  const { data: workspace } = useQuery({
    queryKey: ["pm-workspace", workspaceMeta?.id],
    queryFn: () => pmApi<PmWorkspace>(`/workspaces/${workspaceMeta!.id}`),
    enabled: Boolean(workspaceMeta?.id),
    refetchInterval: 20_000,
  });

  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("member");
  const [temp, setTemp] = useState<string | null>(null);

  const invite = useMutation({
    mutationFn: () =>
      pmApi<PmMember>(`/workspaces/${workspace!.id}/members`, {
        method: "POST",
        body: JSON.stringify({ email, display_name: name, role }),
      }),
    onSuccess: (row) => {
      setEmail("");
      setName("");
      setTemp(row.temporary_password || null);
      qc.invalidateQueries({ queryKey: ["pm-workspace", workspace?.id] });
    },
  });

  const patch = useMutation({
    mutationFn: ({ memberId, body }: { memberId: string; body: Record<string, unknown> }) =>
      pmApi(`/workspaces/${workspace!.id}/members/${memberId}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-workspace", workspace?.id] }),
  });

  const remove = useMutation({
    mutationFn: (memberId: string) =>
      pmApi(`/workspaces/${workspace!.id}/members/${memberId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pm-workspace", workspace?.id] }),
  });

  function onInvite(e: FormEvent) {
    e.preventDefault();
    if (email.trim()) invite.mutate();
  }

  return (
    <PmShell>
      <p className="text-xs uppercase tracking-[0.2em] text-cyan">Team</p>
      <h1 className="mt-1 font-serif text-3xl sm:text-4xl">People</h1>
      <p className="mt-2 text-clay">Invite, assign roles, and see who is online.</p>

      {workspaceMeta?.can_create_features && (
        <form onSubmit={onInvite} className="card mt-6 grid gap-3 p-5 sm:grid-cols-4">
          <input className="field" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="field" placeholder="Display name" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="field" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="member">member</option>
            <option value="admin">admin</option>
            <option value="owner">owner</option>
          </select>
          <button className="btn-primary" disabled={invite.isPending}>
            Invite user
          </button>
          {invite.isError && <p className="text-sm text-violet sm:col-span-4">{invite.error.message}</p>}
          {temp && (
            <p className="text-sm text-moss sm:col-span-4">
              New account created. Temporary password: <strong>{temp}</strong>
            </p>
          )}
        </form>
      )}

      <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs uppercase text-clay">
            <tr>
              <th className="px-3 py-2">Person</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {(workspace?.members || []).map((m) => (
              <tr key={m.id} className="border-b border-line last:border-0">
                <td className="px-3 py-3">
                  <div className="font-medium">{m.display_name || m.email}</div>
                  <div className="text-xs text-clay">{m.email}</div>
                </td>
                <td className="px-3 py-3">
                  <span className={`pm-dot ${m.online ? "is-on" : ""}`} /> {presenceLabel(m)}
                </td>
                <td className="px-3 py-3">
                  {workspaceMeta?.can_create_features ? (
                    <select
                      className="field w-auto"
                      value={m.role}
                      onChange={(e) => patch.mutate({ memberId: m.id, body: { role: e.target.value } })}
                    >
                      <option value="member">member</option>
                      <option value="admin">admin</option>
                      <option value="owner">owner</option>
                    </select>
                  ) : (
                    pmPill(m.role)
                  )}
                </td>
                <td className="px-3 py-3 text-right">
                  {workspaceMeta?.can_create_features && m.user_id !== me?.id && (
                    <button className="text-xs text-clay" onClick={() => remove.mutate(m.id)}>
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PmShell>
  );
}
