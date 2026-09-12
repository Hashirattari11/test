import type { Metadata } from "next";
import PricingClient from "../../components/PricingClient";
import { SITE_URL } from "../../lib/site";

export const metadata: Metadata = {
  title: "Pricing & Plans",
  description:
    "Simple, transparent pricing for API monitoring. Starter $500/mo, Growth $2,000/mo, Enterprise custom. All plans include a 14-day free trial — no credit card required.",
  alternates: { canonical: SITE_URL + "/pricing" },
  robots: { index: true, follow: true },
};

export default function Page() {
  return <PricingClient />;
}