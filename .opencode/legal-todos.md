# Mission: Legal/Trust pages + Full Verification & Clean Code pass

## M1: Legal content pages (accurate, no fabrication) | status: completed
- [x] S1.1: lib/site.ts — SUPPORT_EMAIL (NEXT_PUBLIC_SUPPORT_EMAIL env) + legal placeholders
- [x] S1.2: components/LegalLayout.tsx — shared layout (header, TOC-ready, footer w/ 6 legal links)
- [x] S1.3: /privacy rewrite (accurate: OAuth data, scans, provider metadata, encrypted tokens, Resend, Stripe, retention, rights)
- [x] S1.4: /terms rewrite (14 required sections)
- [x] S1.5: /cookies (no tracking cookies; local/session storage; hosting platform cookie)
- [x] S1.6: /security (real practices: Fernet AES-128-CBC+HMAC, JWT, CORS, service-role server-side, PR scopes)
- [x] S1.7: /acceptable-use
- [x] S1.8: /contact (env-configurable email + GitHub issues; no invented emails)

## M2: Trust/SEO wiring + landing fixes | status: completed
- [x] S2.1: sitemap.ts + middleware publicPaths += 4 new pages
- [x] S2.2: LandingClient — honest stats (12/44+/1500/100%), badge, hero "Auto-fix PRs you review", footer 6 legal links, inline pricing fake claims removed, CTA "500+ teams" removed
- [x] S2.3: login page — SOC 2→OAuth 2.0, Read-only→Encrypted credentials, 10K+/500+/99.9%→12/44+/100%, "never push code"→"Auto-fix opens PRs — you review and merge", email→SUPPORT_EMAIL
- [x] S2.4: PricingClient — sales@autofix.example.com→/contact; fake SLA/SSO/on-premise/audit lines removed; FAQ annual 20% & NET 30 → honest; LegalFooter added
- [x] S2.5: no cookie consent banner (no non-essential cookies — documented on /cookies)

## M3: Verification + regression | status: completed
- [x] S3.1: npx tsc --noEmit clean (twice — incl. after SITE_URL fix)
- [x] S3.2: npm run build exit 0, 49/49 static (6 legal pages) — verified locally AND on Vercel
- [x] S3.3: backend pytest regression — 107 passed
- [x] S3.4: deployed (dpl_DeS9wg6k25RUF3QWSQPGDLXajFod READY → autofix-iota.vercel.app); LIVE: /privacy /terms /cookies /security /acceptable-use /contact all 200; sitemap.xml = autofix-iota URLs (all 8); / and /login 200. Also fixed SITE_URL (stale alias frontend-eight-phi-60 → autofix-iota) — commit 655934b.
- [x] S3.5: Final report delivered (STATUS READY). Provider-Repo separation re-verified by code trace: provider pages use only provider-connection endpoints (POST /health/provider-connections/{provider}/collect, h.py:960); zero repository_id in usage/quota/rate-limits pages; legacy repo-keyed history endpoints unused by provider flow.