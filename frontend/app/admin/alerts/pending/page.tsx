"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getPendingAlerts,
  approveAlert,
  rejectAlert,
  PendingAlert,
} from "../../../../lib/admin";
import { formatDate, Spinner } from "../../../../components/ui";

function badgeTone(severity?: string | null) {
  switch (severity) {
    case "critical":
    case "high":
      return "danger";
    case "medium":
      return "warn";
    default:
      return "neutral";
  }
}

function SeverityBadge({ severity }: { severity?: string | null }) {
  return (
    <span className={`badge badge-${badgeTone(severity)}`}>{severity || "n/a"}</span>
  );
}

export default function AdminPendingAlertsPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<PendingAlert[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(() => {
    getPendingAlerts()
      .then((r) => setAlerts(r.alerts))
      .catch((e) => setError(e?.message || "Failed to load queue"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleApprove(id: string) {
    setBusyId(id);
    setMessage(null);
    try {
      const r = await approveAlert(id);
      setMessage(r.email_sent ? `Alert approved & email sent.` : "Alert approved (email failed).");
      load();
    } catch (e) {
      setMessage(`Approve failed: ${e instanceof Error ? e.message : "error"}`);
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(id: string) {
    setBusyId(id);
    setMessage(null);
    try {
      await rejectAlert(id);
      setMessage("Alert rejected (dismissed).");
      load();
    } catch (e) {
      setMessage(`Reject failed: ${e instanceof Error ? e.message : "error"}`);
    } finally {
      setBusyId(null);
    }
  }

  if (error) {
    return (
      <main className="container page">
        <h1>Alert Approval Queue</h1>
        <p className="muted">Could not load the queue (admin-only).</p>
        <p className="muted">{error}</p>
      </main>
    );
  }

  if (alerts === null) {
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
          <h1>Alert Approval Queue</h1>
          <p className="muted" style={{ margin: 0 }}>
            Real (non-test) alerts awaiting approval. Approving sends the alert email and marks it sent; rejecting dismisses it.
          </p>
        </div>
      </div>

      {message && (
        <div className="alert" style={{ marginBottom: 16 }}>
          {message}
        </div>
      )}

      {alerts.length === 0 ? (
        <div className="card" style={{ padding: 32, textAlign: "center" }}>
          <p style={{ margin: 0, fontSize: 16 }}>No alerts awaiting approval.</p>
          <p className="muted" style={{ margin: 0 }}>
            When a real breaking change is detected on a monitored provider, it will appear here for review.
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table className="table responsive-cards" style={{ minWidth: 900 }}>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Repo / Customer</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Email Preview</th>
                <th>Created</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td data-label="Provider">{a.provider || a.api_name || "—"}</td>
                  <td data-label="Repo / Customer">
                    <div>{a.repo_name || "—"}</div>
                    <div className="muted">{a.customer_email || "no email"}</div>
                  </td>
                  <td data-label="Severity">
                    <SeverityBadge severity={a.severity} />
                  </td>
                  <td data-label="Confidence">{a.confidence || "—"}</td>
                  <td data-label="Email Preview">
                    <div style={{ maxWidth: 320 }}>
                      {a.subject && <div style={{ fontWeight: 600 }}>{a.subject}</div>}
                      {a.preview && <div className="muted" style={{ fontSize: 12 }}>{a.preview}</div>}
                      {a.evidence && <div className="muted" style={{ fontSize: 12 }}>📎 {a.evidence}</div>}
                    </div>
                  </td>
                  <td data-label="Created" className="muted">{a.created_at ? formatDate(a.created_at) : "—"}</td>
                  <td data-label="Actions" style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={busyId === a.id}
                      onClick={() => handleApprove(a.id)}
                    >
                      Approve
                    </button>{" "}
                    <button
                      className="btn btn-secondary btn-sm"
                      disabled={busyId === a.id}
                      onClick={() => handleReject(a.id)}
                    >
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
