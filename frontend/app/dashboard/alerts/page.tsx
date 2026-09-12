"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertWithRepo, listAllAlerts, updateAlertStatus } from "@/lib/api";

import { formatDate, SeverityBadge, Spinner } from "@/components/ui";
import { ErrorCard, PageHeader } from "@/components/dashboard-ui";

export default function AlertsPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<AlertWithRepo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [repoFilter, setRepoFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("open");
  const [busyId, setBusyId] = useState<string | null>(null);

  const setStatus = async (id: string, status: "resolved" | "ignored") => {
    setBusyId(id);
    try {
      await updateAlertStatus(id, status);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to update alert");
    } finally {
      setBusyId(null);
    }
  };

  const load = useCallback(async () => {
    try {
      const a = await listAllAlerts();
      setAlerts(a);
    } catch (e: any) {
      setError(e.message || "Failed to load alerts");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const repos = alerts ? Array.from(new Set(alerts.map((a) => a.repo_name))).sort() : [];

  const filtered = (alerts ?? []).filter(
    (a) =>
      (severityFilter === "all" || a.severity === severityFilter) &&
      (repoFilter === "all" || a.repo_name === repoFilter) &&
      (statusFilter === "all" ||
        (statusFilter === "open"
          ? a.status !== "resolved" && a.status !== "ignored"
          : a.status === statusFilter))
  );

  return (
    <div className="p-page">
      <PageHeader
        title="Alerts"
        subtitle="Breaking changes matched to your code across all monitored repos, sorted by severity."
      />

      {error && <ErrorCard title="Could not load alerts" body={error} retry={load} />}

      <section className="card" style={{ padding: 0 }}>
        <div
          className="p-toolbar"
          style={{
            padding: "16px 20px 0",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div className="p-filters" style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div className="p-filter-group" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <label className="muted small" htmlFor="sevFilter" style={{ margin: 0 }}>Severity</label>
              <select
                id="sevFilter"
                className="input"
                style={{ width: "auto", padding: "6px 10px" }}
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
              >
                <option value="all">All</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            {repos.length > 0 && (
              <div className="p-filter-group" style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <label className="muted small" htmlFor="repoFilter" style={{ margin: 0 }}>Repo</label>
                <select
                  id="repoFilter"
                  className="input"
                  style={{ width: "auto", padding: "6px 10px" }}
                  value={repoFilter}
                  onChange={(e) => setRepoFilter(e.target.value)}
                >
                  <option value="all">All repos</option>
                  {repos.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="p-filter-group" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <label className="muted small" htmlFor="statusFilter" style={{ margin: 0 }}>Status</label>
              <select
                id="statusFilter"
                className="input"
                style={{ width: "auto", padding: "6px 10px" }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="open">Open</option>
                <option value="resolved">Resolved</option>
                <option value="ignored">Ignored</option>
                <option value="all">All</option>
              </select>
            </div>
          </div>
        </div>

        {alerts === null ? (
          <div style={{ padding: 20 }}><Spinner /> Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="empty" style={{ marginTop: 16 }}>
            {alerts.length === 0 ? "No alerts yet. You're all clear. 🎉" : "No alerts match the current filters."}
          </div>
        ) : (
          <div className="p-table-scroll">
            <table className="table responsive-cards">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Change</th>
                  <th>Repository</th>
                  <th>Affected location</th>
                  <th>Email</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.id}>
                    <td data-label="Severity">
                      <SeverityBadge severity={a.severity} reason={a.severity_reason} />
                    </td>
                    <td data-label="Change">
                      <span className="pill pill-amber" style={{ marginBottom: 4 }}>
                        {a.change_type.replace(/_/g, " ")}
                      </span>
                      <div className="small" style={{ marginTop: 4 }}>{a.description}</div>
                      {a.source_url && (
                        <a className="small" href={a.source_url} target="_blank" rel="noreferrer">
                          Changelog →
                        </a>
                      )}
                    </td>
                    <td data-label="Repository">
                      <Link className="small" href={`/dashboard/repos/${a.repo_id}`}>{a.repo_name}</Link>
                    </td>
                    <td data-label="Location">
                      {a.file_path ? (
                        <code style={{ whiteSpace: "normal", wordBreak: "break-word" }}>
                          {a.file_path}
                          {a.line_number ? `:${a.line_number}` : ""}
                        </code>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td data-label="Email">
                      {a.email_sent ? (
                        <span className="pill pill-green">Sent</span>
                      ) : (
                        <span className="pill pill-gray">Pending</span>
                      )}
                    </td>
                    <td data-label="Date" className="muted small">{formatDate(a.created_at)}</td>
                    <td data-label="Actions" className="p-card-actions">
                      {a.status === "resolved" || a.status === "ignored" ? (
                        <span className="pill pill-gray" style={{ textTransform: "capitalize" }}>{a.status}</span>
                      ) : (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            className="btn btn-secondary btn-small"
                            disabled={busyId === a.id}
                            onClick={() => setStatus(a.id, "resolved")}
                          >
                            Resolve
                          </button>
                          <button
                            className="btn btn-secondary btn-small"
                            disabled={busyId === a.id}
                            onClick={() => setStatus(a.id, "ignored")}
                          >
                            Ignore
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}