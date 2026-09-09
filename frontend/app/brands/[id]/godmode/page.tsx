"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Markdown } from "@/components/Markdown";
import { Shell } from "@/components/Shell";
import { WorkInline } from "@/components/WorkLoader";
import { api, Brand, ChatMessage, publicAsset } from "@/lib/api";

const STARTERS = [
  "Launch a 2-week Spring Edit campaign across email and Instagram.",
  "I need a product-hunt style launch for our iOS app next month.",
  "Research competitors and draft a positioning brief before we spend.",
];

const PLATFORMS = [
  { id: "instagram", label: "Instagram 4:5" },
  { id: "instagram_story", label: "IG story 9:16" },
  { id: "twitter", label: "X 16:9" },
  { id: "linkedin", label: "LinkedIn 1.91:1" },
  { id: "facebook", label: "Facebook 1.91:1" },
  { id: "reddit", label: "Reddit 16:9" },
  { id: "pinterest", label: "Pinterest 2:3" },
  { id: "tiktok", label: "TikTok 9:16" },
];

function imagesOf(m: ChatMessage) {
  const fromField = m.images || [];
  const fromMd = [...m.content.matchAll(/!\[[^\]]*]\((https?:[^)]+)\)/g)].map((x) => x[1]);
  return [...new Set([...fromField, ...fromMd].map((src) => publicAsset(src) || src))];
}

export default function GodModePage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const bottom = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState("");
  const { data: brand } = useQuery({
    queryKey: ["brand", id],
    queryFn: () => api<Brand>(`/brands/${id}`),
  });
  const { data: messages = [], isLoading } = useQuery({
    queryKey: ["godmode", id],
    queryFn: () => api<ChatMessage[]>(`/brands/${id}/godmode/messages`),
  });
  const send = useMutation({
    mutationFn: (content: string) =>
      api<ChatMessage>(`/brands/${id}/godmode/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["godmode", id] }),
  });

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, send.isPending]);

  function submit(text: string) {
    const content = text.trim();
    if (!content || send.isPending) return;
    setDraft("");
    send.mutate(content);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    submit(draft);
  }

  return (
    <Shell brandId={id} full>
      <div className="mx-auto flex min-h-0 w-full min-w-0 max-w-3xl flex-1 flex-col px-3 sm:px-4">
        <div className="shrink-0 border-b border-white/10 py-4">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan">CMO God Mode</p>
          <h1 className="font-serif text-3xl">{brand?.name || "Brief the CMO"}</h1>
          <p className="mt-1 text-sm text-clay">
            Markdown plans, generated images, and platform-sized frames. Pick a network before we render a still.
          </p>
        </div>

        <div className="chat-scroll min-h-0 flex-1 space-y-4 overflow-y-auto py-4 sm:py-6">
          {isLoading && <WorkInline label="Loading conversation" />}
          {!isLoading && messages.length === 0 && (
            <div className="rounded-3xl border border-dashed border-white/15 p-8 text-center">
              <p className="font-serif text-3xl">What should we run?</p>
              <p className="mt-2 text-sm text-clay">
                Website {brand?.website_url || "—"} · App {brand?.app_url || "—"} · Logo{" "}
                {brand?.logo_url ? "set" : "optional"}
              </p>
              <div className="mt-6 space-y-2">
                {STARTERS.map((s) => (
                  <button key={s} className="btn-ghost w-full text-left" onClick={() => submit(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => {
            const imgs = imagesOf(m);
            return (
              <div
                key={m.id}
                className={
                  m.role === "user"
                    ? "ml-2 rounded-2xl bg-violet/20 px-4 py-3 sm:ml-12"
                    : "mr-2 min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 sm:mr-8"
                }
              >
                <div className="mb-1 text-[11px] uppercase tracking-wide text-clay">
                  {m.role === "user" ? "You" : "CMO"}
                </div>
                {m.role === "assistant" ? (
                  <Markdown>{m.content}</Markdown>
                ) : (
                  <div className="whitespace-pre-wrap text-sm leading-6">{m.content}</div>
                )}
                {m.role === "assistant" && imgs.length > 0 && !/!\[[^\]]*]\(https?:/.test(m.content) && (
                  <div className="mt-3 grid gap-3">
                    {imgs.map((src) => (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        key={src}
                        src={src}
                        alt="Generated visual"
                        className="max-h-[28rem] w-full rounded-xl border border-white/10 bg-void object-contain"
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {send.isPending && <WorkInline label="CMO is planning the brief" />}
          <div ref={bottom} />
        </div>

        <form onSubmit={onSubmit} className="shrink-0 border-t border-white/10 py-4">
          <div className="mb-2 flex flex-wrap gap-2">
            {PLATFORMS.map((p) => (
              <button
                key={p.id}
                type="button"
                className="rounded-full border border-white/15 px-3 py-1 text-xs text-cyan hover:bg-white/10"
                onClick={() =>
                  submit(`Generate the image for ${p.label}. Use platform=${p.id} and the correct aspect ratio.`)
                }
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="flex items-end gap-2 rounded-2xl border border-white/15 bg-void/70 p-2">
            <textarea
              className="field min-h-[52px] flex-1 resize-none border-0 bg-transparent"
              placeholder="Describe the campaign — or tap a platform after asking for an image…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(draft);
                }
              }}
            />
            <button className="btn-primary" disabled={send.isPending || !draft.trim()}>
              Send
            </button>
          </div>
        </form>
      </div>
    </Shell>
  );
}
