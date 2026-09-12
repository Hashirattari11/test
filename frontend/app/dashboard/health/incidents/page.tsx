"use client";

import { useEffect, useState } from "react";
import { getProviderIncidentsFeed, ProviderIncident } from "../../../../lib/api";
import { formatDate } from "../../../../components/ui";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<ProviderIncident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await getProviderIncidentsFeed();
        setIncidents(res.incidents || []);
      } catch {
        setIncidents([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div className="loading">Loading provider incidents…</div>;

  return (
    <div>
      <h1>Runtime Intelligence · Provider Incidents</h1>
      <p className="subtitle">
        Real incidents detected for your providers. Incidents are refreshed during scans.
      </p>

      {incidents.length === 0 ? (
        <div className="empty-state">
          <p>
            No active incidents recorded for your detected providers. Incidents are refreshed during scans.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {incidents.map((inc) => (
            <div
              key={inc.id}
              style={{ padding: 12, border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10 }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <span style={{ textTransform: "capitalize", fontWeight: 700 }}>{inc.provider}</span>
                  <span
                    style={{
                      marginLeft: 8,
                      padding: "2px 8px",
                      borderRadius: 999,
                      fontSize: 12,
                      background:
                        inc.status === "resolved"
                          ? "rgba(16,185,129,0.15)"
                          : inc.status === "active" || inc.status === "ongoing"
                            ? "rgba(239,68,68,0.15)"
                            : "rgba(245,158,11,0.15)",
                      color:
                        inc.status === "resolved"
                          ? "#10b981"
                          : inc.status === "active" || inc.status === "ongoing"
                            ? "#ef4444"
                            : "#f59e0b",
                    }}
                  >
                    {inc.status || "investigating"}
                  </span>
                </div>
                <span style={{ opacity: 0.5 }}>Started {formatDate(inc.started_at as string)}</span>
              </div>
              {inc.title && <p style={{ margin: "6px 0 0", fontWeight: 600 }}>{inc.title}</p>}
              {inc.impact && <p style={{ margin: "4px 0 0", fontSize: 13, opacity: 0.8 }}>{inc.impact}</p>}
              {inc.source_url && (
                <a
                  href={inc.source_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: 13, opacity: 0.7 }}
                >
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