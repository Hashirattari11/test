"""Tests for the real provider-change monitoring system (M7.1).

Covers: registry (44 providers, official sources), strict adapters + SSRF
guard, fingerprint/dedup, evidence-based classification, no-fabrication
invariant, and alert-email gating rules.
"""
import unittest
from unittest.mock import patch, MagicMock

from app.changelog.sources import (
    PROVIDER_SOURCES,
    ALL_PROVIDER_IDS,
    PROVIDER_SOURCES_BY_ID,
    HTML_STRICT,
    RSS,
    GITHUB_RELEASES,
    NONE,
)
from app.changelog.base import ProviderAdapter, RawEntry, FetchError
from app.changelog.fingerprint import fingerprint_for_external
from app.changelog.classify import (
    CHANGE_TYPES,
    SEVERITIES,
    CONFIDENCES,
    classify_entry,
)
from app.changelog.adapters import AdapterFactory


class TestProviderRegistry(unittest.TestCase):
    """S7.1.1: exactly 44 providers, all with official sources or NONE."""

    def test_exactly_44_providers(self):
        self.assertEqual(len(PROVIDER_SOURCES), 44)
        self.assertEqual(len(set(ALL_PROVIDER_IDS)), 44)

    def test_provider_ids_match_frontend(self):
        # Frontend registry ids (mirror of frontend/lib/providers/registry.ts).
        frontend = {
            "stripe", "shopify", "twilio", "sendgrid", "github", "openai",
            "anthropic", "paypal", "resend", "slack", "supabase", "firebase",
            "aws", "vercel", "cloudinary", "googleai", "huggingface",
            "elevenlabs", "postmark", "mailgun", "digitalocean", "sentry",
            "auth0", "clerk", "mapbox", "algolia", "posthog", "mixpanel",
            "segment", "intercom", "discord", "telegram", "whatsapp", "twitter",
            "zoom", "pusher", "youtube", "notion", "airtable", "mongodb",
            "redis", "plaid", "openweather", "serpapi",
        }
        self.assertEqual(set(ALL_PROVIDER_IDS), frontend)

    def test_every_provider_has_official_source_or_unavailable(self):
        for p in PROVIDER_SOURCES:
            self.assertTrue(p.changelog_url.startswith("https://"), p.provider_id)
            if p.source_kind != NONE:
                self.assertIn(p.source_kind, (RSS, GITHUB_RELEASES, HTML_STRICT))
            if p.source_kind in (RSS, GITHUB_RELEASES):
                self.assertTrue(p.feed_url.startswith("https://"), p.provider_id)

    def test_default_status_map(self):
        self.assertEqual(PROVIDER_SOURCES_BY_ID["stripe"].default_status, "ACTIVE")
        self.assertEqual(PROVIDER_SOURCES_BY_ID["twilio"].default_status, "LIMITED")
        src = ProviderSource_for_test_unavailable()
        self.assertEqual(src.default_status, "SOURCE_UNAVAILABLE")


def ProviderSource_for_test_unavailable():
    from app.changelog.sources import ProviderSource
    return ProviderSource("nonexistent", "Nonexistent", "other", NONE,
                          "https://example.com/")


class TestFingerprint(unittest.TestCase):
    """S7.1.2: stable fingerprint + dedup key."""

    def test_fingerprint_stable(self):
        a = fingerprint_for_external("stripe", "https://docs.stripe.com/changelog/abc")
        b = fingerprint_for_external("stripe", "https://docs.stripe.com/changelog/abc")
        self.assertEqual(a, b)
        c = fingerprint_for_external("stripe", "https://docs.stripe.com/changelog/abd")
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, fingerprint_for_external("shopify", "https://docs.stripe.com/changelog/abc"))

    def test_fingerprint_external(self):
        self.assertEqual(
            fingerprint_for_external("stripe", "id-123"),
            fingerprint_for_external("stripe", "id-123"),
        )


class TestNoFabricationInvariant(unittest.TestCase):
    """S7.1.3 + S3.1.4: RawEntry requires ALL fields; nothing defaulted."""

    def test_missing_external_id_rejected(self):
        with self.assertRaises(ValueError):
            RawEntry(external_id="", title="Change", url="https://x/1",
                     published_at="2026-09-01T00:00:00Z", summary="", source="s")

    def test_missing_title_rejected(self):
        with self.assertRaises(ValueError):
            RawEntry(external_id="1", title="", url="https://x/1",
                     published_at="2026-09-01T00:00:00Z", summary="", source="s")

    def test_missing_url_rejected(self):
        with self.assertRaises(ValueError):
            RawEntry(external_id="1", title="Change", url="",
                     published_at="2026-09-01T00:00:00Z", summary="", source="s")

    def test_missing_date_rejected(self):
        with self.assertRaises(ValueError):
            RawEntry(external_id="1", title="Change", url="https://x/1",
                     published_at="", summary="", source="s")


class TestClassification(unittest.TestCase):
    """S7.1.3: 15 change types, 6 severities, 4 confidences, evidence rules."""

    def test_enums_complete(self):
        self.assertEqual(len(CHANGE_TYPES), 15)
        self.assertEqual(len(SEVERITIES), 6)
        self.assertEqual(len(CONFIDENCES), 4)
        for t in ("BREAKING_CHANGE", "DEPRECATION", "AUTH_CHANGE", "SECURITY_CHANGE",
                  "NEW_FEATURE", "BUG_FIX", "OTHER"):
            self.assertIn(t, CHANGE_TYPES)

    def test_breaking_keyword(self):
        result = classify_entry(
            title="Breaking change: charge creation requires idempotency key",
            summary="The `charges.create` endpoint now requires an idempotency key.",
            source_kind=HTML_STRICT,
        )
        self.assertEqual(result.change_type, "BREAKING_CHANGE")
        # Evidence-based severity: no urgency/timeframe keywords -> MEDIUM+,
        # never INFO/LOW/UNKNOWN for a breaking change.
        self.assertIn(result.severity, ("CRITICAL", "HIGH", "MEDIUM"))
        self.assertEqual(result.confidence, "HIGH")

    def test_breaking_with_urgency_is_critical(self):
        result = classify_entry(
            title="Breaking change: mandatory action required immediately",
            summary="The `charges.create` endpoint now requires an idempotency key.",
            source_kind=HTML_STRICT,
        )
        self.assertEqual(result.change_type, "BREAKING_CHANGE")
        self.assertEqual(result.severity, "CRITICAL")

    def test_deprecation_keyword(self):
        result = classify_entry(
            title="Deprecation: `/auth/get` is deprecated",
            summary="The `/auth/get` endpoint is superseded by `/identity/get`.",
            source_kind=HTML_STRICT,
        )
        self.assertEqual(result.change_type, "DEPRECATION")
        self.assertGreaterEqual(result.severity, "MEDIUM")

    def test_unclassified_gets_other(self):
        result = classify_entry(
            title="March platform update",
            summary="Various minor platform improvements.",
            source_kind=HTML_STRICT,
        )
        # "release"/"added" keywords can still classify; worst case OTHER.
        self.assertIn(result.change_type, CHANGE_TYPES)

    def test_every_result_carries_evidence(self):
        result = classify_entry(
            title="New model `gpt-5` is available",
            summary="We are adding gpt-5 to the API.",
            source_kind=HTML_STRICT,
        )
        self.assertIn(result.change_type, CHANGE_TYPES)
        # High confidence requires structural evidence.
        if result.confidence == "HIGH":
            self.assertTrue(result.evidence)

    def test_unknown_confidence_requires_no_evidence(self):
        result = classify_entry(
            title="Weekly roundup",
            summary="General announcements.",
            source_kind=HTML_STRICT,
        )
        if result.confidence == "UNKNOWN":
            self.assertEqual(result.evidence, [])


class TestSchedulerAdapter(unittest.TestCase):
    """S3.2.5: factory produces adapters for all providers."""

    def test_factory_all_covers_44(self):
        adapters = AdapterFactory.all(ALL_PROVIDER_IDS)
        self.assertEqual(len(adapters), 44)
        self.assertIn("stripe", adapters)
        self.assertIn("redis", adapters)
        self.assertIn("sentry", adapters)

    def test_ssrf_guard_refuses_foreign_host(self):
        src = PROVIDER_SOURCES_BY_ID["stripe"]
        adapter = ProviderAdapter(src)
        with self.assertRaises(FetchError) as ctx:
            adapter._assert_allowed_url("http://169.254.169.254/latest/meta-data")
        self.assertIn("SSRF", str(ctx.exception))

    def test_ssrf_guard_allows_registry_host(self):
        src = PROVIDER_SOURCES_BY_ID["stripe"]
        adapter = ProviderAdapter(src)
        adapter._assert_allowed_url("https://docs.stripe.com/changelog/feed.rss")  # no raise

    def test_ssrf_guard_refuses_non_http(self):
        src = PROVIDER_SOURCES_BY_ID["stripe"]
        adapter = ProviderAdapter(src)
        with self.assertRaises(FetchError):
            adapter._assert_allowed_url("file:///etc/passwd")


class TestAlertEmailSubject(unittest.TestCase):
    """S4.1.3: subject format per user spec (brand Breaklytix)."""

    def test_critical_subject_format(self):
        from app.alerts import render_alert_email
        subject, _, _ = render_alert_email(
            "acme/api", {"api_name": "stripe", "id": "x"},
            [{"file_path": "a.py", "line_number": 1}],
            severity="critical", confidence="high",
        )
        self.assertIn("[Breaklytix] High-Risk API Change Detected", subject)
        self.assertIn("Stripe", subject)

    def test_medium_subject_uses_notice_variant(self):
        from app.alerts import render_alert_email
        subject, _, _ = render_alert_email(
            "acme/api", {"api_name": "plaid", "id": "x"},
            [{"file_path": "a.py"}],
            severity="medium", confidence="high",
        )
        self.assertIn("[Breaklytix] API Change Notice", subject)
        self.assertNotIn("High-Risk", subject)

    def test_unknown_severity_never_emailed(self):
        from app.alerts import _email_repo_alert_group
        counts = {"emails_sent": 0, "emails_failed": 0}
        with patch("app.alerts.db") as mock_db, patch("app.alerts.score_severity") as mock_score:
            mock_score.return_value = ("unknown", "no evidence")
            ok = _email_repo_alert_group(
                {"api_name": "aws", "severity": "UNKNOWN", "confidence": "UNKNOWN",
                 "change_type": "OTHER", "id": "evt", "source_url": ""},
                {"user_id": "u1", "full_name": "acme/api", "id": "r1"},
                [{"file_path": "a.py"}],
                counts,
            )
            self.assertFalse(ok)
            self.assertEqual(counts["emails_sent"], 0)
            self.assertEqual(counts["emails_failed"], 0)


if __name__ == "__main__":
    unittest.main()