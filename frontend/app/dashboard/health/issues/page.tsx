"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "../../../../lib/api";

interface Issue {
  id: string;
  provider: string;
  repo_id: string;
  category: string;
  severity: string;
  status: string;
  confidence: number;
  title: string;
  description: string;
  evidence: string;
  file: string | null;
  line: number | null;
  source: string;
  recommended_action: string;
  auto_fix_available: boolean;
  created_at: string;
  risk_level?: string;
  risk_score?: number;
  risk_factors?: string[];
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#84cc16",
  info: "#6b7280",
};

const CATEGORY_LABELS: Record<string, string> = {
  provider_problem: "Provider Problem",
  customer_code: "Code Issue",
  customer_usage: "Usage Issue",
  provider_incident: "Provider Incident",
  dependency: "Dependency",
  configuration: "Configuration",
  unknown: "Unknown",
};

export default function IssuesPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ status: "open" });
    if (severity) params.set("severity", severity);
    if (category) params.set("category", category);
    apiFetch(`/health/issues?${params}`)
      .then((res: any) => setIssues(Array.isArray(res) ? res : res.issues || []))
      .catch(() => setIssues([]))
      .finally(() => setLoading(false));
  }, [severity, category]);

  if (loading) return <div className="loading">Loading issues...</div>;

  return (
    <div className="issues-page">
      <h1>Reliability Issues</h1>
      <p className="subtitle">All open issues across your repositories</p>

      <div className="filters">
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="info">Info</option>
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All Categories</option>
          <option value="provider_problem">Provider Problem</option>
          <option value="customer_code">Code Issue</option>
          <option value="customer_usage">Usage Issue</option>
          <option value="provider_incident">Provider Incident</option>
          <option value="dependency">Dependency</option>
          <option value="configuration">Configuration</option>
        </select>
      </div>

      {issues.length === 0 ? (
        <div className="empty-state">
          <p>No open issues found.</p>
          <Link href="/dashboard/health" className="btn btn-primary">
            Back to Health Dashboard
          </Link>
        </div>
      ) : (
        <div className="issues-list">
          {issues.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <span className="issue-severity" style={{ color: SEVERITY_COLORS[issue.severity] || "#6b7280" }}>
                  {issue.severity.toUpperCase()}
                </span>
                {issue.risk_level && (
                  <span
                    className={`issue-risk risk-${issue.risk_level}`}
                    title={issue.risk_factors?.join(", ") || "Explainable risk score"}
                  >
                    Risk {issue.risk_level}
                    {typeof issue.risk_score === "number" ? ` · ${issue.risk_score}` : ""}
                  </span>
                )}
                <span className="issue-category">{CATEGORY_LABELS[issue.category] || issue.category}</span>
                <span className="issue-provider">{issue.provider}</span>
              </div>
              <h3 className="issue-title">{issue.title}</h3>
              <p className="issue-description">{issue.description}</p>
              {issue.file && (
                <p className="issue-location">
                  File: {issue.file}{issue.line ? `:${issue.line}` : ""}
                </p>
              )}
              <div className="issue-footer">
                <span className="issue-confidence">Confidence: {(issue.confidence * 100).toFixed(0)}%</span>
                {issue.auto_fix_available && <span className="issue-fix-badge">Auto-fix available</span>}
                <span className="issue-source">Source: {issue.source}</span>
              </div>
              {issue.recommended_action && (
                <p className="issue-action">Recommended: {issue.recommended_action}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}