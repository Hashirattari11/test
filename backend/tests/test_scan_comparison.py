"""Tests: scan-to-scan comparison delta (pure compare_scan_findings)."""
from __future__ import annotations

from app.routers.repos import compare_scan_findings


def _row(file: str, line: int, message: str, status: str = "open", severity: str = "medium", **extra) -> dict:
    return {"file": file, "line": line, "message": message, "status": status, "severity": severity, **extra}


def test_empty_baseline_all_added():
    before: list[dict] = []
    after = [_row("a.py", 1, "hit"), _row("b.py", 2, "hit2")]
    delta = compare_scan_findings(before, after)
    assert delta["added_count"] == 2
    assert delta["removed_count"] == 0
    assert delta["unchanged_count"] == 0
    assert delta["added_by_severity"] == {"medium": 2}


def test_added_removed_unchanged():
    before = [_row("a.py", 1, "m1"), _row("b.py", 2, "m2", severity="high")]
    after = [_row("a.py", 1, "m1"), _row("c.py", 3, "m3")]
    delta = compare_scan_findings(before, after)
    assert delta["added_count"] == 1
    assert delta["added"][0]["file"] == "c.py"
    assert delta["removed_count"] == 1
    assert delta["removed"][0]["file"] == "b.py"
    assert delta["unchanged_count"] == 1


def test_resolved_and_regressed():
    before = [_row("a.py", 1, "m1", status="open"), _row("b.py", 2, "m2", status="fixed")]
    after = [_row("a.py", 1, "m1", status="fixed"), _row("b.py", 2, "m2", status="open")]
    delta = compare_scan_findings(before, after)
    assert delta["resolved_count"] == 1
    assert delta["regressed_count"] == 1


def test_severity_rollup():
    before: list[dict] = []
    after = [
        _row("a.py", 1, "m1", severity="critical"),
        _row("b.py", 2, "m2", severity="low"),
        _row("c.py", 3, "m3", severity="critical"),
    ]
    delta = compare_scan_findings(before, after)
    assert delta["added_by_severity"] == {"critical": 2, "low": 1}


def test_runs_never_mutate_inputs():
    before = [_row("a.py", 1, "m1")]
    after = [_row("a.py", 1, "m1")]
    before_copy = list(before)
    after_copy = list(after)
    compare_scan_findings(before, after)
    assert before == before_copy
    assert after == after_copy