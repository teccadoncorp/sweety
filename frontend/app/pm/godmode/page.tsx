"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Markdown } from "@/components/Markdown";
import { PmShell } from "@/components/pm/PmShell";
import { WorkInline } from "@/components/WorkLoader";
import { getPmWorkspaceId, pmApi, PmChatMessage, PmMe } from "@/lib/pm";

const STARTERS = [
  "Create a checkout feature with stories for cart, payment, and receipts.",
  "Add a feature for team invites and roles.",
  "Break out a mobile offline-sync epic with three stories.",
];

export default function PmGodModePage() {
  const qc = useQueryClient();
  const scroller = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState("");
  const { data: me } = useQuery({
    queryKey: ["pm-me"],
    queryFn: () => pmApi<PmMe>("/auth/me"),
  });
  const workspace = me?.workspaces.find((w) => w.id === getPmWorkspaceId()) || me?.workspaces[0];
  const workspaceId = workspace?.id;

  const { data: messages = [], isLoading } = useQuery({
    queryKey: ["pm-godmode", workspaceId],
    queryFn: () => pmApi<PmChatMessage[]>(`/workspaces/${workspaceId}/godmode/messages`),
    enabled: Boolean(workspaceId && workspace?.can_create_features),
  });

  const send = useMutation({
    mutationFn: (content: string) =>
      pmApi<PmChatMessage>(`/workspaces/${workspaceId}/godmode/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pm-godmode", workspaceId] });
      qc.invalidateQueries({ queryKey: ["pm-projects"] });
    },
  });

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
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

  if (me && workspace && !workspace.can_create_features) {
    return (
      <PmShell>
        <p className="font-serif text-3xl">God Mode is for admins</p>
        <p className="mt-2 text-clay">Ask a workspace owner to create features, or work issues on the board.</p>
      </PmShell>
    );
  }

  return (
    <PmShell full>
      <div className="mx-auto flex h-full min-h-0 w-full min-w-0 max-w-3xl flex-1 flex-col px-3 sm:px-4">
        <div className="shrink-0 border-b border-line bg-white py-3">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan">Task God Mode</p>
          <h1 className="font-serif text-2xl sm:text-3xl">{workspace?.name || "Create features"}</h1>
          <p className="mt-1 hidden text-sm text-clay sm:block">
            Describe a capability. God Mode writes the feature and optional stories onto the board.
          </p>
        </div>

        <div ref={scroller} className="chat-scroll min-h-0 flex-1 space-y-4 overflow-y-auto py-4 sm:py-6">
          {isLoading && <WorkInline label="Loading conversation" />}
          {!isLoading && messages.length === 0 && (
            <div className="rounded-xl border border-dashed border-line bg-white p-8 text-center">
              <p className="font-serif text-3xl">What should we build?</p>
              <p className="mt-2 text-sm text-clay">Features only. Members pick up the issues after.</p>
              <div className="mt-6 space-y-2">
                {STARTERS.map((s) => (
                  <button key={s} className="btn-ghost w-full text-left" onClick={() => submit(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={
                m.role === "user"
                  ? "ml-2 rounded-xl bg-violet/10 px-4 py-3 sm:ml-12"
                  : "mr-2 min-w-0 rounded-xl border border-line bg-white px-4 py-3 sm:mr-8"
              }
            >
              <div className="mb-1 text-[11px] uppercase tracking-wide text-clay">
                {m.role === "user" ? "You" : "God Mode"}
              </div>
              {m.role === "assistant" ? (
                <Markdown>{m.content}</Markdown>
              ) : (
                <div className="whitespace-pre-wrap text-sm leading-6">{m.content}</div>
              )}
            </div>
          ))}
          {send.isPending && <WorkInline label="Creating features" />}
        </div>

        <form
          onSubmit={onSubmit}
          className="sticky bottom-0 z-10 shrink-0 border-t border-line bg-white pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3"
        >
          <div className="flex items-end gap-2 rounded-xl border border-line bg-paper p-2">
            <textarea
              className="field min-h-[52px] flex-1 resize-none border-0 bg-transparent"
              placeholder="Describe the feature…"
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
    </PmShell>
  );
}
