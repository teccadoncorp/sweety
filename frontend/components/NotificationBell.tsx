"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, BrandNotification } from "@/lib/api";

export function NotificationBell({ brandId }: { brandId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const { data = [] } = useQuery({
    queryKey: ["notifications", brandId],
    queryFn: () => api<BrandNotification[]>(`/brands/${brandId}/notifications`),
    refetchInterval: 12000,
    refetchIntervalInBackground: false,
  });
  const unread = data.filter((n) => !n.read_at);

  const markAll = useMutation({
    mutationFn: () => api(`/brands/${brandId}/notifications/read-all`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", brandId] }),
  });
  const markOne = useMutation({
    mutationFn: (id: string) => api(`/brands/${brandId}/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", brandId] }),
  });

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={root}>
      <button
        type="button"
        className="relative text-clay hover:text-ink"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
      >
        Alerts
        {unread.length > 0 && (
          <span className="absolute -right-2 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-violet px-1 text-[10px] text-white">
            {unread.length}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-line bg-white p-3 shadow-card">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-clay">Needs you</p>
            {unread.length > 0 && (
              <button className="text-xs text-violet" onClick={() => markAll.mutate()} type="button">
                Mark all read
              </button>
            )}
          </div>
          {data.length === 0 && <p className="text-sm text-ink/50">No alerts yet.</p>}
          <ul className="max-h-80 space-y-2 overflow-y-auto">
            {data.slice(0, 12).map((n) => (
              <li key={n.id} className={`rounded-lg p-2 ${n.read_at ? "bg-white" : "bg-paper"}`}>
                <Link
                  href={n.href || `/brands/${brandId}/approvals`}
                  className="block text-sm font-medium text-ink"
                  onClick={() => {
                    if (!n.read_at) markOne.mutate(n.id);
                    setOpen(false);
                  }}
                >
                  {n.title}
                </Link>
                {n.body && <p className="mt-1 line-clamp-2 text-xs text-clay">{n.body}</p>}
                <p className="mt-1 text-[10px] text-clay">{new Date(n.created_at).toLocaleString()}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
