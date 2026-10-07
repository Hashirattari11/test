"""Tests for the alert read-state lifecycle (unread badge -> mark read).

Covers:
- read_at surfaces in list_all_alerts output (unread = None)
- PATCH /repos/alerts/read marks only the OWNER's alerts (IDOR-safe)
- marking is idempotent (already-read rows are not re-touched)
- marking a subset updates exactly that subset
"""
from types import SimpleNamespace

import pytest

from app.routers import repos as repos_mod


class FakeQuery:
    """Fluent fake recording ops and applying basic PostgREST semantics."""

    def __init__(self, store, table):
        self._store = store
        self._table = table
        self.ops = []
        self._update_payload = None

    def select(self, *cols, **kwargs):
        self.ops.append(("select", cols, kwargs))
        return self

    def update(self, payload):
        self._update_payload = payload
        self.ops.append(("update", payload, {}))
        return self

    def eq(self, col, val):
        self.ops.append(("eq", col, val, {}))
        return self

    def in_(self, col, vals):
        self.ops.append(("in_", col, list(vals), {}))
        return self

    def is_(self, col, val):
        self.ops.append(("is_", col, val, {}))
        return self

    def order(self, *a, **k):
        self.ops.append(("order", a, k))
        return self

    def limit(self, n):
        self.ops.append(("limit", n, {}))
        return self

    def execute(self):
        self._store.setdefault("queries", []).append((self._table, list(self.ops), self._update_payload))
        data = list(self._store.get("data", {}).get(self._table, []))
        # Model filters for reads.
        for op in self.ops:
            if op[0] == "eq" and data and isinstance(data[0], dict):
                data = [r for r in data if r.get(op[1]) == op[2]]
            elif op[0] == "in_" and data and isinstance(data[0], dict):
                data = [r for r in data if r.get(op[1]) in op[2]]
            elif op[0] == "is_" and data and isinstance(data[0], dict):
                if val_is_null(op[2]):
                    data = [r for r in data if r.get(op[1]) is None]
        # Model the update: apply payload to matching rows, return updated rows.
        if self._update_payload is not None:
            updated = []
            for r in data:
                r.update(self._update_payload)
                updated.append(r)
            return SimpleNamespace(data=updated, count=None)
        return SimpleNamespace(data=data, count=None)


def val_is_null(v):
    return v is None or (isinstance(v, str) and v.lower() == "null")


class FakeDB:
    def __init__(self, data):
        self.store = {"data": data, "queries": []}

    def table(self, name):
        return FakeQuery(self.store, name)


@pytest.fixture
def owned_alerts_db(monkeypatch):
    """Two repos for u1 (r1, r2), one repo for u2 (r3); alerts across all."""
    data = {
        "repos": [
            {"id": "r1", "user_id": "u1", "full_name": "o/one"},
            {"id": "r2", "user_id": "u1", "full_name": "o/two"},
            {"id": "r3", "user_id": "u2", "full_name": "other/repo"},
        ],
        "alerts": [
            {"id": "a1", "repo_id": "r1", "read_at": None, "status": "sent", "is_test": False},
            {"id": "a2", "repo_id": "r2", "read_at": None, "status": "sent", "is_test": False},
            {"id": "a3", "repo_id": "r3", "read_at": None, "status": "sent", "is_test": False},  # foreign
            {"id": "a4", "repo_id": "r1", "read_at": "2026-01-01T00:00:00Z", "status": "sent", "is_test": False},  # already read
        ],
    }
    fake = FakeDB(data)
    monkeypatch.setattr(repos_mod, "db", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# list_all_alerts surfaces read_at (unread vs read)
# ---------------------------------------------------------------------------
def test_list_alerts_includes_read_at(owned_alerts_db):
    out = repos_mod.list_all_alerts(repository_id=None, user_id="u1")
    by_id = {a.id: a for a in out}
    assert by_id["a1"].read_at is None  # unread
    assert by_id["a4"].read_at is not None  # read
    assert "a3" not in by_id  # foreign repo's alert never leaks (isolation)


# ---------------------------------------------------------------------------
# mark_alerts_read: ownership, subset, idempotency, foreign ids
# ---------------------------------------------------------------------------
def test_mark_all_read_marks_only_owned_unread(owned_alerts_db):
    result = repos_mod.mark_alerts_read(body=None, user_id="u1")
    # a1, a2 are unread+owned; a4 already read (is_ null excludes it); a3 foreign.
    assert result.updated == 2
    by_id = {a["id"]: a for a in owned_alerts_db.store["data"]["alerts"]}
    assert by_id["a1"]["read_at"] is not None
    assert by_id["a2"]["read_at"] is not None
    assert by_id["a3"]["read_at"] is None  # untouched — belongs to u2
    assert by_id["a4"]["read_at"] == "2026-01-01T00:00:00Z"  # preserved


def test_mark_subset_read(owned_alerts_db):
    result = repos_mod.mark_alerts_read(
        body=repos_mod.MarkAlertsReadIn(alert_ids=["a2"]), user_id="u1"
    )
    assert result.updated == 1
    by_id = {a["id"]: a for a in owned_alerts_db.store["data"]["alerts"]}
    assert by_id["a2"]["read_at"] is not None
    assert by_id["a1"]["read_at"] is None


def test_mark_read_idempotent(owned_alerts_db):
    first = repos_mod.mark_alerts_read(body=None, user_id="u1")
    assert first.updated == 2
    second = repos_mod.mark_alerts_read(body=None, user_id="u1")
    assert second.updated == 0  # nothing unread remains


def test_mark_read_with_foreign_ids_is_noop_for_them(owned_alerts_db):
    """Passing another user's alert id must not touch it (IDOR-safe)."""
    result = repos_mod.mark_alerts_read(
        body=repos_mod.MarkAlertsReadIn(alert_ids=["a3"]), user_id="u1"
    )
    assert result.updated == 0
    by_id = {a["id"]: a for a in owned_alerts_db.store["data"]["alerts"]}
    assert by_id["a3"]["read_at"] is None


def test_mark_read_user_without_repos(owned_alerts_db):
    result = repos_mod.mark_alerts_read(body=None, user_id="u-with-no-repos")
    assert result.updated == 0
