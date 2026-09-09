"use client";

import Lottie from "lottie-react";
import working from "@/lottie/working.json";

export function WorkLoader({
  label = "Working",
  size = 88,
  inline = false,
}: {
  label?: string;
  size?: number;
  inline?: boolean;
}) {
  const body = (
    <div className="flex flex-col items-center justify-center gap-2 text-center">
      <Lottie animationData={working} loop className="block" style={{ width: size, height: size }} />
      <p className="text-xs uppercase tracking-[0.2em] text-cyan">{label}</p>
      <div className="h-1 w-36 overflow-hidden rounded-full bg-white/10">
        <div className="progress-indeterminate h-full rounded-full bg-gradient-to-r from-violet via-cyan to-violet" />
      </div>
    </div>
  );
  if (inline) return body;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-void/70 backdrop-blur-sm">{body}</div>
  );
}

export function WorkInline({ label = "Thinking" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
      <Lottie animationData={working} loop style={{ width: 44, height: 44 }} />
      <div>
        <div className="text-sm text-ink">{label}</div>
        <div className="mt-1 h-1 w-40 overflow-hidden rounded-full bg-white/10">
          <div className="progress-indeterminate h-full rounded-full bg-gradient-to-r from-violet via-cyan to-violet" />
        </div>
      </div>
    </div>
  );
}
