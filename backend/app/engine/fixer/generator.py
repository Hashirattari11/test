"""Fix generator: turn a breaking finding + file content into a concrete,
deterministic code change. No AI guessing — if no safe transform exists the
generator returns None (honest "no automated fix" instead of broken output)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GeneratedFix:
    file: str
    old_value: str
    new_value: str
    new_content: str
    diff: str
    applied: bool = True


def find_rule(rule_id: str | None):
    if not rule_id:
        return None
    try:
        from ..rules.registry import RULES
    except Exception:
        return None
    return next((r for r in RULES if r.id == rule_id), None)


def apply_fix_to_text(content: str, old_value: str | None, new_value: str | None) -> str | None:
    """Replace the first occurrence of old_value with new_value. Returns None
    if old_value is missing (fix no longer applies) or empty/malformed."""
    if not old_value or new_value is None:
        return None
    if old_value not in content:
        return None
    return content.replace(old_value, new_value, 1)


def generate_fix(finding: dict, original_content: str) -> GeneratedFix | None:
    """Build a fix from a finding dict (rule_id + current_usage available).

    A finding with no rule-derived old/new pair yields None (no automated fix).
    """
    rule = find_rule(finding.get("rule_id"))
    if rule is None or not rule.old_value or rule.new_value is None:
        return None
    new_content = apply_fix_to_text(original_content, rule.old_value, rule.new_value)
    if new_content is None:
        return None
    from .diff import make_diff
    diff = make_diff(finding.get("file") or "file", original_content, new_content)
    return GeneratedFix(
        file=finding.get("file") or "file",
        old_value=rule.old_value,
        new_value=rule.new_value,
        new_content=new_content,
        diff=diff,
    )