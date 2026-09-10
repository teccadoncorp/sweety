"use client";

import { useState } from "react";
import { publicAsset } from "@/lib/api";

function fileName(src: string) {
  try {
    const path = new URL(src, window.location.origin).pathname;
    const base = path.split("/").pop();
    if (base && /\.(png|jpe?g|webp|gif|svg)$/i.test(base)) return base;
  } catch {
    /* use fallback */
  }
  return `sweety-visual-${Date.now()}.png`;
}

export async function downloadAsset(src: string) {
  const url = publicAsset(src) || src;
  const proxied = `/download?url=${encodeURIComponent(url)}`;
  const res = await fetch(proxied);
  if (!res.ok) throw new Error("download failed");
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = fileName(url);
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}

export function ChatImage({ src, alt = "" }: { src: string; alt?: string }) {
  const [busy, setBusy] = useState(false);
  const href = publicAsset(src) || src;

  async function onDownload() {
    setBusy(true);
    try {
      await downloadAsset(href);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="group relative my-3 overflow-hidden rounded-xl border border-line bg-paper">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={href} alt={alt} className="max-h-[28rem] w-full object-contain" />
      <button
        type="button"
        onClick={onDownload}
        disabled={busy}
        className="absolute bottom-3 right-3 rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-medium text-ink shadow-sm hover:bg-paper"
      >
        {busy ? "Saving…" : "Download"}
      </button>
    </div>
  );
}
