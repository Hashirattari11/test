"use client";

import { useEffect, useState } from "react";
import { getDetections, listRepos, Repo } from "../../../../lib/api";

const STATUS_COLOR: Record<string, string> = {
  monitored: "#10b981",
  planned: "#3b82f6",
  coming_soon: "#f59e0b",
  unsupported: "#6b7280",
};

export default function CodeUsagePage() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [repoId, setRepoId] = useState("");
  const [groups, setGroups] = useState<
    { api_name: string; status: string; detection_count: number; file_count: number; detections: unknown[] }[]
  >([]);
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
    getDetections(repoId)
      .then((d) => setGroups(d.footprint || []))
      .catch(() => setGroups([]))
      .finally(() => setLoading(false));
  }, [repoId]);

  return (
    <div>
      <h1>Code Break Detection · API Usage in Code</h1>
      <p className="subtitle">Every detected API call, file, and line — right from your code</p>

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
        <div className="loading">Loading code usage…</div>
      ) : groups.length === 0 ? (
        <div className="empty-state">
          <p>No detections yet. Scan a repository first.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {groups.map((g) => (
            <div key={g.api_name} style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <span style={{ textTransform: "capitalize", fontWeight: 700 }}>{g.api_name}</span>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: 999,
                    fontSize: 12,
                    background: `${STATUS_COLOR[g.status] || "#6b7280"}22`,
                    color: STATUS_COLOR[g.status] || "#6b7280",
                  }}
                >
                  {g.status}
                </span>
                <span style={{ opacity: 0.6 }}>{g.detection_count} detections · {g.file_count} files</span>
              </div>
              <div style={{ marginTop: 8, fontSize: 13 }}>
                {(g.detections || []).slice(0, 8).map((d, i) => (
                  <p key={i} style={{ margin: "2px 0", opacity: 0.8, fontFamily: "monospace" }}>
                    {(d as { file_path: string }).file_path}
                    {(d as { line_number?: number }).line_number != null
                      ? `:${(d as { line_number: number }).line_number}`
                      : ""}
                    {(d as { matched_snippet?: string }).matched_snippet
                      ? ` — ${(d as { matched_snippet: string }).matched_snippet.slice(0, 60)}`
                      : ""}
                  </p>
                ))}
                {(g.detections || []).length > 8 && (
                  <p style={{ opacity: 0.5 }}>… and {(g.detections || []).length - 8} more</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}