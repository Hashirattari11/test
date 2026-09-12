"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { acceptConsent, getConsentStatus } from "../../lib/api";
import { clearSession, getUser } from "../../lib/auth";
import { Spinner } from "../../components/ui";

export default function LegalAcceptancePage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notAuthed, setNotAuthed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUser(); // ensure a session exists; route guard in dashboard layout handles redirects
    setLoading(false);
  }, []);

  async function handleAccept() {
    if (!checked || busy) return;
    setBusy(true);
    setError(null);
    try {
      const user = await acceptConsent("2026-09-10", "2026-09-10");
      if (user.consent_required === false) {
        router.replace("/dashboard");
        return;
      }
      setError("Consent was recorded but we could not confirm it. Please try again.");
    } catch (e: any) {
      setError(e?.message || "Could not save your consent. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRecheck() {
    setLoading(true);
    setError(null);
    try {
      const user = await getConsentStatus();
      if (user.consent_required === false) {
        router.replace("/dashboard");
        return;
      }
      setChecked(false);
    } catch (e: any) {
      setError(e?.message || "Could not check your consent status.");
      if (e?.status === 401) {
        clearSession();
        setNotAuthed(true);
      }
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="center-screen">
        <Spinner />
        <p className="muted">Checking consent status…</p>
      </div>
    );
  }

  return (
    <div className="center-screen">
      <div className="card" style={{ maxWidth: 520 }}>
        <LogoMark />
        <h2 style={{ marginTop: "1rem" }}>Update required</h2>
        <p className="muted">
          Before you continue, please review and accept our updated policies.
        </p>
        <ul style={{ margin: "0.5rem 0 1rem", paddingLeft: "1.2rem" }}>
          <li>
            <Link href="/privacy" target="_blank" rel="noopener noreferrer">
              Privacy Policy
            </Link>{" "}
            (effective 2026-09-10)
          </li>
          <li>
            <Link href="/terms" target="_blank" rel="noopener noreferrer">
              Terms of Service
            </Link>{" "}
            (effective 2026-09-10)
          </li>
        </ul>
        <label
          className="legal-check-row"
          style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", marginBottom: "1rem" }}
        >
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            disabled={busy}
            style={{ marginTop: "0.2rem" }}
          />
          <span>
            I have read and agree to the{" "}
            <Link href="/privacy" target="_blank" rel="noopener noreferrer">
              Privacy Policy
            </Link>{" "}
            and{" "}
            <Link href="/terms" target="_blank" rel="noopener noreferrer">
              Terms of Service
            </Link>
            .
          </span>
        </label>
        {error && <div className="error-box" style={{ marginBottom: "0.75rem" }}>{error}</div>}
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button className="btn" disabled={!checked || busy} onClick={handleAccept}>
            {busy ? "Saving…" : "Accept & Continue"}
          </button>
          <button className="btn btn-ghost" disabled={busy} onClick={handleRecheck}>
            Re-check status
          </button>
          <button
            className="btn btn-ghost"
            disabled={busy}
            onClick={() => {
              clearSession();
              router.replace("/dashboard");
            }}
          >
            Sign out
          </button>
        </div>
        {notAuthed && (
          <p className="muted" style={{ marginTop: "0.75rem" }}>
            Your session expired — <Link href="/dashboard">continue here</Link>.
          </p>
        )}
      </div>
    </div>
  );
}

function LogoMark() {
  return (
    <div
      style={{
        width: 40,
        height: 40,
        borderRadius: 10,
        background: "linear-gradient(135deg, #635bff 0%, #8b5cf6 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#fff",
        fontWeight: 800,
        fontSize: 18,
      }}
      aria-hidden
    >
      A
    </div>
  );
}