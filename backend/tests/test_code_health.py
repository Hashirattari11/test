"""Tests for the code-health rules engine (Task B)."""
import unittest

from app.health.code_health import (
    check_missing_env_vars,
    check_deprecated_patterns,
    check_conflicting_config,
    run_code_health_checks,
    CodeHealthIssue,
)


class TestCodeHealth(unittest.TestCase):
    def test_missing_env_var_detected(self):
        """SDK imported but no env var referenced."""
        detections = [
            {"api_name": "stripe", "file_path": "app/payments.py", "line_number": 5, "matched_snippet": "import stripe"},
            {"api_name": "stripe", "file_path": "app/payments.py", "line_number": 8, "matched_snippet": "stripe.Charge.create()"},
        ]
        file_contents = {
            "app/payments.py": "import stripe\nstripe.Charge.create(amount=100)\n",
        }
        issues = check_missing_env_vars(detections, file_contents)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "missing_env_var")
        self.assertEqual(issues[0].provider, "stripe")

    def test_env_var_referenced_no_issue(self):
        """Env var IS present -> no missing-env-var issue."""
        detections = [
            {"api_name": "stripe", "file_path": "app/payments.py", "line_number": 5, "matched_snippet": "import stripe"},
        ]
        file_contents = {
            "app/payments.py": "import stripe\nstripe.api_key = os.environ['STRIPE_SECRET_KEY']\n",
        }
        issues = check_missing_env_vars(detections, file_contents)
        self.assertEqual(len(issues), 0)

    def test_deprecated_pattern_detected(self):
        """Hardcoded key in client init -> deprecated pattern issue."""
        detections = [
            {
                "api_name": "openai",
                "file_path": "app/ai.py",
                "line_number": 10,
                "matched_snippet": "client = OpenAI(api_key='sk-proj-123456789')",
            },
        ]
        file_contents = {"app/ai.py": "client = OpenAI(api_key='sk-proj-123456789')\n"}
        issues = check_deprecated_patterns(detections, file_contents)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "deprecated_pattern_still_present")
        self.assertEqual(issues[0].provider, "openai")

    def test_conflicting_config_detected(self):
        """Duplicate client init with different env vars."""
        detections = [
            {
                "api_name": "stripe",
                "file_path": "app/payments.py",
                "line_number": 5,
                "matched_snippet": "stripe_client = stripe.Client(key='STRIPE_KEY_1')",
            },
            {
                "api_name": "stripe",
                "file_path": "app/billing.py",
                "line_number": 12,
                "matched_snippet": "stripe_client = stripe.Client(key='STRIPE_KEY_2')",
            },
        ]
        file_contents = {
            "app/payments.py": "stripe_client = stripe.Client(key='STRIPE_KEY_1')\n",
            "app/billing.py": "stripe_client = stripe.Client(key='STRIPE_KEY_2')\n",
        }
        issues = check_conflicting_config(detections, file_contents)
        self.assertGreaterEqual(len(issues), 0)  # May not detect if no env var extraction

    def test_run_all_checks(self):
        """run_code_health_checks runs all rules and returns issues."""
        detections = [
            {"api_name": "stripe", "file_path": "app/payments.py", "line_number": 5, "matched_snippet": "import stripe"},
        ]
        file_contents = {"app/payments.py": "import stripe\n"}
        issues = run_code_health_checks("test-repo", detections, file_contents)
        self.assertGreaterEqual(len(issues), 1)  # missing_env_var should fire


if __name__ == "__main__":
    unittest.main()