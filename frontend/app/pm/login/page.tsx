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
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (mode === "register") return;
    setError("");
    setBusy(true);
    try {
      const data = await pmApi<{ access_token: string }>(`/auth/login`, {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
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
              {mode === "register" ? (
                <div className="login-blocked">
                  <h2>Create account</h2>
                  <p>
                    Account creation is blocked for security reasons. Contact an admin to be added to the console.
                  </p>
                </div>
              ) : (
                <>
                  <h2>Open the console</h2>
                  <p className="login-card-lede">Task console accounts are separate from marketing God Mode.</p>
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
                  <label>
                    Password
                    <input
                      className="field"
                      type="password"
                      autoComplete="current-password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </label>
                  {error && <p className="login-error">{error}</p>}
                  {busy && <WorkInline label="Opening the console" />}
                  <button className="btn-primary login-submit" type="submit" disabled={busy}>
                    Enter console
                  </button>
                </>
              )}
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
