"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthed } from "../lib/auth";
import { PROVIDER_REGISTRY } from "../lib/providers/registry";
import type { ProviderCategory } from "../lib/providers/types";
import { LEGAL_LINKS } from "./LegalLayout";
import { LogoMark } from "./Logo";

/* ─── Intersection Observer hook ─── */
function useReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); io.disconnect(); } },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, visible };
}

/* ─── Animated counter ─── */
function CountUp({ target, suffix = "" }: { target: number; suffix?: string }) {
  const [val, setVal] = useState(0);
  const { ref, visible } = useReveal(0.3);
  useEffect(() => {
    if (!visible) return;
    let start = 0;
    const duration = 1200;
    const step = (ts: number) => {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      setVal(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [visible, target]);
  return <span ref={ref}>{val.toLocaleString()}{suffix}</span>;
}

/* ─── Provider category → color + label helpers ─── */
const CATEGORY_COLORS: Record<ProviderCategory, string> = {
  payment: "#635bff",
  communication: "#f22f46",
  cloud: "#06b6d4",
  ai: "#a78bfa",
  analytics: "#f59e0b",
  database: "#22c55e",
  devtools: "#1f2328",
  media: "#ec4899",
  other: "#64748b",
};
function categoryColor(cat: ProviderCategory): string {
  return CATEGORY_COLORS[cat] || "#64748b";
}
function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export default function LandingPage() {
  const router = useRouter();
  useEffect(() => { if (isAuthed()) router.replace("/dashboard"); }, [router]);

  const hero = useReveal(0.1);
  const stats = useReveal(0.2);
  const problems = [useReveal(), useReveal(), useReveal()];
  const steps = [useReveal(), useReveal(), useReveal(), useReveal()];
  const apisRef = useReveal(0.1);
  const pricing = [useReveal(), useReveal(), useReveal()];
  const cta = useReveal();

  return (
    <>
      {/* ─── Inline Keyframes ─── */}
      <style>{`
        .lp-hero-bg {
          position: absolute; inset: 0; z-index: 0; overflow: hidden;
          background: linear-gradient(135deg, #0f0a2e 0%, #1a1145 30%, #0d1b3e 60%, #0a0f2c 100%);
        }
        .lp-hero-bg::before {
          content: ""; position: absolute; inset: -50%;
          width: 200%; height: 200%;
          background: radial-gradient(ellipse at 30% 20%, rgba(99,91,255,0.25) 0%, transparent 50%),
                      radial-gradient(ellipse at 70% 60%, rgba(139,92,246,0.2) 0%, transparent 50%),
                      radial-gradient(ellipse at 50% 90%, rgba(6,182,212,0.15) 0%, transparent 50%);
          animation: meshGradient 12s ease infinite;
        }
        .lp-hero-bg::after {
          content: ""; position: absolute; inset: 0;
          background-image: radial-gradient(circle, rgba(255,255,255,0.05) 1px, transparent 1px);
          background-size: 32px 32px;
        }
        .lp-floating-badge {
          position: absolute; padding: 8px 16px; border-radius: 999px;
          font-size: 12px; font-weight: 600; color: white;
          backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1);
          animation: float 4s ease-in-out infinite;
          pointer-events: none;
        }
        .lp-glow-btn {
          position: relative; overflow: hidden;
          transition: transform 0.2s, box-shadow 0.3s;
        }
        .lp-glow-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 32px rgba(99,91,255,0.4);
        }
        .lp-glow-btn::after {
          content: ""; position: absolute; inset: 0;
          background: linear-gradient(135deg, transparent 30%, rgba(255,255,255,0.15) 50%, transparent 70%);
          transform: translateX(-100%); transition: transform 0.5s;
        }
        .lp-glow-btn:hover::after { transform: translateX(100%); }
        .lp-stat-card {
          background: rgba(255,255,255,0.06); backdrop-filter: blur(12px);
          border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
          padding: 28px 24px; text-align: center; transition: transform 0.3s, border-color 0.3s;
        }
        .lp-stat-card:hover { transform: translateY(-4px); border-color: rgba(99,91,255,0.4); }
        .lp-stat-number { font-size: 36px; font-weight: 800; color: white; line-height: 1; }
        .lp-stat-label { font-size: 14px; color: rgba(255,255,255,0.6); margin-top: 8px; }
        .lp-problem-card {
          background: var(--surface); border: 1px solid var(--border);
          border-radius: 16px; padding: 32px; transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
        }
        .lp-problem-card:hover { transform: translateY(-6px); box-shadow: 0 16px 48px rgba(16,24,40,0.1); border-color: var(--accent); }
        .lp-problem-icon {
          width: 56px; height: 56px; border-radius: 14px; display: flex;
          align-items: center; justify-content: center; margin-bottom: 20px;
          background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
          color: white; transition: transform 0.3s;
        }
        .lp-problem-card:hover .lp-problem-icon { transform: scale(1.1) rotate(5deg); }
        .lp-step-card {
          position: relative; background: var(--surface); border: 1px solid var(--border);
          border-radius: 16px; padding: 32px; text-align: center;
          transition: transform 0.3s, box-shadow 0.3s;
        }
        .lp-step-card::before {
          content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
          background: linear-gradient(90deg, var(--accent), #8b5cf6);
          border-radius: 16px 16px 0 0;
        }
        .lp-step-card:hover { transform: translateY(-4px); box-shadow: 0 12px 36px rgba(16,24,40,0.08); }
        .lp-step-number {
          width: 48px; height: 48px; border-radius: 50%; display: flex;
          align-items: center; justify-content: center; margin: 0 auto 20px;
          background: linear-gradient(135deg, var(--accent), #8b5cf6);
          color: white; font-size: 20px; font-weight: 800;
        }
        .lp-step-card.future { opacity: 0.65; }
        .lp-api-card {
          background: var(--bg); border: 1px solid var(--border); border-radius: 16px;
          padding: 28px; transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
        }
        .lp-api-card:hover { transform: translateY(-4px) scale(1.01); box-shadow: 0 12px 36px rgba(16,24,40,0.1); }
        .lp-api-logo {
          width: 52px; height: 52px; border-radius: 14px; display: flex;
          align-items: center; justify-content: center; color: white;
          font-weight: 800; font-size: 20px; margin-bottom: 16px;
        }
        .lp-pricing-card {
          position: relative; background: var(--surface); border: 1px solid var(--border);
          border-radius: 16px; padding: 36px; display: flex; flex-direction: column;
          transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
        }
        .lp-pricing-card:hover { transform: translateY(-6px); box-shadow: 0 16px 48px rgba(16,24,40,0.1); }
        .lp-pricing-card.popular {
          border-color: var(--accent); box-shadow: 0 8px 32px rgba(99,91,255,0.15);
        }
        .lp-pricing-card.popular::before {
          content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px;
          background: linear-gradient(90deg, var(--accent), #8b5cf6, #06b6d4);
          background-size: 200% 200%; animation: gradientMove 3s ease infinite;
          border-radius: 16px 16px 0 0;
        }
        .lp-check { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; font-size: 14px; }
        .lp-check svg { width: 20px; height: 20px; color: var(--green); flex-shrink: 0; margin-top: 2px; }
        .lp-cta-section {
          position: relative; overflow: hidden; padding: 80px 24px; text-align: center;
          background: linear-gradient(135deg, #0f0a2e, #1a1145, #0d1b3e);
          border-radius: 24px; margin: 0 24px;
        }
        .lp-cta-section::before {
          content: ""; position: absolute; inset: 0;
          background-image: radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px);
          background-size: 28px 28px;
        }
        .lp-cta-glow {
          position: absolute; width: 400px; height: 400px; border-radius: 50%;
          background: radial-gradient(circle, rgba(99,91,255,0.2) 0%, transparent 70%);
          top: 50%; left: 50%; transform: translate(-50%, -50%);
          animation: pulseScale 4s ease-in-out infinite;
        }
        .lp-code-window {
          background: #1a1a2e; border-radius: 16px; overflow: hidden;
          border: 1px solid #2d2d44; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          transition: transform 0.4s;
        }
        .lp-code-window:hover { transform: translateY(-4px) rotateY(-2deg); }
        .lp-code-header {
          display: flex; align-items: center; gap: 8px; padding: 14px 18px;
          background: #22223b; border-bottom: 1px solid #2d2d44;
        }
        .lp-code-dot { width: 12px; height: 12px; border-radius: 50%; }
        .lp-code-content {
          margin: 0; padding: 24px; overflow-x: auto;
          font-family: var(--font-mono); font-size: 13px; line-height: 1.7;
          color: #e4e4e7; white-space: pre;
        }
        .lp-scroll-top {
          position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px;
          border-radius: 50%; background: var(--accent); color: white; border: none;
          cursor: pointer; display: flex; align-items: center; justify-content: center;
          box-shadow: 0 4px 16px rgba(99,91,255,0.3); z-index: 90;
          opacity: 0; transform: translateY(16px); transition: opacity 0.3s, transform 0.3s;
          pointer-events: none;
        }
        .lp-scroll-top.show { opacity: 1; transform: translateY(0); pointer-events: auto; }
        .lp-scroll-top:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(99,91,255,0.4); }
        @media (max-width: 1024px) {
          .lp-stats-grid { grid-template-columns: repeat(2, 1fr) !important; }
          .lp-apis-grid { grid-template-columns: repeat(3, 1fr) !important; }
        }
        @media (max-width: 880px) {
          .lp-steps-grid { grid-template-columns: repeat(2, 1fr) !important; }
        }
        @media (max-width: 768px) {
          .lp-hero { padding: 100px 16px 60px; }
          .lp-hero .container { grid-template-columns: 1fr !important; text-align: center; gap: 48px; }
          .lp-hero-cta { align-items: center; }
          .lp-hero-grid { grid-template-columns: 1fr !important; }
          .lp-stats-grid { grid-template-columns: repeat(2, 1fr) !important; }
          .lp-steps-grid { grid-template-columns: 1fr !important; }
          .lp-apis-grid { grid-template-columns: repeat(2, 1fr) !important; }
          .lp-pricing-grid { grid-template-columns: 1fr !important; max-width: 400px; margin: 0 auto; }
          .lp-floating-badge { display: none; }
          .lp-cta-section { margin: 0 0; border-radius: 16px; padding: 56px 20px; }
          .lp-code-window { max-width: 100%; }
        }
      `}</style>

      <header className="landing-nav">
        <div className="landing-nav-inner">
          <Link href="/" className="brand"><LogoMark size={26} withWordmark /></Link>
          <nav className="landing-nav-links">
            <Link href="#features">Features</Link>
            <Link href="#apis">APIs</Link>
            <Link href="#pricing">Pricing</Link>
            <Link href="/login" className="landing-nav-link">Log in</Link>
            <Link href="/dashboard" className="btn btn-primary lp-glow-btn">Get Started Free</Link>
          </nav>
          {/* Mobile-only CTA (nav links are hidden <768px) */}
          <Link href="/dashboard" className="btn btn-primary lp-glow-btn landing-nav-cta-mobile">Start</Link>
        </div>
      </header>

      <main>
        {/* ═══════ HERO ═══════ */}
        <section className="lp-hero" style={{ position: "relative", minHeight: "100vh", display: "flex", alignItems: "center", padding: "120px 24px 80px" }} aria-labelledby="hero-title">
          <div className="lp-hero-bg" />
          <div className="container" style={{ position: "relative", zIndex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 60, alignItems: "center" }} ref={hero.ref}>
            <div style={{ opacity: hero.visible ? 1 : 0, transform: hero.visible ? "translateY(0)" : "translateY(32px)", transition: "all 0.7s ease" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 16px", borderRadius: 999, background: "rgba(99,91,255,0.15)", border: "1px solid rgba(99,91,255,0.3)", color: "#a78bfa", fontSize: 13, fontWeight: 600, marginBottom: 24 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#34d399", animation: "pulse 2s infinite" }} />
                Monitors 12 provider changelogs daily
              </div>
              <h1 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, lineHeight: 1.1, margin: "0 0 24px", letterSpacing: "-0.02em", color: "white" }}>
                Stop losing <span style={{ background: "linear-gradient(135deg, #a78bfa, #06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>40 hours</span> every time{" "}
                <span style={{ background: "linear-gradient(135deg, var(--accent), #8b5cf6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Stripe changes their API</span>
              </h1>
              <p style={{ fontSize: 18, lineHeight: 1.7, color: "rgba(255,255,255,0.65)", margin: "0 0 32px", maxWidth: 520 }}>
                Breaklytix detects which third-party APIs your repos use, monitors changelogs for breaking changes, and alerts you <strong style={{ color: "white" }}>before</strong> your code breaks.
              </p>
              <div className="lp-hero-cta" style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>
                <Link href="/dashboard" className="btn btn-primary btn-lg lp-glow-btn" style={{ fontSize: 16, padding: "16px 32px", background: "linear-gradient(135deg, var(--accent), #7c3aed)", border: "none", borderRadius: 12 }}>
                  Connect your GitHub repo — free scan
                </Link>
                <p style={{ fontSize: 14, color: "rgba(255,255,255,0.45)", margin: 0 }}>14-day free trial · No credit card · Auto-fix PRs you review</p>
              </div>
            </div>
            <div style={{ opacity: hero.visible ? 1 : 0, transform: hero.visible ? "translateX(0)" : "translateX(40px)", transition: "all 0.7s ease 0.2s" }} className="lp-hero-grid">
              {/* Floating badges */}
              <div className="lp-floating-badge" style={{ top: -10, right: 40, background: "rgba(99,91,255,0.3)", animationDelay: "0s" }}>API Detection</div>
              <div className="lp-floating-badge" style={{ top: 60, right: -20, background: "rgba(16,185,129,0.3)", animationDelay: "1s" }}>Auto-Fix</div>
              <div className="lp-floating-badge" style={{ bottom: 40, right: 20, background: "rgba(245,158,11,0.3)", animationDelay: "2s" }}>Real-time Alerts</div>
              <div className="lp-code-window">
                <div className="lp-code-header">
                  <span className="lp-code-dot" style={{ background: "#ff5f57" }} />
                  <span className="lp-code-dot" style={{ background: "#ffbd2e" }} />
                  <span className="lp-code-dot" style={{ background: "#28ca42" }} />
                  <span style={{ marginLeft: "auto", fontSize: 13, color: "#8b8ba8", fontFamily: "var(--font-mono)" }}>payments/stripe.ts</span>
                </div>
                <pre className="lp-code-content"><code>{`// ⚠️ Breaking change detected!
import Stripe from "stripe";

const stripe = new Stripe(
  process.env.STRIPE_SECRET_KEY
);

// BEFORE (deprecated in 2024-04)
const charge = await stripe.charges.create({
  amount: 2000,
  currency: "usd",
  source: "tok_visa",
});

// AFTER (migrate to PaymentIntents)
const intent = await stripe.paymentIntents.create({
  amount: 2000,
  currency: "usd",
  payment_method: "pm_card_visa",
});`}</code></pre>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════ STATS BAR ═══════ */}
        <section style={{ background: "linear-gradient(135deg, #0f0a2e, #1a1145)", padding: "48px 24px" }} ref={stats.ref}>
          <div className="container">
            <div className="lp-stats-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24, opacity: stats.visible ? 1 : 0, transform: stats.visible ? "translateY(0)" : "translateY(24px)", transition: "all 0.6s ease" }}>
              <div className="lp-stat-card" style={{ animationDelay: "0.1s" }}>
                <div className="lp-stat-number"><CountUp target={12} /></div>
                <div className="lp-stat-label">Provider changelogs monitored</div>
              </div>
              <div className="lp-stat-card" style={{ animationDelay: "0.2s" }}>
                <div className="lp-stat-number"><CountUp target={44} suffix="+" /></div>
                <div className="lp-stat-label">API usage patterns detected</div>
              </div>
              <div className="lp-stat-card" style={{ animationDelay: "0.3s" }}>
                <div className="lp-stat-number"><CountUp target={1500} /></div>
                <div className="lp-stat-label">Files scanned per repository</div>
              </div>
              <div className="lp-stat-card" style={{ animationDelay: "0.4s" }}>
                <div className="lp-stat-number">100%</div>
                <div className="lp-stat-label">Real data — no fabricated metrics</div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════ PROBLEM SECTION ═══════ */}
        <section id="features" className="section" style={{ background: "var(--bg)" }} aria-labelledby="problem-title">
          <div className="container">
            <div className="section-header">
              <h2 id="problem-title" style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.2, margin: "0 0 12px" }}>The problem every team faces</h2>
              <p className="section-subheadline">API providers ship breaking changes constantly. Catching them manually doesn&apos;t scale.</p>
            </div>
            <div className="lp-steps-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24, maxWidth: 1000, margin: "0 auto" }}>
              {[
                { icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>, title: "Surprise breaking changes", desc: "Stripe, Shopify, Twilio deprecate endpoints without clear migration paths. You find out in production." },
                { icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>, title: "Hours wasted on manual fixes", desc: "Teams spend 40+ hours per incident finding affected code, reading migration guides, and updating implementations." },
                { icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="20" x2="6" y2="20"/><path d="M12 4v16"/><path d="m6 12 6-6 6 6"/></svg>, title: "Revenue loss from downtime", desc: "A single broken payment integration can cost thousands per minute in lost transactions and customer trust." },
              ].map((p, i) => (
                <div key={i} className="lp-problem-card" ref={problems[i].ref} style={{ opacity: problems[i].visible ? 1 : 0, transform: problems[i].visible ? "translateY(0)" : "translateY(24px)", transition: `all 0.6s ease ${i * 0.15}s` }}>
                  <div className="lp-problem-icon">{p.icon}</div>
                  <h3 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 12px" }}>{p.title}</h3>
                  <p style={{ fontSize: 15, color: "var(--muted)", lineHeight: 1.6, margin: 0 }}>{p.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════ HOW IT WORKS ═══════ */}
        <section id="how-it-works" className="section" style={{ background: "var(--surface)" }} aria-labelledby="how-title">
          <div className="container">
            <div className="section-header">
              <h2 id="how-title" style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.2, margin: "0 0 12px" }}>How it works</h2>
              <p className="section-subheadline">Three steps from vulnerable to protected — zero maintenance.</p>
            </div>
            <div className="lp-steps-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24, maxWidth: 1200, margin: "0 auto" }}>
              {[
                { num: 1, title: "Connect your repo", desc: "Sign in with GitHub and select a repository. We scan your codebase for third-party API usage." },
                { num: 2, title: "We monitor changelogs", desc: "Our daily cron scrapes official changelogs. When a breaking change is published, we cross-reference it against your code." },
                { num: 3, title: "Get alerted instantly", desc: "Receive an email with the exact change, affected file, and line number — fix it before users notice." },
                { num: 4, title: "Auto-fix via PR", desc: "For high-confidence changes, Breaklytix opens a GitHub PR with the fix applied. Review, merge, done.", future: true },
              ].map((s, i) => (
                <div key={i} className={`lp-step-card ${s.future ? "future" : ""}`} ref={steps[i].ref} style={{ opacity: steps[i].visible ? 1 : 0, transform: steps[i].visible ? "translateY(0)" : "translateY(24px)", transition: `all 0.6s ease ${i * 0.15}s` }}>
                  <div className="lp-step-number">{s.num}</div>
                  <h3 style={{ fontSize: 17, fontWeight: 700, margin: "0 0 12px" }}>{s.title}{s.future && <span style={{ marginLeft: 8, padding: "2px 8px", background: "var(--amber-bg)", color: "var(--amber)", borderRadius: 999, fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>Phase 2</span>}</h3>
                  <p style={{ fontSize: 14, color: "var(--muted)", lineHeight: 1.6, margin: 0 }}>{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════ SUPPORTED APIs ═══════ */}
        <section id="apis" className="section" style={{ background: "var(--bg)" }} aria-labelledby="apis-title">
          <div className="container">
            <div className="section-header">
              <h2 id="apis-title" style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.2, margin: "0 0 12px" }}>Supported APIs</h2>
              <p className="section-subheadline">
                We detect and monitor <strong style={{ color: "var(--accent)" }}>{PROVIDER_REGISTRY.length}+ third-party APIs</strong> — payments, communication, cloud, AI, analytics, databases and more.
              </p>
            </div>
            <div ref={apisRef.ref} className="lp-apis-grid" style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 20, maxWidth: 1200, margin: "0 auto", opacity: apisRef.visible ? 1 : 0, transform: apisRef.visible ? "translateY(0)" : "translateY(24px)", transition: "all 0.6s ease" }}>
              {PROVIDER_REGISTRY.map((api) => {
                const color = categoryColor(api.category);
                return (
                  <div key={api.id} className="lp-api-card" style={{ opacity: 1 }}>
                    <div className="lp-api-logo" style={{ background: color }}>{api.displayName.charAt(0)}</div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>{api.displayName}</h3>
                    <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 600, background: "var(--green-bg)", color: "var(--green)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>{api.monitoringStatus === "supported" ? "Monitored" : "Detected"}</span>
                    <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>{capitalize(api.category)} · {api.detectionEnabled ? "Detection active" : "Detection ready"}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ═══════ PRICING ═══════ */}
        <section id="pricing" className="section" style={{ background: "var(--surface)" }} aria-labelledby="pricing-title">
          <div className="container">
            <div className="section-header">
              <h2 id="pricing-title" style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.2, margin: "0 0 12px" }}>Simple, transparent pricing</h2>
              <p className="section-subheadline">All plans include a 14-day free trial. No credit card required.</p>
            </div>
            <div className="lp-pricing-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24, maxWidth: 1000, margin: "0 auto", alignItems: "stretch" }}>
              {[
                { name: "Starter", price: "$500", period: "/mo", desc: "For small teams monitoring a few APIs", features: ["10 monitored APIs", "Detects all 44+ API providers", "Breaking change email alerts", "Auto-fix PRs (high confidence)", "Review UI for manual approval", "Weekly digest emails", "GitHub PR integration", "Email support"], cta: "Start free trial", popular: false },
                { name: "Growth", price: "$2,000", period: "/mo", desc: "For growing teams with multiple services", features: ["50 monitored APIs", "All Starter features", "Priority alert processing", "Custom webhook notifications", "Team collaboration (up to 5 seats)", "Usage analytics dashboard", "Priority email support"], cta: "Start free trial", popular: true },
                { name: "Enterprise", price: "$10,000", period: "/mo", desc: "For large organizations with unlimited needs", features: ["Unlimited monitored APIs", "All Growth features", "Dedicated support engineer", "Custom fix rule development", "Custom alert routing", "OAuth 2.0 sign-in", "Unlimited team seats"], cta: "Contact sales", popular: false },
              ].map((plan, i) => (
                <div key={i} className={`lp-pricing-card ${plan.popular ? "popular" : ""}`} ref={pricing[i].ref} style={{ opacity: pricing[i].visible ? 1 : 0, transform: pricing[i].visible ? "translateY(0)" : "translateY(24px)", transition: `all 0.6s ease ${i * 0.15}s` }}>
                  {plan.popular && <div style={{ position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)", padding: "4px 14px", background: "var(--accent)", color: "white", borderRadius: 999, fontSize: 12, fontWeight: 600, whiteSpace: "nowrap" }}>Most Popular</div>}
                  <div style={{ textAlign: "center", marginBottom: 24, paddingBottom: 24, borderBottom: "1px solid var(--border)" }}>
                    <h3 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 8px" }}>{plan.name}</h3>
                    <p style={{ fontSize: 14, color: "var(--muted)", margin: "0 0 16px" }}>{plan.desc}</p>
                    <div style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: 4 }}>
                      <span style={{ fontSize: 48, fontWeight: 800, lineHeight: 1 }}>{plan.price}</span>
                      <span style={{ fontSize: 16, color: "var(--muted)" }}>{plan.period}</span>
                    </div>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px", flex: 1 }}>
                    {plan.features.map((f) => (
                      <li key={f} className="lp-check">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                   <Link href="/dashboard" className={`btn ${plan.popular ? "btn-primary" : "btn-outline"} btn-block`} style={{ padding: "14px 24px", fontSize: 15, fontWeight: 600, borderRadius: 12 }}>
                    {plan.cta}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════ CTA SECTION ═══════ */}
        <section style={{ padding: "80px 24px" }} ref={cta.ref}>
          <div className="lp-cta-section" style={{ opacity: cta.visible ? 1 : 0, transform: cta.visible ? "translateY(0)" : "translateY(24px)", transition: "all 0.6s ease" }}>
            <div className="lp-cta-glow" />
            <div style={{ position: "relative", zIndex: 1, maxWidth: 600, margin: "0 auto" }}>
              <h2 style={{ fontSize: "clamp(28px, 4vw, 36px)", fontWeight: 800, color: "white", margin: "0 0 16px", lineHeight: 1.2 }}>Ready to stop losing hours to API breaking changes?</h2>
              <p style={{ fontSize: 18, color: "rgba(255,255,255,0.6)", margin: "0 0 32px", lineHeight: 1.6 }}>Monitor 12 provider changelogs, detect 44+ API usage patterns, and auto-fix breaking changes — no fabricated metrics.</p>
               <Link href="/dashboard" className="btn btn-primary btn-lg lp-glow-btn" style={{ fontSize: 16, padding: "16px 36px", background: "linear-gradient(135deg, var(--accent), #7c3aed)", border: "none", borderRadius: 12 }}>
                Get started — it&apos;s free
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* ═══════ FOOTER ═══════ */}
      <footer className="landing-footer">
        <div className="container">
          <div className="footer-grid">
            <div className="footer-brand">
              <Link href="/" className="brand" style={{ fontSize: 20, color: "white" }}><LogoMark size={30} withWordmark /></Link>
              <p className="footer-tagline">Detect. Alert. Fix. Automatically.</p>
            </div>
            <div className="footer-links">
              <div className="footer-column">
                <h4>Product</h4>
                <ul>
                  <li><Link href="#features">Features</Link></li>
                  <li><Link href="#apis">Supported APIs</Link></li>
                  <li><Link href="#pricing">Pricing</Link></li>
                   <li><Link href="/dashboard">Dashboard</Link></li>
                </ul>
              </div>
              <div className="footer-column">
                <h4>Legal</h4>
                <ul>
                  {LEGAL_LINKS.map((l) => (
                    <li key={l.href}><Link href={l.href}>{l.label}</Link></li>
                  ))}
                </ul>
              </div>
              <div className="footer-column">
                <h4>Contact</h4>
                <ul>
                  <li><a href="mailto:hashirattari73@gmail.com">hashirattari73@gmail.com</a></li>
                </ul>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; {new Date().getFullYear()} Breaklytix. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Scroll to top */}
      <ScrollToTop />
    </>
  );
}

function ScrollToTop() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 400);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <button className={`lp-scroll-top ${show ? "show" : ""}`} onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} aria-label="Scroll to top">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="18 15 12 9 6 15" /></svg>
    </button>
  );
}
