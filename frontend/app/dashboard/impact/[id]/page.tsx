"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getImpactAnalysis,
  ImpactAnalysis as ImpactAnalysisType,
  generateImpactFix,
  ImpactFix,
} from "../../../../lib/api";
import { Badge, severityTone, timeAgo } from "../../../../components/dashboard-ui";
import { Spinner } from "../../../../components/ui";

const SEVERITY_COLORS: Record<string, string> = {
  safe: "#22c55e",
  low: "#84cc16",
  medium: "#f59e0b",
  high: "#f97316",
  breaking: "#ef4444",
  unknown: "#6b7280",
};

const VERIFICATION_LABELS: Record<string, string> = {
  not_verified: "NOT VERIFIED",
  static_analysis: "STATIC ANALYSIS",
  verified: "VERIFIED",
  verification_failed: "VERIFICATION FAILED",
};

const VERIFICATION_COLORS: Record<string, string> = {
  not_verified: "#6b7280",
  static_analysis: "#f59e0b",
  verified: "#22c55e",
  verification_failed: "#ef4444",
};

export default function ImpactDetailPage() {
  const params = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<ImpactAnalysisType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [fixing, setFixing] = useState(false);
  const [fixResult, setFixResult] = useState<ImpactFix[] | null>(null);
  const [fixMessage, setFixMessage] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    getImpactAnalysis(params.id)
      .then(setAnalysis)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [params?.id]);

  const runFix = async () => {
    if (!analysis || fixing) return;
    setFixing(true);
    setFixMessage("");
    setFixResult(null);
    try {
      const res = await generateImpactFix(analysis.id);
      if (res.success) {
        setFixResult(res.fixes);
        setFixMessage(res.message);
        // Refresh analysis with fix status
        const updated = await getImpactAnalysis(analysis.id);
        setAnalysis(updated);
      } else {
        setFixMessage(res.message);
      }
    } catch (e) {
      setFixMessage(String(e));
    } finally {
      setFixing(false);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ padding: "40px 0" }}>
        <Spinner /> Loading analysis…
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="container" style={{ padding: "40px 0" }}>
        <h1>Impact Analysis Not Found</h1>
        <p className="muted">{error || "This analysis may have been deleted."}</p>
        <Link href="/dashboard/impact" className="btn btn-secondary">← Back to Impact Engine</Link>
      </div>
    );
  }

  return (
    <div>
      <Link href="/dashboard/impact" className="small muted" style={{ textDecoration: "none" }}>
        ← Back to Impact Engine
      </Link>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", margin: "12px 0 4px" }}>
        <h1 style={{ margin: 0 }}>{analysis.provider} API Changed</h1>
        <Badge tone={severityTone(analysis.severity)}>{analysis.severity.toUpperCase()}</Badge>
        <span style={{ color: SEVERITY_COLORS[analysis.severity] || "#6b7280", fontWeight: 800, fontSize: 22 }}>
          {Math.round(analysis.confidence * 100)}% confidence
        </span>
      </div>
      <p className="muted" style={{ marginTop: 0 }}>
        Change: {analysis.change_type.replace(/_/g, " ")} · Detected {timeAgo(analysis.detected_at)}
      </p>

      {/* Verification status */}
      <div style={{ margin: "12px 0", padding: "12px 16px", borderRadius: 8, border: `1px solid ${VERIFICATION_COLORS[analysis.verification_status]}`, background: `${VERIFICATION_COLORS[analysis.verification_status]}14` }}>
        <strong style={{ color: VERIFICATION_COLORS[analysis.verification_status] }}>
          {VERIFICATION_LABELS[analysis.verification_status] || analysis.verification_status.toUpperCase()}
        </strong>
        <span className="muted small" style={{ marginLeft: 10 }}>
          {analysis.verification_status === "verified"
            ? "Fix passed verification checks."
            : analysis.verification_status === "verification_failed"
            ? "Fix failed verification checks."
            : analysis.verification_status === "static_analysis"
            ? "Impact identified through static analysis only — not runtime verified."
            : "No verification has been performed yet."}
        </span>
      </div>

      <div className="grid impact-cols" style={{ gridTemplateColumns: "1fr 1fr", gap: 20, marginTop: 20 }}>

        {/* Left column: change details */}
        <section className="card" style={{ padding: 20 }}>
          <h2 style={{ marginTop: 0 }}>Change Details</h2>
          <dl className="impact-meta-grid" style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 12px", margin: 0 }}>
            <dt className="muted small">Provider</dt>
            <dd><strong>{analysis.provider}</strong></dd>
            <dt className="muted small">API / Endpoint</dt>
            <dd>{analysis.api_endpoint || "—"}</dd>
            <dt className="muted small">Change type</dt>
            <dd>{analysis.change_type.replace(/_/g, " ")}</dd>
            <dt className="muted small">Change date</dt>
            <dd>{new Date(analysis.detected_at).toLocaleString()}</dd>
            {analysis.source_url && (
              <>
                <dt className="muted small">Source</dt>
                <dd>
                  <a href={analysis.source_url} target="_blank" rel="noreferrer" className="small">
                    {analysis.source_url.slice(0, 60)}…
                  </a>
                </dd>
              </>
            )}
            <dt className="muted small">SDK / Package</dt>
            <dd>
              {analysis.affected_sdks.length > 0 ? (
                analysis.affected_sdks.map((s, i) => (
                  <span key={i} className="pill pill-blue" style={{ fontSize: 11, marginRight: 4 }}>
                    {String(s.package || s.provider || "")}
                  </span>
                ))
              ) : (
                "—"
              )}
            </dd>
          </dl>
          {analysis.change_description && (
            <p className="muted small" style={{ marginTop: 14 }}>{analysis.change_description}</p>
          )}
        </section>

        {/* Right column: impact */}
        <section className="card" style={{ padding: 20 }}>
          <h2 style={{ marginTop: 0 }}>Impact Assessment</h2>
          <dl className="impact-meta-grid" style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 12px", margin: 0 }}>
            <dt className="muted small">Severity</dt>
            <dd><Badge tone={severityTone(analysis.severity)}>{analysis.severity.toUpperCase()}</Badge></dd>
            <dt className="muted small">Confidence</dt>
            <dd>{Math.round(analysis.confidence * 100)}%</dd>
            <dt className="muted small">Why affected</dt>
            <dd>{analysis.impact_reason || "—"}</dd>
            <dt className="muted small">Expected behavior</dt>
            <dd>{analysis.expected_behavior || "—"}</dd>
            <dt className="muted small">Potential failure</dt>
            <dd>{analysis.potential_failure || "—"}</dd>
            <dt className="muted small">Fix status</dt>
            <dd>{analysis.fix_status.replace(/_/g, " ")}</dd>
          </dl>
        </section>
      </div>

      {/* Affected files */}
      <section className="card" style={{ padding: 0, marginTop: 20 }}>
        <div style={{ padding: "16px 20px 0" }}>
          <h2 style={{ marginBottom: 4 }}>Affected Code</h2>
          <p className="muted small" style={{ marginTop: 0 }}>
            {analysis.affected_files.length} affected location{analysis.affected_files.length !== 1 ? "s" : ""} in this repository.
          </p>
        </div>
        {analysis.affected_files.length === 0 ? (
          <div className="empty" style={{ padding: 24 }}>No affected files detected.</div>
        ) : (
          <div style={{ padding: "0 20px 20px" }}>
            {analysis.affected_files.map((f, i) => (
              <div key={i} className="code-block" style={{
                marginBottom: 12,
                padding: 12,
                background: "var(--bg-2, #f9fafb)",
                borderRadius: 8,
                border: "1px solid var(--border, #e5e7eb)",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <code style={{ fontWeight: 600 }}>{f.file_path}</code>
                  {f.line_number && <span className="pill pill-gray" style={{ fontSize: 10 }}>line {f.line_number}</span>}
                  {f.function_name && <span className="pill pill-blue" style={{ fontSize: 10 }}>{f.function_name}()</span>}
                  {f.workflow && <span className="pill pill-amber" style={{ fontSize: 10 }}>{f.workflow}</span>}
                </div>
                {f.reason && <p className="small muted" style={{ margin: "6px 0 0" }}>{f.reason}</p>}
                {f.snippet && (
                  <pre style={{ margin: "8px 0 0", fontSize: 12, overflowX: "auto" }}>
                    <code>{f.snippet}</code>
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Fix generation */}
      <section className="card" style={{ padding: 20, marginTop: 20 }}>
        <h2 style={{ marginTop: 0 }}>Fix</h2>
        {analysis.recommended_fix ? (
          <>
            <p><strong>Recommended fix:</strong> {analysis.recommended_fix}</p>
            {analysis.fix_diff && (
              <pre style={{ background: "var(--bg-2, #f3f4f6)", padding: 14, borderRadius: 8, fontSize: 12, overflowX: "auto" }}>
                <code>{analysis.fix_diff}</code>
              </pre>
            )}
          </>
        ) : (
          <p className="muted">No fix generated yet.</p>
        )}
        <button
          className="btn btn-primary"
          onClick={runFix}
          disabled={fixing}
          style={{ marginTop: 4 }}
        >
          {fixing ? "Generating fix…" : "Generate Fix"}
        </button>
        {fixMessage && <p className="small muted" style={{ marginTop: 8 }}>{fixMessage}</p>}
        {fixResult && fixResult.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <strong className="small">Generated fixes:</strong>
            {fixResult.map((fix, i) => (
              <div key={i} className="code-block" style={{ marginTop: 8, padding: 12, background: "var(--bg-2, #f3f4f6)", borderRadius: 8, fontSize: 12 }}>
                <div><strong>{fix.file_path}</strong></div>
                <div className="small muted" style={{ margin: "4px 0" }}>{fix.description}</div>
                {fix.diff && <pre style={{ margin: 0, overflowX: "auto" }}><code>{fix.diff}</code></pre>}
              </div>
            ))}
          </div>
        )}
        <p className="small muted" style={{ marginTop: 12 }}>
          Fixes are never auto-merged. Run project tests/typecheck/lint before creating a PR.
        </p>
      </section>
    </div>
  );
}