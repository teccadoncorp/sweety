"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { WorkInline } from "@/components/WorkLoader";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("board@sweety.local");
  const [password, setPassword] = useState("sweety");
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
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6">
      <p className="text-sm uppercase tracking-[0.2em] text-cyan">CMO command plane</p>
      <h1 className="mt-3 font-serif text-6xl leading-none">Sweety</h1>
      <p className="mt-4 max-w-md text-clay">
        Brief the CMO in God Mode. Connect socials. Watch the org run the plan.
      </p>
      <form onSubmit={onSubmit} className="card mt-10 space-y-4 p-6">
        <label className="block text-sm">
          Email
          <input className="field mt-1" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="block text-sm">
          Password
          <input
            className="field mt-1"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="text-sm text-violet">{error}</p>}
        {busy && <WorkInline label="Signing you in" />}
        <div className="flex items-center gap-3">
          <button className="btn-primary" type="submit" disabled={busy}>
            {mode === "login" ? "Enter God Mode" : "Create account"}
          </button>
          <button
            type="button"
            className="text-sm text-clay"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Need an account?" : "Have an account?"}
          </button>
        </div>
        <p className="text-xs text-clay/70">Demo seed: board@sweety.local / sweety</p>
      </form>
    </div>
  );
}
