// Central site config — single source of truth for SEO metadata.
export const SITE_URL = "https://frontend-eight-phi-60.vercel.app";
export const SITE_NAME = "Breaklytix";
export const SITE_DESCRIPTION =
  "Detect the third-party APIs your repos use and get alerted the moment a provider ships a breaking change.";

// Support contact. Configure via NEXT_PUBLIC_SUPPORT_EMAIL; falls back to the
// project's actual support address (also shown on the login page).
export const SUPPORT_EMAIL =
  process.env.NEXT_PUBLIC_SUPPORT_EMAIL || "hashirattari73@gmail.com";

// Legal operator placeholder — replace with the registered company name/address
// before a commercial launch (see NEXT_PUBLIC_LEGAL_ENTITY / _ADDRESS).
export const LEGAL_ENTITY =
  process.env.NEXT_PUBLIC_LEGAL_ENTITY || "Breaklytix";
export const LEGAL_ADDRESS = process.env.NEXT_PUBLIC_LEGAL_ADDRESS || "";