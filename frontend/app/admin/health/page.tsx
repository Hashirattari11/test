"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAdminHealth, HealthRow } from "../../../lib/admin";
import { formatDate, Spinner } from "../../../components/ui";

export default function AdminHealthPage() {
  const router = useRouter();
  const [rows, setRows] = useState<HealthRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminHealth()
      .then((r) => setRows(r.rows))
      .catch((e) => setError(e?.message || "Failed to load health"));
  }, []);

  if (error) {
    return (
      <main className="container page">
        <h1>System Health</h1>
        <p className="muted">Could not load health (admin-only). {error}</p>
      </main>
    );
  }

  if (rows === null) {
    return (
      <main className="container page" style={{ textAlign: "center", paddingTop: 80 }}>
        <Spinner /> Loading…
      </main>
    );
  }

  return (
    <main className="container page">
      <div className="row" style={{ marginBottom: 24, alignItems: "center" }}>
        <div>
          <h1>System Health</h1>
          <p className="muted" style={{ margin: 0 }}>
            Recent background job runs (fetching, processing, alerts), newest first.
          </p>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="card" style={{ padding: 32, textAlign: "center" }}>
          <p className="muted" style={{ margin: 0 }}>
            No health records yet. Background jobs will populate this table as they run.
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table className="table responsive-cards" style={{ minWidth: 700 }}>
            <thead>
              <tr>
                <th>Job</th>
                <th>Status</th>
                <th>Duration (ms)</th>
                <th>Error</th>
                <th>Ran At</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id || `${r.job_name}-${r.ran_at}`}>
                  <td data-label="Job">{r.job_name}</td>
                  <td data-label="Status">
                    <span
                      className={`badge badge-${r.status === "ok" ? "success" : "danger"}`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td data-label="Duration (ms)">{r.duration_ms ?? "—"}</td>
                  <td data-label="Error" className="muted">{r.error_message || "—"}</td>
                  <td data-label="Ran At" className="muted">{r.ran_at ? formatDate(r.ran_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
