"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ConnectorsPanel } from "@/components/ConnectorsPanel";
import { Shell } from "@/components/Shell";
import { WorkInline } from "@/components/WorkLoader";
import { api, Brand } from "@/lib/api";

export default function ConnectPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { data: brand, isLoading } = useQuery({
    queryKey: ["brand", id],
    queryFn: () => api<Brand>(`/brands/${id}`),
  });
  const [website, setWebsite] = useState("");
  const [appUrl, setAppUrl] = useState("");
  const [logoUrl, setLogoUrl] = useState("");

  const save = useMutation({
    mutationFn: () =>
      api(`/brands/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          website_url: website || brand?.website_url,
          app_url: appUrl || brand?.app_url,
          logo_url: logoUrl || brand?.logo_url,
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brand", id] }),
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const token = localStorage.getItem("sweety_token");
      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API}/api/v1/brands/${id}/godmode/logo`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brand", id] }),
  });

  return (
    <Shell brandId={id}>
      <p className="text-sm uppercase tracking-[0.18em] text-cyan">Connections</p>
      <h1 className="mt-1 font-serif text-3xl sm:text-4xl lg:text-5xl">Social & brand profile</h1>
      <p className="mt-3 max-w-2xl text-clay">
        This is the connector desk. Login with Reddit, X, LinkedIn, Facebook, or Instagram when the
        developer app is in <code>.env</code>. Otherwise paste a token. HeyGen and MCP live here too.
      </p>
      {isLoading && <div className="mt-6"><WorkInline label="Loading connectors" /></div>}

      <section className="card mt-8 space-y-3 p-6">
        <h2 className="font-serif text-2xl">Optional brand assets</h2>
        {brand?.logo_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={brand.logo_url} alt="" className="h-16 w-16 rounded-xl object-cover" />
        )}
        <input
          className="field"
          placeholder={brand?.website_url || "Website URL"}
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
        />
        <input
          className="field"
          placeholder={brand?.app_url || "App URL"}
          value={appUrl}
          onChange={(e) => setAppUrl(e.target.value)}
        />
        <input
          className="field"
          placeholder={brand?.logo_url || "Logo URL"}
          value={logoUrl}
          onChange={(e) => setLogoUrl(e.target.value)}
        />
        <label className="text-sm text-clay">
          Or upload a logo
          <input
            className="mt-2 block text-sm"
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
            }}
          />
        </label>
        {(save.isPending || upload.isPending) && <WorkInline label="Saving brand profile" />}
        <button className="btn-primary" onClick={() => save.mutate()}>
          Save profile
        </button>
      </section>

      <div className="mt-10">
        <ConnectorsPanel brandId={id} />
      </div>
    </Shell>
  );
}
