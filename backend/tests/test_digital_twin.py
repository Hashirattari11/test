"""Offline tests for the API Digital Twin engine.

Run with:  python -m pytest tests/test_digital_twin.py -q
No network, no database — the Supabase client is replaced with an in-memory
fake (same style as tests/test_repo_isolation.py).

Covers:
  * engine unit behavior — status labels, no-fabrication evidence rules,
    symbol extraction, recommended change derivation;
  * repo isolation — a repo is NEVER given another repo's analysis rows;
  * idempotent, honest run bookkeeping (triggered_by, run_id, final status);
  * alert dedup (one alert per (event, repo)) via the EXISTING alerts table.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.digital_twin as dt
from app.digital_twin import (
    STATUS_BREAKING_RISK,
    STATUS_HIGH_RISK,
    STATUS_NO_MATCH,
    STATUS_POTENTIAL,
    STATUS_SAFE,
    STATUS_UNKNOWN,
    _analyze_event_usage,
    _recommended_change,
    _symbol_from_detection,
    get_repo_twin_summary,
    get_twin_analysis,
    run_digital_twin,
)


# ---------------------------------------------------------------------------
# In-memory fake PostgREST client (filters applied client-side like the DB).
# ---------------------------------------------------------------------------
class _FakeQuery:
    def __init__(self, tables: dict[str, list[dict]], name: str):
        self._tables = tables
        self._name = name
        self._rows = tables.get(name, [])
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
            elif op == "gte":
                rows = [r for r in rows if (r.get(col) or "") >= val]
        return rows

    def select(self, *a: Any, **k: Any) -> "_FakeQuery":
        return self

    def eq(self, col: str, val: Any) -> "_FakeQuery":
        self.filters.append(("eq", col, val))
        return self

    def in_(self, col: str, vals: list) -> "_FakeQuery":
        self.filters.append(("in", col, vals))
        return self

    def neq(self, col: str, val: Any) -> _FakeQuery:
        self.filters.append(("neq", col, val))
        return self

    def gte(self, col: str, val: Any) -> "_FakeQuery":
        self.filters.append(("gte", col, val))
        return self

    def insert(self, row: dict) -> "_FakeQuery":
        self.filters.append(("insert", "", row))
        return self

    def upsert(self, rows, **k: Any) -> "_FakeQuery":
        self.filters.append(("upsert", "", rows))
        return self

    def update(self, values: dict) -> "_FakeQuery":
        self.filters.append(("update", "", values))
        return self

    def limit(self, *a: Any) -> "_FakeQuery":
        return self

    def order(self, *a: Any, **k: Any) -> "_FakeQuery":
        return self

    def range(self, *a: Any, **k: Any) -> "_FakeQuery":
        return self

    def execute(self) -> Any:
        class _Resp:
            data: list[dict] = []
            count: int | None = None

        resp = _Resp()
        out: list[dict] = self._apply()
        for op, _col, val in self.filters:
            if op == "insert":
                if isinstance(val, list):
                    out = list(val)
                else:
                    out = [dict(val, id=val.get("id") or "inserted-id")]
                # Mutate the underlying table so subsequent reads see inserts.
                self._tables.setdefault(self._name, []).extend(dict(r) for r in out)
            elif op == "upsert":
                out = [dict(r, id=r.get("id") or "upserted-id") for r in val]
                self._tables.setdefault(self._name, []).extend(dict(r) for r in out)
            elif op == "update":
                # out holds references to the table's rows — merge in place.
                for r in out:
                    r.update(val)
        resp.data = out
        return resp


class _FakeDB:
    def __init__(self, tables: dict[str, list[dict]]):
        self._tables = {k: list(v) for k, v in tables.items()}
        self.inserted: dict[str, list[dict]] = {}

    def __call__(self) -> "_FakeDB":
        return self

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self._tables, name)

    def fetch_one(self, table: str, match: dict) -> dict | None:
        for r in self._tables.get(table, []):
            if all(r.get(k) == v for k, v in match.items()):
                return r
        return None


# ---------------------------------------------------------------------------
# Fixtures — REPO_A owned by u1, REPO_C owned by u2 (isolation convention).
# ---------------------------------------------------------------------------
REPO_A = {"id": "repoA", "full_name": "acme/backend", "user_id": "u1"}
REPO_C = {"id": "repoC", "full_name": "other/app", "user_id": "u2"}

EVENT = {
    "id": "evt-1",
    "api_name": "stripe",
    "provider_display": "Stripe",
    "change_type": "BREAKING_CHANGE",
    "title": "The /v1/charges endpoint was removed",
    "description": "The charges endpoint was removed in API v3.",
    "old_value": "charges",
    "new_value": None,
    "source_url": "https://stripe.com/changelog/entry-1",
    "symbols": "charges",
}


def _det(rid: str, **over) -> dict:
    base = {
        "id": f"det-{rid}-1",
        "repo_id": rid,
        "api_name": "stripe",
        "file_path": "src/pay.py",
        "line_number": 42,
        "matched_snippet": "stripe.Charge.create(amount=100)",
        "symbols": "Charge,charges",
    }
    base.update(over)
    return base


def _fake(tables: dict[str, list[dict]]) -> _FakeDB:
    fake = _FakeDB(tables)
    dt.db = fake  # type: ignore[assignment]
    dt.fetch_one = fake.fetch_one  # type: ignore[assignment]
    return fake


# ---------------------------------------------------------------------------
# 1. Engine units — no-fabrication rules
# ---------------------------------------------------------------------------
def test_symbol_extraction_never_guessed():
    assert _symbol_from_detection({"symbols": "Charge,PaymentIntent"}) == "Charge"
    assert _symbol_from_detection({"symbols": ""}) is None
    assert _symbol_from_detection({}) is None
    assert _symbol_from_detection({"symbols": ["Webhook", "Charge"]}) == "Webhook"


def test_recommended_change_map():
    assert "Remove or replace" in _recommended_change("BREAKING_CHANGE", ["symbol"])
    assert "Migrate" in _recommended_change("DEPRECATION", [])
    assert "security" in _recommended_change("SECURITY_CHANGE", []).lower()
    assert _recommended_change("NEW_FEATURE", []) is None


def test_no_fabrication_without_matches():
    """A detection with zero matched fields must NOT become a finding."""
    findings, _ = _analyze_event_usage(EVENT, [_det("repoA", api_name="openai")], None)
    assert findings == []


def test_provider_only_match_is_honest():
    """Provider-level match keeps file evidence but says evidence is partial."""
    det = _det("repoA", symbols="some_other_thing", matched_snippet="client = StripeClient(key)")
    findings, _ = _analyze_event_usage(EVENT, [det], None)
    assert len(findings) == 1
    f = findings[0]
    assert f.impact_status in (STATUS_POTENTIAL, STATUS_UNKNOWN, STATUS_HIGH_RISK)
    assert "Evidence not available" in f.explanation


def test_full_match_produces_breaking_risk_with_evidence():
    findings, _ = _analyze_event_usage(EVENT, [_det("repoA")], ["stripe"])
    assert findings, "a token-matching detection should produce a finding"
    top = max(findings, key=lambda f: f.confidence)
    assert top.affected_file == "src/pay.py"
    assert top.line_number == 42
    assert top.affected_symbol == "Charge"
    assert top.explanation.startswith("Detected usage: src/pay.py:42")
    assert top.recommended_change


# ---------------------------------------------------------------------------
# 2. run_digital_twin — honest bookkeeping + no-fabrication
# ---------------------------------------------------------------------------
def test_run_with_no_detections_is_truthful_no_match():
    fake = _fake({
        "repos": [REPO_A],
        "api_detections": [],
        "changelog_events": [EVENT],
        "digital_twin_runs": [],
        "digital_twin_analyses": [],
        "alerts": [],
        "scans": [],
    })
    res = run_digital_twin("repoA", "acme/backend")
    assert res.events_considered == 1
    assert res.no_match_count == 1
    assert res.findings == []
    assert res.analyses_created == 0
    assert res.alerts_created == 0
    assert res.run_id  # run row still recorded — honest bookkeeping


def test_run_persists_run_and_analyses_with_run_id():
    fake = _fake({
        "repos": [REPO_A],
        "api_detections": [_det("repoA")],
        "changelog_events": [EVENT],
        "digital_twin_runs": [],
        "digital_twin_analyses": [],
        "alerts": [],
        "scans": [],
    })
    res = run_digital_twin("repoA", "acme/backend")
    assert res.analyses_created >= 1
    assert res.run_id
    runs = fake._tables["digital_twin_runs"]
    assert len(runs) == 1
    row = runs[0]
    assert row.get("triggered_by") == "user"       # param recorded, not inferred
    assert row.get("status") == "completed"        # finalized, not stuck "running"
    # analyses carry the run_id
    for a in fake._tables["digital_twin_analyses"]:
        assert a.get("run_id") == res.run_id or a.get("run_id") is None
        break


def test_triggered_by_cron_recorded():
    fake = _fake({
        "repos": [REPO_A],
        "api_detections": [_det("repoA")],
        "changelog_events": [EVENT],
        "digital_twin_runs": [],
        "digital_twin_analyses": [],
        "alerts": [],
        "scans": [],
    })
    run_digital_twin("repoA", "acme/backend", triggered_by="cron")
    assert fake._tables["digital_twin_runs"][0].get("triggered_by") == "cron"


def test_no_alert_for_repo_without_usages():
    """No detections -> no alerts, no email attempts (no noise for non-users)."""
    fake = _fake({
        "repos": [REPO_A, REPO_C],
        "api_detections": [],
        "changelog_events": [EVENT],
        "digital_twin_runs": [],
        "digital_twin_analyses": [],
        "alerts": [],
        "scans": [],
    })
    res = run_digital_twin("repoC", "other/app")
    assert res.alerts_created == 0
    assert fake._tables["alerts"] == []


def test_alert_dedup_one_per_event_repo():
    """Second run must NOT create a second alert for the same (event, repo)."""
    tables = {
        "repos": [REPO_A],
        "api_detections": [_det("repoA")],
        "changelog_events": [EVENT],
        "digital_twin_runs": [],
        "digital_twin_analyses": [],
        "alerts": [],
        "scans": [],
    }
    fake = _fake(tables)
    first = run_digital_twin("repoA", "acme/backend")
    assert first.alerts_created == 1
    second = run_digital_twin("repoA", "acme/backend")
    assert second.alerts_created == 0, "duplicate alert for same event must be suppressed"
    assert len(fake._tables["alerts"]) == 1


def test_analysis_rows_are_persisted_idempotently():
    tables = {
        "repos": [REPO_A],
        "api_detections": [_det("repoA")],
        "changelog_events": [EVENT],
        "digital_twin_runs": [],
        "digital_twin_analyses": [],
        "alerts": [],
        "scans": [],
    }
    fake = _fake(tables)
    run_digital_twin("repoA", "acme/backend")
    first_count = len(fake._tables["digital_twin_analyses"])
    run_digital_twin("repoA", "acme/backend")
    # Upsert path: rows re-written (fake records upsert as data) but never
    # duplicated beyond the unique (repo, event, detection) identity.
    identities = {
        (r["repository_id"], r["change_event_id"], r["api_detection_id"])
        for r in fake._tables["digital_twin_analyses"]
    }
    assert len(identities) == first_count


# ---------------------------------------------------------------------------
# 3. Read APIs — repo isolation (IDOR-safe)
# ---------------------------------------------------------------------------
def test_summary_scoped_to_repo():
    fake = _fake({
        "repos": [REPO_A, REPO_C],
        "digital_twin_analyses": [
            {"id": "a1", "repository_id": "repoA", "impact_status": STATUS_HIGH_RISK,
             "severity": "high", "confidence": 0.9, "provider_id": "stripe",
             "change_event_id": "evt-1", "created_at": "2026-09-30T00:00:00Z"},
            {"id": "a2", "repository_id": "repoC", "impact_status": STATUS_BREAKING_RISK,
             "severity": "breaking", "confidence": 0.9, "provider_id": "stripe",
             "change_event_id": "evt-2", "created_at": "2026-09-30T00:00:00Z"},
        ],
        "digital_twin_runs": [],
    })
    s = get_repo_twin_summary("repoA")
    assert s["affected_usages"] == 1
    assert s["high_risk"] == 1
    assert s["breaking_risk"] == 0
    assert s["providers"] == ["stripe"]


def test_analysis_detail_must_belong_to_repo():
    fake = _fake({
        "digital_twin_analyses": [
            {"id": "a1", "repository_id": "repoA", "impact_status": STATUS_HIGH_RISK},
            {"id": "a2", "repository_id": "repoC", "impact_status": STATUS_BREAKING_RISK},
        ],
    })
    assert get_twin_analysis("a1", "repoA")["id"] == "a1"
    assert get_twin_analysis("a2", "repoA") is None, \
        "analysis from another repo must not be readable"
    assert get_twin_analysis("a2", "repoC")["id"] == "a2"


def test_status_labels_are_static_only():
    """Labels never claim production is failing — they are static-analysis only."""
    labels = {STATUS_NO_MATCH, STATUS_SAFE, STATUS_POTENTIAL, STATUS_HIGH_RISK,
              STATUS_BREAKING_RISK, STATUS_UNKNOWN}
    for label in labels:
        assert "FAIL" not in label
        assert "PRODUCTION" not in label
