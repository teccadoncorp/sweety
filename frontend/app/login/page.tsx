"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { LoginScene } from "@/components/LoginScene";
import { WorkInline } from "@/components/WorkLoader";
import { api, setToken } from "@/lib/api";
import { useAppName } from "@/lib/branding";

const PILLARS = [
  { k: "01", t: "Mission to campaign", d: "The CMO opens a real first campaign the moment a brand is created." },
  { k: "02", t: "Consent before live", d: "Every draft waits on the board. Nothing publishes until you approve it." },
  { k: "03", t: "One kill switch", d: "Pause every agent instantly. Resume when the room is ready." },
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
    setError("");
    setBusy(true);
    try {
      const data = await api<{ access_token: string }>(`/auth/${mode}`, {
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
            <p className="login-kicker">Marketing control plane</p>
            <h1 className="login-title">
              Brief the CMO.
              <br />
              Watch the org run.
            </h1>
            <p className="login-lede">
              Strategy, drafts, calendar, and publish — with a human on the consent gate. Agents work. You decide what goes live.
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
              <h2>{mode === "login" ? "Enter the board" : "Stand up a board"}</h2>
              <p className="login-card-lede">
                {mode === "login" ? "Use your board email to open God Mode." : "A new org starts from your first brand mission."}
              </p>
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
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </label>
              {error && <p className="login-error">{error}</p>}
              {busy && <WorkInline label={mode === "login" ? "Opening the board" : "Creating your board"} />}
              <button className="btn-primary login-submit" type="submit" disabled={busy}>
                {mode === "login" ? "Enter God Mode" : "Create account"}
              </button>
              <button
                type="button"
                className="login-demo"
                onClick={() => {
                  setEmail("board@sweety.local");
                  setPassword("sweety");
                  setMode("login");
                }}
              >
                Fill demo credentials
              </button>
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
