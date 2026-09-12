"""Fix generator for Impact Engine.

Generates minimal patches for detected code breaks using existing
infrastructure. Never auto-merges - requires explicit user action.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..engine.fixer.generator import generate_fix as engine_generate_fix, GeneratedFix
from ..engine.rules.registry import RULES

logger = logging.getLogger("autofix.impact.fix")


@dataclass
class ImpactFix:
    """A generated fix for an impact analysis."""
    file_path: str
    old_value: str
    new_value: str
    diff: str
    confidence: float
    rule_id: str | None = None
    description: str = ""


def generate_impact_fix(
    affected_file: dict,
    change_type: str,
    provider: str,
    original_content: str | None = None,
) -> ImpactFix | None:
    """Generate a fix for an affected file.
    
    Args:
        affected_file: Dict with file_path, line_number, snippet, etc.
        change_type: Type of change (removed, deprecated, renamed, etc.)
        provider: Provider name
        original_content: Original file content (if available)
    
    Returns:
        ImpactFix if fix can be generated, None otherwise
    """
    file_path = affected_file.get("file_path", "")
    snippet = affected_file.get("snippet", "")
    line_number = affected_file.get("line_number")
    
    # Find matching rule for this provider and change type
    matching_rule = _find_matching_rule(provider, change_type, snippet)
    
    if not matching_rule:
        logger.debug("No matching rule for %s/%s", provider, change_type)
        return None
    
    # If we have original content, use engine's fix generator
    if original_content and matching_rule.old_value and matching_rule.new_value:
        from ..engine.fixer.generator import apply_fix_to_text
        from ..engine.fixer.diff import make_diff
        
        new_content = apply_fix_to_text(original_content, matching_rule.old_value, matching_rule.new_value)
        if new_content:
            diff = make_diff(file_path, original_content, new_content)
            return ImpactFix(
                file_path=file_path,
                old_value=matching_rule.old_value,
                new_value=matching_rule.new_value,
                diff=diff,
                confidence=matching_rule.confidence,
                rule_id=matching_rule.id,
                description=matching_rule.recommended_fix,
            )
    
    # Otherwise, return rule-based fix without diff
    if matching_rule.old_value and matching_rule.new_value:
        return ImpactFix(
            file_path=file_path,
            old_value=matching_rule.old_value,
            new_value=matching_rule.new_value,
            diff="",  # No diff without original content
            confidence=matching_rule.confidence,
            rule_id=matching_rule.id,
            description=matching_rule.recommended_fix,
        )
    
    return None


def _find_matching_rule(
    provider: str,
    change_type: str,
    snippet: str,
):
    """Find a matching rule for the given provider and snippet."""
    for rule in RULES:
        # Check provider match
        if rule.provider is not None and rule.provider != provider:
            continue
        
        # Check change type match (approximate)
        if rule.change_type != change_type:
            # Allow some flexibility
            if not (rule.change_type == "deprecated" and change_type in ("removed", "deprecated")):
                continue
        
        # Check pattern match
        if rule.matches(snippet):
            return rule
    
    return None


def generate_fixes_for_analysis(
    affected_files: list[dict],
    change_type: str,
    provider: str,
    file_contents: dict[str, str] | None = None,
) -> list[ImpactFix]:
    """Generate fixes for all affected files in an analysis.
    
    Args:
        affected_files: List of affected file dicts
        change_type: Type of change
        provider: Provider name
        file_contents: Optional dict of file_path -> content
    
    Returns:
        List of ImpactFix objects
    """
    fixes = []
    
    for affected in affected_files:
        file_path = affected.get("file_path", "")
        content = file_contents.get(file_path) if file_contents else None
        
        fix = generate_impact_fix(
            affected_file=affected,
            change_type=change_type,
            provider=provider,
            original_content=content,
        )
        
        if fix:
            fixes.append(fix)
    
    return fixes
