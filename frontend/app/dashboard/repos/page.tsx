"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { connectRepo, GitHubRepo, listGithubRepos, Repo, listRepos, scanRepo } from "@/lib/api";

export default function ReposPage() {
  const [repos, setRepos] = useState<Repo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanningId, setScanningId] = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [ghRepos, setGhRepos] = useState<GitHubRepo[] | null>(null);
  const [ghError, setGhError] = useState<string | null>(null);
  const [ghErrorStatus, setGhErrorStatus] = useState<number | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);

  const load = () => {
    setError(null);
    listRepos()
      .then(setRepos)
      .catch((e) => setError(e.message || "Failed to load repositories."));
  };

  useEffect(load, []);

  const onScan = (id: string) => {
    setScanningId(id);
    scanRepo(id)
      .then(() => load())
      .catch((e) => setError(e.message || "Scan failed."))
      .finally(() => setScanningId(null));
  };

  async function openPicker() {
    setShowPicker(true);
    setGhError(null);
    setGhErrorStatus(null);
    setGhRepos(null);
    try {
      setGhRepos(await listGithubRepos());
    } catch (e: any) {
      setGhErrorStatus(e?.status ?? null);
      setGhError(e.message || "Failed to load GitHub repositories.");
    }
  }

  async function connect(r: GitHubRepo) {
    setConnecting(r.github_repo_id);
    try {
      await connectRepo({ github_repo_id: r.github_repo_id, full_name: r.full_name, default_branch: r.default_branch });
      await load();
      setShowPicker(false);
    } catch (e: any) {
      setGhError(e.message || "Failed to connect repository.");
    } finally {
      setConnecting(null);
    }
  }

  const connectedIds = useMemo(
    () => new Set((repos ?? []).map((r) => r.github_repo_id)),
    [repos]
  );

  return (
    <div className="container">
      <div className="page-header">
        <h1>Repositories</h1>
        <p>Connected repositories and their scan status.</p>
        <button className="btn btn-primary" onClick={openPicker}>
          + Connect Repository
        </button>
      </div>

      {error && (
        <div
          style={{
            border: "1px solid #fca5a5",
            background: "#fef2f2",
            borderRadius: 10,
            padding: "12px 16px",
            marginBottom: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <span style={{ color: "#b91c1c" }}>{error}</span>
          {/expired|reconnect|No GitHub connection/i.test(error) && (
            <Link href="/dashboard" className="btn btn-primary">
              Reconnect GitHub
            </Link>
          )}
        </div>
      )}

      {!repos ? (
        <p className="loading">Loading repositories...</p>
      ) : repos.length === 0 ? (
        <div style={{ textAlign: "center", padding: "48px 24px" }}>
          <p className="empty-state">
            No repositories connected yet. Connect a GitHub repository to start monitoring for
            breaking API changes.
          </p>
          <button className="btn btn-primary" onClick={openPicker}>
            + Connect your first repository
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {repos.map((r) => (
            <div
              key={r.id}
              style={{
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 12,
                padding: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <div style={{ minWidth: 240 }}>
                <Link
                  href={`/dashboard/repos/${r.id}`}
                  style={{ fontWeight: 600, textDecoration: "none", color: "inherit" }}
                >
                  {r.full_name}
                </Link>
                <div className="small muted">
                  branch: {r.default_branch || "-"} · last scan:{" "}
                  {r.last_scanned_at ? new Date(r.last_scanned_at).toLocaleString() : "never"}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => onScan(r.id)}
                  disabled={scanningId === r.id}
                >
                  {scanningId === r.id ? "Scanning..." : "Scan now"}
                </button>
                <Link className="btn btn-secondary" href={`/dashboard/repos/${r.id}/fixes`}>
                  Fixes
                </Link>
                <Link className="btn btn-primary" href={`/dashboard/repos/${r.id}`}>
                  Open
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ─── Connect Repository Modal ─── */}
      {showPicker && (
        <div
          onClick={() => setShowPicker(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            background: "rgba(15,23,42,0.55)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--surface,#fff)",
              border: "1px solid var(--border,#e5e7eb)",
              borderRadius: 16,
              padding: 28,
              width: "100%",
              maxWidth: 560,
              maxHeight: "80vh",
              overflow: "auto",
              boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 20,
              }}
            >
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 4px" }}>
                  Connect a repository
                </h2>
                <p style={{ fontSize: 13, color: "var(--muted,#6b7280)", margin: 0 }}>
                  Select a GitHub repository to monitor
                </p>
              </div>
              <button className="btn btn-sm" onClick={() => setShowPicker(false)}>
                ✕
              </button>
            </div>
            {ghError && (
              <div style={{ color: "#b91c1c", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 10, padding: "14px 16px", marginBottom: 12 }}>
                {ghErrorStatus === 401 ? (
                  <>
                    <div style={{ fontWeight: 600, marginBottom: 10 }}>GitHub authorization needs to be renewed.</div>
                    <Link href="/auth/github" className="btn btn-sm btn-primary" style={{ borderRadius: 8 }}>
                      Reconnect GitHub
                    </Link>
                  </>
                ) : (
                  <>
                    <div style={{ fontWeight: 600, marginBottom: 10 }}>Unable to load your GitHub repositories.</div>
                    <button className="btn btn-sm" onClick={openPicker} style={{ borderRadius: 8 }}>
                      Retry
                    </button>
                  </>
                )}
              </div>
            )}
            {ghRepos === null && !ghError ? (
              <div style={{ textAlign: "center", padding: 40, color: "var(--muted,#6b7280)" }}>
                Loading your GitHub repositories...
              </div>
            ) : (ghRepos ?? []).length === 0 ? (
              <div style={{ textAlign: "center", padding: 40, color: "var(--muted,#6b7280)" }}>
                No GitHub repositories available to connect. Create a repository on
                GitHub or request access to an existing one.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(ghRepos ?? []).map((r) => {
                  const already = connectedIds.has(r.github_repo_id);
                  return (
                    <div
                      key={r.github_repo_id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "12px 14px",
                        borderRadius: 10,
                        border: "1px solid var(--border,#e5e7eb)",
                        background: "var(--bg,#fff)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: 8,
                            background: "#1f2328",
                            color: "white",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: 700,
                            fontSize: 12,
                            flexShrink: 0,
                          }}
                        >
                          {r.full_name.split("/").pop()?.charAt(0)?.toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14 }}>{r.full_name}</div>
                          {r.private && (
                            <span style={{ fontSize: 11, color: "var(--muted,#6b7280)" }}>
                              Private
                            </span>
                          )}
                        </div>
                      </div>
                      {already ? (
                        <span style={{ color: "#0a7d3d", fontSize: 13, fontWeight: 500 }}>
                          ✓ Connected
                        </span>
                      ) : (
                        <button
                          className="btn btn-sm btn-primary"
                          disabled={connecting === r.github_repo_id}
                          onClick={() => connect(r)}
                        >
                          {connecting === r.github_repo_id ? "Connecting..." : "Connect"}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}