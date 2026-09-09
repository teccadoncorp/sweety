"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ConnectorsPanel } from "@/components/ConnectorsPanel";
import { Shell, pill } from "@/components/Shell";
import { AdapterHealth, api, Brand, Skill } from "@/lib/api";

function SettingsBody() {
  const params = useSearchParams();
  const connected = params.get("connected");
  const connectorError = params.get("connector_error");
  const brandFromUrl = params.get("brand");

  const { data: status } = useQuery({
    queryKey: ["settings"],
    queryFn: () =>
      api<{
        openrouter_configured: boolean;
        openrouter_key_preview: string;
        default_model: string;
        heygen_configured: boolean;
        models?: { chat?: string; image?: string; search?: string };
      }>("/settings/status"),
  });
  const { data: adapters = [] } = useQuery({
    queryKey: ["adapters"],
    queryFn: () => api<AdapterHealth[]>("/adapters"),
  });
  const { data: skills = [] } = useQuery({
    queryKey: ["skills"],
    queryFn: () => api<Skill[]>("/skills"),
  });
  const { data: brands = [] } = useQuery({
    queryKey: ["brands"],
    queryFn: () => api<Brand[]>("/brands"),
  });
  const [brandId, setBrandId] = useState(brandFromUrl || "");
  const selected = brandId || brands[0]?.id || "";

  return (
    <Shell>
      <p className="text-sm uppercase tracking-[0.18em] text-clay">Board</p>
      <h1 className="mt-1 font-serif text-5xl">Settings</h1>
      {connected && (
        <p className="mt-3 text-sm text-moss">Connected {connected}. Pick a Page if this was Facebook / Instagram.</p>
      )}
      {connectorError && <p className="mt-3 text-sm text-rose">{connectorError}</p>}

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <section className="card p-6">
          <h2 className="font-serif text-2xl">OpenRouter</h2>
          <p className="mt-2 text-sm text-ink/70">
            Keys stay on the server. Restart compose after changing <code>.env</code>.
          </p>
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt>Configured</dt>
              <dd>{status?.openrouter_configured ? "yes" : "no"}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Key</dt>
              <dd>{String(status?.openrouter_key_preview || "—")}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Chat</dt>
              <dd>{String(status?.models?.chat || status?.default_model || "")}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Image</dt>
              <dd>{String(status?.models?.image || "")}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Search</dt>
              <dd>{String(status?.models?.search || "")}</dd>
            </div>
            <div className="flex justify-between">
              <dt>HeyGen env</dt>
              <dd>{status?.heygen_configured ? "yes" : "no"}</dd>
            </div>
          </dl>
        </section>
        <section className="card p-6">
          <h2 className="font-serif text-2xl">Adapters</h2>
          <ul className="mt-4 space-y-3">
            {adapters.map((a) => (
              <li key={a.name} className="flex items-start justify-between gap-3 text-sm">
                <div>
                  <div className="font-medium">{a.name}</div>
                  <div className="text-ink/60">{a.detail}</div>
                </div>
                {pill(a.status)}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="mt-10">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="text-sm">
            Brand for connectors
            <select
              className="field mt-1"
              value={selected}
              onChange={(e) => setBrandId(e.target.value)}
            >
              {brands.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="mb-4 text-sm text-clay">
          Prefer the brand <strong>Connectors</strong> tab in the top nav — social login lives there.
        </p>
        {selected ? <ConnectorsPanel brandId={selected} /> : <p className="text-sm text-clay">Create a brand first.</p>}
      </div>

      <section className="card mt-10 p-6">
        <h2 className="font-serif text-2xl">Skills</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {skills.map((s) => (
            <div key={s.slug} className="rounded-xl border border-ink/10 p-4">
              <div className="font-medium">{s.name}</div>
              <div className="text-xs text-ink/50">
                {s.slug} · v{s.version}
              </div>
              <p className="mt-2 text-sm text-ink/70">{s.description}</p>
            </div>
          ))}
        </div>
      </section>
    </Shell>
  );
}

export default function SettingsPage() {
  return (
    <Suspense>
      <SettingsBody />
    </Suspense>
  );
}
