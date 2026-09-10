"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { LoginScene } from "@/components/LoginScene";
import { WorkInline } from "@/components/WorkLoader";
import { api, setToken } from "@/lib/api";
import { useAppName } from "@/lib/branding";

const PILLARS = [
  { t: "Mission to campaign", d: "The CMO opens a first campaign the moment a brand is created." },
  { t: "Consent before live", d: "Every draft waits on the board. Nothing publishes until you approve." },
  { t: "One kill switch", d: "Pause every agent immediately. Resume when the room is ready." },
];

export default function LoginPage() {
  const router = useRouter();
  const appName = useAppName();
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
      const data = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setToken(data.access_token);
      router.push("/brands");
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
            <span className="login-mark">{appName.slice(0, 1)}</span>
            <span>{appName}</span>
          </Link>
        </header>

        <div className="login-split">
          <section className="login-copy">
            <p className="login-kicker">Control plane</p>
            <h1 className="login-title">
              The board,
              <br />
              not the prompt.
            </h1>
            <p className="login-lede">
              Brief the CMO, approve what ships, and pause the org with one switch. Quiet tools. Human consent.
            </p>
            <ul className="login-pillars">
              {PILLARS.map((item) => (
                <li key={item.t}>
                  <strong>{item.t}</strong>
                  <p>{item.d}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="login-panel">
            <form onSubmit={onSubmit} className="login-card">
              <div className="login-tabs">
                <button
                  type="button"
                  className={mode === "login" ? "is-on" : ""}
                  onClick={() => setMode("login")}
                >
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
                    Account creation is blocked for security reasons. Contact an admin to be added to the board.
                  </p>
                </div>
              ) : (
                <>
                  <h2>Sign in</h2>
                  <p className="login-card-lede">Use your board email.</p>
                  <label>
                    Email
                    <input
                      className="field"
                      type="email"
                      autoComplete="email"
                      placeholder="you@brand.com"
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
                  {busy && <WorkInline label="Opening the board" />}
                  <button className="btn-primary login-submit" type="submit" disabled={busy}>
                    Enter God Mode
                  </button>
                </>
              )}
              <Link href="/pm/login" className="login-demo" style={{ display: "block", textAlign: "center" }}>
                Open the Task console instead
              </Link>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}
