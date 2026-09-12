"use client";

import { useMemo, useState } from "react";
import { DOCS } from "@/lib/docs";

export function DocsSearch() {
  const [q, setQ] = useState("");
  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return [];
    return DOCS.filter(
      (d) =>
        d.title.toLowerCase().includes(term) ||
        d.summary.toLowerCase().includes(term) ||
        d.section.toLowerCase().includes(term) ||
        d.content.some((b) => (b.t === "p" || b.t === "tip") && b.x.toLowerCase().includes(term))
    ).slice(0, 8);
  }, [q]);

  return (
    <div style={{ maxWidth: 560, margin: "0 auto", padding: "0 16px 8px" }}>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search documentation…"
        aria-label="Search documentation"
        className="p-input"
        style={{ width: "100%", padding: 12, borderRadius: 10, fontSize: 15 }}
      />
      {q.trim() && (
        <div className="p-docs-results" style={{ marginTop: 8, borderRadius: 12, overflow: "hidden" }}>
          {results.length === 0 && (
            <div className="p" style={{ padding: 12, opacity: 0.6, fontSize: 14 }}>No articles match “{q}”.</div>
          )}
          {results.map((r) => (
            <a
              key={r.slug}
              href={`/docs/${r.slug}`}
              style={{ display: "block", padding: "10px 12px", textDecoration: "none", fontSize: 14 }}
              className="p-docs-result"
            >
              <strong style={{ display: "block", fontSize: 14 }}>{r.title}</strong>
              <span style={{ opacity: 0.6, fontSize: 12 }}>{r.section}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}