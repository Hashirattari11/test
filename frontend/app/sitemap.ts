import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Public marketing pages only — private/authenticated routes are never listed.
export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  const pages: { path: string; priority: number }[] = [
    { path: "", priority: 1 },
    { path: "/pricing", priority: 0.8 },
    { path: "/privacy", priority: 0.3 },
    { path: "/terms", priority: 0.3 },
    { path: "/cookies", priority: 0.2 },
    { path: "/security", priority: 0.2 },
    { path: "/acceptable-use", priority: 0.2 },
    { path: "/contact", priority: 0.3 },
  ];
  return pages.map(({ path, priority }) => ({
    url: `${SITE_URL}${path}`,
    lastModified,
    changeFrequency: "weekly",
    priority,
  }));
}