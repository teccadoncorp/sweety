"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { pill } from "@/components/Shell";
import { api } from "@/lib/api";
import { useAppName } from "@/lib/branding";

type Provider = {
  id: string;
  label: string;
  auth: string;
  description: string;
  connect_hint: string;
  scopes: string[];
  manual_fields: string[];
  oauth_ready: boolean;
  env_ready: boolean;
  callback_url: string | null;
};

type Connector = {
  id: string;
  provider: string;
  status: string;
  display_name: string;
  extra: Record<string, string>;
  connected: boolean;
  error: string;
};

export function ConnectorsPanel({ brandId }: { brandId: string }) {
  const appName = useAppName();
  const qc = useQueryClient();
  const { data: catalog } = useQuery({
    queryKey: ["catalog"],
    queryFn: () => api<{ providers: Provider[]; models: Record<string, string> }>("/connector-catalog"),
  });
  const { data: connected } = useQuery({
    queryKey: ["connectors", brandId],
    queryFn: () => api<{ connectors: Record<string, Connector> }>(`/brands/${brandId}/connectors`),
  });
  const { data: mcp = [] } = useQuery({
    queryKey: ["mcp", brandId],
    queryFn: () =>
      api<{ id: string; name: string; transport: string; url: string; command: string }[]>(`/brands/${brandId}/mcp`),
  });

  const [manual, setManual] = useState<Record<string, Record<string, string>>>({});
  const [mcpForm, setMcpForm] = useState({ name: "", transport: "http", url: "", command: "" });

  const oauth = useMutation({
    mutationFn: (provider: string) =>
      api<{ authorize_url: string }>(`/brands/${brandId}/connectors/${provider}/authorize`),
    onSuccess: (data) => {
      window.location.href = data.authorize_url;
    },
  });

  const saveManual = useMutation({
    mutationFn: ({ provider, body }: { provider: string; body: Record<string, string> }) =>
      api(`/brands/${brandId}/connectors/${provider}/manual`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors", brandId] }),
  });

  const drop = useMutation({
    mutationFn: (provider: string) =>
      api(`/brands/${brandId}/connectors/${provider}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors", brandId] }),
  });

  const addMcp = useMutation({
    mutationFn: () =>
      api(`/brands/${brandId}/mcp`, {
        method: "POST",
        body: JSON.stringify(mcpForm),
      }),
    onSuccess: () => {
      setMcpForm({ name: "", transport: "http", url: "", command: "" });
      qc.invalidateQueries({ queryKey: ["mcp", brandId] });
    },
  });

  const removeMcp = useMutation({
    mutationFn: (id: string) => api(`/brands/${brandId}/mcp/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mcp", brandId] }),
  });

  return (
    <div className="space-y-8">
      <section className="card p-6">
        <h2 className="font-serif text-2xl">Model map</h2>
        <p className="mt-2 text-sm text-ink/60">
          Chat, search, and images go through OpenRouter. Video is HeyGen. Change models in{" "}
          <code>.env</code> (<code>SWEETY_CHAT_MODEL</code>, <code>SWEETY_IMAGE_MODEL</code>,{" "}
          <code>SWEETY_SEARCH_MODEL</code>).
        </p>
        <dl className="mt-4 grid gap-2 text-sm md:grid-cols-2">
          {Object.entries(catalog?.models || {}).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 rounded-xl bg-paper px-3 py-2">
              <dt className="capitalize">{k}</dt>
              <dd className="text-ink/70">{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section>
        <h2 className="font-serif text-3xl">Social & media</h2>
        <p className="mt-2 max-w-2xl text-sm text-ink/65">
          Login with the network when the developer app is configured. Otherwise paste a token from that
          platform&apos;s developer console. Instagram rides on Facebook Login and needs a public image URL
          to publish.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {(catalog?.providers || []).map((p) => {
            const row = connected?.connectors?.[p.id];
            const fields = manual[p.id] || {};
            return (
              <article key={p.id} className="card p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-serif text-2xl">{p.label}</h3>
                    <p className="mt-1 text-sm text-ink/65">{p.description}</p>
                  </div>
                  {pill(row?.status || (p.env_ready ? "ready" : "disconnected"))}
                </div>
                <p className="mt-2 text-xs text-ink/50">{p.connect_hint}</p>
                {row?.display_name && (
                  <p className="mt-2 text-sm">Connected as {row.display_name}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  {p.auth === "oauth" && (
                    <button
                      className="btn-primary"
                      disabled={!p.oauth_ready || oauth.isPending}
                      onClick={() => oauth.mutate(p.id)}
                    >
                      {p.oauth_ready ? "Login with " + p.label : "Add app keys in .env"}
                    </button>
                  )}
                  {row?.connected && (
                    <button className="btn-ghost" onClick={() => drop.mutate(p.id)}>
                      Disconnect
                    </button>
                  )}
                </div>
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs text-ink/50">
                    Paste token / API key instead
                  </summary>
                  <div className="mt-2 space-y-2">
                    {p.manual_fields.map((field) => (
                      <input
                        key={field}
                        className="field"
                        placeholder={field}
                        type={field.includes("token") || field.includes("key") ? "password" : "text"}
                        value={fields[field] || ""}
                        onChange={(e) =>
                          setManual((prev) => ({
                            ...prev,
                            [p.id]: { ...prev[p.id], [field]: e.target.value },
                          }))
                        }
                      />
                    ))}
                    <button
                      className="btn-ghost"
                      onClick={() => saveManual.mutate({ provider: p.id, body: fields })}
                    >
                      Save credentials
                    </button>
                  </div>
                </details>
              </article>
            );
          })}
        </div>
      </section>

      <section className="card p-6">
        <h2 className="font-serif text-2xl">MCP servers</h2>
        <p className="mt-2 text-sm text-ink/65">
          Point {appName} at an MCP server (HTTP/SSE URL or a stdio command). Agents can list and call its
          tools on heartbeat.
        </p>
        <div className="mt-4 space-y-2">
          {mcp.map((s) => (
            <div key={s.id} className="flex items-center justify-between rounded-xl bg-paper px-3 py-2 text-sm">
              <div>
                <div className="font-medium">{s.name}</div>
                <div className="text-ink/50">
                  {s.transport} · {s.url || s.command}
                </div>
              </div>
              <button className="text-rose" onClick={() => removeMcp.mutate(s.id)}>
                Remove
              </button>
            </div>
          ))}
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          <input
            className="field"
            placeholder="Name"
            value={mcpForm.name}
            onChange={(e) => setMcpForm({ ...mcpForm, name: e.target.value })}
          />
          <select
            className="field"
            value={mcpForm.transport}
            onChange={(e) => setMcpForm({ ...mcpForm, transport: e.target.value })}
          >
            <option value="http">HTTP JSON-RPC</option>
            <option value="sse">SSE</option>
            <option value="stdio">stdio command</option>
          </select>
          <input
            className="field md:col-span-2"
            placeholder={mcpForm.transport === "stdio" ? "Command e.g. npx" : "https://mcp.example.com/mcp"}
            value={mcpForm.transport === "stdio" ? mcpForm.command : mcpForm.url}
            onChange={(e) =>
              mcpForm.transport === "stdio"
                ? setMcpForm({ ...mcpForm, command: e.target.value })
                : setMcpForm({ ...mcpForm, url: e.target.value })
            }
          />
        </div>
        <button className="btn-primary mt-3" onClick={() => addMcp.mutate()} disabled={!mcpForm.name}>
          Add MCP connection
        </button>
      </section>
    </div>
  );
}
