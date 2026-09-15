"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  apiFetch,
  ApiError,
  listRepos,
  Repo,
  scanRepo,
  getUsageGraph,
  UsageGraph,
} from "../../../lib/api";

interface HealthOverview {
  score: number;
  status: string;
  repos: number;
  integrations: number;
  providers: Array<{ provider: string; score: number; status: string }>;
  issues: Record<string, number>;
}

const statusColor = (score: number) =>
  score >= 90 ? "#22c55e" : score >= 75 ? "#84cc16" : score >= 50 ? "#f59e0b" : score >= 25 ? "#f97316" : "#ef4444";

const statusLabel = (score: number) =>
  score >= 90 ? "Excellent" : score >= 75 ? "Healthy" : score >= 50 ? "Warning" : score >= 25 ? "At Risk" : "Critical";

export default function HealthPage() {
  const [data, setData] = useState<HealthOverview | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState("");
  const [graph, setGraph] = useState<UsageGraph | null>(null);
  const [graphError, setGraphError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadOverview = () =>
    apiFetch<HealthOverview>("/health/overview")
      .then(setData)
      .catch(() => setData(null));

  useEffect(() => {
    Promise.all([loadOverview(), listRepos()])
      .then(([, repoList]) => setRepos(repoList || []))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedRepo) {
      setGraph(null);
      setGraphError("");
      return;
    }
    setGraphError("");
    setGraph(null);
    getUsageGraph(selectedRepo)
      .then(setGraph)
      .catch((e) => setGraphError(String(e)));
  }, [selectedRepo]);

  const runScan = async () => {
    if (!selectedRepo || scanning) return;
    setScanning(true);
    // Progressive sub-steps while the real scan pipeline runs server-side.
    const scanStages = [
      "Fetching repository…",
      "Analyzing files…",
      "Detecting APIs…",
      "Checking SDKs / dependencies…",
      "Checking reliability…",
      "Generating health report…",
    ];
    let stage = 0;
    setScanMessage(scanStages[0]);
    const stageTimer = window.setInterval(() => {
      stage = Math.min(stage + 1, scanStages.length - 1);
      setScanMessage(scanStages[stage]);
    }, 1200);
    try {
      const result = await scanRepo(selectedRepo);
      window.clearInterval(stageTimer);
      let msg =
        `Scan complete: ${result.files_scanned} files, ${result.detections_found} detections` +
        ` (${result.apis_detected.join(", ") || "none"}). Health re-computed.`;
      if (result.plan_limit_exceeded && result.plan_warning) {
        msg = `${msg} Warning: ${result.plan_warning}`;
      }
      setScanMessage(msg);
      // Refresh everything with the new real data.
      await loadOverview();
      const repoList = await listRepos();
      setRepos(repoList || []);
      const g = await getUsageGraph(selectedRepo);
      setGraph(g);
    } catch (e) {
      window.clearInterval(stageTimer);
      const apiErr = e instanceof ApiError ? e : null;
      const raw = apiErr ? apiErr.message : String(e);
      let human = raw;
      if (!apiErr) {
        human = "Network error while reaching the backend — please retry.";
      } else if (apiErr.status === 500) {
        human = `Backend scanner error — please retry, and check the backend logs if it persists. (${raw})`;
      } else if (apiErr.status === 502) {
        human = `Backend could not reach GitHub or a provider: ${raw}`;
      } else if (apiErr.status === 404) {
        human = "Repository not found or no longer accessible from this account.";
      } else if (apiErr.status === 401) {
        human = "GitHub authorization has expired — please reconnect your GitHub account, then retry.";
      } else if (apiErr.status === 403) {
        human = `Access denied: ${raw}`;
      }
      setScanMessage(`Scan failed: ${human}`);
    } finally {
      setScanning(false);
    }
  };

  if (loading) return <div className="loading">Loading health data...</div>;
  if (!data) return <div className="error-state">Health data unavailable.</div>;

  const totalIssues = Object.values(data.issues || {}).reduce((a, b) => a + b, 0);
  const scoreColor = statusColor(data.score);
  const label = statusLabel(data.score);

  return (
    <div className="health-page">
      <h1>API Health</h1>
      <p className="subtitle">Reliability intelligence for all your API integrations</p>

      {/* Repo selector + real scan, inside Health */}
      <section className="scan-panel">
        <h2>Scan a repository</h2>
        <div className="scan-controls">
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            disabled={scanning}
          >
            <option value="">Select a connected repository…</option>
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.full_name}
                {r.last_scanned_at ? ` (scanned ${new Date(r.last_scanned_at).toLocaleDateString()})` : " (never scanned)"}
              </option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={runScan} disabled={!selectedRepo || scanning}>
            {scanning ? "Scanning…" : "Scan now"}
          </button>
          {repos.length === 0 && (
            <Link href="/dashboard/repos" className="btn btn-secondary">
              Connect a repository
            </Link>
          )}
        </div>
        {scanMessage && (
          <p className={scanMessage.startsWith("Scan failed") ? "usage-error" : "scan-message"}>{scanMessage}</p>
        )}
        {scanning && <div className="loading-inline">This pulls real code, manifests, and provider status data…</div>}
      </section>

      {/* Real usage graph for the selected repo */}
      {selectedRepo && graph && graph.integrations.length > 0 && (
        <section>
          <h2>Usage Graph — {graph.integrations.length} integration(s)</h2>
          <div className="usage-graph-list">
            {graph.integrations.map((it) => (
              <div key={it.provider} className="graph-integration">
                <div className="graph-header">
                  <span className="provider-name">{it.provider}</span>
                  <span className="graph-meta">
                    {it.methods.length} method(s) · {it.files.length} file(s)
                    {it.config_refs.length > 0 ? ` · ${it.config_refs.length} env ref(s)` : ""}
                  </span>
                </div>
                {it.methods.length > 0 && (
                  <p className="graph-methods">
                    <strong>SDK calls:</strong> {it.methods.join(", ")}
                  </p>
                )}
                {it.config_refs.length > 0 && (
                  <p className="graph-env">
                    <strong>Config (env var NAMES only):</strong> {it.config_refs.join(", ")}
                  </p>
                )}
                <table className="graph-table responsive-cards">
                  <thead>
                    <tr>
                      <th>Method / Endpoint</th>
                      <th>File</th>
                      <th>Line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {it.usage_points.map((pt, i) => (
                      <tr key={i}>
                        <td data-label="Method / Endpoint">{pt.method}</td>
                        <td data-label="File" className="mono">{pt.file}</td>
                        <td data-label="Line">{pt.line ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </section>
      )}
      {selectedRepo && !graph && !graphError && <p className="loading-inline">Loading usage graph…</p>}
      {graphError && <p className="usage-error">Usage graph unavailable: {graphError}</p>}
      {selectedRepo && graph && graph.integrations.length === 0 && (
        <p className="empty-state">No API detections in this repo yet — run a scan above to generate the usage graph.</p>
      )}

      <div className="health-overview-grid">
        <div className="health-score-card">
          <div className="score-circle" style={{ borderColor: scoreColor }}>
            <span className="score-value">{data.score}</span>
            <span className="score-label">{label}</span>
          </div>
          <p className="score-status" style={{ color: scoreColor }}>{label}</p>
        </div>

        <div className="health-stats">
          <div className="stat-card">
            <span className="stat-value">{data.repos}</span>
            <span className="stat-label">Repos Monitored</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{data.integrations}</span>
            <span className="stat-label">Integrations</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{totalIssues}</span>
            <span className="stat-label">Open Issues</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{data.issues.critical || 0}</span>
            <span className="stat-label">Critical</span>
          </div>
        </div>
      </div>

      <h2>Provider Health</h2>
      <div className="provider-grid">
        {data.providers.map((p) => (
          <div key={p.provider} className="provider-card">
            <div className="provider-header">
              <span className="provider-name">{p.provider}</span>
              <span className="provider-score" style={{ color: statusColor(p.score) }}>
                {p.score}
              </span>
            </div>
            <span className={`provider-status status-${p.status}`}>{p.status}</span>
          </div>
        ))}
        {data.providers.length === 0 && (
          <p className="empty-state">No provider data yet. Select a repository above and run a scan.</p>
        )}
      </div>

      <div className="health-actions">
        <Link href="/dashboard/health/issues" className="btn btn-primary">
          View All Issues
        </Link>
        <Link href="/dashboard/repos" className="btn btn-secondary">
          Manage Repositories
        </Link>
      </div>
    </div>
  );
}