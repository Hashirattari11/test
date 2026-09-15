"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listRepos,
  Repo,
  getImpactAnalyses,
  ImpactAnalysis,
  runFireDrill,
} from "../../../../lib/api";
import { Badge, severityTone, timeAgo } from "../../../../components/dashboard-ui";
import { Spinner } from "../../../../components/ui";

const SEVERITY_COLORS: Record<string, string> = {
  safe: "#22c55e",
  low: "#84cc16",
  medium: "#f59e0b",
  high: "#f97316",
  breaking: "#ef4444",
  unknown: "#6b7280",
};

// Common providers for quick selection
const COMMON_PROVIDERS = ["stripe", "openai", "anthropic", "twilio", "sendgrid", "supabase", "github", "shopify", "firebase", "slack", "resend", "vercel"];

export default function FireDrillPage() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [provider, setProvider] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ImpactAnalysis | null>(null);
  const [error, setError] = useState("");
  const [recentAnalyses, setRecentAnalyses] = useState<ImpactAnalysis[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRepos()
      .then((r) => setRepos(r || []))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const runDrill = async () => {
    if (!selectedRepo || !provider.trim() || running) return;
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const res = await runFireDrill(selectedRepo, provider.trim().toLowerCase());
      setResult(res);
      // Load recent analyses for this repo
      const analyses = await getImpactAnalyses(selectedRepo, 20).catch(() => null);
      if (analyses) setRecentAnalyses(analyses.analyses || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ padding: "40px 0" }}>
        <Spinner /> Loading…
      </div>
    );
  }

  return (
    <div>
      <Link href="/dashboard/impact" className="small muted" style={{ textDecoration: "none" }}>
        ← Back to Impact Engine
      </Link>
      <h1 style={{ margin: "8px 0 4px" }}>API Fire Drill</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        Before deployment, analyze your repository against known third-party API changes.
        Is this deployment likely to break because of an external API?
      </p>

      {/* Drill controls */}
      <section className="card" style={{ padding: 20, marginTop: 16 }}>
        <h2 style={{ marginTop: 0 }}>Run Fire Drill</h2>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <select
            className="input"
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            style={{ minWidth: 220 }}
          >
            <option value="">Select repository…</option>
            {repos.map((r) => (
              <option key={r.id} value={r.id}>{r.full_name}</option>
            ))}
          </select>
          <input
            className="input"
            placeholder="Provider (e.g. stripe)"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            style={{ minWidth: 160 }}
          />
          <button
            className="btn btn-primary"
            onClick={runDrill}
            disabled={!selectedRepo || !provider.trim() || running}
          >
            {running ? "Running drill…" : "Run Fire Drill"}
          </button>
        </div>
        <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
          <span className="muted small" style={{ marginRight: 4 }}>Quick pick:</span>
          {COMMON_PROVIDERS.map((p) => (
            <button
              key={p}
              className="pill"
              style={{
                cursor: "pointer",
                background: provider === p ? "var(--primary, #1a1a2e)" : "transparent",
                color: provider === p ? "#fff" : "var(--muted, #6b7280)",
                border: "1px solid var(--border, #e5e7eb)",
              }}
              onClick={() => setProvider(p)}
            >
              {p}
            </button>
          ))}
        </div>
        {error && <p style={{ color: "#ef4444", marginTop: 12 }}>{error}</p>}
      </section>

      {/* Drill result */}
      {result && (
        <section className="card" style={{ padding: 0, marginTop: 20 }}>
          <div style={{ padding: "16px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <h2 style={{ margin: 0 }}>Drill Result</h2>
              <Badge tone={severityTone(result.severity)}>{result.severity.toUpperCase()}</Badge>
              <span style={{ color: SEVERITY_COLORS[result.severity] || "#6b7280", fontWeight: 700 }}>
                {Math.round(result.confidence * 100)}% confidence
              </span>
            </div>
            <p className="muted small" style={{ margin: "8px 0 0" }}>
              Provider: <strong>{result.provider}</strong> · Change: {result.change_type.replace(/_/g, " ")}
            </p>

            {result.impact_reason && (
              <p style={{ marginTop: 12 }}><strong>Assessment:</strong> {result.impact_reason}</p>
            )}
            {result.potential_failure && (
              <p className="muted" style={{ marginTop: 4 }}><strong>Potential failure:</strong> {result.potential_failure}</p>
            )}

            {result.affected_files.length > 0 ? (
              <div style={{ marginTop: 16 }}>
                <strong className="small">Affected files:</strong>
                <ul style={{ margin: "6px 0 0", paddingLeft: 20 }}>
                  {result.affected_files.map((f, i) => (
                    <li key={i} className="small" style={{ marginBottom: 4 }}>
                      <code>{f.file_path}</code>
                      {f.line_number ? `:${f.line_number}` : ""}
                      {f.reason ? <span className="muted"> — {f.reason}</span> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="muted" style={{ marginTop: 16 }}>No affected files detected in this repository.</p>
            )}

            <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: "var(--bg-2, #f9fafb)", border: "1px solid var(--border, #e5e7eb)" }}>
              <span className="small muted">
                <strong>Verification:</strong>{" "}
                {result.verification_status === "verified"
                  ? "VERIFIED — fix passed verification checks."
                  : result.verification_status === "static_analysis"
                  ? "STATIC ANALYSIS — identified through static analysis only."
                  : result.verification_status === "verification_failed"
                  ? "VERIFICATION FAILED"
                  : "NOT VERIFIED"}
              </span>
              {result.source_url && (
                <span className="small muted" style={{ display: "block", marginTop: 6 }}>
                  Source: <a href={result.source_url} target="_blank" rel="noreferrer">{result.source_url.slice(0, 60)}…</a>
                </span>
              )}
            </div>

            <Link href={`/dashboard/impact/${result.id}`} className="btn btn-secondary" style={{ marginTop: 16 }}>
              Open Full Analysis
            </Link>
          </div>
        </section>
      )}

      {/* Recent analyses */}
      {recentAnalyses.length > 0 && (
        <section className="card" style={{ padding: 0, marginTop: 20 }}>
          <div style={{ padding: "16px 20px 0" }}>
            <h2 style={{ marginBottom: 4 }}>Recent Drill Results</h2>
            <p className="muted small" style={{ marginTop: 0 }}>Impact analyses from this repository.</p>
          </div>
          <table className="table responsive-cards">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Change</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Detected</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {recentAnalyses.map((a) => (
                <tr key={a.id}>
                  <td data-label="Provider"><strong>{a.provider}</strong></td>
                  <td data-label="Change" className="small">{a.change_type}</td>
                  <td data-label="Severity"><Badge tone={severityTone(a.severity)}>{a.severity.toUpperCase()}</Badge></td>
                  <td data-label="Confidence">{Math.round(a.confidence * 100)}%</td>
                  <td data-label="Detected" className="muted small">{timeAgo(a.detected_at)}</td>
                  <td>
                    <Link href={`/dashboard/impact/${a.id}`} className="btn btn-sm btn-secondary">Details</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}