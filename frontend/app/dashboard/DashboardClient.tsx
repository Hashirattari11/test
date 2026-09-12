"use client";

// ---------------------------------------------------------------------------
// AutoFix API â€” Monitoring Dashboard (Session-9 redesign, Session-10 prune).
// EVERY metric comes from the real backend: provider connections, real
// provider incidents, real alerts, real repository scans. NO simulated data.
// Repository data lives ONLY in the Code Intelligence section; provider
// metrics are connection-scoped (runtime). The API Usage panel summarizes the
// real changelog-monitored providers plus what code scans have detected.
// ---------------------------------------------------------------------------

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertWithRepo,
  DashboardStats,
  getDashboardStats,
  getHealthErrors,
  getProviderConnections,
  getProviderIncidentsFeed,
  HealthIssue,
  HealthRuntimeList,
  listAllAlerts,
  listRepos,
  ProviderConnection,
  ProviderIncident,
  Repo,
} from "@/lib/api";
import {
  Badge,
  ErrorCard,
  severityLabel,
  severityTone,
  Skeleton,
  SkeletonGrid,
  StatCard,
  timeAgo,
} from "@/components/dashboard-ui";

function fmtProvider(p: string): string {
  return p
    .split(/[_-]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// Real event kind: used for Recent Activity (all from real data).
type ActivityEvent = {
  id: string;
  ts: string;
  kind: "provider_connected" | "provider_error" | "api_error" | "break_alert" | "incident";
  label: string;
  detail: string;
  tone: "green" | "amber" | "red" | "gray";
};

function dotTone(tone: string): string {
  return tone === "green" ? "green" : tone === "amber" ? "amber" : tone === "red" ? "red" : "gray";
}

export default function DashboardClient() {
  const [connections, setConnections] = useState<ProviderConnection[] | null>(null);
  const [alerts, setAlerts] = useState<AlertWithRepo[] | null>(null);
  const [errors, setErrors] = useState<HealthRuntimeList<"errors"> | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [repos, setRepos] = useState<Repo[] | null>(null);
  const [incidents, setIncidents] = useState<ProviderIncident[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [conns, al, er, st, rp, inc] = await Promise.all([
        getProviderConnections().catch(() => ({ connections: [] as ProviderConnection[] })),
        listAllAlerts().catch(() => [] as AlertWithRepo[]),
        getHealthErrors(200).catch(() => null),
        getDashboardStats().catch(() => null),
        listRepos().catch(() => [] as Repo[]),
        getProviderIncidentsFeed()
          .then((r) => r.incidents || [])
          .catch(() => [] as ProviderIncident[]),
      ]);
      setConnections(conns.connections);
      setAlerts(al);
      setErrors(er);
      setStats(st);
      setRepos(rp);
      setIncidents(inc);
    } catch (e) {
      setLoadError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // One refresh on mount; manual refresh via header button is available.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const connected = connections ?? [];
  const openAlerts = useMemo(
    () =>
      (alerts ?? []).filter((a) => !a.is_test && a.status !== "resolved" && a.status !== "ignored"),
    [alerts]
  );

  const errorIssues: HealthIssue[] = (errors?.errors as HealthIssue[] | undefined) ?? [];

  // Open incidents: real, from the runtime provider-incidents feed.
  const openIncidents = useMemo(
    () =>
      (incidents ?? [])
        .filter((inc) => !inc.status || String(inc.status).toLowerCase() !== "resolved")
        .sort((a, b) => (b.started_at ?? "").localeCompare(a.started_at ?? "")),
    [incidents]
  );

  // Real activity stream: connections, alerts, errors, incidents â€” no fabrications.
  const activity: ActivityEvent[] = useMemo(() => {
    const ev: ActivityEvent[] = [];
    for (const c of connected) {
      ev.push({
        id: `conn-${c.provider}`,
        ts: c.connected_at ?? "",
        kind: "provider_connected",
        label: "Provider connected",
        detail: `${fmtProvider(c.provider)} connected with a validated API key`,
        tone: c.last_error ? "amber" : "green",
      });
      if (c.last_error) {
        ev.push({
          id: `err-${c.provider}`,
          ts: c.connected_at ?? "",
          kind: "provider_error",
          label: "Provider collector error",
          detail: `${fmtProvider(c.provider)} â€” ${c.last_error}`,
          tone: "red",
        });
      }
    }
    for (const a of openAlerts.slice(0, 6)) {
      ev.push({
        id: `alert-${a.id}`,
        ts: a.created_at ?? "",
        kind: "break_alert",
        label: "Potential breaking change",
        detail: `${a.change_type} Â· ${a.repo_name}`,
        tone: severityTone(a.severity) === "red" ? "red" : severityTone(a.severity) === "amber" ? "amber" : "green",
      });
    }
    for (const err of errorIssues.slice(0, 6)) {
      ev.push({
        id: `api-${err.id}`,
        ts: err.created_at,
        kind: "api_error",
        label: "API error detected",
        detail: `${err.provider} Â· ${err.title}`,
        tone: err.severity === "critical" || err.severity === "high" ? "red" : "amber",
      });
    }
    for (const inc of openIncidents.slice(0, 4)) {
      ev.push({
        id: `inc-${inc.provider}`,
        ts: inc.started_at ?? "",
        kind: "incident",
        label: "Provider incident",
        detail: `${fmtProvider(inc.provider)} â€” ${inc.title}`,
        tone: "red",
      });
    }
    return ev
      .filter((e) => e.ts)
      .sort((a, b) => b.ts.localeCompare(a.ts))
      .slice(0, 10);
  }, [connected, openAlerts, errorIssues, openIncidents]);

  // API Performance: REAL error counts bucketed by day (last 7 days).
  const perfBars = useMemo(() => {
    const days: { label: string; count: number }[] = [];
    if (!errors) return days; // fetch failed â†’ insufficient data
    const now = Date.now();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now - i * 86400000);
      days.push({ label: d.toLocaleDateString(undefined, { weekday: "short" }), count: 0 });
    }
    for (const err of errorIssues) {
      if (!err.created_at) continue;
      const idx = Math.floor((now - new Date(err.created_at).getTime()) / 86400000);
      if (idx >= 0 && idx < 7) days[6 - idx].count += 1;
    }
    return days;
  }, [errors, errorIssues]);

  const monitoringActive =
    connected.length > 0 || (repos ?? []).length > 0 || (stats?.scans_total ?? 0) > 0;

  // Overall health overview â€” derived from REAL signals only.
  type HealthStatus = "Healthy" | "Degraded" | "Unavailable" | "Unknown";
  const healthStatus: HealthStatus = useMemo(() => {
    if (connections === null && errors === null && incidents === null && stats === null) return "Unknown";
    if (openIncidents.length > 0 || connected.some((c) => c.last_error)) return "Degraded";
    if (errors !== null && (errors.total ?? 0) > 0) return "Degraded";
    if (monitoringActive) return "Healthy";
    return "Unavailable";
  }, [connections, errors, incidents, stats, openIncidents, connected, monitoringActive]);

  const healthTone = (s: HealthStatus) =>
    s === "Healthy" ? "green" : s === "Degraded" ? "amber" : "gray";

  // Open issues sorted Critical â†’ High â†’ Medium â†’ Low; each links to its detail page.
  const openIssues = useMemo(() => {
    const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    return [...errorIssues].sort(
      (a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9)
    );
  }, [errorIssues]);

  const lastUpdated =
    connected.map((c) => c.connected_at ?? "").concat(openAlerts.map((a) => a.created_at ?? "")).sort().slice(-1)[0] || null;

  if (loading) {
    return (
      <div className="mc-grid mc-stack" style={{ padding: 4 }}>
        <SkeletonGrid count={6} card />
        <Skeleton style={{ height: 160 }} />
        <Skeleton style={{ height: 220 }} />
      </div>
    );
  }

  if (loadError && !connections) {
    return <ErrorCard title="Dashboard failed to load" body={loadError} />;
  }

  return (
    <div className="mc-grid mc-stack" style={{ padding: 4 }}>
      {/* â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Monitoring Dashboard</h1>
          <p className="mc-header-note" style={{ margin: "4px 0 0" }}>
            {connected.length} connected provider{connected.length !== 1 ? "s" : ""} Â·{" "}
            {(repos ?? []).length} monitored repositor{(repos ?? []).length !== 1 ? "ies" : "y"}
            {lastUpdated ? ` Â· updated ${timeAgo(lastUpdated)}` : ""}
          </p>
        </div>
        <Link href="/dashboard/health" className="mc-status" style={{ textDecoration: "none" }}>
          <span className={`mc-dot ${healthTone(healthStatus)}`} />
          {healthStatus}
        </Link>
      </div>

      {/* â”€â”€ Metric cards (real) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-grid mc-cards">
        <StatCard label="Connections" value={connected.length} tone={connected.length > 0 ? "accent" : "gray"} delta="provider API keys connected" />
        <StatCard
          label="Monitored APIs"
          value={stats ? stats.monitored_api_count : "—"}
          tone={stats && stats.monitored_api_count > 0 ? "green" : "gray"}
          delta={stats ? "changelogs watched daily" : "no data"}
        />
        <StatCard
          label="Degraded"
          value={connected.filter((c) => c.last_error).length}
          tone={connected.some((c) => c.last_error) ? "amber" : "gray"}
          delta={connected.some((c) => c.last_error) ? "connections with collector errors" : "all connections healthy"}
        />
        <StatCard label="Incidents" value={openIncidents.length} tone={openIncidents.length > 0 ? "red" : "gray"} delta={openIncidents.length === 0 && incidents ? "no active incidents" : undefined} />
        <StatCard
          label="API Errors"
          value={errors ? errors.total : "Unknown"}
          tone={(errors?.total ?? 0) > 0 ? "red" : "gray"}
          delta={errors ? `${errors.critical ?? 0} critical` : "no data"}
        />
        <StatCard
          label="Potential Breaks"
          value={alerts ? openAlerts.length : "Unknown"}
          tone={openAlerts.length > 0 ? "amber" : "gray"}
          delta={openAlerts.length === 0 ? "no open alerts" : undefined}
        />
        <StatCard
          label="Scans Completed"
          value={stats ? stats.scans_completed : "Unknown"}
          tone={(stats?.scans_completed ?? 0) > 0 ? "green" : "gray"}
          delta={stats && stats.last_scan_at ? `last ${timeAgo(stats.last_scan_at)}` : "no scans yet"}
        />
      </div>

      {/* â”€â”€ API Performance â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>API Performance</h3>
        {perfBars.length === 0 ? (
          <p className="mc-empty">
            No performance history yet â€” error telemetry begins once monitoring runs. (Response-time
            telemetry is not collected; this graph plots real detected API errors.)
          </p>
        ) : (
          <>
            <div className="mc-bars">
              {perfBars.map((b) => (
                <div key={b.label} className={`mc-bar ${b.count > 0 ? "red" : "green"}`}>
                  <b style={{ height: `${Math.max(b.count > 0 ? 8 : 2, (b.count / (perfBars.reduce((s, x) => s + x.count, 0) || 1)) * 100)}px` }} />
                  <span>{b.count}</span>
                  <small>{b.label}</small>
                </div>
              ))}
            </div>
            <p className="mc-sub" style={{ marginTop: 8 }}>
              Real API errors per day (last 7 days) â€” {errorIssues.length} total detected.
            </p>
          </>
        )}
      </div>

      {/* â”€â”€ Open Incidents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>Open Incidents</h3>
        {openIncidents.length === 0 ? (
          <p className="mc-empty">No active incidents.</p>
        ) : (
          <div>
            {openIncidents.slice(0, 6).map((inc, i) => (
              <div key={`${inc.provider}-${i}`} className="mc-row">
                <span className="mc-dot red" />
                <span style={{ minWidth: 0, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  <span style={{ fontWeight: 600 }}>{fmtProvider(inc.provider)}</span> â€” {inc.title}
                </span>
                <Badge tone="red" dot>{inc.status}</Badge>
                <span className="mc-sub" style={{ whiteSpace: "nowrap" }}>{timeAgo(inc.started_at)}</span>
              </div>
            ))}
          </div>
        )}
        <Link href="/dashboard/health/incidents" style={{ fontSize: 12, color: "var(--accent)" }}>
          View all incidents â†’
        </Link>
      </div>

      {/* â”€â”€ API Usage (real: changelog monitors + code detections) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>API Usage</h3>
        <div className="mc-grid mc-cards" style={{ marginBottom: 12 }}>
          <StatCard
            label="Monitored Changelogs"
            value={stats ? stats.monitored_api_count : "—"}
            tone={stats && stats.monitored_api_count > 0 ? "green" : "gray"}
            delta={stats ? "provider changelogs scanned daily" : "no data"}
          />
          <StatCard
            label="Integrations in Code"
            value={stats ? stats.providers_monitored : "—"}
            tone={stats && stats.providers_monitored > 0 ? "accent" : "gray"}
            delta={stats && stats.providers_monitored === 0 ? "connect a repo and scan to detect" : "detected by static analysis"}
          />
          <StatCard label="Findings" value={stats ? stats.findings_total : "—"} tone={(stats?.findings_open ?? 0) > 0 ? "amber" : "gray"} delta={stats ? `${stats.findings_open} open` : undefined} />
          <StatCard label="Scans Completed" value={stats ? stats.scans_completed : "—"} tone={(stats?.scans_completed ?? 0) > 0 ? "green" : "gray"} />
        </div>
        <p className="mc-empty" style={{ marginTop: 0 }}>
          {stats && stats.providers_monitored === 0
            ? "No API integrations detected in your code yet — run a repository scan to map which third-party APIs you use."
            : "API usage is detected from real repository scans (static analysis of imports and SDK calls)."}
        </p>
        <div className="mc-actions">
          <Link href="/dashboard/health/code-usage" className="btn btn-secondary">API Usage in Code</Link>
          <Link href="/dashboard/health/sdk" className="btn btn-secondary">SDK / Library Checker</Link>
          <Link href="/dashboard/health/scanner" className="btn btn-secondary">Run Repository Scan</Link>
        </div>
      </div>

      {/* â”€â”€ Recent Activity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>Recent Activity</h3>
        {activity.length === 0 ? (
          <p className="mc-empty">
            No activity yet â€” events appear when providers are connected, keys verified, incidents
            detected, or scans complete.
          </p>
        ) : (
          <div>
            {activity.map((e) => (
              <div key={e.id} className="mc-row">
                <span className={`mc-dot ${dotTone(e.tone)}`} />
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ display: "block", fontWeight: 600 }}>{e.label}</span>
                  <span style={{ display: "block", fontSize: 12, color: "var(--muted)" }}>{e.detail}</span>
                </span>
                <span className="mc-sub" style={{ whiteSpace: "nowrap" }}>{timeAgo(e.ts)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* â”€â”€ Code Intelligence (repository data ONLY here) â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>Code Intelligence</h3>
        {!stats || (stats.repos === 0 && (repos ?? []).length === 0) ? (
          <p className="mc-empty">
            No repositories monitored. <Link href="/dashboard/settings/integrations" style={{ color: "var(--accent)" }}>Connect a GitHub repository</Link> to enable code intelligence.
          </p>
        ) : (
          <div className="mc-grid mc-cards" style={{ marginBottom: 12 }}>
            <StatCard label="Repositories" value={stats.repos} tone="accent" />
            <StatCard label="API Integrations" value={stats.providers_monitored} tone="accent" delta="detected in code" />
            <StatCard label="Scans Completed" value={stats.scans_completed} tone="green" delta={stats.last_scan_at ? `last ${timeAgo(stats.last_scan_at)}` : undefined} />
            <StatCard label="Findings" value={stats.findings_total} tone={stats.findings_open > 0 ? "amber" : "gray"} delta={`${stats.findings_open} open`} />
            <StatCard label="Auto-Fix PRs" value={stats.prs_created} tone={stats.prs_created > 0 ? "green" : "gray"} delta={`${stats.fixes_created} fixes`} />
          </div>
        )}
      </div>

      {/* â”€â”€ Potential API Breaks (real open alerts) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>Potential API Breaks</h3>
        {!alerts ? (
          <p className="mc-empty">No alert data available.</p>
        ) : openAlerts.length === 0 ? (
          <p className="mc-empty">No potential breaks detected.</p>
        ) : (
          <table className="mc-table responsive-cards">
            <thead>
              <tr>
                <th>Detected change</th>
                <th>Affected integration</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Detected</th>
              </tr>
            </thead>
            <tbody>
              {openAlerts.slice(0, 8).map((a) => (
                <tr key={a.id}>
                  <td data-label="Detected change" style={{ fontWeight: 600 }}>{a.change_type}</td>
                  <td data-label="Affected integration">{a.repo_name}</td>
                  <td data-label="Severity"><Badge tone={severityTone(a.severity)} dot>{severityLabel(a.severity)}</Badge></td>
                  <td data-label="Status" style={{ fontSize: 12 }}>{a.status}</td>
                  <td data-label="Detected" style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>{timeAgo(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ marginTop: 10 }}>
          <Link href="/dashboard/alerts" style={{ fontSize: 12, color: "var(--accent)" }}>View all alerts â†’</Link>
        </div>
      </div>

      {/* â”€â”€ Open Health Issues (real, severity-sorted, linked) â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>Open Health Issues</h3>
        {!errors ? (
          <p className="mc-empty">No issue data available.</p>
        ) : openIssues.length === 0 ? (
          <p className="mc-empty">No open health issues detected.</p>
        ) : (
          <div>
            {openIssues.slice(0, 8).map((iss) => (
              <Link
                key={iss.id}
                href={`/dashboard/health/issues/${iss.id}`}
                className="mc-row"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <span className={`mc-dot ${severityTone(iss.severity) === "red" ? "red" : severityTone(iss.severity) === "amber" ? "amber" : "gray"}`} />
                <span style={{ minWidth: 0, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  <span style={{ fontWeight: 600 }}>{iss.title}</span>{" "}
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>Â· {iss.provider}</span>
                </span>
                <Badge tone={severityTone(iss.severity)} dot>{severityLabel(iss.severity)}</Badge>
                <span className="mc-sub" style={{ whiteSpace: "nowrap" }}>{timeAgo(iss.created_at)}</span>
              </Link>
            ))}
          </div>
        )}
        <Link href="/dashboard/health/issues" style={{ fontSize: 12, color: "var(--accent)" }}>
          View all issues â†’
        </Link>
      </div>

      {/* â”€â”€ Quick Actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="mc-panel">
        <h3>Quick Actions</h3>
        <div className="mc-actions">
          <Link href="/dashboard/settings/integrations" className="btn btn-primary">+ Connect Provider or Repository</Link>
          <Link href="/dashboard/health/scanner" className="btn btn-secondary">Run Repository Scan</Link>
          <Link href="/dashboard/health/incidents" className="btn btn-secondary">View Incidents</Link>
          <Link href="/dashboard/alerts" className="btn btn-secondary">View Alerts</Link>
        </div>
      </div>
    </div>
  );
}