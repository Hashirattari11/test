"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import RepositorySelector from "../../../../components/RepositorySelector";
import { getHealthRateLimit } from "../../../../lib/api";
import { formatDate } from "../../../../components/ui";

function RateLimitEventsContent() {
  const searchParams = useSearchParams();
  const repoId = searchParams.get("repository_id") ?? "";
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!repoId) { setEvents([]); setLoading(false); return; }
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
        <RepositorySelector />
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

export default function RateLimitEventsPage() {
  return <Suspense fallback={<div className="loading">Loading rate limit events…</div>}><RateLimitEventsContent /></Suspense>;
}
