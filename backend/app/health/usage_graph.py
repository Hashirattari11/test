"""API usage graph: Repository -> Provider -> SDK method -> file -> line -> env ref.

Built from REAL detection rows persisted by the scanner (``api_detections``):
provider, file, line and the matched snippet. The extractor pulls the concrete
SDK method chain and environment-variable NAME references out of the snippets.

Security: only environment variable NAMES are ever extracted (``STRIPE_SECRET_KEY``);
values are never captured, stored or returned.
"""
from __future__ import annotations

import re

# SDK method chains: stripe.paymentIntents.create(), client.responses.create()
_METHOD_RE = re.compile(r"([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*){1,3})\s*\(")

# Env var NAME references (never the value).
_ENV_RES = [
    re.compile(r"process\.env\.([A-Z_][A-Z0-9_]+)"),
    re.compile(r"os\.environ\[\s*['\"]([A-Z_][A-Z0-9_]+)['\"]\s*\]"),
    re.compile(r"os\.getenv\(\s*['\"]([A-Z_][A-Z0-9_]+)['\"]"),
    re.compile(r"getenv\(\s*['\"]([A-Z_][A-Z0-9_]+)['\"]"),
    re.compile(r"env\[\s*['\"]([A-Z_][A-Z0-9_]+)['\"]\s*\]"),
]


def extract_method(snippet: str) -> str | None:
    """Return the longest SDK method chain found in the snippet."""
    best: str | None = None
    for m in _METHOD_RE.finditer(snippet or ""):
        chain = m.group(1)
        if best is None or len(chain) > len(best):
            best = chain
    return best


def extract_env_refs(snippet: str) -> list[str]:
    """Return deduped env var NAMES referenced in the snippet (values never extracted)."""
    refs: list[str] = []
    for pattern in _ENV_RES:
        for m in pattern.finditer(snippet or ""):
            name = m.group(1)
            if name not in refs:
                refs.append(name)
    return refs


def build_usage_graph(detections: list[dict]) -> dict[str, dict]:
    """Aggregate detection rows into a per-provider usage graph.

    ``detections`` rows: {"api_name"|"provider", "file_path"|"file",
                          "line_number"|"line", "matched_snippet"}.
    Returns {provider: {methods: [..], files: [..], config_refs: [..],
                        usage_points: [{method, file, line}]}}.
    """
    graph: dict[str, dict] = {}
    for d in detections:
        provider = d.get("api_name") or d.get("provider") or "unknown"
        file = d.get("file_path") or d.get("file") or "?"
        line = d.get("line_number") or d.get("line") or None
        snippet = d.get("matched_snippet") or ""

        node = graph.setdefault(provider, {
            "methods": [], "files": [], "config_refs": [], "usage_points": [],
        })

        method = extract_method(snippet)
        if method and method not in node["methods"]:
            node["methods"].append(method)
        if file and file not in node["files"]:
            node["files"].append(file)
        for ref in extract_env_refs(snippet):
            if ref not in node["config_refs"]:
                node["config_refs"].append(ref)
        if method:
            node["usage_points"].append({
                "method": method,
                "file": file,
                "line": line,
            })
    return graph