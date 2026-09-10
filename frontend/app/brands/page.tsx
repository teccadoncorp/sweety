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
  const visible = brands.filter((brand) => brand.name !== "Sweety Demo");
  const [open, setOpen] = useState(false);
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
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["brands"] });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (name.trim()) create.mutate();
  }

  function closeForm() {
    if (!create.isPending) setOpen(false);
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.18em] text-cyan">Portfolio</p>
          <h1 className="mt-1 font-serif text-3xl sm:text-4xl lg:text-5xl">Brands</h1>
        </div>
        <button className="btn-primary" type="button" onClick={() => setOpen(true)}>
          New brand
        </button>
      </div>
      {isLoading && (
        <div className="mt-8">
          <WorkInline label="Loading brands" />
        </div>
      )}
      {!isLoading && visible.length === 0 && (
        <div className="card mt-10 p-10 text-center">
          <p className="font-serif text-2xl">No brands yet</p>
          <p className="mt-2 text-sm text-clay">Create one with a mission. The CMO will open the first campaign from it.</p>
          <button className="btn-primary mt-6" type="button" onClick={() => setOpen(true)}>
            New brand
          </button>
        </div>
      )}
      {visible.length > 0 && (
      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        {visible.map((brand) => (
          <Link
            key={brand.id}
            href={`/brands/${brand.id}/command`}
            className="card block min-h-[220px] min-w-0 p-8 hover:bg-paper"
          >
            <div className="flex items-start gap-5">
              {brand.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={publicAsset(brand.logo_url)} alt="" className="h-16 w-16 shrink-0 rounded-2xl object-cover" />
              ) : (
                <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-violet/15 font-serif text-3xl text-violet">
                  {brand.name.slice(0, 1)}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h2 className="min-w-0 break-words font-serif text-3xl sm:text-4xl">{brand.name}</h2>
                  <span className="shrink-0 text-sm text-clay">
                    {money(brand.spent_usd)} / {money(brand.monthly_budget_usd)}
                  </span>
                </div>
                <p className="mt-3 line-clamp-4 text-base leading-6 text-clay">
                  {brand.mission || "No mission yet."}
                </p>
                <p className="mt-5 text-sm text-violet">
                  {brand.campaigns_count
                    ? `${brand.campaigns_count} campaign${brand.campaigns_count === 1 ? "" : "s"}${
                        brand.launch_campaign ? ` · ${brand.launch_campaign}` : ""
                      }`
                    : "Campaign will open from the mission"}
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>
      )}

      {open && (
        <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-ink/30 p-4 sm:p-8" onClick={closeForm}>
          <form onSubmit={onSubmit} onClick={(e) => e.stopPropagation()} className="card relative mt-8 w-full max-w-xl space-y-3 p-6 sm:p-8">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-serif text-3xl">New brand</h2>
                <p className="mt-1 text-sm text-clay">
                  The mission is required for the CMO to generate the first campaign.
                </p>
              </div>
              <button type="button" className="btn-ghost px-3 py-1 text-sm" onClick={closeForm}>
                Close
              </button>
            </div>
            <input className="field" placeholder="Brand name" value={name} onChange={(e) => setName(e.target.value)} />
            <textarea
              className="field min-h-24"
              placeholder="Mission — the CMO opens the first campaign from this"
              value={mission}
              onChange={(e) => setMission(e.target.value)}
              required
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
            <div className="flex gap-2 pt-2">
              <button className="btn-primary" type="submit" disabled={create.isPending || !name.trim() || !mission.trim()}>
                Create brand
              </button>
              <button className="btn-ghost" type="button" onClick={closeForm} disabled={create.isPending}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
      {create.isPending && <WorkLoader label="Standing up the org" />}
    </Shell>
  );
}
