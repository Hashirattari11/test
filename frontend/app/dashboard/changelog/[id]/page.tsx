"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { Spinner } from "@/components/ui";
import { getChangelogNotices, ChangelogNotice as ApiNotice } from "@/lib/api";

interface NoticeDetail {
  id: string;
  api_name: string;
  title: string;
  source_url: string;
  detected_at: string;
  description: string;
  change_type: string;
  severity: string;
  confidence?: string;
  created_at?: string;
}

export default function ChangelogNoticePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [notice, setNotice] = useState<NoticeDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await getChangelogNotices();
        const found = (res.notices || []).find((a: ApiNotice) => a.id === id);
        if (!found) {
          setNotFound(true);
          return;
        }
        const ev: Record<string, any> = found.changelog_events || {};
        setNotice({
          id: found.id,
          api_name: ev.api_name || found.api_name || "unknown",
          title: ev.title || found.title || "API change",
          source_url: ev.source_url || found.source_url || "",
          detected_at: ev.detected_at || found.detected_at || found.created_at || "",
          description: ev.description || found.description || "",
          change_type: ev.change_type || found.change_type || "other",
          severity: found.severity || "medium",
          confidence: found.confidence || ev.severity || "low",
          created_at: found.created_at || "",
        });
      } catch (e: any) {
        setNotFound(true);
      } finally {
        setLoading(false);
      }
    })();
  }, [id, router]);

  if (loading) {
    return (
      <div className="page">
        <Spinner /> Loading notice…
      </div>
    );
  }

  if (notFound || !notice) {
    return (
      <div className="page">
        <h1>Notice Not Found</h1>
        <p className="muted">This changelog notice could not be found or is no longer available.</p>
        <Link className="btn btn-primary" href="/dashboard/changelog">
          ← Back to Changelog
        </Link>
      </div>
    );
  }

  const getStatusBadge = (confidence?: string) => {
    switch ((confidence || "low").toLowerCase()) {
      case "high":
        return <span className="pill pill-red">Action Required</span>;
      case "medium":
        return <span className="pill pill-amber">Review Recommended</span>;
      default:
        return <span className="pill pill-gray">Potential</span>;
    }
  };

  return (
    <div className="page">
      <Link className="btn btn-secondary" href="/dashboard/changelog" style={{ marginBottom: 16 }}>
        ← Back to Changelog
      </Link>
      <h1 style={{ marginBottom: 4 }}>{notice.title}</h1>
      <p className="muted small" style={{ margin: 0 }}>{notice.api_name} · Provider change</p>

      <div style={{ display: "flex", gap: 8, margin: "12px 0 20px" }}>
        <span className="pill pill-amber" style={{ textTransform: "capitalize" }}>
          {notice.change_type.replace(/_/g, " ")}
        </span>
        {getStatusBadge(notice.confidence)}
        <span className="pill pill-gray">{notice.severity}</span>
      </div>

      <section className="card" style={{ padding: 20 }}>
        <p>{notice.description || "No description provided for this change."}</p>
        {notice.detected_at && (
          <p className="muted small" style={{ marginTop: 12 }}>
            Detected: {new Date(notice.detected_at).toLocaleString()}
          </p>
        )}
        {notice.source_url && (
          <p style={{ marginTop: 8 }}>
            <a href={notice.source_url} target="_blank" rel="noreferrer">
              Official source →
            </a>
          </p>
        )}
      </section>
    </div>
  );
}
