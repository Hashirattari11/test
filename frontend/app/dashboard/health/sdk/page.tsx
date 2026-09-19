"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState, Suspense} from "react";
import { useSearchParams } from "next/navigation";
import RepositorySelector from "../../../../components/RepositorySelector";
import { getHealthIssues, HealthIssue } from "../../../../lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#84cc16",
  info: "#6b7280",
};

function SdkPage() {
  const searchParams = useSearchParams();
  const repositoryId = searchParams.get("repository_id") ?? "";
  const [issues, setIssues] = useState<HealthIssue[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!repositoryId) {
      // Never silently show ALL repositories' data before a repo is selected.
      setIssues([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setIssues([]); // clear previous repository's results while loading
    getHealthIssues({ category: "dependency", status: "open", limit: 200, repositoryId })
      .then((res) => setIssues(Array.isArray(res) ? res : []))
      .catch(() => setIssues([]))
      .finally(() => setLoading(false));
  }, [repositoryId]);

  useEffect(load, [load]);

  if (loading) return <div className="loading">Loading SDK checks…</div>;

  return (
    <div>
      <h1>Code Break Detection · SDK / Library Checker</h1>
      <p className="subtitle">
        Manifest-driven SDK version findings (package.json, requirements.txt, Gemfile…) — scoped to the selected repository
      </p>
      <div style={{ margin: "12px 0" }}>
        <RepositorySelector />
      </div>

      {issues.length === 0 ? (
        <div className="empty-state">
          <p>
            No SDK/dependency findings for this repository. Scan it with a manifest (for example package.json) to check
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
                {issue.repo_full_name && (
                  <span className="issue-provider" style={{ opacity: 0.7 }}>{issue.repo_full_name}</span>
                )}
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

export default function Page() {
  return <Suspense fallback={<div />}><SdkPage /></Suspense>;
}
