"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import RepositorySelector from "../../../../components/RepositorySelector";
import { getHealthAnomalies, HealthIssue } from "../../../../lib/api";
import { formatDate } from "../../../../components/ui";

export default function AnomaliesPage() {
  const searchParams = useSearchParams();
  const repositoryId = searchParams.get("repository_id") ?? "";
  const [issues, setIssues] = useState<HealthIssue[]>([]);
  const [summary, setSummary] = useState<{ total: number; critical: number; high: number }>({
    total: 0,
    critical: 0,
    high: 0,
  });
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!repositoryId) {
      // Never silently show ALL repositories' data before a repo is selected.
      setIssues([]);
      setSummary({ total: 0, critical: 0, high: 0 });
      setLoading(false);
      return;
    }
    setLoading(true);
    setIssues([]); // clear previous repository's results while loading
    getHealthAnomalies(500, repositoryId)
      .then((res) => {
        setIssues(Array.isArray(res.anomalies) ? res.anomalies : []);
        setSummary({ total: res.total, critical: res.critical, high: res.high });
      })
      .catch(() => {
        setIssues([]);
        setSummary({ total: 0, critical: 0, high: 0 });
      })
      .finally(() => setLoading(false));
  }, [repositoryId]);

  useEffect(load, [load]);

  const anomalies = useMemo(
    () => issues.filter((i) => i.risk_level === "high" || i.risk_level === "critical"),
    [issues]
  );

  if (loading) return <div className="loading">Loading anomalies…</div>;

  return (
    <div>
      <h1>Runtime &amp; Usage Intelligence · Anomalies</h1>
      <p className="subtitle">Findings flagged with high/critical explainable risk — scoped to the selected repository</p>
      <div style={{ margin: "12px 0" }}>
        <RepositorySelector />
      </div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: -8 }}>
        {summary.total} open anomaly{summary.total !== 1 ? "ies" : ""} · {summary.critical} critical · {summary.high} high
      </p>

      {anomalies.length === 0 ? (
        <div className="empty-state">
          <p>No high-risk anomalies for this repository.</p>
          <Link href="/dashboard/health/issues" className="btn btn-primary">
            View all issues
          </Link>
        </div>
      ) : (
        <div className="issues-list">
          {anomalies.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <span className={`issue-risk risk-${issue.risk_level}`}>
                  Risk {issue.risk_level}
                  {typeof issue.risk_score === "number" ? ` · ${issue.risk_score}` : ""}
                </span>
                <span className="issue-category">{issue.category}</span>
                <span className="issue-provider">{issue.provider}</span>
                {issue.repo_full_name && (
                  <span className="issue-provider" style={{ opacity: 0.7 }}>{issue.repo_full_name}</span>
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
              {issue.risk_factors && issue.risk_factors.length > 0 && (
                <p style={{ fontSize: 13, opacity: 0.75 }}>Factors: {issue.risk_factors.join(", ")}</p>
              )}
              <div className="issue-footer">
                <span className="issue-confidence">Confidence: {Math.round((issue.confidence || 0) * 100)}%</span>
                <span className="issue-source">Created {formatDate(issue.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}