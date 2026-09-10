"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { clearPmToken, getPmToken, getPmWorkspaceId, pmApi, PmMe, PmProject, setPmWorkspaceId } from "@/lib/pm";

type NavItem = { href: string; label: string; match?: "exact" | "prefix" };

function itemActive(pathname: string, item: NavItem) {
  if (item.match === "exact") return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function PmShell({
  children,
  projectId,
  full = false,
}: {
  children: React.ReactNode;
  projectId?: string;
  full?: boolean;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!getPmToken()) router.replace("/pm/login");
  }, [router]);

  useEffect(() => {
    if (!getPmToken()) return;
    const beat = () => pmApi("/auth/heartbeat", { method: "POST" }).catch(() => undefined);
    beat();
    const id = window.setInterval(beat, 45_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const { data: me } = useQuery({
    queryKey: ["pm-me"],
    queryFn: () => pmApi<PmMe>("/auth/me"),
  });

  const workspaceId = getPmWorkspaceId() || me?.workspaces[0]?.id;
  useEffect(() => {
    if (workspaceId) setPmWorkspaceId(workspaceId);
  }, [workspaceId]);

  const workspace = me?.workspaces.find((w) => w.id === workspaceId) || me?.workspaces[0];

  const { data: projects = [] } = useQuery({
    queryKey: ["pm-projects", workspace?.id],
    queryFn: () => pmApi<PmProject[]>(`/workspaces/${workspace!.id}/projects`),
    enabled: Boolean(workspace?.id),
  });

  const groups: { label: string; items: NavItem[] }[] = [
    {
      label: "Console",
      items: [
        { href: "/pm", label: "Projects", match: "exact" },
        { href: "/pm/people", label: "People", match: "prefix" },
        ...(workspace?.can_create_features
          ? [{ href: "/pm/godmode", label: "God Mode", match: "prefix" as const }]
          : []),
      ],
    },
  ];

  if (projectId) {
    const base = `/pm/projects/${projectId}`;
    groups.push({
      label: "Project",
      items: [
        { href: base, label: "Board", match: "exact" },
        { href: `${base}/features`, label: "Epics", match: "prefix" },
        { href: `${base}/report`, label: "Reports", match: "prefix" },
      ],
    });
  }

  const topClass = (active: boolean) => (active ? "text-violet font-medium" : "text-clay hover:text-ink");

  const sidebar = (
    <nav className="flex h-full flex-col">
      <div className="border-b border-line px-4 py-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-clay">Workspace</p>
        <p className="mt-1 truncate font-serif text-lg text-ink">{workspace?.name || "Task console"}</p>
        {me && me.workspaces.length > 1 && (
          <select
            className="field mt-3"
            value={workspace?.id || ""}
            onChange={(e) => {
              setPmWorkspaceId(e.target.value);
              router.push("/pm");
            }}
          >
            {me.workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="mb-1.5 px-3 text-[11px] font-medium uppercase tracking-[0.16em] text-clay">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = itemActive(pathname, item);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={`flex items-center rounded-lg px-3 py-2 text-sm ${
                      active ? "bg-violet text-white" : "text-ink/80 hover:bg-paper hover:text-ink"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
        {projects.length > 0 && (
          <div>
            <p className="mb-1.5 px-3 text-[11px] font-medium uppercase tracking-[0.16em] text-clay">Boards</p>
            <div className="space-y-0.5">
              {projects.map((p) => {
                const href = `/pm/projects/${p.id}`;
                const active = pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <Link
                    key={p.id}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm ${
                      active ? "bg-violet text-white" : "text-ink/80 hover:bg-paper hover:text-ink"
                    }`}
                  >
                    <span className="truncate">{p.name}</span>
                    <span className={active ? "text-white/80" : "text-clay"}>{p.key}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
      <div className="border-t border-line p-3 text-xs text-clay">
        {workspace?.can_create_features ? "God Mode can create features" : "Member — work issues on the board"}
      </div>
    </nav>
  );

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden">
      <header className="z-30 shrink-0 border-b border-line bg-white">
        <div className="h-0.5 w-full bg-violet" />
        <div className="flex items-center gap-3 px-3 py-2.5 sm:px-4">
          <button
            type="button"
            className="rounded-lg border border-line px-2.5 py-1.5 text-sm text-ink lg:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-label="Open menu"
          >
            Menu
          </button>
          <Link href="/pm" className="shrink-0 text-lg font-semibold tracking-tight text-violet">
            Task console
          </Link>
          <nav className="ml-auto flex min-w-0 items-center gap-x-4 text-sm">
            <span className="hidden truncate text-clay sm:inline">{me?.display_name || me?.email}</span>
            <Link className={topClass(false)} href="/login">
              Marketing
            </Link>
            <button
              className="text-violet"
              onClick={() => {
                clearPmToken();
                router.push("/pm/login");
              }}
            >
              Sign out
            </button>
          </nav>
        </div>
      </header>
      <div className="relative flex min-h-0 flex-1">
        <aside className="hidden w-56 shrink-0 border-r border-line bg-white lg:block">{sidebar}</aside>
        {open && (
          <div className="absolute inset-0 z-20 lg:hidden">
            <button
              type="button"
              className="absolute inset-0 bg-ink/20"
              aria-label="Close menu"
              onClick={() => setOpen(false)}
            />
            <aside className="relative z-10 h-full w-64 max-w-[80vw] border-r border-line bg-white shadow-card">
              {sidebar}
            </aside>
          </div>
        )}
        <main
          className={
            full
              ? "relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
              : "min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto"
          }
        >
          {full ? children : <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</div>}
        </main>
      </div>
    </div>
  );
}

export function pmPill(status: string) {
  const tone: Record<string, string> = {
    backlog: "bg-paper text-clay",
    todo: "bg-cyan/10 text-cyan",
    planned: "bg-cyan/10 text-cyan",
    in_progress: "bg-violet/10 text-violet",
    review: "bg-violet/15 text-violet",
    done: "bg-moss/15 text-moss",
    story: "bg-cyan/10 text-cyan",
    epic: "bg-violet/15 text-violet",
    ticket: "bg-cyan/10 text-cyan",
    subticket: "bg-paper text-clay",
    task: "bg-paper text-clay",
    bug: "bg-violet/15 text-violet",
    overdue: "bg-violet/15 text-violet",
    godmode: "bg-violet/10 text-violet",
    pm_godmode: "bg-violet/10 text-violet",
    human: "bg-paper text-clay",
    owner: "bg-moss/15 text-moss",
    admin: "bg-violet/10 text-violet",
    member: "bg-paper text-clay",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs ${tone[status] || "bg-paper text-clay"}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
