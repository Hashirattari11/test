"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  getTwinAnalyses,
  getTwinSummary,
  runTwinSimulation,
  TwinAnalysis,
  TwinRunResponse,
  TwinSummary,
} from "../../../lib/api";
import RepositorySelector from "../../../components/RepositorySelector";
import { Badge, BadgeTone, timeAgo } from "../../../components/dashboard-ui";

const STATUS_TONES: Record<string, BadgeTone> = {
  "BREAKING RISK": "red",
  "HIGH RISK": "red",
  "POTENTIAL IMPACT": "amber",
  SAFE: "green",
  "NO MATCH": "gray",
  UNKNOWN: "gray",
};

function statusTone(status: string | undefined): BadgeTone {
  return STATUS_TONES[status || ""] || "gray";
}

function DigitalTwinPage() {
  const searchParams = useSearchParams();
  const repositoryId = searchParams.get("repository_id") ?? "";
  const [summary, setSummary] = useState<TwinSummary | null>(null);
  const [analyses, setAnalyses] = useState<TwinAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<TwinRunResponse | null>(null);
  const [runError, setRunError] = useState("");

  const load = useCallback(() => {
    if (!repositoryId) {
      setSummary(null);
      setAnalyses([]);
      return Promise.resolve();
    }
    return Promise.all([
      getTwinSummary(repositoryId).catch(() => null),
      getTwinAnalyses(repositoryId, 100).catch(() => [] as TwinAnalysis[]),
    ]).then(([s, a]) => {
      setSummary(s);
      setAnalyses(a || []);
    });
  }, [repositoryId]);

  useEffect(() => {
    setLoading(true);
    setRunResult(null);
    setRunError("");
    load()
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [repositoryId, load]);

  const runSimulation = async () => {
    if (!repositoryId || running) return;
    setRunning(true);
    setRunError("");
    setRunResult(null);
    try {
      const res = await runTwinSimulation(repositoryId);
      setRunResult(res);
      await load();
    } catch (e) {
      setRunError(
        String(e).includes("404")
          ? "Digital Twin tables are not available yet — the database migration has not been applied."
          : String(e)
      );
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="container" style={{ padding: "20px 16px", maxWidth: 1000, margin: "0 auto" }}>
      <Link href="/dashboard" className="muted small" style={{ textDecoration: "none" }}>
        ← Back to Dashboard
      </Link>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between", margin: "8px 0 4px" }}>
        <h1 style={{ margin: 0 }}>⚡ API Digital Twin</h1>
        <div style={{ minWidth: 220 }}>
          <RepositorySelector value={repositoryId} onChange={() => { /* URL write triggers reload */ }} />
        </div>
      </div>
      <p className="muted" style={{ marginTop: 0 }}>
        Simulates real, already-detected provider changelog events against this repository&apos;s
        real scanned API usage — with exact file / symbol / line evidence and what to change.
        Static analysis only: labels never claim production is already failing.
      </p>

      {!repositoryId ? (
        <div className="card" style={{ padding: 20 }}>
          <p className="muted" style={{ margin: 0 }}>
            Select a repository to run a simulation. The Digital Twin is always repository-scoped.
          </p>
        </div>
      ) : (
        <>
          {/* Summary */}
          {loading ? (
            <div className="card" style={{ padding: 20 }}><span className="muted">Loading…</span></div>
          ) : (
            <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, margin: "14px 0" }}>
              <SummaryCard label="Provider Changes" value={summary ? String(summary.provider_changes) : "—"} />
              <SummaryCard label="Affected Usages" value={summary ? String(summary.affected_usages) : "—"} color="var(--amber, #f59e0b)" />
              <SummaryCard label="Potential Breaks" value={summary ? String(summary.potential_breaks) : "—"} color="var(--red, #ef4444)" />
              <SummaryCard label="Breaking Risk" value={summary ? String(summary.breaking_risk) : "—"} color="var(--red, #ef4444)" />
              <SummaryCard label="Safe" value={summary ? String(summary.safe) : "—"} color="var(--green, #22c55e)" />
            </div>
          )}

          {/* Run simulation */}
          <div className="card" style={{ padding: 16, marginBottom: 16 }}>
            <h2 style={{ marginTop: 0 }}>Run Future Simulation</h2>
            <p className="muted small" style={{ marginTop: 0 }}>
              Replays the latest real provider events (breaking changes, deprecations, security
              changes) against this repository&apos;s detected usage. Idempotent — re-running never
              duplicates evidence. One alert is created per affected event via the existing alerts
              pipeline.
            </p>
            <button className="btn btn-primary" onClick={runSimulation} disabled={running || !repositoryId}>
              {running ? "Simulating…" : "Run Future Simulation"}
            </button>
            {runError && (
              <p style={{ color: "var(--red, #ef4444)", marginBottom: 0, marginTop: 10 }}>{runError}</p>
            )}
            {runResult && (
              <div style={{ marginTop: 14, borderTop: "1px solid var(--border, #e5e7eb)", paddingTop: 12 }}>
                <b>Latest run:</b>{" "}
                {runResult.events_considered} event{runResult.events_considered !== 1 ? "s" : ""} considered ·{" "}
                {runResult.analyses_created} analysis row{runResult.analyses_created !== 1 ? "s" : ""} written ·{" "}
                {runResult.no_match_count} no-match ·{" "}
                {runResult.alerts_created} alert{runResult.alerts_created !== 1 ? "s" : ""} created
                {runResult.email_status && runResult.email_status !== "not_attempted" && (
                  <> · email: {runResult.email_status}{runResult.email_detail ? ` (${runResult.email_detail})` : ""}</>
                )}
                {runResult.findings.length === 0 && runResult.no_match_count > 0 && (
                  <p className="muted" style={{ marginBottom: 0 }}>
                    No affected usages found — this repository&apos;s scanned code does not use the
                    changed APIs. No evidence, no alerts: nothing fabricated.
                  </p>
                )}
                {runResult.findings.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <h3 style={{ margin: "0 0 6px" }}>WHAT YOU NEED TO CHANGE</h3>
                    {runResult.findings.slice(0, 10).map((f, i) => (
                      <div key={`${f.api_detection_id}-${i}`} className="card" style={{ padding: "10px 12px", marginBottom: 8 }}>
                        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                          <Badge tone={statusTone(f.impact_status)} dot>{f.impact_status}</Badge>
                          <code style={{ fontSize: 12 }}>
                            {f.affected_file || "Evidence not available"}
                            {f.line_number ? `:${f.line_number}` : ""}
                            {f.affected_symbol ? ` · ${f.affected_symbol}` : ""}
                          </code>
                          {typeof f.confidence === "number" && (
                            <span className="muted small">{Math.round(f.confidence * 100)}% confidence</span>
                          )}
                        </div>
                        <p style={{ margin: "6px 0 4px", fontSize: 13 }}>{f.explanation}</p>
                        {f.recommended_change && (
                          <p style={{ margin: 0, fontSize: 13 }}>
                            <b>Recommended change:</b> {f.recommended_change}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Persisted evidence table */}
          <div className="card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>Simulation Evidence</h2>
            <p className="muted small" style={{ marginTop: 0 }}>
              Persisted (repository, provider event, detected usage) matches from real runs.
              File / symbol / line fields come from real scan evidence — empty means evidence was
              not available, never guessed.
            </p>
            {analyses.length === 0 ? (
              <p className="muted" style={{ margin: 0 }}>
                No simulation evidence yet for this repository. Run a simulation above.
              </p>
            ) : (
              <table className="mc-table responsive-cards" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Provider</th>
                    <th>File / Evidence</th>
                    <th>Symbol</th>
                    <th>Line</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  {analyses.slice(0, 50).map((a) => (
                    <tr key={a.id}>
                      <td data-label="Status"><Badge tone={statusTone(a.impact_status)} dot>{a.impact_status}</Badge></td>
                      <td data-label="Provider">{a.provider_id}</td>
                      <td data-label="File" style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        <code style={{ fontSize: 12 }}>{a.affected_file || "Evidence not available"}</code>
                      </td>
                      <td data-label="Symbol">{a.affected_symbol || "—"}</td>
                      <td data-label="Line">{a.line_number ?? "—"}</td>
                      <td data-label="Severity">{a.severity}</td>
                      <td data-label="Confidence">{Math.round((a.confidence ?? 0) * 100)}%</td>
                      <td data-label="When" className="muted small" style={{ whiteSpace: "nowrap" }}>{a.created_at ? timeAgo(a.created_at) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {summary?.last_simulation && (
              <p className="muted small" style={{ marginBottom: 0, marginTop: 10 }}>
                Last simulation: {timeAgo(summary.last_simulation)}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="card" style={{ padding: "14px 16px", textAlign: "center" }}>
      <div style={{ fontSize: 24, fontWeight: 800, color: color || "var(--text, #1a1a2e)" }}>{value}</div>
      <div className="muted small" style={{ textTransform: "uppercase", letterSpacing: 0.5, marginTop: 2 }}>{label}</div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div />}>
      <DigitalTwinPage />
    </Suspense>
  );
}
