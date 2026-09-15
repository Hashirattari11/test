import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getDoc, docsBySection, relatedDocs, prevNext, type DocBlock } from "@/lib/docs";
import { LogoMark } from "@/components/Logo";

export function generateStaticParams() {
  return docsBySection().flatMap((g) => g.articles.map((a) => ({ slug: a.slug })));
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const doc = getDoc(params.slug);
  if (!doc) return {};
  return {
    title: `${doc.title} | Breaklytix Documentation`,
    description: doc.summary,
    robots: { index: true, follow: true },
    alternates: { canonical: `https://frontend-eight-phi-60.vercel.app/docs/${doc.slug}` },
  };
}

function Block({ b }: { b: DocBlock }) {
  switch (b.t) {
    case "h":
      return <h2 className="h2" style={{ fontSize: 20, margin: "28px 0 8px" }}>{b.x}</h2>;
    case "p":
      return <p className="p" style={{ marginBottom: 12, lineHeight: 1.7 }}>{b.x}</p>;
    case "tip":
      return (
        <div style={{ borderRadius: 10, padding: "12px 14px", margin: "16px 0", fontSize: 14, lineHeight: 1.6, background: "var(--accent-soft, rgba(99,91,255,0.08))", border: "1px solid rgba(99,91,255,0.25)" }}>
          <strong style={{ display: "block", marginBottom: 2 }}>Tip</strong>
          {b.x}
        </div>
      );
    case "ul":
      return (
        <ul style={{ margin: "8px 0 16px", paddingLeft: 20, display: "grid", gap: 6 }}>
          {b.x.map((li, i) => (
            <li key={i} style={{ lineHeight: 1.6 }}>{li}</li>
          ))}
        </ul>
      );
    case "code":
      return (
        <pre style={{ padding: 14, borderRadius: 10, overflowX: "auto", fontSize: 13, lineHeight: 1.6, background: "var(--code-bg, #0f1117)", color: "#e2e8f0", margin: "12px 0 16px" }}>{b.x}</pre>
      );
    default:
      return null;
  }
}

export default function DocArticlePage({ params }: { params: { slug: string } }) {
  const doc = getDoc(params.slug);
  if (!doc) notFound();

  const groups = docsBySection();
  const related = relatedDocs(doc.slug);
  const { prev, next } = prevNext(doc.slug);

  return (
    <div className="p-docs" style={{ paddingTop: 64 }}>
      <div className="p-docs-layout" style={{ maxWidth: 1120, margin: "0 auto", padding: "0 24px 80px" }}>
        {/* Left nav (desktop) */}
        <nav className="p-docs-nav" aria-label="Documentation sections" style={{ position: "sticky", top: 24, maxHeight: "calc(100vh - 48px)", overflowY: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <LogoMark size={22} />
            <a href="/docs" style={{ fontWeight: 700, fontSize: 15, textDecoration: "none", color: "inherit" }}>Docs home</a>
          </div>
          {groups.map((g) => (
            <div key={g.section} style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.6, opacity: 0.5, marginBottom: 6 }}>{g.section}</div>
              {g.articles.map((a) => (
                <a
                  key={a.slug}
                  href={`/docs/${a.slug}`}
                  className={`p-docs-navlink ${a.slug === doc.slug ? "active" : ""}`}
                  aria-current={a.slug === doc.slug ? "page" : undefined}
                  style={{
                    display: "block",
                    padding: "3px 0 3px 10px",
                    fontSize: 13,
                    textDecoration: "none",
                    borderLeft: a.slug === doc.slug ? "2px solid var(--accent, #635bff)" : "2px solid transparent",
                    color: a.slug === doc.slug ? "var(--accent, #635bff)" : "inherit",
                    opacity: a.slug === doc.slug ? 1 : 0.7,
                  }}
                >
                  {a.title}
                </a>
              ))}
            </div>
          ))}
        </nav>

        {/* Article */}
        <article style={{ minWidth: 0 }}>
          {/* Mobile collapsible nav */}
          <details className="p-docs-mobilenav" style={{ marginBottom: 20 }}>
            <summary style={{ cursor: "pointer", fontSize: 14, fontWeight: 600, padding: "10px 12px", borderRadius: 10, border: "1px solid var(--border, rgba(128,128,128,.22))", background: "var(--surface, #fff)" }}>
              {doc.section} · Contents
            </summary>
            <div style={{ padding: "8px 4px" }}>
              {groups.map((g) => (
                <div key={g.section} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", opacity: 0.5, margin: "6px 0" }}>{g.section}</div>
                  {g.articles.map((a) => (
                    <a key={a.slug} href={`/docs/${a.slug}`} style={{ display: "block", padding: "3px 8px", fontSize: 13.5, textDecoration: "none", color: "inherit", fontWeight: a.slug === doc.slug ? 700 : 400 }}>{a.title}</a>
                  ))}
                </div>
              ))}
            </div>
          </details>

          <header style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 0.8, opacity: 0.5, marginBottom: 6 }}>{doc.section}</div>
            <h1 className="h1" style={{ fontSize: 28, marginBottom: 8 }}>{doc.title}</h1>
            <p className="p" style={{ opacity: 0.7, maxWidth: 640 }}>{doc.summary}</p>
          </header>
          <div className="p-docs-body" style={{ maxWidth: 680 }}>
            {doc.content.map((b, i) => (
              <Block key={i} b={b} />
            ))}
          </div>

          {related.length > 0 && (
            <div style={{ marginTop: 36, paddingTop: 20, borderTop: "1px solid var(--border, rgba(128,128,128,0.2))" }}>
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.6, opacity: 0.5, marginBottom: 10 }}>Related articles</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {related.map((r) => (
                  <a key={r.slug} href={`/docs/${r.slug}`} className="btn btn-secondary btn-sm" style={{ textDecoration: "none" }}>{r.title}</a>
                ))}
              </div>
            </div>
          )}

          {(prev || next) && (
            <nav aria-label="Article pagination" style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 32 }}>
              {prev ? (
                <a href={`/docs/${prev.slug}`} style={{ textDecoration: "none", display: "block", maxWidth: "48%" }}>
                  <span style={{ fontSize: 12, opacity: 0.5 }}>← Previous</span>
                  <strong style={{ display: "block" }}>{prev.title}</strong>
                </a>
              ) : <span />}
              {next ? (
                <a href={`/docs/${next.slug}`} style={{ textDecoration: "none", display: "block", textAlign: "right", maxWidth: "48%" }}>
                  <span style={{ fontSize: 12, opacity: 0.5 }}>Next →</span>
                  <strong style={{ display: "block" }}>{next.title}</strong>
                </a>
              ) : <span />}
            </nav>
          )}
        </article>
      </div>
    </div>
  );
}