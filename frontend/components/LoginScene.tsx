"use client";

import { useEffect, useRef } from "react";

export function LoginScene() {
  const stage = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;

    const onMove = (event: MouseEvent) => {
      const x = (event.clientX / window.innerWidth - 0.5) * 14;
      const y = (event.clientY / window.innerHeight - 0.5) * 10;
      el.style.setProperty("--tilt-x", `${18 + y}deg`);
      el.style.setProperty("--tilt-y", `${-10 - x}deg`);
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  return (
    <div className="login-scene" aria-hidden>
      <div className="login-glow login-glow-a" />
      <div className="login-glow login-glow-b" />
      <div className="login-glow login-glow-c" />
      <div ref={stage} className="login-stage">
        <div className="login-ring login-ring-a" />
        <div className="login-ring login-ring-b" />
        <div className="login-grid" />
        <article className="login-float login-float-1">
          <span>Campaign</span>
          <strong>Spring Edit</strong>
          <em>brief ready</em>
        </article>
        <article className="login-float login-float-2">
          <span>Consent</span>
          <strong>3 drafts</strong>
          <em>awaiting board</em>
        </article>
        <article className="login-float login-float-3">
          <span>Publish</span>
          <strong>LinkedIn</strong>
          <em>after you say go</em>
        </article>
        <div className="login-orb login-orb-a" />
        <div className="login-orb login-orb-b" />
        <div className="login-orb login-orb-c" />
      </div>
    </div>
  );
}
