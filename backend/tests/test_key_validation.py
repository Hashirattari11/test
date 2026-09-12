"""Unit tests for real per-provider key validation (network mocked)."""
import unittest.mock as mock
import urllib.error

from app.health.key_validation import SUPPORTED, validate_provider_key


class _FakeResp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_supported_providers():
    # Every provider with a REAL probe must be registered; the always-present
    # core set must be there. New probes are additive (never shrink the core).
    assert {"openai", "github", "anthropic", "stripe", "sendgrid", "twilio"} <= SUPPORTED
    assert len(SUPPORTED) >= 30  # Session-8: real probes for the 44-provider matrix


def test_unknown_provider():
    ok, msg = validate_provider_key("definitely-not-real", "sk-1234567890abcdef")
    assert not ok
    assert "Unsupported provider" in msg


def test_twilio_requires_sid_token_format():
    ok, msg = validate_provider_key("twilio", "AC1234567890abcdef")
    assert not ok
    assert "sid:auth_token" in msg


@mock.patch("app.health.key_validation.urllib.request.urlopen")
def test_openai_valid(urlopen):
    urlopen.return_value = _FakeResp(200)
    ok, msg = validate_provider_key("openai", "OPENAI_TEST_KEY")
    assert ok
    assert "accepted" in msg


@mock.patch("app.health.key_validation.urllib.request.urlopen")
def test_openai_invalid(urlopen):
    urlopen.side_effect = urllib.error.HTTPError(
        "https://api.openai.com/v1/models", 401, "Unauthorized", None, None
    )
    ok, msg = validate_provider_key("openai", "OPENAI_TEST_KEY")
    assert not ok
    assert "rejected" in msg
    assert "401" in msg


@mock.patch("app.health.key_validation.urllib.request.urlopen")
def test_stripe_network_error(urlopen):
    urlopen.side_effect = urllib.error.URLError("Name or service not known")
    ok, msg = validate_provider_key("stripe", "STRIPE_TEST_KEY")
    assert not ok
    assert "unreachable" in msg


@mock.patch("app.health.key_validation.urllib.request.urlopen")
def test_github_valid_sends_user_agent(urlopen):
    urlopen.return_value = _FakeResp(200)
    ok, msg = validate_provider_key("github", "GITHUB_TEST_TOKEN")
    assert ok
    request = urlopen.call_args.args[0]
    # urllib normalizes header names to title-case; compare case-insensitively
    assert request.headers.get("User-Agent") or request.headers.get("User-agent") == "autofix-health"
    assert any(v == "Bearer GITHUB_TEST_TOKEN" for k, v in request.headers.items() if "Authorization" in k or "authorization" == k.lower())


@mock.patch("app.health.key_validation.urllib.request.urlopen")
def test_twilio_valid_uses_basic_auth(urlopen):
    urlopen.return_value = _FakeResp(200)
    ok, msg = validate_provider_key("twilio", "AC0123456789abcdef:secret-token-123")
    assert ok
    request = urlopen.call_args.args[0]
    auth = request.headers.get("Authorization", "")
    assert auth.startswith("Basic ")


@mock.patch("app.health.key_validation.urllib.request.urlopen")
def test_anthropic_sends_version_header(urlopen):
    urlopen.return_value = _FakeResp(200)
    ok, msg = validate_provider_key("anthropic", "ANTHROPIC_TEST_KEY")
    assert ok
    request = urlopen.call_args.args[0]
    headers = {k.lower(): v for k, v in request.headers.items()}
    assert headers.get("anthropic-version") == "2023-06-01"
    assert headers.get("x-api-key") == "ANTHROPIC_TEST_KEY"
