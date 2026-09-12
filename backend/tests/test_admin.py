"""Admin role / admin-panel tests.

These are pure unit tests (no live DB): the Supabase client and session lookup
are monkeypatched so the tests run offline, matching the project's existing
test style. Full 403/access behaviour is verified end-to-end against the
deployed environment instead.
"""
import pytest
from fastapi import HTTPException

from app import deps
from app.changelog import admin as changelog_admin


class FakeAdminUser:
    """Bag exposing .data like a PostgREST response."""
    def __init__(self, row):
        self.data = row


def _fake_fetch_user(user_dict):
    """Return a fetch_one that returns a specific user row (or None)."""
    def _fetch(table, match):
        assert table == "users"
        assert "id" in match
        return user_dict
    return _fetch


# ---------------------------------------------------------------------------
# require_admin dependency
# ---------------------------------------------------------------------------
def test_require_admin_ok(monkeypatch):
    monkeypatch.setattr(
        deps, "fetch_one",
        _fake_fetch_user({"id": "u1", "email": "a@b.com", "is_admin": True}),
    )
    result = deps.require_admin(user_id="u1")
    assert result["is_admin"] is True


def test_require_admin_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(
        deps, "fetch_one",
        _fake_fetch_user({"id": "u1", "email": "a@b.com", "is_admin": False}),
    )
    with pytest.raises(HTTPException) as exc:
        deps.require_admin(user_id="u1")
    assert exc.value.status_code == 403


def test_require_admin_rejects_missing_user(monkeypatch):
    monkeypatch.setattr(deps, "fetch_one", _fake_fetch_user(None))
    with pytest.raises(HTTPException) as exc:
        deps.require_admin(user_id="nobody")
    assert exc.value.status_code == 403


def test_require_admin_owner_fallback(monkeypatch):
    """Owner UUID is granted access even if is_admin is False in the DB (OR fallback)."""
    monkeypatch.setattr(
        deps, "fetch_one",
        _fake_fetch_user({"id": "3d206f17-7abc-4857-be29-00c8406ce16f", "is_admin": False}),
    )
    result = deps.require_admin(user_id="3d206f17-7abc-4857-be29-00c8406ce16f")
    # Owner is allowed even though is_admin is False (owner OR fallback).
    assert result["is_admin"] is False
    assert result["id"] == "3d206f17-7abc-4857-be29-00c8406ce16f"


# ---------------------------------------------------------------------------
# changelog/admin.is_admin()
# ---------------------------------------------------------------------------
def test_changelog_is_admin_true(monkeypatch):
    monkeypatch.setattr(
        changelog_admin, "db",
        lambda: _FakeTable(FakeAdminUser([{"is_admin": True}])),
    )
    assert changelog_admin.is_admin("u1") is True


def test_changelog_is_admin_false(monkeypatch):
    monkeypatch.setattr(
        changelog_admin, "db",
        lambda: _FakeTable(FakeAdminUser([{"is_admin": False}])),
    )
    assert changelog_admin.is_admin("u1") is False


def test_changelog_is_admin_owner(monkeypatch):
    # Owner short-circuits to True without a DB query dependency.
    monkeypatch.setattr(
        changelog_admin, "db",
        lambda: _raise_if_called(),
    )
    assert changelog_admin.is_admin("3d206f17-7abc-4857-be29-00c8406ce16f") is True


class _FakeTable:
    """Fluent fake for db().table(...).select(...).eq(...).execute()."""
    def __init__(self, response):
        self._response = response

    def table(self, name):
        return self

    def select(self, *cols, **kwargs):
        return self

    def eq(self, col, val):
        return self

    def execute(self):
        return self._response


def _raise_if_called():
    raise AssertionError("DB should not be called for owner shortcut")
