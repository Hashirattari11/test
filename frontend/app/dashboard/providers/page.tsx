"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { Spinner } from "@/components/ui";
import { getMonitoringMatrix, MonitoringProviderRow } from "@/lib/api";
import { getProvider, getAllProviderIds } from "@/lib/providers/registry";

function statusBadge(status?: string) {
  switch (status) {
    case "ACTIVE":
      return <span className="pill pill-green">Active</span>;
    case "LIMITED":
      return <span className="pill pill-amber">Limited</span>;
    case "SOURCE_UNAVAILABLE":
      return <span className="pill pill-gray">Source Unavailable</span>;
    case "ERROR":
      return <span className="pill pill-red">Error</span>;
    default:
      return <span className="pill pill-gray">{status || "Unknown"}</span>;
  }
}

export default function ProvidersPage() {
  const [rows, setRows] = useState<MonitoringProviderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await getMonitoringMatrix();
      setRows(res.providers || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to load monitoring matrix");
      setRows([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Ensure all 44 registry providers appear even if a row is missing.
  const merged: MonitoringProviderRow[] = (rows ?? []).slice();
  const seen = new Set(merged.map((r) => r.provider_id));
  for (const id of getAllProviderIds()) {
    if (!seen.has(id)) {
      const p = getProvider(id);
      merged.push({
        provider_id: id,
        display_name: p?.displayName || id,
        status: p?.monitoringStatus === "unavailable" ? "SOURCE_UNAVAILABLE" : "LIMITED",
        source_kind: "UNKNOWN",
        source_url: p?.changelogConfig?.changelogUrl || null,
        feed_url: p?.changelogConfig?.rssUrl || null,
      });
    }
  }
  merged.sort((a, b) => (a.display_name || a.provider_id).localeCompare(b.display_name || b.provider_id));

  const counts = merged.reduce<Record<string, number>>((acc, r) => {
    const k = r.status || "UNKNOWN";
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Provider Monitoring Matrix</h1>
          <p className="muted small" style={{ margin: 0 }}>
            Health of official-source monitoring across all 44 registered providers.
            ACTIVE = machine-readable feed, LIMITED = official page with strict extraction,
            SOURCE_UNAVAILABLE = no official change feed exists, ERROR = last fetch failed.
          </p>
        </div>
        <Link className="btn btn-secondary" href="/dashboard/changelog">
          Provider Changes
        </Link>
      </div>

      {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, margin: "16px 0" }}>
        {Object.entries(counts).map(([status, count]) => (
          <div key={status} className="card" style={{ padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{count}</div>
            <div className="muted small">{status.replace(/_/g, " ")}</div>
          </div>
        ))}
      </div>

      <section className="card" style={{ padding: 0 }}>
        {rows === null ? (
          <div style={{ padding: 20 }}><Spinner /> Loading monitoring matrix…</div>
        ) : (
          <table className="table responsive-cards">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Status</th>
                <th>Source kind</th>
                <th>Source</th>
                <th>Last fetch</th>
                <th>Last error</th>
              </tr>
            </thead>
            <tbody>
              {merged.map((r) => (
                <tr key={r.provider_id}>
                  <td data-label="Provider">
                    <span style={{ fontWeight: 600 }}>{r.display_name || r.provider_id}</span>
                    <div className="small muted">{r.provider_id}</div>
                  </td>
                  <td data-label="Status">{statusBadge(r.status)}</td>
                  <td data-label="Source kind">
                    <span className="pill pill-gray" style={{ fontSize: 11 }}>
                      {(r.source_kind || "UNKNOWN").replace(/_/g, " ")}
                    </span>
                  </td>
                  <td data-label="Source">
                    {r.source_url ? (
                      <a className="small" href={r.source_url} target="_blank" rel="noreferrer">
                        official page →
                      </a>
                    ) : (
                      <span className="muted small">—</span>
                    )}
                  </td>
                  <td data-label="Last fetch" className="muted small">
                    {r.last_fetch_at ? new Date(r.last_fetch_at).toLocaleString() : "never"}
                  </td>
                  <td data-label="Last error" className="muted small" style={{ maxWidth: 260 }}>
                    {r.last_error ? (
                      <span style={{ color: "#c0392b" }} title={r.last_error}>
                        {r.last_error.length > 60 ? `${r.last_error.slice(0, 60)}…` : r.last_error}
                      </span>
                    ) : (
                      <span>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}