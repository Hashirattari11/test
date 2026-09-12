"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getImpactSummary,
  ImpactSummary,
  listRepos,
  Repo,
  getImpactAnalyses,
  ImpactAnalysis,
  runFireDrill,
  analyzeChangelogEvent,
} from "../../../lib/api";
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

export default function ImpactPage() {
  const [summary, setSummary] = useState<ImpactSummary | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [analyses, setAnalyses] = useState<ImpactAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [analysesLoading, setAnalysesLoading] = useState(false);
  const [drillRunning, setDrillRunning] = useState(false);
  const [drillProvider, setDrillProvider] = useState("");
  const [drillResult, setDrillResult] = useState<ImpactAnalysis | null>(null);
  const [drillError, setDrillError] = useState("");

  useEffect(() => {
    Promise.all([getImpactSummary().catch(() => null), listRepos()])
      .then(([s, r]) => {
        setSummary(s);
        setRepos(r || []);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedRepo) {
      setAnalyses([]);
      return;
    }
    setAnalysesLoading(true);
    getImpactAnalyses(selectedRepo, 20)
      .then((res) => setAnalyses(res.analyses || []))
      .catch(() => setAnalyses([]))
      .finally(() => setAnalysesLoading(false));
  }, [selectedRepo]);

  const runDrill = async () => {
    if (!selectedRepo || !drillProvider.trim() || drillRunning) return;
    setDrillRunning(true);
    setDrillError("");
    setDrillResult(null);
    try {
      const result = await runFireDrill(selectedRepo, drillProvider.trim().toLowerCase());
      setDrillResult(result);
      // Refresh summary + analyses after drill
      const [s] = await Promise.all([getImpactSummary().catch(() => null)]);
      if (s) setSummary(s);
      const res = await getImpactAnalyses(selectedRepo, 20).catch(() => null);
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
        <Spinner /> Loading impact dataâ€¦
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ marginBottom: 4 }}>Impact Engine</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        What exactly will break in your code if a third-party API changes?{" "}
        <Link href="/docs/impact-overview" style={{ textDecoration: "none" }}>Learn more</Link>
      </p>

      {/* Summary cards */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 14, margin: "24px 0" }}>
        <SummaryCard label="Total Analyses" value={summary ? String(summary.total_analyses) : "â€”"} />
        <SummaryCard label="Affected Repos" value={summary ? String(summary.affected_repos) : "â€”"} />
        {Object.entries(summary?.by_severity || {}).map(([sev, count]) => (
          <SummaryCard
            key={sev}
            label={sev.toUpperCase()}
            value={String(count)}
            color={SEVERITY_COLORS[sev]}
          />
        ))}
      </div>

      {/* Recent analyses */}
      <section className="card" style={{ padding: 0, marginTop: 20 }}>
        <div style={{ padding: "16px 20px 0" }}>
          <h2 style={{ marginBottom: 4 }}>Recently Detected Changes</h2>
          <p className="muted small" style={{ marginTop: 0 }}>
            Impact analyses from detected provider changes.
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
            No impact analyses yet. Select a repository and run a Fire Drill.
          </div>
        )}
      </section>

      {/* Fire Drill */}
      <section className="card" style={{ padding: 20, marginTop: 20 }}>
        <h2 style={{ marginBottom: 4 }}>API Fire Drill</h2>
        <p className="muted small" style={{ marginTop: 0 }}>
          Before deployment, analyze a repository against known third-party API changes.
          Answer: "Is this deployment likely to break because of an external API?"
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
          <select
            className="input"
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            style={{ minWidth: 200 }}
          >
            <option value="">Select repositoryâ€¦</option>
            {repos.map((r) => (
              <option key={r.id} value={r.id}>{r.full_name}</option>
            ))}
          </select>
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
            disabled={!selectedRepo || !drillProvider.trim() || drillRunning}
          >
            {drillRunning ? "Running drillâ€¦" : "Run Fire Drill"}
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

      {/* Repo analyses */}
      {selectedRepo && (
        <section className="card" style={{ padding: 0, marginTop: 20 }}>
          <div style={{ padding: "16px 20px 0" }}>
            <h2 style={{ marginBottom: 4 }}>Analyses for Selected Repo</h2>
            <p className="muted small" style={{ marginTop: 0 }}>
              Impact analyses scoped to this repository.
            </p>
          </div>
          {analysesLoading ? (
            <div style={{ padding: 20 }}><Spinner /> Loadingâ€¦</div>
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