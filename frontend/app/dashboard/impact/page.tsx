"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState, Suspense} from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  getImpactSummary,
  ImpactSummary,
  getImpactAnalyses,
  ImpactAnalysis,
  runFireDrill,
} from "../../../lib/api";
import RepositorySelector from "../../../components/RepositorySelector";
import { Badge, severityTone, timeAgo } from "../../../components/dashboard-ui";
import { Spinner } from "../../../components/ui";

const SEVERITY_COLORS: Record<string, string> = {
  safe: "var(--green, #22c55e)",
  low: "var(--lime, #84cc16)",
  medium: "var(--amber, #f59e0b)",
  high: "var(--orange, #f97316)",
  breaking: "var(--red, #ef4444)",
  unknown: "var(--muted, #6b7280)",
};

function ImpactPage() {
  const searchParams = useSearchParams();
  const repositoryId = searchParams.get("repository_id") ?? "";
  const [summary, setSummary] = useState<ImpactSummary | null>(null);
  const [analyses, setAnalyses] = useState<ImpactAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [analysesLoading, setAnalysesLoading] = useState(false);
  const [drillRunning, setDrillRunning] = useState(false);
  const [drillProvider, setDrillProvider] = useState("");
  const [drillResult, setDrillResult] = useState<ImpactAnalysis | null>(null);
  const [drillError, setDrillError] = useState("");

  const loadSummary = useCallback(() => {
    if (!repositoryId) {
      setSummary(null);
      // Keep the return type a Promise so .catch()/.finally() below typecheck.
      return Promise.resolve();
    }
    return getImpactSummary(repositoryId).catch(() => null).then(setSummary);
  }, [repositoryId]);

  useEffect(() => {
    setLoading(true);
    if (!repositoryId) {
      setLoading(false);
      return;
    }
    setSummary(null);
    loadSummary()
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [repositoryId, loadSummary]);

  useEffect(() => {
    if (!repositoryId) {
      setAnalyses([]);
      return;
    }
    setAnalysesLoading(true);
    setAnalyses([]); // clear previous repository's results while loading
    getImpactAnalyses(repositoryId, 20)
      .then((res) => setAnalyses(res.analyses || []))
      .catch(() => setAnalyses([]))
      .finally(() => setAnalysesLoading(false));
  }, [repositoryId]);

  const runDrill = async () => {
    if (!repositoryId || !drillProvider.trim() || drillRunning) return;
    setDrillRunning(true);
    setDrillError("");
    setDrillResult(null);
    try {
      const result = await runFireDrill(repositoryId, drillProvider.trim().toLowerCase());
      setDrillResult(result);
      // Refresh summary + analyses after drill
      loadSummary();
      const res = await getImpactAnalyses(repositoryId, 20).catch(() => null);
      if (res) setAnalyses(res.analyses || []);
    } catch (e) {
      setDrillError(String(e));
    } finally {
      setDrillRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ padding: "40px 0" }}>
        <Spinner /> Loading impact data…
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ marginBottom: 4 }}>Impact Engine</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        How could third-party API changes affect your code?{" "}
        <Link href="/docs/impact-overview" style={{ textDecoration: "none" }}>Learn more</Link>
      </p>

      <div style={{ margin: "16px 0" }}>
        <RepositorySelector />
      </div>

      {/* Summary cards (scoped to the selected repository) */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 14, margin: "24px 0" }}>
        <SummaryCard label="Total Analyses" value={summary ? String(summary.total_analyses) : "—"} />
        <SummaryCard label="Affected Repos" value={summary ? String(summary.affected_repos) : "—"} />
        {Object.entries(summary?.by_severity || {}).map(([sev, count]) => (
          <SummaryCard
            key={sev}
            label={sev.toUpperCase()}
            value={String(count)}
            color={SEVERITY_COLORS[sev]}
          />
        ))}
      </div>

      {/* Recent analyses (scoped) */}
      <section className="card" style={{ padding: 0, marginTop: 20 }}>
        <div style={{ padding: "16px 20px 0" }}>
          <h2 style={{ marginBottom: 4 }}>Recently Detected Changes</h2>
          <p className="muted small" style={{ marginTop: 0 }}>
            Impact analyses from detected provider changes, scoped to this repository.
          </p>
        </div>
        {summary && summary.recent_analyses.length > 0 ? (
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
              {summary.recent_analyses.map((a) => (
                <tr key={a.id}>
                  <td data-label="Provider"><strong>{a.provider}</strong></td>
                  <td data-label="Change" className="small">{a.change_type}</td>
                  <td data-label="Severity">
                    <Badge tone={severityTone(a.severity)}>{a.severity.toUpperCase()}</Badge>
                  </td>
                  <td data-label="Confidence">{Math.round(a.confidence * 100)}%</td>
                  <td data-label="Detected" className="muted small">{timeAgo(a.detected_at)}</td>
                  <td>
                    <Link href={`/dashboard/impact/${a.id}`} className="btn btn-sm btn-secondary">
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty" style={{ padding: 24 }}>
            No impact analyses for this repository yet. Run a Fire Drill below.
          </div>
        )}
      </section>

      {/* Fire Drill (scoped to the selected repository) */}
      <section className="card" style={{ padding: 20, marginTop: 20 }}>
        <h2 style={{ marginBottom: 4 }}>API Fire Drill</h2>
        <p className="muted small" style={{ marginTop: 0 }}>
          Before deployment, analyze the selected repository against known third-party API changes.
          Answer: "Is this deployment likely to break because of an external API?"
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
          <input
            className="input"
            placeholder="Provider (e.g. stripe, openai)"
            value={drillProvider}
            onChange={(e) => setDrillProvider(e.target.value)}
            style={{ minWidth: 160 }}
          />
          <button
            className="btn btn-primary"
            onClick={runDrill}
            disabled={!repositoryId || !drillProvider.trim() || drillRunning}
          >
            {drillRunning ? "Running drill…" : "Run Fire Drill"}
          </button>
        </div>

        {drillError && <p style={{ color: "var(--red, #ef4444)", marginTop: 12 }}>{drillError}</p>}

        {drillResult && (
          <div style={{ marginTop: 16, padding: 16, background: "var(--bg-2, #f9fafb)", borderRadius: 8, border: "1px solid var(--border, #e5e7eb)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <Badge tone={severityTone(drillResult.severity)}>{drillResult.severity.toUpperCase()}</Badge>
              <strong>{drillResult.provider}</strong>
              <span className="muted small">{drillResult.change_type}</span>
              <span className="muted small">Confidence: {Math.round(drillResult.confidence * 100)}%</span>
            </div>
            {drillResult.impact_reason && (
              <p style={{ marginTop: 8 }}>{drillResult.impact_reason}</p>
            )}
            {drillResult.affected_files.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <strong className="small">Affected files:</strong>
                <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                  {drillResult.affected_files.slice(0, 5).map((f, i) => (
                    <li key={i} className="small">{f.file_path}{f.line_number ? `:${f.line_number}` : ""}</li>
                  ))}
                </ul>
              </div>
            )}
            <Link href={`/dashboard/impact/${drillResult.id}`} className="btn btn-sm btn-secondary" style={{ marginTop: 12 }}>
              View Full Analysis
            </Link>
          </div>
        )}
      </section>

      {/* Repo analyses (scoped) */}
      {repositoryId && (
        <section className="card" style={{ padding: 0, marginTop: 20 }}>
          <div style={{ padding: "16px 20px 0" }}>
            <h2 style={{ marginBottom: 4 }}>Analyses for Selected Repo</h2>
            <p className="muted small" style={{ marginTop: 0 }}>
              Impact analyses scoped to this repository.
            </p>
          </div>
          {analysesLoading ? (
            <div style={{ padding: 20 }}><Spinner /> Loading…</div>
          ) : analyses.length === 0 ? (
            <div className="empty" style={{ padding: 24 }}>No analyses for this repo yet.</div>
          ) : (
            <table className="table responsive-cards">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Change</th>
                  <th>Severity</th>
                  <th>Confidence</th>
                  <th>Files</th>
                  <th>Detected</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((a) => (
                  <tr key={a.id}>
                    <td data-label="Provider"><strong>{a.provider}</strong></td>
                    <td data-label="Change" className="small">{a.change_type}</td>
                    <td data-label="Severity"><Badge tone={severityTone(a.severity)}>{a.severity.toUpperCase()}</Badge></td>
                    <td data-label="Confidence">{Math.round(a.confidence * 100)}%</td>
                    <td data-label="Files">{a.affected_files.length}</td>
                    <td data-label="Detected" className="muted small">{timeAgo(a.detected_at)}</td>
                    <td>
                      <Link href={`/dashboard/impact/${a.id}`} className="btn btn-sm btn-secondary">
                        Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="card" style={{ padding: "16px 18px", textAlign: "center" }}>
      <div style={{ fontSize: 26, fontWeight: 800, color: color || "var(--text, #1a1a2e)" }}>{value}</div>
      <div className="muted small" style={{ textTransform: "uppercase", letterSpacing: 0.5, marginTop: 2 }}>{label}</div>
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<div />}><ImpactPage /></Suspense>;
}
