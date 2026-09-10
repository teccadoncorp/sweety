"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { LoginScene } from "@/components/LoginScene";
import { WorkInline } from "@/components/WorkLoader";
import { pmApi, setPmToken, setPmWorkspaceId } from "@/lib/pm";

const PILLARS = [
  { k: "01", t: "Separate console", d: "Its own login and board. Marketing stays on God Mode." },
  { k: "02", t: "Features first", d: "God Mode writes epics. The team turns them into issues." },
  { k: "03", t: "Same database", d: "Lives in the pm schema — isolated tables, shared Postgres." },
];

export default function PmLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await pmApi<{ access_token: string }>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          ...(mode === "register" ? { display_name: displayName } : {}),
        }),
      });
      setPmToken(data.access_token);
      const me = await pmApi<{ workspaces: { id: string }[] }>("/auth/me");
      if (me.workspaces[0]) setPmWorkspaceId(me.workspaces[0].id);
      router.push("/pm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <LoginScene />
      <div className="login-content">
        <header>
          <Link href="/" className="login-brand">
            <span className="login-mark">W</span>
            <span>Task console</span>
          </Link>
        </header>

        <div className="login-split">
          <section className="login-copy">
            <p className="login-kicker">Project management</p>
            <h1 className="login-title">
              Features in.
              <br />
              Work on the board.
            </h1>
            <p className="login-lede">
              A Jira-style workspace with projects, features, and issues. God Mode creates the features. You ship them.
            </p>
            <ul className="login-pillars">
              {PILLARS.map((item) => (
                <li key={item.k}>
                  <span>{item.k}</span>
                  <div>
                    <strong>{item.t}</strong>
                    <p>{item.d}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="login-panel">
            <form onSubmit={onSubmit} className="login-card">
              <div className="login-tabs">
                <button type="button" className={mode === "login" ? "is-on" : ""} onClick={() => setMode("login")}>
                  Sign in
                </button>
                <button
                  type="button"
                  className={mode === "register" ? "is-on" : ""}
                  onClick={() => setMode("register")}
                >
                  Create account
                </button>
              </div>
              <h2>{mode === "login" ? "Open the console" : "Join the board"}</h2>
              <p className="login-card-lede">
                {mode === "login"
                  ? "Task console accounts are separate from marketing God Mode."
                  : "New accounts join the default workspace as members."}
              </p>
              <label>
                Email
                <input
                  className="field"
                  type="email"
                  autoComplete="email"
                  placeholder="you@team.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </label>
              {mode === "register" && (
                <label>
                  Display name
                  <input
                    className="field"
                    placeholder="Alex"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </label>
              )}
              <label>
                Password
                <input
                  className="field"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </label>
              {error && <p className="login-error">{error}</p>}
              {busy && <WorkInline label={mode === "login" ? "Opening the console" : "Creating your account"} />}
              <button className="btn-primary login-submit" type="submit" disabled={busy}>
                {mode === "login" ? "Enter console" : "Create account"}
              </button>
              <button
                type="button"
                className="login-demo"
                onClick={() => {
                  setEmail("contact@cpdash.ai");
                  setPassword("supersecret123");
                  setMode("login");
                }}
              >
                Fill demo credentials
              </button>
              <Link href="/login" className="login-demo" style={{ display: "block", textAlign: "center" }}>
                Marketing God Mode login
              </Link>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}
