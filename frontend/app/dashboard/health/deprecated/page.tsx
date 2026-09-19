"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useMemo, useState, Suspense} from "react";
import { useSearchParams } from "next/navigation";
import RepositorySelector from "../../../../components/RepositorySelector";
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

function DeprecatedPage() {
  const searchParams = useSearchParams();
  const repositoryId = searchParams.get("repository_id") ?? "";
  const [issues, setIssues] = useState<HealthIssue[]>([]);
  const [alerts, setAlerts] = useState<AlertWithRepo[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!repositoryId) {
      // Never silently show ALL repositories' data before a repo is selected.
      setIssues([]);
      setAlerts([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setIssues([]); // clear previous repository's results while loading
    setAlerts([]);
    Promise.all([
      getHealthIssues({ status: "open", limit: 500, repositoryId }),
      listAllAlerts(repositoryId),
    ])
      .then(([is, al]) => {
        setIssues(Array.isArray(is) ? is : []);
        setAlerts(Array.isArray(al) ? al : []);
      })
      .catch(() => {
        setIssues([]);
        setAlerts([]);
      })
      .finally(() => setLoading(false));
  }, [repositoryId]);

  useEffect(load, [load]);

  const engineFindings = useMemo(
    () => issues.filter((i) => i.category === "configuration" || i.category === "dependency"),
    [issues]
  );

  const changelogFindings = useMemo(
    () =>
      alerts.filter(
        (a) =>
          a.change_type &&
          (a.change_type.toLowerCase().includes("deprecat") ||
            a.change_type.toLowerCase().includes("remov") ||
            a.change_type.toLowerCase().includes("retire"))
      ),
    [alerts]
  );

  if (loading) return <div className="loading">Loading deprecated APIs…</div>;

  return (
    <div>
      <h1>Code Break Detection · Deprecated APIs</h1>
      <p className="subtitle">
        Engine findings + changelog notices about deprecated/removed APIs — scoped to the selected repository
      </p>
      <div style={{ margin: "12px 0" }}>
        <RepositorySelector />
      </div>

      <h2 style={{ fontSize: 18, margin: "8px 0" }}>Engine findings ({engineFindings.length})</h2>
      {engineFindings.length === 0 ? (
        <p style={{ opacity: 0.6 }}>No configuration/dependency findings for this repository.</p>
      ) : (
        <div className="issues-list">
          {engineFindings.map((issue) => (
            <div key={issue.id} className="issue-card">
              <div className="issue-header">
                <span style={{ color: SEVERITY_COLOR[issue.severity] || "#6b7280", fontWeight: 700 }}>
                  {issue.severity.toUpperCase()}
                </span>
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
            </div>
          ))}
        </div>
      )}

      <h2 style={{ fontSize: 18, margin: "16px 0 8px" }}>Changelog notices ({changelogFindings.length})</h2>
      {changelogFindings.length === 0 ? (
        <p style={{ opacity: 0.6 }}>No deprecation notices for this repository.</p>
      ) : (
        <div className="issues-list">
          {changelogFindings.map((a) => (
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
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<div />}><DeprecatedPage /></Suspense>;
}
