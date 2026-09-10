"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Shell, pill } from "@/components/Shell";
import { WorkInline } from "@/components/WorkLoader";
import { api, Approval } from "@/lib/api";

function draftText(a: Approval) {
  return a.payload?.text || a.payload?.summary || "";
}

export default function ApprovalsPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const { data = [], isLoading } = useQuery({
    queryKey: ["approvals", id],
    queryFn: () => api<Approval[]>(`/brands/${id}/approvals`),
    refetchInterval: 8000,
  });

  const rows = useMemo(
    () => (filter === "pending" ? data.filter((a) => a.status === "pending") : data),
    [data, filter],
  );

  const decide = useMutation({
    mutationFn: ({ approvalId, status, text }: { approvalId: string; status: string; text?: string }) =>
      api(`/brands/${id}/approvals/${approvalId}/decide`, {
        method: "POST",
        body: JSON.stringify({ status, text }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals", id] });
      qc.invalidateQueries({ queryKey: ["calendar", id] });
      qc.invalidateQueries({ queryKey: ["command", id] });
      qc.invalidateQueries({ queryKey: ["notifications", id] });
      qc.invalidateQueries({ queryKey: ["campaigns", id] });
    },
  });

  return (
    <Shell brandId={id}>
      <p className="text-xs uppercase tracking-[0.28em] text-cyan">Consent gate</p>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl sm:text-4xl">Approvals</h1>
          <p className="mt-2 max-w-xl text-sm text-ink/70">
            Nothing publishes until you approve it. Edit the draft, then approve or reject.
          </p>
        </div>
        <div className="flex gap-2">
          {(["pending", "all"] as const).map((key) => (
            <button
              key={key}
              className={filter === key ? "btn-primary" : "btn-ghost"}
              onClick={() => setFilter(key)}
              type="button"
            >
              {key === "pending" ? `Queue (${data.filter((a) => a.status === "pending").length})` : "All"}
            </button>
          ))}
        </div>
      </div>
      {isLoading && (
        <div className="mt-8">
          <WorkInline label="Loading queue" />
        </div>
      )}
      <div className="mt-8 space-y-4">
        {rows.length === 0 && (
          <div className="card p-5 text-sm text-ink/70">
            {filter === "pending" ? "Nothing waiting on the board." : "No approval history yet."} Connect LinkedIn or
            Instagram under{" "}
            <Link href={`/brands/${id}/connect`} className="text-cyan">
              Connectors
            </Link>{" "}
            so an approved post can actually go live.
          </div>
        )}
        {rows.map((a) => {
          const text = edits[a.id] ?? draftText(a);
          const result = a.payload?.publish_result;
          return (
            <article key={a.id} className="card p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="text-sm font-medium capitalize">{a.kind.replaceAll("_", " ")}</span>
                  {a.payload?.platform && (
                    <span className="ml-2 text-xs uppercase tracking-wide text-clay">{a.payload.platform}</span>
                  )}
                </div>
                {pill(a.status)}
              </div>
              {a.payload?.title && <h2 className="mt-2 font-serif text-xl">{a.payload.title}</h2>}
              {a.status === "pending" ? (
                <textarea
                  className="field mt-3 min-h-32"
                  value={text}
                  onChange={(e) => setEdits((m) => ({ ...m, [a.id]: e.target.value }))}
                />
              ) : (
                <p className="mt-3 whitespace-pre-wrap text-sm text-ink/80">{text || "—"}</p>
              )}
              {result && (
                <p className={`mt-2 text-sm ${result.ok ? "text-moss" : "text-violet"}`}>
                  {result.ok ? "Published." : result.error || "Publish failed."}
                </p>
              )}
              <p className="mt-2 text-xs text-clay">{new Date(a.created_at).toLocaleString()}</p>
              {a.status === "pending" && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    className="btn-primary"
                    disabled={decide.isPending}
                    onClick={() => decide.mutate({ approvalId: a.id, status: "approved", text })}
                    type="button"
                  >
                    Approve{a.payload?.platform ? ` & publish to ${a.payload.platform}` : ""}
                  </button>
                  <button
                    className="btn-ghost"
                    disabled={decide.isPending}
                    onClick={() => decide.mutate({ approvalId: a.id, status: "rejected", text })}
                    type="button"
                  >
                    Reject
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </Shell>
  );
}
