"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Spinner } from "@/components/ui";
import { getChangelogNotices, ChangelogNotice as ApiNotice } from "@/lib/api";

interface ChangelogNotice {
  id: string;
  api_name: string;
  title: string;
  source_url: string;
  detected_at: string;
  description: string;
  change_type: string;
  severity: string;
  confidence?: string;
  status: "potential" | "review_recommended" | "action_required" | "dismissed";
}

// Map a confidence label to a dashboard status (Phase B spec).
function statusFromConfidence(confidence?: string | null): ChangelogNotice["status"] {
  switch ((confidence || "low").toLowerCase()) {
    case "high":
      return "action_required";
    case "medium":
      return "review_recommended";
    default:
      return "potential";
  }
}

export default function ChangelogPage() {
  const router = useRouter();
  const [notices, setNotices] = useState<ChangelogNotice[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [providerFilter, setProviderFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const load = useCallback(async () => {
    try {
      const res = await getChangelogNotices();
      const items: ChangelogNotice[] = (res.notices || []).map((a: ApiNotice) => {
        const ev: Record<string, any> = a.changelog_events || {};
        return {
          id: a.id,
          api_name: ev.api_name || a.api_name || "unknown",
          title: ev.title || a.title || "API change",
          source_url: ev.source_url || a.source_url || "",
          detected_at: ev.detected_at || a.detected_at || a.created_at || "",
          description: ev.description || a.description || "",
          change_type: ev.change_type || a.change_type || "other",
          severity: a.severity || "medium",
          confidence: a.confidence || ev.severity || "low",
          status: statusFromConfidence(a.confidence || ev.severity),
        };
      });
      // Sort newest first.
      items.sort((x, y) => (y.detected_at || "").localeCompare(x.detected_at || ""));
      setNotices(items);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to load changelog notices");
      setNotices([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const providers = notices ? Array.from(new Set(notices.map((n) => n.api_name))).sort() : [];

  const filtered = (notices ?? []).filter(
    (n) =>
      (providerFilter === "all" || n.api_name === providerFilter) &&
      (statusFilter === "all" || n.status === statusFilter)
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "action_required":
        return <span className="pill pill-red">Action Required</span>;
      case "review_recommended":
        return <span className="pill pill-amber">Review Recommended</span>;
      case "potential":
        return <span className="pill pill-gray">Potential</span>;
      case "dismissed":
        return <span className="pill pill-gray">Dismissed</span>;
      default:
        return <span className="pill pill-gray">{status}</span>;
    }
  };

  const getConfidenceBadge = (confidence?: string) => {
    switch (confidence) {
      case "high":
        return <span className="pill pill-red" style={{ fontSize: 11 }}>High</span>;
      case "medium":
        return <span className="pill pill-amber" style={{ fontSize: 11 }}>Medium</span>;
      case "low":
        return <span className="pill pill-gray" style={{ fontSize: 11 }}>Low</span>;
      default:
        return null;
    }
  };

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Changelog Notices</h1>
          <p className="muted small" style={{ margin: 0 }}>
            Official API changes from monitored providers. Review and take action as needed.
          </p>
        </div>
        <Link className="btn btn-secondary" href="/dashboard/alerts">
          Alert History
        </Link>
      </div>

      {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

      <section className="card" style={{ padding: 0 }}>
        <div
          style={{
            padding: "16px 20px 0",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <label className="muted small" htmlFor="providerFilter" style={{ margin: 0 }}>Provider</label>
              <select
                id="providerFilter"
                className="input"
                style={{ width: "auto", padding: "6px 10px" }}
                value={providerFilter}
                onChange={(e) => setProviderFilter(e.target.value)}
              >
                <option value="all">All providers</option>
                {providers.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <label className="muted small" htmlFor="statusFilter" style={{ margin: 0 }}>Status</label>
              <select
                id="statusFilter"
                className="input"
                style={{ width: "auto", padding: "6px 10px" }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All statuses</option>
                <option value="action_required">Action Required</option>
                <option value="review_recommended">Review Recommended</option>
                <option value="potential">Potential</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>
          </div>
        </div>

        {notices === null ? (
          <div style={{ padding: 20 }}><Spinner /> Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="empty" style={{ marginTop: 16 }}>
            {notices.length === 0
              ? "No changelog notices yet. We're monitoring 12 providers for API changes."
              : "No notices match the current filters."}
          </div>
        ) : (
          <table className="table responsive-cards">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Change</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Published</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((n) => (
                <tr key={n.id}>
                  <td data-label="Provider">
                    <span style={{ textTransform: "capitalize" }}>{n.api_name}</span>
                  </td>
                  <td data-label="Change">
                    <span className="pill pill-amber" style={{ marginBottom: 4 }}>
                      {n.change_type.replace(/_/g, " ")}
                    </span>
                    <div className="small" style={{ marginTop: 4 }}>{n.title}</div>
                    {n.source_url && (
                      <a className="small" href={n.source_url} target="_blank" rel="noreferrer">
                        Official source →
                      </a>
                    )}
                  </td>
                  <td data-label="Confidence">{getConfidenceBadge(n.confidence)}</td>
                  <td data-label="Status">{getStatusBadge(n.status)}</td>
                  <td data-label="Published" className="muted small">{new Date(n.detected_at).toLocaleDateString()}</td>
                  <td>
                    <Link className="btn btn-sm" href={`/dashboard/changelog/${n.id}`}>
                      View
                    </Link>
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
