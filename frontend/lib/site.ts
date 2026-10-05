// Central site config — single source of truth for SEO metadata.
// Custom domain verified on Vercel (2026-10-01).
export const SITE_URL = "https://breaklytix.site";
export const SITE_NAME = "Breaklytix";
// Keep between 150–160 chars so search engines show the full snippet.
export const SITE_DESCRIPTION =
  "Breaklytix detects the third-party APIs your repos use, monitors 44+ provider changelogs around the clock, and alerts you the moment a breaking change ships.";

// Support contact. Configure via NEXT_PUBLIC_SUPPORT_EMAIL; falls back to the
// project's actual support address (also shown on the login page).
export const SUPPORT_EMAIL =
  process.env.NEXT_PUBLIC_SUPPORT_EMAIL || "hashirattari73@gmail.com";

// Legal operator placeholder — replace with the registered company name/address
// before a commercial launch (see NEXT_PUBLIC_LEGAL_ENTITY / _ADDRESS).
export const LEGAL_ENTITY =
  process.env.NEXT_PUBLIC_LEGAL_ENTITY || "Breaklytix";
export const LEGAL_ADDRESS = process.env.NEXT_PUBLIC_LEGAL_ADDRESS || "";