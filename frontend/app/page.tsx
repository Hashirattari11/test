import type { Metadata } from "next";
import LandingClient from "../components/LandingClient";
import { SITE_URL, SITE_DESCRIPTION } from "../lib/site";

export const metadata: Metadata = {
  title: "Automatically detect & fix breaking API changes",
  description: SITE_DESCRIPTION,
  alternates: { canonical: SITE_URL + "/" },
  robots: { index: true, follow: true },
  openGraph: {
    title: "Breaklytix — Never let a broken API catch you off guard",
    description: SITE_DESCRIPTION,
    url: SITE_URL + "/",
    type: "website",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Breaklytix",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Web",
  url: SITE_URL + "/",
  description: SITE_DESCRIPTION,
  offers: { "@type": "Offer", price: "500", priceCurrency: "USD" },
};

export default function Page() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <LandingClient />
    </>
  );
}