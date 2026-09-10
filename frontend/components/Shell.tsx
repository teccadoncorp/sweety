"use client";

import { KillSwitch } from "@/components/KillSwitch";
import { NotificationBell } from "@/components/NotificationBell";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, Brand, clearToken, getToken } from "@/lib/api";
import { useAppName } from "@/lib/branding";
import { useEffect, useState } from "react";

type NavItem = { href: string; label: string; match?: "exact" | "prefix" };

function brandNav(brandId: string): { label: string; items: NavItem[] }[] {
  const base = `/brands/${brandId}`;
  return [
    {
      label: "Console",
      items: [
        { href: `${base}/command`, label: "Command", match: "prefix" },
        { href: `${base}/godmode`, label: "God Mode", match: "prefix" },
      ],
    },
    {
      label: "Work",
      items: [
        { href: `${base}/approvals`, label: "Approvals", match: "prefix" },
        { href: `${base}/calendar`, label: "Calendar", match: "prefix" },
        { href: `${base}/studio`, label: "Studio", match: "prefix" },
      ],
    },
    {
      label: "Brand",
      items: [
        { href: `${base}/crm`, label: "CRM", match: "prefix" },
        { href: base, label: "Org", match: "exact" },
        { href: `${base}/connect`, label: "Connectors", match: "prefix" },
      ],
    },
  ];
}

function itemActive(pathname: string, item: NavItem) {
  if (item.match === "exact") return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function NavLink({
  item,
  pathname,
  onClick,
}: {
  item: NavItem;
  pathname: string;
  onClick?: () => void;
}) {
  const active = itemActive(pathname, item);
  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={`flex items-center rounded-lg px-3 py-2 text-sm ${
        active ? "bg-violet text-white" : "text-ink/80 hover:bg-paper hover:text-ink"
      }`}
    >
      {item.label}
    </Link>
  );
}

export function Shell({
  children,
  brandId,
  full = false,
}: {
  children: React.ReactNode;
  brandId?: string;
  full?: boolean;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const appName = useAppName();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const { data: brand } = useQuery({
    queryKey: ["brand", brandId],
    queryFn: () => api<Brand>(`/brands/${brandId}`),
    enabled: Boolean(brandId),
  });

  const groups = brandId ? brandNav(brandId) : [];
  const topClass = (active: boolean) =>
    active ? "text-violet font-medium" : "text-clay hover:text-ink";

  const sidebar = brandId ? (
    <nav className="flex h-full flex-col">
      <div className="border-b border-line px-4 py-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-clay">Working on</p>
        <p className="mt-1 truncate font-serif text-lg text-ink">{brand?.name || "Brand"}</p>
      </div>
      <div className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="mb-1.5 px-3 text-[11px] font-medium uppercase tracking-[0.16em] text-clay">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavLink key={item.href} item={item} pathname={pathname} onClick={() => setOpen(false)} />
              ))}
            </div>
          </div>
        ))}
      </div>
      {brandId && (
        <div className="space-y-2 border-t border-line p-3">
          <KillSwitch brandId={brandId} />
        </div>
      )}
    </nav>
  ) : null;

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden">
      <header className="z-30 shrink-0 border-b border-line bg-white">
        <div className="h-0.5 w-full bg-violet" />
        <div className="flex items-center gap-3 px-3 py-2.5 sm:px-4">
          {brandId && (
            <button
              type="button"
              className="rounded-lg border border-line px-2.5 py-1.5 text-sm text-ink lg:hidden"
              onClick={() => setOpen((v) => !v)}
              aria-label="Open menu"
            >
              Menu
            </button>
          )}
          <Link href="/brands" className="shrink-0 text-lg font-semibold tracking-tight text-violet">
            {appName}
          </Link>
          <nav className="ml-auto flex min-w-0 items-center gap-x-4 text-sm">
            <Link className={topClass(pathname === "/brands")} href="/brands">
              Brands
            </Link>
            {brandId && <NotificationBell brandId={brandId} />}
            <Link className={topClass(pathname.startsWith("/pm"))} href="/pm">
              Tasks
            </Link>
            <Link className={topClass(pathname === "/settings")} href="/settings">
              Settings
            </Link>
            <button
              className="text-violet"
              onClick={() => {
                clearToken();
                router.push("/login");
              }}
            >
              Sign out
            </button>
          </nav>
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        {brandId && (
          <aside className="hidden w-56 shrink-0 border-r border-line bg-white lg:block">{sidebar}</aside>
        )}
        {brandId && open && (
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
          {full ? (
            children
          ) : (
            <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</div>
          )}
        </main>
      </div>
    </div>
  );
}

export function money(value: string | number) {
  const n = typeof value === "string" ? parseFloat(value) : value;
  return `$${(n || 0).toFixed(2)}`;
}

export function pill(status: string) {
  const tone: Record<string, string> = {
    active: "bg-moss/15 text-moss",
    ready: "bg-moss/15 text-moss",
    done: "bg-moss/15 text-moss",
    approved: "bg-moss/15 text-moss",
    draft: "bg-clay/15 text-clay",
    backlog: "bg-paper text-clay",
    paused: "bg-clay/15 text-clay",
    published: "bg-moss/15 text-moss",
    rejected: "bg-violet/15 text-violet",
    scheduled: "bg-cyan/10 text-cyan",
    awaiting_approval: "bg-violet/10 text-violet",
    review: "bg-violet/10 text-violet",
    pending: "bg-violet/10 text-violet",
    blocked: "bg-violet/15 text-violet",
    checked_out: "bg-cyan/10 text-cyan",
    running: "bg-cyan/10 text-cyan",
    signal: "bg-cyan/10 text-cyan",
    qualify: "bg-violet/10 text-violet",
    propose: "bg-violet/15 text-violet",
    commit: "bg-moss/15 text-moss",
    won: "bg-moss/15 text-moss",
    lost: "bg-paper text-clay",
    ice: "bg-paper text-clay",
    cool: "bg-clay/15 text-clay",
    warm: "bg-violet/10 text-violet",
    hot: "bg-violet/15 text-violet",
    star: "bg-cyan/15 text-cyan",
    lead: "bg-paper text-clay",
    terminated: "bg-paper text-clay",
    missing_key: "bg-violet/15 text-violet",
    not_configured: "bg-paper text-clay",
    stubbed: "bg-paper text-clay",
    disconnected: "bg-paper text-clay",
    connected: "bg-moss/15 text-moss",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs ${tone[status] || "bg-paper text-clay"}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
