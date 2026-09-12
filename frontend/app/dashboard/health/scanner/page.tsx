"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  getScans,
  listRepos,
  Repo,
  ScanRecord,
  scanRepo,
  ScanResult,
} from "../../../../lib/api";
import { formatDate } from "../../../../components/ui";

const STAGES = [
  "Fetching repositoryâ€¦",
  "Analyzing filesâ€¦",
  "Detecting APIsâ€¦",
  "Checking SDKs and dependenciesâ€¦",
  "Checking reliabilityâ€¦",
  "Generating health reportâ€¦",
];

export default function ScannerPage() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [repoId, setRepoId] = useState("");
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [scanning, setScanning] = useState(false);
  const [stage, setStage] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const ticker = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    listRepos()
      .then((rs) => {
        setRepos(rs);
        if (rs[0]) setRepoId(rs[0].id);
      })
      .catch(() => setRepos([]));
  }, []);

  useEffect(() => {
    if (!repoId) return;
    getScans(repoId)
      .then((d) => setScans(d.scans || []))
      .catch(() => setScans([]));
  }, [repoId]);

  const runScan = async () => {
    setScanning(true);
    setResult(null);
    setMessage(null);
    setStage(0);
    ticker.current = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 1200);
    try {
      const r = await scanRepo(repoId);
      setResult(r);
      const base = `Scan complete: ${r.files_scanned} files, ${r.detections_found} detections, ${r.apis_detected?.length ?? 0} APIs found.`;
      if (r.plan_warning) setMessage(`${base} ${r.plan_warning}`);
      else setMessage(base);
    } catch (e) {
      setMessage(`Scan failed: ${String(e)}`);
    } finally {
      if (ticker.current) clearInterval(ticker.current);
      ticker.current = null;
      setScanning(false);
      getScans(repoId)
        .then((d) => setScans(d.scans || []))
        .catch(() => {});
    }
  };

  return (
    <div>
      <h1>Code Break Detection Â· Repository Scanner</h1>
      <p className="subtitle">Scan a repository â€” detect API usage, SDK versions, and break risks{" "}
        <Link href="/docs/repository-scanner" style={{ textDecoration: "none" }}>Learn more</Link></p>

      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <select value={repoId} onChange={(e) => setRepoId(e.target.value)}>
          {repos.map((r) => (
            <option key={r.id} value={r.id}>
              {r.full_name}
            </option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={runScan} disabled={scanning || !repoId}>
          {scanning ? `Scanningâ€¦ ${STAGES[stage]}` : "Scan now"}
        </button>
      </div>

      {scanning && (
        <div
          style={{
            padding: 16,
            border: "1px solid rgba(16,185,129,0.25)",
            borderRadius: 10,
            background: "rgba(16,185,129,0.06)",
            marginBottom: 16,
            fontWeight: 600,
            color: "#10b981",
          }}
        >
          {STAGES[stage]}
        </div>
      )}

      {message && (
        <div
          style={{
            padding: 14,
            border: `1px solid ${message.startsWith("Scan failed") ? "rgba(239,68,68,0.35)" : "rgba(16,185,129,0.35)"}`,
            borderRadius: 10,
            background: message.startsWith("Scan failed") ? "rgba(239,68,68,0.08)" : "rgba(16,185,129,0.08)",
            marginBottom: 16,
          }}
        >
          {message}
        </div>
      )}

      <h2 style={{ fontSize: 18, margin: "8px 0" }}>Scan history</h2>
      {scans.length === 0 ? (
        <p style={{ opacity: 0.6 }}>No scans yet.</p>
      ) : (
        <table className="data-table responsive-cards" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th>Status</th>
              <th>Files</th>
              <th>Detections</th>
              <th>Created</th>
              <th>Completed</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => (
              <tr key={s.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                <td data-label="Status">
                  <span
                    style={{
                      color:
                        s.status === "COMPLETED"
                          ? "#10b981"
                          : s.status === "FAILED"
                            ? "#ef4444"
                            : "#f59e0b",
                      fontWeight: 600,
                    }}
                  >
                    {s.status}
                  </span>
                </td>
                <td data-label="Files">{s.stats?.files_scanned ?? "â€”"}</td>
                <td data-label="Detections">{s.stats?.detections_found ?? s.stats?.findings_total ?? "â€”"}</td>
                <td data-label="Created">{s.created_at ? formatDate(s.created_at as string) : "â€”"}</td>
                <td data-label="Completed">{s.finished_at ? formatDate(s.finished_at as string) : "â€”"}</td>
                <td data-label="Error" style={{ opacity: 0.6 }}>{s.error_message || "â€”"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}