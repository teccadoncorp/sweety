"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Shell, pill } from "@/components/Shell";
import { WorkInline } from "@/components/WorkLoader";
import { api, CalendarSnapshot, ContentItem } from "@/lib/api";

function itemDate(item: ContentItem) {
  return item.scheduled_for || item.published_at || item.created_at;
}

function dayKey(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export default function CalendarPage() {
  const { id } = useParams<{ id: string }>();
  const [cursor, setCursor] = useState(() => startOfDay(new Date()));
  const { data, isLoading } = useQuery({
    queryKey: ["calendar", id],
    queryFn: () => api<CalendarSnapshot>(`/brands/${id}/calendar`),
    refetchInterval: 10000,
  });
  const items = data?.items || [];
  const counts = data?.counts || {};

  const days = useMemo(() => {
    const start = new Date(cursor);
    start.setDate(start.getDate() - start.getDay());
    return Array.from({ length: 28 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [cursor]);

  const byDay = useMemo(() => {
    const map: Record<string, ContentItem[]> = {};
    for (const item of items) {
      const key = dayKey(itemDate(item));
      (map[key] ||= []).push(item);
    }
    return map;
  }, [items]);

  function shift(weeks: number) {
    const next = new Date(cursor);
    next.setDate(next.getDate() + weeks * 7);
    setCursor(next);
  }

  return (
    <Shell brandId={id}>
      <p className="text-xs uppercase tracking-[0.28em] text-cyan">Timeline</p>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
        <h1 className="font-serif text-3xl sm:text-4xl">Content calendar</h1>
        <div className="flex gap-2">
          <button className="btn-ghost" type="button" onClick={() => shift(-4)}>
            Prev
          </button>
          <button className="btn-ghost" type="button" onClick={() => setCursor(startOfDay(new Date()))}>
            Today
          </button>
          <button className="btn-ghost" type="button" onClick={() => shift(4)}>
            Next
          </button>
        </div>
      </div>

      <section className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          ["Created", counts.created ?? items.length],
          ["Awaiting", counts.awaiting_approval ?? 0],
          ["Scheduled", counts.scheduled ?? 0],
          ["Published", counts.published ?? 0],
          ["Rejected", counts.rejected ?? 0],
        ].map(([label, value]) => (
          <div key={String(label)} className="card p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-clay">{label}</div>
            <div className="mt-1 font-serif text-2xl text-cyan">{value}</div>
          </div>
        ))}
      </section>

      {isLoading && (
        <div className="mt-8">
          <WorkInline label="Loading calendar" />
        </div>
      )}

      <div className="mt-8 grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-line bg-line">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d} className="bg-paper px-2 py-1 text-[11px] uppercase tracking-wide text-clay">
            {d}
          </div>
        ))}
        {days.map((d) => {
          const key = dayKey(d.toISOString());
          const localKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
          const cell = byDay[localKey] || byDay[key] || [];
          const todayLocal = localKey === `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}-${String(new Date().getDate()).padStart(2, "0")}`;
          return (
            <div key={localKey} className={`min-h-28 bg-white p-2 ${todayLocal ? "ring-1 ring-inset ring-violet/40" : ""}`}>
              <div className="text-xs text-clay">{d.getDate()}</div>
              <div className="mt-1 space-y-1">
                {cell.slice(0, 3).map((item) => (
                  <Link
                    key={item.id}
                    href={`/brands/${id}/approvals`}
                    className="block truncate rounded bg-paper px-1.5 py-0.5 text-[11px] text-ink hover:bg-violet/10"
                    title={`${item.status} ${item.title || item.kind}`}
                  >
                    {item.status === "published" ? "●" : item.status === "scheduled" ? "○" : "·"} {item.channel}
                  </Link>
                ))}
                {cell.length > 3 && <div className="text-[10px] text-clay">+{cell.length - 3} more</div>}
              </div>
            </div>
          );
        })}
      </div>

      <section className="mt-10">
        <h2 className="font-serif text-2xl">Activity log</h2>
        <div className="mt-4 space-y-3">
          {items.length === 0 && <p className="text-sm text-ink/50">No drafts yet. Wake the CMO from a brand with a mission.</p>}
          {items.map((item) => (
            <article key={item.id} className="card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-medium">{item.title || item.kind}</div>
                  <div className="text-xs uppercase tracking-wide text-clay">
                    {item.channel} · {item.kind}
                  </div>
                </div>
                {pill(item.status)}
              </div>
              <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-ink/70">{item.body}</p>
              <p className="mt-2 text-xs text-clay">
                {item.published_at
                  ? `Published ${new Date(item.published_at).toLocaleString()}`
                  : item.scheduled_for
                    ? `Scheduled ${new Date(item.scheduled_for).toLocaleString()}`
                    : `Created ${new Date(item.created_at).toLocaleString()}`}
              </p>
            </article>
          ))}
        </div>
      </section>
    </Shell>
  );
}
