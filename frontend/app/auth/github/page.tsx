"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { buildGithubAuthUrl } from "../../../lib/api";
import { SITE_URL } from "../../../lib/site";

/**
 * /auth/github — Starts the GitHub OAuth dance.
 * Pins a one-time CSRF `state` (kept in session storage, read back on /auth/callback)
 * then redirects to GitHub's authorize endpoint. Keeps the callback on the same origin.
 */
export default function AuthGithubClient() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function start() {
      const state =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : Math.random().toString(36).slice(2);
      try {
        sessionStorage.setItem("autofix_oauth_state", state);
      } catch {
        /* sessionStorage unavailable — OAuth still proceeds (state is advisory) */
      }
      // GitHub OAuth Apps allow exactly ONE callback URL, so the redirect_uri
      // must be the canonical production one regardless of which origin the
      // user started from (vercel.app previews would otherwise trigger
      // GitHub's redirect_uri_mismatch). Localhost keeps its own origin so
      // local dev can use a dedicated localhost OAuth app.
      const isLocal = /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
      const redirectUri = (isLocal ? window.location.origin : SITE_URL) + "/auth/callback";
      window.location.replace(buildGithubAuthUrl(redirectUri, state));
    }
    try {
      start();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach GitHub.");
    }
  }, []);

  if (error) {
    return (
      <AuthShell>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Could not start GitHub sign-in</h1>
        <p style={{ color: "var(--muted)", fontSize: 14, lineHeight: 1.6, margin: "10px 0 20px" }}>{error}</p>
        <Link href="/login" className="btn btn-primary" style={{ borderRadius: 10, padding: "12px 22px" }}>Back to login</Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <div className="auth-spinner" aria-hidden="true" />
      <p style={{ color: "var(--muted)", fontSize: 14 }}>Redirecting to GitHub…</p>
    </AuthShell>
  );
}

function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="lp-login-wrap">
      <div className="lp-card" style={{ textAlign: "center", padding: "44px 28px" }}>{children}</div>
    </div>
  );
}