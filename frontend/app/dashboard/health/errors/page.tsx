"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  createIssueFix,
  getHealthErrors,
  HealthIssue,
  updateHealthIssueStatus,
} from "../../../../lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#84cc16",
  info: "#6b7280",
};

export default function ErrorsPage() {
  const [issues, setIssues] = useState<HealthIssue[]>([]);
  const [summary, setSummary] = useState<{ total: number; critical: number; high: number }>({
    total: 0,
    critical: 0,
    high: 0,
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    getHealthErrors(500)
      .then((res) => {
        setIssues(Array.isArray(res.errors) ? res.errors : []);
        setSummary({ total: res.total, critical: res.critical, high: res.high });
      })
      .catch(() => {
        setIssues([]);
        setSummary({ total: 0, critical: 0, high: 0 });
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const errors = useMemo(
    () => issues.filter((i) => (i.severity === "critical" || i.severity === "high") && (i.category || "") !== "provider_incident"),
    [issues]
  );

  const resolve = async (id: string) => {
    setBusy(id);
    try {
      await updateHealthIssueStatus(id, "resolved");
      load();
    } catch {
      /* toast-free */
    } finally {
      setBusy(null);
    }
  };

  const queueFix = async (id: string) => {
    setBusy(id);
    try {
      await createIssueFix(id);
      alert("Auto-fix queued — see Code Break Detection → Auto-Fix PRs to review/approve.");
    } catch (e) {
      alert(`Could not queue fix: ${String(e)}`);
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <div className="loading">Loading API errors…</div>;

  return (
    <div>
      <h1>Runtime &amp; Usage Intelligence · API Errors</h1>
      <p className="subtitle">High/critical reliability findings across your repositories</p>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: -8 }}>
        {summary.total} open error{summary.total !== 1 ? "s" : ""} · {summary.critical} critical · {summary.high} high
      </p>

      {errors.length === 0 ? (
        <div className="empty-state">
          <p>No high-severity API errors right now. Nice.</p>
          <Link href="/dashboard/health/issues" className="btn btn-primary">
            View all issues
          </Link>
        </div>
      ) : (
        <div className="issues-list">
          {errors.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <span style={{ color: SEVERITY_COLOR[issue.severity] || "#6b7280", fontWeight: 700 }}>
                  {issue.severity.toUpperCase()}
                </span>
                <span className="issue-category">{issue.category}</span>
                <span className="issue-provider">{issue.provider}</span>
                {issue.risk_level && (
                  <span className={`issue-risk risk-${issue.risk_level}`}>Risk {issue.risk_level}</span>
                )}
              </div>
              <h3 className="issue-title">{issue.title}</h3>
              <p className="issue-description">{issue.description}</p>
              {issue.file && (
                <p className="issue-location">
                  File: {issue.file}
                  {issue.line ? `:${issue.line}` : ""}
                </p>
              )}
              <div className="issue-footer">
                <span className="issue-confidence">Confidence: {Math.round((issue.confidence || 0) * 100)}%</span>
                <span className="issue-source">Source: {issue.source}</span>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                {issue.auto_fix_available && (
                  <button className="btn btn-sm btn-primary" disabled={busy === issue.id} onClick={() => queueFix(issue.id)}>
                    Queue fix
                  </button>
                )}
                <button className="btn btn-sm btn-secondary" disabled={busy === issue.id} onClick={() => resolve(issue.id)}>
                  Mark resolved
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}