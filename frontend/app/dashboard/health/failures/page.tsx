"use client";

import { useEffect, useMemo, useState } from "react";
import { getHealthFailures, HealthIssue, updateHealthIssueStatus } from "../../../../lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#84cc16",
  info: "#6b7280",
};

export default function FailuresPage() {
  const [issues, setIssues] = useState<HealthIssue[]>([]);
  const [summary, setSummary] = useState<{ total: number; customer_code: number; provider_incident: number }>({
    total: 0,
    customer_code: 0,
    provider_incident: 0,
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    getHealthFailures(500)
      .then((res) => {
        setIssues(Array.isArray(res.failures) ? res.failures : []);
        setSummary({ total: res.total, customer_code: res.customer_code, provider_incident: res.provider_incident });
      })
      .catch(() => {
        setIssues([]);
        setSummary({ total: 0, customer_code: 0, provider_incident: 0 });
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const failures = useMemo(
    () => issues.filter((i) => i.category === "customer_code" || i.category === "provider_incident"),
    [issues]
  );

  const resolve = async (id: string) => {
    setBusy(id);
    try {
      await updateHealthIssueStatus(id, "resolved");
      load();
    } catch {
      /* ignore */
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <div className="loading">Loading failures…</div>;

  return (
    <div>
      <h1>Runtime &amp; Usage Intelligence · Failures</h1>
      <p className="subtitle">Code-side failures and provider incidents affecting your repos</p>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: -8 }}>
        {summary.total} open failure{summary.total !== 1 ? "s" : ""} · {summary.customer_code} code-side · {summary.provider_incident} provider
      </p>

      {failures.length === 0 ? (
        <div className="empty-state">
          <p>No failures recorded.</p>
        </div>
      ) : (
        <div className="issues-list">
          {failures.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <span style={{ color: SEVERITY_COLOR[issue.severity] || "#6b7280", fontWeight: 700 }}>
                  {issue.severity.toUpperCase()}
                </span>
                <span className="issue-category">{issue.category}</span>
                <span className="issue-provider">{issue.provider}</span>
              </div>
              <h3 className="issue-title">{issue.title}</h3>
              <p className="issue-description">{issue.description}</p>
              {issue.file && (
                <p className="issue-location">
                  File: {issue.file}
                  {issue.line ? `:${issue.line}` : ""}
                </p>
              )}
              {issue.recommended_action && <p className="issue-action">Recommended: {issue.recommended_action}</p>}
              <div className="issue-footer">
                <span className="issue-confidence">Confidence: {Math.round((issue.confidence || 0) * 100)}%</span>
                <span className="issue-source">Source: {issue.source}</span>
              </div>
              <div style={{ marginTop: 10 }}>
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