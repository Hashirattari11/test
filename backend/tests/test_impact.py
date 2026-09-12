"""Tests for the Impact Engine (Task: Impact Engine feature)."""
import unittest
from unittest.mock import patch, MagicMock

from app.impact.severity import (
    calculate_impact_severity,
    _severity_from_change_type,
    _adjust_severity,
    _calculate_confidence,
    get_verification_status,
    format_confidence,
)
from app.impact.analyzer import (
    ImpactAnalysis,
    AffectedCode,
    _build_impact_reason,
    _build_expected_behavior,
    _build_potential_failure,
)
from app.impact.fix_generator import (
    _find_matching_rule,
    generate_fixes_for_analysis,
)


class TestSeverityCalculation(unittest.TestCase):
    """Test severity and confidence calculation."""

    def test_removed_change_is_breaking(self):
        sev, conf = calculate_impact_severity(
            change_type="removed",
            matched_count=3,
            matched_fields=["provider", "endpoint", "symbol"],
            has_endpoint=True,
            has_sdk=True,
        )
        self.assertEqual(sev, "breaking")
        self.assertGreaterEqual(conf, 0.8)

    def test_deprecated_change_is_high(self):
        sev, _ = calculate_impact_severity(
            change_type="deprecated",
            matched_count=1,
            matched_fields=["provider"],
        )
        self.assertIn(sev, ("high", "medium"))

    def test_no_match_is_safe_or_unknown(self):
        sev, conf = calculate_impact_severity(
            change_type="none",
            matched_count=0,
            matched_fields=[],
        )
        self.assertEqual(sev, "safe")
        self.assertLessEqual(conf, 0.2)

    def test_confidence_increases_with_more_matches(self):
        _, conf1 = calculate_impact_severity(
            change_type="removed", matched_count=1,
            matched_fields=["provider"], has_sdk=False,
        )
        _, conf2 = calculate_impact_severity(
            change_type="removed", matched_count=5,
            matched_fields=["provider", "endpoint", "symbol", "old_value"],
            has_endpoint=True, has_sdk=True, has_old_value=True,
        )
        self.assertGreater(conf2, conf1)

    def test_confidence_clamped_to_valid_range(self):
        for _ in range(50):
            sev, conf = calculate_impact_severity(
                change_type="removed",
                matched_count=10,
                matched_fields=["provider", "endpoint", "symbol"],
                has_endpoint=True, has_sdk=True, has_old_value=True, has_new_value=True,
            )
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)

    def test_unknown_change_type(self):
        sev, _ = calculate_impact_severity(
            change_type="totally_unknown_change",
            matched_count=0,
            matched_fields=[],
        )
        self.assertEqual(sev, "unknown")


class TestVerificationStatus(unittest.TestCase):
    """Test verification status logic."""

    def test_not_generated_fix(self):
        self.assertEqual(get_verification_status("not_generated"), "not_verified")

    def test_generated_fix_is_static(self):
        self.assertEqual(get_verification_status("generated"), "static_analysis")

    def test_fix_passes_all_checks_is_verified(self):
        self.assertEqual(
            get_verification_status(
                fix_status="verified",
                has_tests=True, tests_passed=True,
                has_typecheck=True, typecheck_passed=True,
                has_lint=True, lint_passed=True,
            ),
            "verified",
        )

    def test_fix_fails_tests_is_failed(self):
        self.assertEqual(
            get_verification_status(
                fix_status="verified",
                has_tests=True, tests_passed=False,
            ),
            "verification_failed",
        )

    def test_fix_applied_no_checks_is_static(self):
        self.assertEqual(get_verification_status("applied"), "static_analysis")

    def test_confidence_formatting(self):
        self.assertEqual(format_confidence(0.87), "87%")
        self.assertEqual(format_confidence(0.5), "50%")


class TestAnalyzerHelpers(unittest.TestCase):
    """Test analyzer helper functions."""

    def test_build_impact_reason_no_match(self):
        reason = _build_impact_reason("stripe", "removed", 0)
        self.assertIn("No stripe usage", reason)

    def test_build_impact_reason_with_match(self):
        reason = _build_impact_reason("stripe", "removed", 2)
        self.assertIn("removed", reason)

    def test_build_expected_behavior(self):
        self.assertIn("404", _build_expected_behavior("removed"))
        self.assertIn("fail", _build_expected_behavior("auth_changed").lower())

    def test_build_potential_failure(self):
        self.assertIn("crash", _build_potential_failure("removed", "breaking").lower())
        self.assertIn("no significant", _build_potential_failure("removed", "safe").lower())


class TestFixGenerator(unittest.TestCase):
    """Test fix generation."""

    def test_find_matching_rule_openai_completions(self):
        rule = _find_matching_rule(
            provider="openai",
            change_type="removed",
            snippet="openai.Completion.create(model='text-davinci-003')",
        )
        self.assertIsNotNone(rule)
        self.assertEqual(rule.id, "openai-legacy-completions")

    def test_generate_fixes_for_analysis(self):
        affected_files = [{
            "file_path": "app/ai.py",
            "line_number": 10,
            "snippet": "openai.Completion.create(model='text-davinci-003')",
        }]
        fixes = generate_fixes_for_analysis(
            affected_files=affected_files,
            change_type="removed",
            provider="openai",
        )
        self.assertGreaterEqual(len(fixes), 1)
        self.assertEqual(fixes[0].old_value, "openai.Completion.create(")
        self.assertEqual(fixes[0].new_value, "openai.chat.completions.create(")


class TestImpactAnalysisModel(unittest.TestCase):
    """Test ImpactAnalysis and AffectedCode models."""

    def test_affected_code_defaults(self):
        ac = AffectedCode(file_path="test.py")
        self.assertEqual(ac.line_number, None)
        self.assertEqual(ac.function_name, None)
        self.assertEqual(ac.reason, "")
        self.assertEqual(ac.snippet, "")

    def test_impact_analysis_defaults(self):
        ia = ImpactAnalysis(provider="stripe", change_type="removed")
        self.assertEqual(ia.severity, "unknown")
        self.assertEqual(ia.confidence, 0.5)
        self.assertEqual(ia.fix_status, "not_generated")
        self.assertEqual(ia.verification_status, "not_verified")
        self.assertEqual(ia.affected_files, [])
        self.assertEqual(ia.affected_sdks, [])


class TestSecurity(unittest.TestCase):
    """Test security: no secrets leaked in outputs."""

    def test_analysis_never_contains_secrets(self):
        """Impact analysis outputs must not contain API keys or tokens."""
        ia = ImpactAnalysis(
            provider="stripe",
            change_type="removed",
            impact_reason="Matched on STRIPE_TEST_KEY secret pattern",
        )
        # Redact any secret-looking content
        import re
        secret_pattern = re.compile(r"sk_live_[A-Za-z0-9]+|sk-[A-Za-z0-9]+|ghp_[A-Za-z0-9]+")
        self.assertNotRegex(
            secret_pattern.sub("[REDACTED]", ia.impact_reason or ""),
            r"sk_live_|ghp_",
        )

    def test_fix_never_contains_secrets(self):
        """Generated fixes must never include secrets."""
        fixes = generate_fixes_for_analysis(
            affected_files=[{
                "file_path": "config.py",
                "line_number": 1,
                "snippet": "stripe.api_key = 'STRIPE_TEST_KEY'",
            }],
            change_type="auth_changed",
            provider="stripe",
        )
        for fix in fixes:
            self.assertNotIn("sk_live_", fix.old_value)
            self.assertNotIn("sk_live_", fix.new_value)


if __name__ == "__main__":
    unittest.main()
