import type { ReactNode } from "react";

export type ProductView = "godmode" | "approvals" | "tasks";

function Dots() {
  return (
    <span className="lp-win-dots" aria-hidden>
      <i />
      <i />
      <i />
    </span>
  );
}

function Window({
  url,
  children,
}: {
  url: string;
  children: ReactNode;
}) {
  return (
    <div className="lp-win">
      <div className="lp-win-bar">
        <Dots />
        <span className="lp-win-url">{url}</span>
      </div>
      {children}
    </div>
  );
}

function SideLink({
  label,
  active,
  badge,
}: {
  label: string;
  active?: boolean;
  badge?: string;
}) {
  return (
    <span className={`lp-side-link ${active ? "is-on" : ""}`}>
      {label}
      {badge ? <em>{badge}</em> : null}
    </span>
  );
}

function GodModeMock() {
  return (
    <div className="lp-app">
      <aside className="lp-side">
        <p className="lp-side-brand">Northwind</p>
        <p className="lp-side-label">Console</p>
        <SideLink label="Command" />
        <SideLink label="God Mode" active />
        <p className="lp-side-label">Work</p>
        <SideLink label="Approvals" badge="1" />
        <SideLink label="Calendar" />
        <SideLink label="Studio" />
        <p className="lp-side-label">Brand</p>
        <SideLink label="CRM" />
        <SideLink label="Connectors" />
        <div className="lp-side-kill">
          <span>Kill switch</span>
          <b>Off</b>
        </div>
      </aside>
      <div className="lp-chat">
        <header className="lp-chat-head">
          <div>
            <p>God Mode</p>
            <strong>Northwind</strong>
          </div>
          <span className="lp-live">Consent on</span>
        </header>
        <div className="lp-chat-body">
          <article className="lp-msg is-you">
            <span>You</span>
            <p>
              Two-week Spring Edit. LinkedIn first, then Instagram. Audience is 28–40, city retail. Do not publish
              anything.
            </p>
          </article>
          <article className="lp-msg">
            <span>CMO</span>
            <p>
              Campaign <b>Spring Edit</b> is open. Copy has the first LinkedIn post. Six slots are on the calendar
              this week. One draft is waiting in Approvals — nothing is live.
            </p>
          </article>
        </div>
        <div className="lp-composer">
          <span>Brief the CMO…</span>
          <em>Send</em>
        </div>
      </div>
    </div>
  );
}

function ApprovalsMock() {
  return (
    <div className="lp-app">
      <aside className="lp-side">
        <p className="lp-side-brand">Northwind</p>
        <p className="lp-side-label">Work</p>
        <SideLink label="Approvals" active badge="2" />
        <SideLink label="Calendar" />
        <SideLink label="Studio" />
        <div className="lp-side-kill">
          <span>Kill switch</span>
          <b>Off</b>
        </div>
      </aside>
      <div className="lp-queue">
        <header className="lp-chat-head">
          <div>
            <p>Consent gate</p>
            <strong>Approvals</strong>
          </div>
          <span className="lp-live">2 waiting</span>
        </header>
        <div className="lp-queue-list">
          <article className="lp-ticket">
            <div className="lp-ticket-meta">
              <span>LinkedIn · Spring Edit</span>
              <time>Today, 14:10</time>
            </div>
            <p>The edit is in store this week — not online. Here is what we cut, and why it still matters.</p>
            <div className="lp-ticket-actions">
              <span className="is-ghost">Edit</span>
              <span className="is-ghost">Reject</span>
              <span className="is-solid">Approve</span>
            </div>
          </article>
          <article className="lp-ticket">
            <div className="lp-ticket-meta">
              <span>Instagram 4:5 · still</span>
              <time>Today, 14:22</time>
            </div>
            <p>Hero still, look 03. No caption until the LinkedIn post is signed off.</p>
            <div className="lp-ticket-actions">
              <span className="is-ghost">Edit</span>
              <span className="is-ghost">Reject</span>
              <span className="is-solid">Approve</span>
            </div>
          </article>
        </div>
      </div>
    </div>
  );
}

function TasksMock() {
  return (
    <div className="lp-app lp-app-pm">
      <aside className="lp-side">
        <p className="lp-side-brand">Core</p>
        <p className="lp-side-label">Project</p>
        <SideLink label="Board" active />
        <SideLink label="Features" />
        <SideLink label="Report" />
        <p className="lp-side-label">Console</p>
        <SideLink label="Projects" />
        <SideLink label="People" />
      </aside>
      <div className="lp-board">
        <header className="lp-chat-head">
          <div>
            <p>Task console</p>
            <strong>Referral rewards</strong>
          </div>
          <span className="lp-live is-quiet">Opened from God Mode</span>
        </header>
        <div className="lp-cols">
          {[
            ["Todo", ["CORE-14 Empty state copy", "CORE-16 Analytics event"]],
            ["Doing", ["CORE-12 Invite flow QA"]],
            ["Review", ["CORE-09 Referral codes"]],
            ["Done", ["CORE-F12 Feature brief"]],
          ].map(([col, cards]) => (
            <div key={String(col)} className="lp-col">
              <span>{col}</span>
              {(cards as string[]).map((card) => (
                <p key={card}>{card}</p>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ProductStage({ view }: { view: ProductView }) {
  const url =
    view === "tasks"
      ? "sweety.local/pm/projects/core"
      : view === "approvals"
        ? "sweety.local/brands/northwind/approvals"
        : "sweety.local/brands/northwind/godmode";

  return (
    <Window url={url}>
      {view === "godmode" && <GodModeMock />}
      {view === "approvals" && <ApprovalsMock />}
      {view === "tasks" && <TasksMock />}
    </Window>
  );
}
