"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAppName } from "@/lib/branding";
import { getToken } from "@/lib/api";
import { ProductStage, type ProductView } from "@/components/landing/ProductMocks";

const TABS: { id: ProductView; label: string }[] = [
  { id: "godmode", label: "God Mode" },
  { id: "approvals", label: "Approvals" },
  { id: "tasks", label: "Task console" },
];

export function LandingPage({ fontClass = "" }: { fontClass?: string }) {
  const appName = useAppName();
  const [scrolled, setScrolled] = useState(false);
  const [menu, setMenu] = useState(false);
  const [inApp, setInApp] = useState(false);
  const [view, setView] = useState<ProductView>("godmode");

  useEffect(() => {
    setInApp(Boolean(getToken()));
  }, []);

  useEffect(() => {
    const root = document.querySelector(".landing-shell");
    if (!root) return;
    const onScroll = () => setScrolled(root.scrollTop > 8);
    root.addEventListener("scroll", onScroll, { passive: true });
    return () => root.removeEventListener("scroll", onScroll);
  }, []);

  const consoleHref = inApp ? "/brands" : "/login";

  return (
    <div className={`landing-shell ${fontClass}`}>
      <header className={`lp-nav ${scrolled ? "is-scrolled" : ""}`}>
        <Link href="/" className="lp-logo">
          <span>{appName.slice(0, 1)}</span>
          {appName}
        </Link>
        <nav className="lp-nav-links">
          <a href="#product">Product</a>
          <a href="#gate">Consent</a>
          <a href="#how">How it works</a>
          <Link href="/pm/login">Task console</Link>
        </nav>
        <div className="lp-nav-cta">
          <Link href="/login" className="lp-text">
            Sign in
          </Link>
          <Link href={consoleHref} className="lp-btn-solid">
            Open console
          </Link>
          <button type="button" className="lp-burger" aria-label="Menu" onClick={() => setMenu((v) => !v)}>
            Menu
          </button>
        </div>
      </header>

      {menu && (
        <div className="lp-mobile">
          <a href="#product" onClick={() => setMenu(false)}>
            Product
          </a>
          <a href="#gate" onClick={() => setMenu(false)}>
            Consent
          </a>
          <a href="#how" onClick={() => setMenu(false)}>
            How it works
          </a>
          <Link href="/pm/login" onClick={() => setMenu(false)}>
            Task console
          </Link>
          <Link href={consoleHref} className="lp-btn-solid" onClick={() => setMenu(false)}>
            Open console
          </Link>
        </div>
      )}

      <section className="lp-hero">
        <h1>The control plane for marketing agents.</h1>
        <p className="lp-lede">
          {appName} runs a CMO, a content desk, and CRM behind a consent gate. Agents can draft and schedule. They
          cannot publish until you approve.
        </p>
        <div className="lp-hero-actions">
          <Link href={consoleHref} className="lp-btn-solid">
            Open God Mode
          </Link>
          <Link href="/pm/login" className="lp-text-btn">
            Task console
          </Link>
        </div>
        <p className="lp-note">Consent gate on by default. Kill switch included. Separate login for product.</p>

        <div className="lp-tabs" role="tablist" aria-label="Product views">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={view === tab.id}
              className={view === tab.id ? "is-on" : ""}
              onClick={() => setView(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="lp-stage">
          <ProductStage view={view} />
        </div>
      </section>

      <section id="product" className="lp-section">
        <div className="lp-section-head">
          <h2>Two consoles. Same company, different keys.</h2>
          <p>
            Marketing lives in God Mode. Engineering lives on the Task console. They share a database, not a login.
          </p>
        </div>
        <div className="lp-rows">
          <article>
            <h3>God Mode</h3>
            <p>
              Chat with the CMO. It opens a campaign from the brand mission, wakes copy and research, and can create
              features for product. The chat is the brief — not a prompt box that forgets the org.
            </p>
            <ul>
              <li>Mission creates the first campaign</li>
              <li>Specialist agents run in parallel</li>
              <li>Drafts land in Approvals, not on the network</li>
            </ul>
          </article>
          <article>
            <h3>Task console</h3>
            <p>
              A board with its own accounts and JWT. When marketing needs software, God Mode opens a feature. The team
              owns stories, bugs, comments, and the done column.
            </p>
            <ul>
              <li>Projects, features, issues</li>
              <li>Separate people and permissions</li>
              <li>Same Postgres, <code>pm</code> schema</li>
            </ul>
          </article>
        </div>
      </section>

      <section id="gate" className="lp-band">
        <div className="lp-band-inner">
          <div>
            <h2>Nothing goes live from a model.</h2>
            <p>
              Every post, still, and social publish sits in Approvals. Edit the copy, reject it, or sign it off.
              LinkedIn and Instagram only fire after that. If the room looks wrong, the kill switch pauses every agent
              on the brand.
            </p>
            <dl>
              <div>
                <dt>Approvals</dt>
                <dd>Consent queue. Edit, approve, reject. No auto-publish.</dd>
              </div>
              <div>
                <dt>Calendar</dt>
                <dd>Drafts, scheduled posts, and published work by date.</dd>
              </div>
              <div>
                <dt>CRM</dt>
                <dd>Hot contacts open a real list, not a vanity counter.</dd>
              </div>
              <div>
                <dt>Kill switch</dt>
                <dd>One control. Entire org paused until you resume.</dd>
              </div>
            </dl>
          </div>
          <ProductStage view="approvals" />
        </div>
      </section>

      <section id="how" className="lp-section">
        <div className="lp-section-head">
          <h2>How a brand actually runs</h2>
          <p>Four steps. Humans stay on the gate the whole way.</p>
        </div>
        <ol className="lp-how">
          <li>
            <span>01</span>
            <div>
              <strong>Create a brand and write the mission</strong>
              <p>The CMO opens a campaign and puts work on copy and strategy. There is no empty org.</p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <strong>Brief God Mode</strong>
              <p>Agents draft posts, score accounts, and can open product features. You watch Command.</p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <strong>Approve what ships</strong>
              <p>The queue holds every publish. Kill switch if you need the room quiet.</p>
            </div>
          </li>
          <li>
            <span>04</span>
            <div>
              <strong>Hand features to product</strong>
              <p>Task console is a different login. Engineering closes the loop on a real board.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="lp-cta">
        <h2>Sign in and brief the CMO.</h2>
        <p>God Mode for marketing. Task console when a feature needs an owner.</p>
        <div className="lp-hero-actions">
          <Link href={consoleHref} className="lp-btn-light">
            Open God Mode
          </Link>
          <Link href="/pm/login" className="lp-text-btn is-light">
            Task console
          </Link>
        </div>
      </section>

      <footer className="lp-foot">
        <span>
          {appName}
        </span>
        <nav>
          <Link href="/login">God Mode</Link>
          <Link href="/pm/login">Task console</Link>
          <Link href="/docs">API</Link>
        </nav>
      </footer>
    </div>
  );
}
