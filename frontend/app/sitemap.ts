import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";
import { DOCS } from "@/lib/docs";

// Public marketing/legal/docs pages only — private/authenticated routes
// (dashboard, admin, auth, authorize) and noindexed pages (/login) are
// never listed.
export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  const pages: { path: string; priority: number; changeFrequency: "weekly" | "monthly" }[] = [
    { path: "", priority: 1, changeFrequency: "weekly" },
    { path: "/pricing", priority: 0.8, changeFrequency: "weekly" },
    { path: "/docs", priority: 0.7, changeFrequency: "weekly" },
    { path: "/contact", priority: 0.3, changeFrequency: "monthly" },
    { path: "/privacy", priority: 0.3, changeFrequency: "monthly" },
    { path: "/terms", priority: 0.3, changeFrequency: "monthly" },
    { path: "/security", priority: 0.2, changeFrequency: "monthly" },
    { path: "/acceptable-use", priority: 0.2, changeFrequency: "monthly" },
    { path: "/cookies", priority: 0.2, changeFrequency: "monthly" },
  ];

  const docPages = DOCS.map((doc) => ({
    url: `${SITE_URL}/docs/${doc.slug}`,
    lastModified,
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  return [
    ...pages.map(({ path, priority, changeFrequency }) => ({
      url: `${SITE_URL}${path}`,
      lastModified,
      changeFrequency,
      priority,
    })),
    ...docPages,
  ];
}
