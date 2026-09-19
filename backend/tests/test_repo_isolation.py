"""Offline tests for repository-scoped data isolation.

Run with:  python -m pytest tests/test_repo_isolation.py -q
No network, no database, no real credentials — the Supabase client is replaced
with an in-memory fake that records every query filter.

Proves the ROOT-CAUSE fix: aggregate endpoints (health errors/failures/
anomalies/issues, impact summary, alerts) accept an optional repository_id that
is (a) enforced on the backend query, and (b) ownership-checked (404 for repos
the caller does not own — IDOR-safe). Without repository_id the endpoint returns
the aggregate (explicit "All Repositories" view).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The routers call db().table(...) and fetch_one(...) at request time; we patch
# those module-level names with the fake.
import app.routers.health as health
import app.routers.impact as impact
import app.routers.repos as repos


# ---------------------------------------------------------------------------
# In-memory fake PostgREST client (records filters, applies them client-side,
# exactly like the real database would for eq/in_ on repo_id)
# ---------------------------------------------------------------------------
class _FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        # Structured filters: ("eq", "repo_id", "repoA") | ("in", "repo_id", ["a","b"])
        self.filters: list[tuple] = []

    def _apply(self) -> list[dict]:
        rows = self._rows
        for op, col, val in self.filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "in":
                rows = [r for r in rows if r.get(col) in val]
            elif op == "neq":
                rows = [r for r in rows if r.get(col) != val]
        return rows

    def select(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def eq(self, col: str, value: Any) -> "_FakeQuery":
        self.filters.append(("eq", col, value))
        return self

    def in_(self, col: str, values: list) -> "_FakeQuery":
        self.filters.append(("in", col, sorted(values)))
        return self

    def neq(self, col: str, value: Any) -> "_FakeQuery":
        self.filters.append(("neq", col, value))
        return self

    def limit(self, n: int) -> "_FakeQuery":
        return self

    def order(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def range(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def execute(self) -> Any:
        class _Resp:
            data: list[dict] = []

        resp = _Resp()
        resp.data = self._apply()
        return resp


class _FakeDB:
    def __init__(self, repos_rows: list[dict], issue_rows: list[dict] | None = None,
                 impact_rows: list[dict] | None = None, alert_rows: list[dict] | None = None):
        self._repos = repos_rows
        self._issues = issue_rows or []
        self._impacts = impact_rows or []
        self._alerts = alert_rows or []

    def __call__(self) -> "_FakeDB":
        # Routers call db().table(...) — the client is a callable factory.
        return self

    def table(self, name: str) -> _FakeQuery:
        if name == "repos":
            return _FakeQuery(self._repos)
        if name == "reliability_issues":
            return _FakeQuery(self._issues)
        if name == "impact_analyses":
            return _FakeQuery(self._impacts)
        if name == "alerts":
            return _FakeQuery(self._alerts)
        return _FakeQuery([])

    def fetch_one(self, table: str, filters: dict) -> dict | None:
        """Replacement for app.db.fetch_one used by _owned_repo helpers."""
        if table != "repos":
            return None
        for r in self._repos:
            if all(r.get(k) == v for k, v in filters.items()):
                return r
        return None


def _patch(fake: _FakeDB) -> None:
    health.db = fake  # type: ignore[assignment]
    health.fetch_one = fake.fetch_one  # type: ignore[assignment]
    impact.db = fake  # type: ignore[assignment]
    repos.db = fake  # type: ignore[assignment]
    repos.fetch_one = fake.fetch_one  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# User u1 owns repoA + repoB; user u2 owns repoC.
REPO_A = {"id": "repoA", "full_name": "acme/backend", "user_id": "u1", "default_branch": "main",
          "agency_client_id": None}
REPO_B = {"id": "repoB", "full_name": "acme/frontend", "user_id": "u1", "default_branch": "main",
          "agency_client_id": None}
REPO_C = {"id": "repoC", "full_name": "other/app", "user_id": "u2", "default_branch": "main",
          "agency_client_id": None}

def _issue(rid: str, sev: str, cat: str, file: str = "src/api.ts") -> dict:
    return {
        "id": f"iss-{rid}-{cat}-{sev}", "repo_id": rid, "provider": "stripe",
        "severity": sev, "category": cat, "status": "open", "confidence": 0.9,
        "title": f"{cat} in {rid}", "description": "d", "file": file,
        "line": 10, "source": "scanner", "recommended_action": None,
        "auto_fix_available": False, "created_at": "2026-09-19T00:00:00Z",
        "risk_score": 0.8, "risk_level": "high", "risk_factors": [],
    }


# ---------------------------------------------------------------------------
# 1. /health/errors — aggregate vs repo-scoped vs IDOR
# ---------------------------------------------------------------------------
def test_errors_aggregate_mixes_all_owned_repos():
    """No repository_id -> both OWNED repos' errors (explicit All view)."""
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B, REPO_C],
        issue_rows=[
            _issue("repoA", "critical", "customer_code"),
            _issue("repoB", "high", "customer_code"),
            _issue("repoC", "critical", "customer_code"),  # NOT owned by u1
        ],
    )
    _patch(fake)
    res = health.list_errors(user_id="u1", repository_id=None, limit=100)
    repos_in_response = {e["repo_id"] for e in res["errors"]}
    assert repos_in_response == {"repoA", "repoB"}, \
        f"aggregate must include only OWNED repos, got {repos_in_response}"
    assert "repoC" not in repos_in_response
    assert res["total"] == 2


def test_errors_scoped_to_repository_a():
    """repository_id=repoA -> ONLY repoA rows in the response."""
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B],
        issue_rows=[
            _issue("repoA", "critical", "customer_code"),
            _issue("repoB", "critical", "customer_code"),
        ],
    )
    _patch(fake)
    res = health.list_errors(user_id="u1", repository_id="repoA", limit=100)
    repos_in_response = {e["repo_id"] for e in res["errors"]}
    assert repos_in_response == {"repoA"}, \
        f"scoped query must return ONLY repoA, got {repos_in_response}"
    assert res["total"] == 1


def test_errors_scoped_to_repository_with_zero_findings():
    """A repo with zero findings returns zero — never another repo's rows."""
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B],
        issue_rows=[_issue("repoB", "critical", "customer_code")],
    )
    _patch(fake)
    res = health.list_errors(user_id="u1", repository_id="repoA", limit=100)
    assert res["errors"] == []
    assert res["total"] == 0


def test_errors_unowned_repository_returns_404():
    """IDOR: requesting another user's repo must 404, never return data."""
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B, REPO_C],
        issue_rows=[_issue("repoC", "critical", "customer_code")],
    )
    _patch(fake)
    from fastapi import HTTPException
    try:
        health.list_errors(user_id="u1", repository_id="repoC", limit=100)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException 404 for unowned repository")


# ---------------------------------------------------------------------------
# 2. /health/issues — scoped + zero-issue repo
# ---------------------------------------------------------------------------
def test_issues_scoped_and_zero():
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B],
        issue_rows=[
            _issue("repoA", "medium", "dependency"),
            _issue("repoB", "high", "customer_code"),
        ],
    )
    _patch(fake)
    res = health.list_issues(user_id="u1", repository_id="repoA", status="open",
                             severity=None, category=None, provider=None, limit=100)
    assert {i["repo_id"] for i in res} == {"repoA"}
    assert len(res) == 1


# ---------------------------------------------------------------------------
# 3. /impact/summary — scoped
# ---------------------------------------------------------------------------
def test_impact_summary_scoped_to_repo():
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B],
        impact_rows=[
            {"id": "impA", "repo_id": "repoA", "severity": "high", "detected_at": "2026-09-19T00:00:00Z"},
            {"id": "impB", "repo_id": "repoB", "severity": "breaking", "detected_at": "2026-09-19T00:00:00Z"},
        ],
    )
    _patch(fake)
    s = impact.get_impact_summary(user_id="u1", repository_id="repoA")
    assert s["total_analyses"] == 1
    assert s["by_severity"] == {"high": 1}


def test_impact_summary_unowned_404():
    fake = _FakeDB(
        repos_rows=[REPO_C],
        impact_rows=[{"id": "impC", "repo_id": "repoC", "severity": "high", "detected_at": "x"}],
    )
    _patch(fake)
    from fastapi import HTTPException
    try:
        impact.get_impact_summary(user_id="u1", repository_id="repoC")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException 404 for unowned repository")


# ---------------------------------------------------------------------------
# 4. /repos/alerts — scoped
# ---------------------------------------------------------------------------
def test_alerts_scoped_to_repo():
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B],
        alert_rows=[
            {"id": "alA", "repo_id": "repoA", "repo_name": "acme/backend", "severity": "high",
             "change_type": "removed endpoint", "status": "open"},
            {"id": "alB", "repo_id": "repoB", "repo_name": "acme/frontend", "severity": "critical",
             "change_type": "breaking change", "status": "open"},
        ],
    )
    _patch(fake)
    out = repos.list_all_alerts(user_id="u1", repository_id="repoA")
    assert {a.id for a in out} == {"alA"}, f"expected only repoA alert, got {[a.id for a in out]}"


def test_alerts_unowned_404():
    fake = _FakeDB(
        repos_rows=[REPO_C],
        alert_rows=[{"id": "alC", "repo_id": "repoC", "repo_name": "other/app", "severity": "high",
                     "change_type": "x", "status": "open"}],
    )
    _patch(fake)
    from fastapi import HTTPException
    try:
        repos.list_all_alerts(user_id="u1", repository_id="repoC")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException 404 for unowned repository")


# ---------------------------------------------------------------------------
# 5. Cross-repo contamination: same file + function name, different repos
#    NEVER merged — identity comes from repository_id, not file/function names.
# ---------------------------------------------------------------------------
def test_cross_repo_contamination_same_file_function():
    fake = _FakeDB(
        repos_rows=[REPO_A, REPO_B],
        issue_rows=[
            _issue("repoA", "critical", "customer_code", file="src/api.ts"),
            _issue("repoB", "critical", "customer_code", file="src/api.ts"),
        ],
    )
    _patch(fake)
    res_a = health.list_errors(user_id="u1", repository_id="repoA", limit=100)
    res_b = health.list_errors(user_id="u1", repository_id="repoB", limit=100)
    assert [e["file"] for e in res_a["errors"]] == ["src/api.ts"]
    assert len(res_a["errors"]) == 1 and len(res_b["errors"]) == 1
    assert res_a["errors"][0]["repo_id"] == "repoA"
    assert res_b["errors"][0]["repo_id"] == "repoB"
    assert res_a["errors"][0]["id"] != res_b["errors"][0]["id"]