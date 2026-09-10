"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAppName } from "@/lib/branding";
import { getToken } from "@/lib/api";
import { Reveal, useCountUp } from "@/components/landing/Reveal";

const WORDS = ["campaigns", "features", "approvals", "the swarm"];

const CASES = [
  {
    slug: "aurora",
    eyebrow: "Retail · 14 days",
    title: "Aurora Atelier shipped a Spring Edit without a 12-person studio.",
    body: "The board briefed God Mode once. Copy, stills, and a calendar came back the same week — nothing live until they approved it.",
    image: "/landing/case-aurora.png",
    quote: "We stopped briefing five agencies. The CMO wrote the plan. We just said yes.",
    person: "Lina Voss, Founder",
    metrics: [
      { k: "11", v: "assets approved" },
      { k: "3.4×", v: "content output" },
      { k: "0", v: "unapproved posts" },
    ],
  },
  {
    slug: "northline",
    eyebrow: "B2B SaaS · 1 quarter",
    title: "Northline turned a quiet CRM into a scored pipeline the sales floor actually used.",
    body: "Agents researched accounts, warmed contacts, and moved deals. Humans kept the kill switch and the close.",
    image: "/landing/case-northline.png",
    quote: "Hot leads showed up scored. We stopped guessing who to call on Monday.",
    person: "Marcus Hale, VP Revenue",
    metrics: [
      { k: "+$420k", v: "pipeline" },
      { k: "38", v: "hot accounts" },
      { k: "6", v: "agents in the swarm" },
    ],
  },
  {
    slug: "harbor",
    eyebrow: "Healthtech · product",
    title: "Harbor Health let God Mode write features — then shipped them on a real board.",
    body: "Marketing God Mode created epics. The Task console turned them into stories, owners, and a done column.",
    image: "/landing/case-harbor.png",
    quote: "The brief became a feature key. Engineering finally saw what the board meant.",
    person: "Priya Shah, Head of Product",
    metrics: [
      { k: "28", v: "features created" },
      { k: "91", v: "issues closed" },
      { k: "2", v: "consoles, one DB" },
    ],
  },
];

function WordCycle() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setI((n) => (n + 1) % WORDS.length), 2400);
    return () => window.clearInterval(id);
  }, []);
  return (
    <span className="lp-cycle" aria-live="polite">
      {WORDS.map((word, idx) => (
        <span key={word} className={idx === i ? "is-on" : ""}>
          {word}
        </span>
      ))}
    </span>
  );
}

function Stat({ n, suffix, label }: { n: number; suffix: string; label: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [on, setOn] = useState(false);
  const value = useCountUp(n, on);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setOn(true), { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className="lp-stat">
      <strong>
        {value}
        {suffix}
      </strong>
      <span>{label}</span>
    </div>
  );
}

export function LandingPage() {
  const appName = useAppName();
  const [scrolled, setScrolled] = useState(false);
  const [menu, setMenu] = useState(false);
  const [inApp, setInApp] = useState(false);
  const heroImg = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setInApp(Boolean(getToken()));
  }, []);

  useEffect(() => {
    const root = document.querySelector(".landing-shell");
    if (!root) return;
    const onScroll = () => {
      setScrolled(root.scrollTop > 12);
      if (heroImg.current) {
        const y = Math.min(48, root.scrollTop * 0.12);
        heroImg.current.style.transform = `translateY(${y}px) scale(1.04)`;
      }
    };
    root.addEventListener("scroll", onScroll, { passive: true });
    return () => root.removeEventListener("scroll", onScroll);
  }, []);

  const consoleHref = inApp ? "/brands" : "/login";

  return (
    <div className="landing-shell">
      <div className="lp-bg" aria-hidden>
        <div className="lp-glow lp-glow-a" />
        <div className="lp-glow lp-glow-b" />
        <div className="lp-grid" />
      </div>

      <header className={`lp-nav ${scrolled ? "is-scrolled" : ""}`}>
        <Link href="/" className="login-brand">
          <span className="login-mark">{appName.slice(0, 1)}</span>
          <span>{appName}</span>
        </Link>
        <nav className="lp-nav-links">
          <a href="#product">Product</a>
          <a href="#cases">Case studies</a>
          <a href="#work">How it works</a>
          <Link href="/pm/login">Task console</Link>
        </nav>
        <div className="lp-nav-cta">
          <Link href={consoleHref} className="btn-primary">
            Enter God Mode
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
          <a href="#cases" onClick={() => setMenu(false)}>
            Case studies
          </a>
          <a href="#work" onClick={() => setMenu(false)}>
            How it works
          </a>
          <Link href="/pm/login" onClick={() => setMenu(false)}>
            Task console
          </Link>
          <Link href={consoleHref} className="btn-primary" onClick={() => setMenu(false)}>
            Enter God Mode
          </Link>
        </div>
      )}

      <section className="lp-hero">
        <Reveal>
          <p className="login-kicker">Marketing control plane · Task console</p>
          <h1 className="lp-title">
            Brief the CMO.
            <br />
            Ship <WordCycle />.
          </h1>
          <p className="lp-lede">
            Agents write the campaign, score the pipeline, and open product features. You keep consent, the kill
            switch, and the done column.
          </p>
          <div className="lp-hero-actions">
            <Link href={consoleHref} className="btn-primary lp-btn">
              Enter God Mode
            </Link>
            <Link href="/pm/login" className="lp-btn-ghost">
              Open the Task console
            </Link>
          </div>
        </Reveal>
        <Reveal delay={120} className="lp-hero-frame">
          <div className="lp-hero-meta">
            <span>Live briefing</span>
            <span className="lp-dot" />
            <span>Consent gate on</span>
          </div>
          <div ref={heroImg} className="lp-hero-photo">
            <Image
              src="/landing/hero.png"
              alt="A marketing command center watching campaign dashboards"
              width={1600}
              height={900}
              priority
            />
          </div>
          <div className="lp-float-row">
            <article className="lp-chip">
              <span>Campaign</span>
              <strong>Spring Edit</strong>
            </article>
            <article className="lp-chip">
              <span>Feature</span>
              <strong>CORE-F12</strong>
            </article>
            <article className="lp-chip">
              <span>Approvals</span>
              <strong>3 waiting</strong>
            </article>
          </div>
        </Reveal>
      </section>

      <section className="lp-marquee" aria-hidden>
        <div className="lp-marquee-track">
          {["God Mode", "Approvals", "Calendar", "CRM swarm", "Kill switch", "Task console", "Features", "Kanban"].map(
            (item) => (
              <span key={item}>{item}</span>
            ),
          )}
          {["God Mode", "Approvals", "Calendar", "CRM swarm", "Kill switch", "Task console", "Features", "Kanban"].map(
            (item) => (
              <span key={`${item}-2`}>{item}</span>
            ),
          )}
        </div>
      </section>

      <section id="product" className="lp-section">
        <Reveal>
          <p className="login-kicker">Two consoles. One database.</p>
          <h2 className="lp-h2">The board briefs. The org runs. Product ships.</h2>
        </Reveal>
        <div className="lp-split">
          <Reveal className="lp-panel">
            <p className="lp-panel-kicker">01 · Marketing</p>
            <h3>God Mode</h3>
            <p>
              Chat with the CMO. Campaigns, drafts, images, and CRM moves happen in tools — then wait on Approvals.
              Nothing publishes until a human says go.
            </p>
            <ul>
              <li>Mission opens a first campaign</li>
              <li>Swarm wakes in parallel</li>
              <li>Create product features for the Task console</li>
            </ul>
            <Link href="/login" className="lp-text-link">
              Sign in to God Mode →
            </Link>
          </Reveal>
          <Reveal delay={100} className="lp-panel-visual">
            <Image
              src="/landing/product-godmode.png"
              alt="God Mode briefing on a laptop in a dark studio"
              width={1280}
              height={720}
            />
          </Reveal>
        </div>
        <div className="lp-split lp-split-rev">
          <Reveal className="lp-panel">
            <p className="lp-panel-kicker">02 · Product</p>
            <h3>Task console</h3>
            <p>
              A Jira-style board in its own login and schema. God Mode writes features. The team owns issues,
              comments, and the done column.
            </p>
            <ul>
              <li>Separate accounts and JWT</li>
              <li>Projects, features, stories, bugs</li>
              <li>Same Postgres — `pm` schema</li>
            </ul>
            <Link href="/pm/login" className="lp-text-link">
              Open the Task console →
            </Link>
          </Reveal>
          <Reveal delay={100} className="lp-panel-visual lp-board-visual">
            <div className="lp-mini-board">
              {["Backlog", "Doing", "Review", "Done"].map((col, i) => (
                <div key={col} className="lp-mini-col">
                  <span>{col}</span>
                  <i className={i === 3 ? "is-done" : ""} />
                  <i className={i === 1 ? "is-live" : ""} />
                  {i < 3 && <i />}
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      <section className="lp-stats">
        <Stat n={12} suffix="" label="specialist agents in the org" />
        <Stat n={40} suffix="+" label="skills the swarm can run" />
        <Stat n={0} suffix="" label="posts live without consent" />
        <Stat n={1} suffix="" label="kill switch for the room" />
      </section>

      <section id="cases" className="lp-section">
        <Reveal>
          <p className="login-kicker">Case studies</p>
          <h2 className="lp-h2">Rooms that briefed once, then watched the work land.</h2>
        </Reveal>
        <div className="lp-cases">
          {CASES.map((item, idx) => (
            <Reveal key={item.slug} className={`lp-case ${idx === 0 ? "is-lead" : ""}`}>
              <div className="lp-case-photo">
                <Image src={item.image} alt={item.title} width={1200} height={900} />
              </div>
              <div className="lp-case-body">
                <p className="lp-panel-kicker">{item.eyebrow}</p>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
                <blockquote>
                  “{item.quote}”
                  <cite>{item.person}</cite>
                </blockquote>
                <div className="lp-case-metrics">
                  {item.metrics.map((m) => (
                    <div key={m.v}>
                      <strong>{m.k}</strong>
                      <span>{m.v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="work" className="lp-section">
        <Reveal>
          <p className="login-kicker">How it works</p>
          <h2 className="lp-h2">Four moves. Humans stay on the gate.</h2>
        </Reveal>
        <ol className="lp-steps">
          {[
            ["Brief", "Tell God Mode the mission, the audience, the date. Optional logo and site."],
            ["Watch", "The CMO opens a campaign, writes tasks, and wakes the swarm."],
            ["Consent", "Approvals hold every publish. One kill switch pauses the org."],
            ["Ship", "Product features land on the Task console. The board closes the loop."],
          ].map(([t, d], i) => (
            <Reveal key={t} delay={i * 80}>
              <li>
                <span>0{i + 1}</span>
                <strong>{t}</strong>
                <p>{d}</p>
              </li>
            </Reveal>
          ))}
        </ol>
      </section>

      <section className="lp-cta">
        <Reveal>
          <h2 className="lp-h2">The board is the product.</h2>
          <p className="lp-lede">
            Start in God Mode for marketing. Open the Task console when features need owners.
          </p>
          <div className="lp-hero-actions">
            <Link href={consoleHref} className="btn-primary lp-btn">
              Enter God Mode
            </Link>
            <Link href="/pm/login" className="lp-btn-ghost">
              Task console login
            </Link>
          </div>
        </Reveal>
      </section>

      <footer className="lp-foot">
        <span>
          {appName} · agents work · you decide
        </span>
        <nav>
          <Link href="/login">God Mode</Link>
          <Link href="/pm/login">Tasks</Link>
          <Link href="/docs">API</Link>
        </nav>
      </footer>
    </div>
  );
}
