"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  approveFix,
  dismissFix,
  Fix,
  FixActionResponse,
  FixesListResponse,
  getFixes,
  FixStatus,
} from "../../../../../lib/api";

import {
  formatDate,
  Nav,
  Spinner,
  StatusPill,
  ApiBadge,
  apiLabel,
} from "../../../../../components/ui";

const STATUS_TABS: { value: FixStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "needs_review", label: "Needs Review" },
  { value: "pr_created", label: "PR Created" },
  { value: "merged", label: "Merged" },
  { value: "rejected", label: "Rejected" },
];

const STATUS_COLORS: Record<FixStatus, string> = {
  pending: "pill-gray",
  needs_review: "pill-amber",
  pr_created: "pill-blue",
  merged: "pill-green",
  rejected: "pill-red",
};

export default function FixesPage() {
  const params = useParams();
  const repoId = String(params.id);

  const [fixes, setFixes] = useState<Fix[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<FixStatus>("needs_review");
  const [actionStates, setActionStates] = useState<Record<string, "idle" | "loading">>({});

  const loadFixes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res: FixesListResponse = await getFixes(repoId, activeTab);
      setFixes(res.fixes);
    } catch (e: any) {
      setError(e.message || "Failed to load fixes");
    } finally {
      setLoading(false);
    }
  }, [repoId, activeTab]);

  useEffect(() => {
    loadFixes();
  }, [loadFixes]);

  async function handleApprove(fix: Fix) {
    setActionStates((prev) => ({ ...prev, [fix.id]: "loading" }));
    try {
      const res: FixActionResponse = await approveFix(repoId, fix.id);
      setFixes((prev) =>
        prev?.map((f) =>
          f.id === fix.id ? { ...f, status: res.status, pr_url: res.pr_url } : f
        ) ?? []
      );
    } catch (e: any) {
      alert(e.message || "Failed to approve fix");
    } finally {
      setActionStates((prev) => ({ ...prev, [fix.id]: "idle" }));
    }
  }

  async function handleDismiss(fix: Fix) {
    if (!confirm("Dismiss this fix? It will be marked as rejected and no PR will be created.")) {
      return;
    }
    setActionStates((prev) => ({ ...prev, [fix.id]: "loading" }));
    try {
      const res: FixActionResponse = await dismissFix(repoId, fix.id);
      setFixes((prev) =>
        prev?.map((f) => (f.id === fix.id ? { ...f, status: res.status } : f)) ?? []
      );
    } catch (e: any) {
      alert(e.message || "Failed to dismiss fix");
    } finally {
      setActionStates((prev) => ({ ...prev, [fix.id]: "idle" }));
    }
  }

  const repoName = fixes?.[0]?.repo_id ? "" : ""; // We don't have repo name here, could fetch

  return (
    <>
      <Nav />
      <main className="container page">
        <p style={{ marginTop: 0 }}>
          <Link href={`/dashboard/repos/${repoId}`}>← Repository</Link>
        </p>

        <div className="row" style={{ marginBottom: 16, alignItems: "center", gap: 16 }}>
          <div>
            <h1 style={{ marginBottom: 2 }}>Fixes Review</h1>
            <p className="muted small" style={{ margin: 0 }}>
              Review and approve auto-generated fixes for this repository.
            </p>
          </div>
        </div>

        {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

        {/* Status Tabs */}
        <div className="card" style={{ marginBottom: 16, padding: "12px 16px" }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                className={`btn btn-sm ${activeTab === tab.value ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setActiveTab(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Fixes List */}
        <section className="card" style={{ padding: 0 }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: "center" }}>
              <Spinner /> Loading fixes…
            </div>
          ) : fixes === null || fixes.length === 0 ? (
            <div className="empty" style={{ padding: 40 }}>
              No fixes found for this status.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="table responsive-cards">
                <thead>
                  <tr>
                    <th style={{ width: "30%" }}>Fix / Rule</th>
                    <th style={{ width: "15%" }}>File</th>
                    <th style={{ width: "12%" }}>Status</th>
                    <th style={{ width: "15%" }}>Confidence</th>
                    <th style={{ width: "15%" }}>Created</th>
                    <th style={{ width: "13%" }}></th>
                  </tr>
                </thead>
                <tbody>
                  {fixes.map((fix) => (
                    <FixRow
                      key={fix.id}
                      fix={fix}
                      onApprove={handleApprove}
                      onDismiss={handleDismiss}
                      loading={actionStates[fix.id] === "loading"}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </>
  );
}

function FixRow({
  fix,
  onApprove,
  onDismiss,
  loading,
}: {
  fix: Fix;
  onApprove: (fix: Fix) => void;
  onDismiss: (fix: Fix) => void;
  loading: boolean;
}) {
  const isReviewable = fix.status === "needs_review" || fix.status === "pending";
  const hasPr = fix.status === "pr_created" || fix.status === "merged";
  const isMerged = fix.status === "merged";

  return (
    <tr key={fix.id} style={{ borderBottom: "1px solid #eee" }}>
      <td data-label="Fix / Rule">
        <div>
          <strong>{fix.rule_title || "Breaklytix Rule"}</strong>
          {fix.rule_confidence && (
            <span
              className={`pill ${STATUS_COLORS[fix.rule_confidence as FixStatus] || "pill-gray"}`}
              style={{ marginLeft: 8, fontSize: 11, textTransform: "capitalize" }}
            >
              {fix.rule_confidence}
            </span>
          )}
          {fix.rule_description && (
            <div className="muted small" style={{ marginTop: 4, maxWidth: 400 }}>
              {fix.rule_description}
            </div>
          )}
        </div>
      </td>
      <td data-label="File">
        <code style={{ fontSize: 12 }}>{fix.file_path}</code>
      </td>
      <td data-label="Status">
        <span className={`pill ${STATUS_COLORS[fix.status]}`}>
          {fix.status.replace("_", " ")}
        </span>
        {fix.pr_url && (
          <div style={{ marginTop: 4 }}>
            <a href={fix.pr_url} target="_blank" rel="noreferrer" className="small">
              PR #{fix.pr_number} →
            </a>
          </div>
        )}
      </td>
      <td data-label="Confidence">
        {fix.rule_old_value && fix.rule_new_value && (
          <div className="small" style={{ fontFamily: "monospace" }}>
            <div style={{ color: "#dc3545" }}>− {fix.rule_old_value}</div>
            <div style={{ color: "#28a745" }}>+ {fix.rule_new_value}</div>
          </div>
        )}
      </td>
      <td data-label="Created" className="muted small">{formatDate(fix.created_at)}</td>
      <td data-label="Actions" style={{ textAlign: "right", whiteSpace: "nowrap" }}>
        {hasPr && !isMerged && fix.pr_url && (
          <a href={fix.pr_url} target="_blank" rel="noreferrer" className="btn btn-sm btn-secondary" style={{ marginRight: 8 }}>
            View PR
          </a>
        )}
        {isReviewable && (
          <>
            <button
              className="btn btn-sm btn-primary"
              onClick={() => onApprove(fix)}
              disabled={loading}
              style={{ marginRight: 8 }}
            >
              {loading ? <><Spinner /> Working…</> : "Approve & Create PR"}
            </button>
            <button
              className="btn btn-sm"
              onClick={() => onDismiss(fix)}
              disabled={loading}
            >
              Dismiss
            </button>
          </>
        )}
        {isMerged && <span className="pill pill-green">Merged</span>}
      </td>
    </tr>
  );
}