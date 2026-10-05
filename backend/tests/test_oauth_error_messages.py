"""Tests for user-safe GitHub OAuth failure messages.

The auth router must translate GitHub OAuth failures into curated, actionable
messages — never echo the caller-supplied redirect URI, the client secret, or
raw provider response bodies.
"""
import pytest

from app.github_client import GitHubError
from app.routers.auth import _safe_github_auth_detail

SECRET = "abcdef0123456789abcdef0123456789abcdef01"
REDIRECT_URI = "https://example.com/auth/callback?staging=1"


@pytest.mark.parametrize(
    ("github_error", "expected_fragment"),
    [
        (
            "OAuth error: incorrect_client_credentials: "
            "The client_id and/or client_secret passed are incorrect.",
            "configuration mismatch",
        ),
        (
            "OAuth error: bad_verification_code: "
            "The code passed is incorrect or expired.",
            "sign in again",
        ),
        (
            "OAuth error: redirect_uri_mismatch: "
            "The redirect_uri is not associated with a client application.",
            "callback URL",
        ),
        (
            "OAuth error: application_suspended: "
            "This application has been suspended.",
            "suspended",
        ),
        (
            "GitHub OAuth is not configured on the server.",
            "not configured",
        ),
    ],
)
def test_known_errors_map_to_safe_actionable_messages(github_error, expected_fragment):
    detail = _safe_github_auth_detail(GitHubError(github_error))
    assert expected_fragment.lower() in detail.lower()


def test_unknown_errors_stay_generic():
    detail = _safe_github_auth_detail(
        GitHubError("OAuth token exchange failed (500): boom")
    )
    assert detail == "GitHub sign-in could not be completed. Please try again."


@pytest.mark.parametrize("sensitive", [SECRET, REDIRECT_URI])
def test_details_never_echo_secrets_or_redirect_uris(sensitive):
    exc = GitHubError(
        f"OAuth error: incorrect_client_credentials: leak {sensitive}"
    )
    detail = _safe_github_auth_detail(exc)
    assert sensitive not in detail
