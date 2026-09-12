"use client";

import { useEffect, useState } from "react";
import { getHealthIssues, HealthIssue } from "../../../../lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#84cc16",
  info: "#6b7280",
};

export default function SdkPage() {
  const [issues, setIssues] = useState<HealthIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHealthIssues({ category: "dependency", status: "open", limit: 200 })
      .then((res) => setIssues(Array.isArray(res) ? res : []))
      .catch(() => setIssues([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading SDK checks…</div>;

  return (
    <div>
      <h1>Code Break Detection · SDK / Library Checker</h1>
      <p className="subtitle">
        Manifest-driven SDK version findings (package.json, requirements.txt, Gemfile…) for your detected APIs
      </p>

      {issues.length === 0 ? (
        <div className="empty-state">
          <p>
            No SDK/dependency findings. Scan a repository with a manifest (for example package.json) to check
            installed SDK versions against supported majors (Stripe 18, SendGrid 8, Supabase 2…).
          </p>
        </div>
      ) : (
        <div className="issues-list">
          {issues.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <span style={{ color: SEVERITY_COLOR[issue.severity] || "#6b7280", fontWeight: 700 }}>
                  {issue.severity.toUpperCase()}
                </span>
                <span className="issue-category">dependency</span>
                <span className="issue-provider">{issue.provider}</span>
              </div>
              <h3 className="issue-title">{issue.title}</h3>
              <p className="issue-description">{issue.description}</p>
              {issue.evidence && (
                <p style={{ fontFamily: "monospace", fontSize: 13, opacity: 0.7 }}>{issue.evidence}</p>
              )}
              {issue.recommended_action && <p className="issue-action">Recommended: {issue.recommended_action}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}