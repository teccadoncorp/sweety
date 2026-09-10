"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { Shell, money } from "@/components/Shell";
import { WorkInline, WorkLoader } from "@/components/WorkLoader";
import { api, Brand, publicAsset } from "@/lib/api";

export default function BrandsPage() {
  const qc = useQueryClient();
  const { data: brands = [], isLoading } = useQuery({
    queryKey: ["brands"],
    queryFn: () => api<Brand[]>("/brands"),
  });
  const [name, setName] = useState("");
  const [mission, setMission] = useState("");
  const [voice, setVoice] = useState("");
  const [audience, setAudience] = useState("");
  const [guidelines, setGuidelines] = useState("");
  const [website, setWebsite] = useState("");
  const [appUrl, setAppUrl] = useState("");
  const [logo, setLogo] = useState("");

  const create = useMutation({
    mutationFn: () =>
      api<Brand>("/brands", {
        method: "POST",
        body: JSON.stringify({
          name,
          mission,
          voice_notes: voice,
          audience,
          guidelines,
          website_url: website,
          app_url: appUrl,
          logo_url: logo,
          seed_org: true,
        }),
      }),
    onSuccess: () => {
      setName("");
      setMission("");
      setVoice("");
      setAudience("");
      setGuidelines("");
      setWebsite("");
      setAppUrl("");
      setLogo("");
      qc.invalidateQueries({ queryKey: ["brands"] });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (name.trim()) create.mutate();
  }

  return (
    <Shell>
      <p className="text-sm uppercase tracking-[0.18em] text-cyan">Portfolio</p>
      <h1 className="mt-1 font-serif text-3xl sm:text-4xl lg:text-5xl">Brands</h1>
      {isLoading && <div className="mt-8"><WorkInline label="Loading brands" /></div>}
      <div className="mt-10 grid gap-6 md:grid-cols-2">
        {brands.map((brand) => (
          <Link key={brand.id} href={`/brands/${brand.id}/godmode`} className="card block min-w-0 p-6 hover:bg-paper">
            <div className="flex items-start gap-4">
              {brand.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={publicAsset(brand.logo_url)} alt="" className="h-12 w-12 shrink-0 rounded-xl object-cover" />
              ) : (
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-violet/20 font-serif text-xl">
                  {brand.name.slice(0, 1)}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h2 className="min-w-0 break-words font-serif text-2xl sm:text-3xl">{brand.name}</h2>
                  <span className="shrink-0 text-sm text-clay">
                    {money(brand.spent_usd)} / {money(brand.monthly_budget_usd)}
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-clay">{brand.mission || "No mission yet."}</p>
                <p className="mt-2 text-xs text-cyan">Open God Mode →</p>
              </div>
            </div>
          </Link>
        ))}
        <form onSubmit={onSubmit} className="card space-y-3 p-6">
          <h2 className="font-serif text-2xl">New brand</h2>
          <input className="field" placeholder="Brand name" value={name} onChange={(e) => setName(e.target.value)} />
          <textarea
            className="field min-h-20"
            placeholder="Mission — the CMO will open the first campaign from this"
            value={mission}
            onChange={(e) => setMission(e.target.value)}
          />
          <textarea
            className="field min-h-16"
            placeholder="Voice / tone"
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
          />
          <textarea
            className="field min-h-16"
            placeholder="Audience"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
          />
          <textarea
            className="field min-h-16"
            placeholder="Do's / don'ts"
            value={guidelines}
            onChange={(e) => setGuidelines(e.target.value)}
          />
          <input className="field" placeholder="Website (optional)" value={website} onChange={(e) => setWebsite(e.target.value)} />
          <input className="field" placeholder="App URL (optional)" value={appUrl} onChange={(e) => setAppUrl(e.target.value)} />
          <input className="field" placeholder="Logo URL (optional)" value={logo} onChange={(e) => setLogo(e.target.value)} />
          {create.isPending && <WorkInline label="Seeding marketing org" />}
          <button className="btn-primary" type="submit" disabled={create.isPending}>
            Seed marketing org
          </button>
        </form>
      </div>
      {create.isPending && <WorkLoader label="Standing up the org" />}
    </Shell>
  );
}
