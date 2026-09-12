"""Tests for GitHub token fallback (stale-token handling).

Guards the fix for "Bad credentials (401)" scanning after a user re-auth:
the per-repo token snapshot goes stale, so we try fresher tokens and surface
a friendly 401 instead of raw GitHub JSON / 502.
"""
import pytest

from app.github_client import GitHubAuthError, GitHubError, call_with_token_fallback


def _ok(tok: str):
    def call(t: str):
        return {"used": t}
    return call


def _boom(tok: str, status: int = 401, msg: str | None = None):
    def call(t: str):
        raise GitHubError(msg or f"Failed ({status}): {tok} rejected ({status})")
    return call


def test_first_token_wins():
    result, used = call_with_token_fallback(["aaa", "bbb"], _ok("aaa"))
    assert result == {"used": "aaa"}
    assert used == "aaa"


def test_falls_back_when_snapshot_rejected():
    # aaa (stale snapshot) is rejected -> bbb (fresher user token) works.
    def call(t: str):
        if t == "aaa":
            raise GitHubError("Failed to list tree (401): Bad credentials")
        return {"used": t}

    result, used = call_with_token_fallback(["aaa", "bbb"], call)
    assert result == {"used": "bbb"}
    assert used == "bbb"


def test_all_rejected_raises_friendly_auth_error():
    with pytest.raises(GitHubAuthError) as ei:
        call_with_token_fallback(["aaa", "bbb"], _boom("x", 401))
    assert "expired" in str(ei.value)
    assert "reconnect" in str(ei.value)


def test_non_auth_error_raises_immediately():
    with pytest.raises(GitHubError) as ei:
        call_with_token_fallback(["aaa", "bbb"], _boom("x", 404, "Failed (404): nope"))
    assert "404" in str(ei.value)


def test_empty_candidates_raises_auth_error():
    with pytest.raises(GitHubAuthError) as ei:
        call_with_token_fallback([], _ok("x"))
    assert "No GitHub connection" in str(ei.value)


def test_non_401_error_skips_fallback_tokens():
    # A 404 means the repo/branch is missing, not the token — must NOT retry.
    with pytest.raises(GitHubError) as ei:
        call_with_token_fallback(["aaa", "bbb"], _boom("x", 404, "Failed (404): not found"))
    assert "404" in str(ei.value)