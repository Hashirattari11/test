"use client";

import { useEffect, useState } from "react";
import { getHealthRateLimit, listRepos, Repo } from "../../../../lib/api";
import { formatDate } from "../../../../components/ui";

export default function RateLimitEventsPage() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [repoId, setRepoId] = useState("");
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRepos()
      .then((rs) => {
        setRepos(rs);
        if (rs[0]) setRepoId(rs[0].id);
      })
      .catch(() => setRepos([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    getHealthRateLimit(repoId)
      .then((d) => setEvents(d.snapshots || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [repoId]);

  return (
    <div>
      <h1>Runtime &amp; Usage Intelligence · Rate Limit Events</h1>
      <p className="subtitle">Every recorded rate-limit snapshot as an event timeline</p>

      <div style={{ marginBottom: 16 }}>
        <label style={{ marginRight: 8, opacity: 0.7 }}>Repository</label>
        <select value={repoId} onChange={(e) => setRepoId(e.target.value)}>
          {repos.map((r) => (
            <option key={r.id} value={r.id}>
              {r.full_name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="loading">Loading rate limit events…</div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <p>No rate-limit events yet. Every repository scan records a real GitHub rate-limit snapshot.</p>
        </div>
      ) : (
        <div className="events-timeline" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {events.map((e, i) => {
            const pct =
              e.limit_value && e.remaining != null
                ? (1 - (e.remaining as number) / (e.limit_value as number)) * 100
                : null;
            return (
              <div
                key={i}
                style={{
                  padding: 12,
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 10,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <span style={{ textTransform: "capitalize", fontWeight: 700 }}>{e.provider as string}</span>
                  <span style={{ opacity: 0.5, marginLeft: 8 }}>{formatDate(e.recorded_at as string)}</span>
                </div>
                <div style={{ fontVariantNumeric: "tabular-nums" }}>
                  <span style={{ color: "#10b981" }}>
                    {typeof e.remaining === "number" ? e.remaining.toLocaleString() : "-"}
                  </span>
                  <span style={{ opacity: 0.5 }}> / {typeof e.limit_value === "number" ? e.limit_value.toLocaleString() : "-"} remaining</span>
                  {pct != null && (
                    <span
                      style={{
                        marginLeft: 10,
                        padding: "2px 8px",
                        borderRadius: 999,
                        fontSize: 12,
                        background: pct >= 80 ? "rgba(239,68,68,0.15)" : "rgba(16,185,129,0.15)",
                        color: pct >= 80 ? "#ef4444" : "#10b981",
                      }}
                    >
                      {pct.toFixed(1)}% used
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}