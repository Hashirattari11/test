"""Unified diff helpers (display-only; actual application is a deterministic
rule-based replacement, see generator.py)."""
from __future__ import annotations

import difflib


def make_diff(path: str, old_content: str, new_content: str, context: int = 3) -> str:
    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=context,
    )
    return "".join(diff)