"use client";

import { useEffect, useState } from "react";
import {
  approveFix,
  dismissFix,
  Fix,
  getFixes,
  listRepos,
  Repo,
} from "../../../../lib/api";
import { formatDate } from "../../../../components/ui";

const STATUS_COLOR: Record<string, string> = {
  pending: "#f59e0b",
  needs_review: "#3b82f6",
  pr_created: "#10b981",
  merged: "#10b981",
  rejected: "#6b7280",
};

export default function BreaklytixPage() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [fixes, setFixes] = useState<(Fix & { repo_name: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    listRepos()
      .then(async (rs) => {
        setRepos(rs);
        const out: (Fix & { repo_name: string })[] = [];
        await Promise.all(
          rs.map(async (r) => {
            try {
              const d = await getFixes(r.id);
              for (const f of d.fixes || []) out.push({ ...f, repo_name: r.full_name });
            } catch {
              /* repo has no fixes endpoint issue */
            }
          })
        );
        out.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
        setFixes(out);
      })
      .catch(() => setFixes([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const act = async (repoId: string, fixId: string, action: "approve" | "dismiss") => {
    setBusy(fixId);
    try {
      if (action === "approve") await approveFix(repoId, fixId);
      else await dismissFix(repoId, fixId);
      load();
    } catch (e) {
      alert(`Action failed: ${String(e)}`);
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <div className="loading">Loading auto-fixes…</div>;

  return (
    <div>
      <h1>Code Break Detection · Auto-Fix PRs</h1>
      <p className="subtitle">
        Deterministic fixes generated from reliability issues — review, approve (creates the change), or dismiss
      </p>

      {fixes.length === 0 ? (
        <div className="empty-state">
          <p>
            No auto-fixes queued yet. Scan a repo, then use <strong>Queue fix</strong> on a finding with
            auto-fix available — it lands here for your review.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {fixes.map((f) => (
            <div key={f.id} style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <div>
                  <span style={{ fontWeight: 700 }}>{f.rule_title || "Breaklytix"}</span>
                  <span style={{ marginLeft: 8, opacity: 0.6 }}>{f.repo_name}</span>
                </div>
                <div>
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: 999,
                      fontSize: 12,
                      background: `${STATUS_COLOR[f.status] || "#6b7280"}22`,
                      color: STATUS_COLOR[f.status] || "#6b7280",
                    }}
                  >
                    {f.status}
                  </span>
                  {f.pr_url && (
                    <a
                      href={f.pr_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ marginLeft: 10, fontSize: 13 }}
                    >
                      PR {f.pr_number} →
                    </a>
                  )}
                </div>
              </div>
              {f.rule_description && <p style={{ margin: "8px 0 0", opacity: 0.85 }}>{f.rule_description}</p>}
              <p style={{ margin: "6px 0 0", fontFamily: "monospace", fontSize: 13, opacity: 0.8 }}>
                {f.file_path}
              </p>
              {f.diff_preview && (
                <pre
                  style={{
                    margin: "8px 0 0",
                    padding: 10,
                    borderRadius: 8,
                    background: "rgba(0,0,0,0.3)",
                    fontSize: 12,
                    overflowX: "auto",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {f.diff_preview.slice(0, 500)}
                </pre>
              )}
              {(f.rule_old_value || f.rule_new_value) && (
                <p style={{ fontSize: 13, opacity: 0.7, margin: "6px 0 0" }}>
                  {f.rule_old_value} → {f.rule_new_value}
                </p>
              )}
              <p style={{ fontSize: 12, opacity: 0.5, margin: "6px 0 0" }}>
                Created {formatDate(f.created_at as string)} · Confidence: {f.rule_confidence || "—"}
              </p>
              {(f.status === "pending" || f.status === "needs_review") && (
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <button
                    className="btn btn-sm btn-primary"
                    disabled={busy === f.id}
                    onClick={() => act(f.repo_id, f.id, "approve")}
                  >
                    Approve &amp; apply
                  </button>
                  <button
                    className="btn btn-sm btn-secondary"
                    disabled={busy === f.id}
                    onClick={() => act(f.repo_id, f.id, "dismiss")}
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}