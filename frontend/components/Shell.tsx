"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken, getToken } from "@/lib/api";
import { useEffect } from "react";

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

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  const navClass = (active: boolean) => (active ? "text-cyan" : "text-clay hover:text-ink");

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden">
      <header className="z-20 shrink-0 border-b border-white/10 bg-void/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl items-start justify-between gap-3 px-4 py-3 sm:items-center sm:px-6">
          <Link href="/brands" className="shrink-0 pt-0.5 font-serif text-xl tracking-tight text-ink sm:text-2xl">
            Sweety
          </Link>
          <nav className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-x-3 gap-y-1.5 text-xs sm:gap-x-4 sm:text-sm">
            <Link className={navClass(pathname === "/brands")} href="/brands">
              Brands
            </Link>
            {brandId && (
              <>
                <Link className={navClass(pathname.endsWith("/godmode"))} href={`/brands/${brandId}/godmode`}>
                  God Mode
                </Link>
                <Link className={navClass(pathname.includes("/command"))} href={`/brands/${brandId}/command`}>
                  Command
                </Link>
                <Link className={navClass(pathname.includes("/crm"))} href={`/brands/${brandId}/crm`}>
                  CRM
                </Link>
                <Link className={navClass(pathname === `/brands/${brandId}`)} href={`/brands/${brandId}`}>
                  Org
                </Link>
                <Link className={navClass(pathname.includes("/studio"))} href={`/brands/${brandId}/studio`}>
                  Studio
                </Link>
                <Link
                  className={navClass(pathname.includes("/connect"))}
                  href={`/brands/${brandId}/connect`}
                >
                  Connectors
                </Link>
              </>
            )}
            <Link className={navClass(pathname === "/settings")} href="/settings">
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
      <main
        className={
          full
            ? "flex min-h-0 flex-1 flex-col overflow-hidden"
            : "mx-auto w-full min-w-0 max-w-6xl flex-1 overflow-x-hidden overflow-y-auto px-4 py-6 sm:px-6 sm:py-8"
        }
      >
        {children}
      </main>
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
    backlog: "bg-white/10 text-clay",
    paused: "bg-clay/15 text-clay",
    awaiting_approval: "bg-violet/15 text-violet",
    review: "bg-violet/15 text-violet",
    pending: "bg-violet/15 text-violet",
    blocked: "bg-violet/20 text-violet",
    checked_out: "bg-cyan/10 text-cyan",
    running: "bg-cyan/15 text-cyan",
    signal: "bg-cyan/15 text-cyan",
    qualify: "bg-violet/15 text-violet",
    propose: "bg-violet/20 text-violet",
    commit: "bg-moss/15 text-moss",
    won: "bg-moss/20 text-moss",
    lost: "bg-white/10 text-clay",
    hot: "bg-violet/25 text-violet",
    star: "bg-cyan/20 text-cyan",
    lead: "bg-white/10 text-clay",
    terminated: "bg-white/10 text-clay",
    missing_key: "bg-violet/20 text-violet",
    not_configured: "bg-white/10 text-clay",
    stubbed: "bg-white/10 text-clay",
    disconnected: "bg-white/10 text-clay",
    connected: "bg-moss/15 text-moss",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs ${tone[status] || "bg-white/10 text-clay"}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
