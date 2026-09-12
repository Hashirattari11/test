"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getHealthIssues,
  HealthIssue,
  listAllAlerts,
  AlertWithRepo,
} from "../../../../lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#84cc16",
};

export default function BreaksPage() {
  const [issues, setIssues] = useState<HealthIssue[]>([]);
  const [alerts, setAlerts] = useState<AlertWithRepo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getHealthIssues({ status: "open", limit: 500 }), listAllAlerts()])
      .then(([is, al]) => {
        setIssues(Array.isArray(is) ? is : []);
        setAlerts(Array.isArray(al) ? al : []);
      })
      .catch(() => {
        setIssues([]);
        setAlerts([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const criticalIssues = useMemo(
    () => issues.filter((i) => i.severity === "critical" || i.severity === "high"),
    [issues]
  );

  const breakAlerts = useMemo(
    () =>
      alerts.filter(
        (a) =>
          (a.severity === "critical" || a.severity === "high") &&
          a.change_type &&
          /breaking|remov|deprecat|moved|renamed|deleted/i.test(a.change_type)
      ),
    [alerts]
  );

  if (loading) return <div className="loading">Loading potential breaks…</div>;

  return (
    <div>
      <h1>Code Break Detection · Potential Breaks</h1>
      <p className="subtitle">Higher-risk findings that could break your code</p>

      <h2 style={{ fontSize: 18, margin: "8px 0" }}>Critical/high findings ({criticalIssues.length})</h2>
      {criticalIssues.length === 0 ? (
        <p style={{ opacity: 0.6 }}>No critical/high findings.</p>
      ) : (
        <div className="issues-list">
          {criticalIssues.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <span style={{ color: SEVERITY_COLOR[issue.severity] || "#6b7280", fontWeight: 700 }}>
                  {issue.severity.toUpperCase()}
                </span>
                <span className="issue-category">{issue.category}</span>
                <span className="issue-provider">{issue.provider}</span>
                {issue.risk_level && <span className={`issue-risk risk-${issue.risk_level}`}>Risk {issue.risk_level}</span>}
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
            </div>
          ))}
        </div>
      )}

      <h2 style={{ fontSize: 18, margin: "16px 0 8px" }}>Breaking-change alerts ({breakAlerts.length})</h2>
      {breakAlerts.length === 0 ? (
        <p style={{ opacity: 0.6 }}>No breaking-change alerts right now.</p>
      ) : (
        <div className="issues-list">
          {breakAlerts.map((a) => (
            <div key={a.id} className="issue-card">
              <div className="issue-header">
                <span style={{ color: SEVERITY_COLOR[a.severity] || "#6b7280", fontWeight: 700 }}>
                  {a.severity.toUpperCase()}
                </span>
                <span className="issue-provider">{a.provider || "api"} · {a.repo_name}</span>
              </div>
              <h3 className="issue-title">{a.change_type}</h3>
              {a.description && <p className="issue-description">{a.description}</p>}
              {a.file_path && (
                <p className="issue-location">
                  Affects: {a.file_path}
                  {a.line_number ? `:${a.line_number}` : ""}
                </p>
              )}
              {a.source_url && (
                <a href={a.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 13, opacity: 0.7 }}>
                  Source →
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      <p style={{ marginTop: 16 }}>
        <Link href="/dashboard/health/auto-fix" className="btn btn-primary">
          Review auto-fixes →
        </Link>
      </p>
    </div>
  );
}