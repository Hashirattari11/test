"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { listRepos, Repo } from "../lib/api";

interface RepositorySelectorProps {
  /** Include an explicit "All Repositories" option (aggregate views only). */
  allowAll?: boolean;
  /** Optional controlled value (defaults to the ?repository_id= URL param). */
  value?: string;
  /** Fired after the selection is written to the URL. */
  onChange?: (repoId: string) => void;
  style?: React.CSSProperties;
}

/**
 * One reusable repository selector for every repository-scoped page.
 *
 * The selected repository lives in the URL (?repository_id=...) — never only in
 * React state — so the choice survives refresh/back and every page shares the
 * same behavior. On repo-scoped views (allowAll=false) the first connected
 * repository is auto-selected so a page never silently shows ALL repositories.
 */
export default function RepositorySelector({
  allowAll = false,
  value,
  onChange,
  style,
}: RepositorySelectorProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    listRepos()
      .then((r) => {
        if (!alive) return;
        setRepos(r || []);
        // Repo-scoped views: auto-select the first repo instead of silently
        // showing an aggregate of every repository.
        if (!allowAll && r && r.length > 0 && !searchParams.get("repository_id")) {
          const params = new URLSearchParams(searchParams.toString());
          params.set("repository_id", r[0].id);
          router.replace(`${window.location.pathname}?${params.toString()}`, { scroll: false });
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading && repos.length === 0) {
    return <div className="loading">Loading repositories…</div>;
  }
  if (repos.length === 0) {
    return <p className="muted small">No repositories connected. Connect one first.</p>;
  }

  const urlRepo = searchParams.get("repository_id") ?? "";
  const selected = value !== undefined ? value : urlRepo || (allowAll ? "" : repos[0].id);

  const change = (repoId: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (repoId) params.set("repository_id", repoId);
    else params.delete("repository_id");
    router.push(`${window.location.pathname}?${params.toString()}`, { scroll: false });
    onChange?.(repoId);
  };

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      <label className="muted small" style={{ margin: 0 }}>Repository</label>
      <select
        className="input"
        value={selected}
        onChange={(e) => change(e.target.value)}
        style={{ minWidth: 220, ...style }}
        aria-label="Repository"
      >
        {allowAll && <option value="">All Repositories</option>}
        {repos.map((r) => (
          <option key={r.id} value={r.id}>{r.full_name}</option>
        ))}
      </select>
    </span>
  );
}