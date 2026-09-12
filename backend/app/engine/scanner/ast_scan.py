"""AST/structural source scanning.

Python files get a real `ast` parse (precise import + call-site extraction).
JS/TS get a comment-aware lexical scan (imports/requires + HTTP-call
expressions). Everything else falls back to the existing regex signature set
(COMPILED_SIGNATURES) so no detectable usage is missed.

Output is a normalized `ScanHit` list: {file, line, snippet, kind, provider,
symbols, message} — the raw material the rules engine (M3) turns into findings.
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field

from ...signatures import COMPILED_SIGNATURES

HTTP_VERBS = {"get", "post", "put", "patch", "delete", "request", "fetch", "send", "list"}

SDK_OBJECTS = {
    "charges", "customers", "completions", "messages", "conversations", "invoices",
    "checkout", "subscriptions", "billing", "payments", "files", "refunds",
    "paymentintents", "token", "products", "prices", "tokens", "plans", "accounts",
}

# Module-name (or fragment) -> provider key (aligns with changelog_sources / signatures).
PROVIDER_BY_FRAGMENT: dict[str, str] = {
    "stripe": "stripe",
    "openai": "openai",
    "anthropic": "anthropic",
    "twilio": "twilio",
    "sendgrid": "sendgrid",
    "@supabase": "supabase",
    "firebase": "firebase",
    "@slack": "slack",
    "resend": "resend",
    "vercel": "vercel",
    "github": "github",
    "shopify": "shopify",
    "aws-sdk": "aws",
    "@aws-sdk": "aws",
    "google-cloud": "google",
    "@google-cloud": "google",
    "azure": "azure",
}


@dataclass
class ScanHit:
    file: str
    line: int
    snippet: str
    kind: str = "call"          # import | call | signature
    provider: str | None = None
    symbols: list[str] = field(default_factory=list)
    message: str = ""


def _infer_provider(text: str) -> str | None:
    low = text.lower()
    for frag, provider in PROVIDER_BY_FRAGMENT.items():
        if frag in low:
            return provider
    return None


def _strip_js_comments(content: str) -> list[str]:
    """Return lines with // and /* */ comments removed (safe for quotes/URLs)."""
    out: list[str] = []
    in_block = False
    for raw in content.splitlines():
        line = raw
        i = 0
        res: list[str] = []
        while i < len(line):
            if in_block:
                end = line.find("*/", i)
                if end == -1:
                    break
                in_block = False
                i = end + 2
                continue
            if line[i : i + 2] == "/*":
                in_block = True
                i += 2
                continue
            if line[i : i + 2] == "//":
                break
            if line[i] in ("'", '"', "`"):
                quote = line[i]
                j = i + 1
                while j < len(line):
                    if line[j] == "\\":
                        j += 2
                        continue
                    if line[j] == quote:
                        break
                    j += 1
                res.append(line[i : min(j + 1, len(line))])
                i = j + 1
                continue
            res.append(line[i])
            i += 1
        out.append("".join(res))
    return out


_IMPORT_RE = re.compile(
    r"(?:import|export)\s+[^'\";]*?\s+from\s+['\"]([^'\"]+)['\"]|require\(\s*['\"]([^'\"]+)['\"]\s*\)"
)
_CALL_RE = re.compile(r"([a-zA-Z_$][\w$]*(?:\.[a-zA-Z_$][\w$]*)+)\s*\(")
_URL_RE = re.compile(r"['\"](https?://[^'\"\s]+)['\"]")


def _scan_js_ts(path: str, content: str) -> list[ScanHit]:
    clean_lines = _strip_js_comments(content)
    hits: list[ScanHit] = []

    # Pre-pass: variable -> provider bindings (const s = new Stripe(...), const x = require('stripe'))
    bindings: dict[str, str] = {}
    for line in clean_lines:
        m = re.search(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*new\s+([A-Za-z_$][\w$]*)\s*\(", line)
        if m:
            prov = _infer_provider(m.group(2))
            if prov:
                bindings[m.group(1)] = prov
        m2 = re.search(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)", line)
        if m2:
            prov = _infer_provider(m2.group(2))
            if prov:
                bindings[m2.group(1)] = prov

    for lineno, line in enumerate(clean_lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        # imports / requires
        for m in _IMPORT_RE.finditer(stripped):
            mod = (m.group(1) or m.group(2) or "").strip()
            if mod:
                hits.append(ScanHit(
                    file=path, line=lineno, snippet=stripped[:500], kind="import",
                    provider=_infer_provider(mod), symbols=[mod],
                    message=f"Imports module '{mod}'",
                ))
        # HTTP-call expressions with a URL argument
        for m in _CALL_RE.finditer(stripped):
            target = m.group(1)
            verb = target.split(".")[-1].lower()
            low_target = target.lower()
            root = target.split(".")[0]
            is_sdk_call = any(obj in low_target for obj in SDK_OBJECTS)
            if verb in HTTP_VERBS or "fetch" in low_target or is_sdk_call:
                url_match = _URL_RE.search(stripped[m.end():])
                url = url_match.group(1) if url_match else None
                provider = _infer_provider(target) or bindings.get(root)
                hits.append(ScanHit(
                    file=path, line=lineno, snippet=stripped[:500], kind="call",
                    provider=provider, symbols=[target],
                    message=f"HTTP call '{target}'" + (f" -> {url}" if url else ""),
                ))
    return hits


def _scan_python(path: str, content: str) -> list[ScanHit]:
    hits: list[ScanHit] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return hits  # fall back to signature pass in scan_content()

    # Pass 1: top-level imported names -> provider (openai, stripe, ...)
    import_name_to_provider: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", None) or ""
            provider = _infer_provider(module or (node.names[0].name if node.names else ""))
            for a in node.names:
                top = a.name.split(".")[0]
                if provider:
                    import_name_to_provider.setdefault(top, provider)
                hits.append(ScanHit(
                    file=path, line=node.lineno,
                    snippet=(ast.get_source_segment(content, node) or "")[:500],
                    kind="import", provider=provider,
                    symbols=[a.name], message=f"Imports module '{module or a.name}'",
                ))

    # Pass 2: calls worth flagging
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        verb = node.func.attr.lower()
        try:
            target: str | None = ast.unparse(node.func)
        except Exception:
            target = None
        root = (target or "").split(".")[0] if target else ""
        provider = (import_name_to_provider.get(root)
                    or _infer_provider(target or "")
                    or _infer_provider(root))
        url = ""
        for a in node.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith(("http://", "https://")):
                url = a.value
                break
        is_http_verb = verb in HTTP_VERBS or "fetch" in verb
        is_sdk_call = provider is not None and root in import_name_to_provider
        if is_http_verb or is_sdk_call:
            hits.append(ScanHit(
                file=path, line=node.lineno,
                snippet=(ast.get_source_segment(content, node) or "")[:500],
                kind="call", provider=provider,
                symbols=[target or verb],
                message=f"SDK/HTTP call '{target}'" + (f" -> {url}" if url else ""),
            ))
    return hits


def scan_content(path: str, content: str) -> list[ScanHit]:
    """Scan one file's text. Returns normalized hits (may be empty)."""
    if not content:
        return []
    ext = os.path.splitext(path)[1].lower()
    hits: list[ScanHit] = []
    if ext == ".py":
        hits = _scan_python(path, content)
    elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        hits = _scan_js_ts(path, content)

    # Universal signature fallback (proven line-regex engine) — catches anything
    # the structural passes missed, e.g. framework-specific wrappers.
    for lineno, raw in enumerate(content.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        for api_name, patterns in COMPILED_SIGNATURES.items():
            for pattern in patterns:
                if pattern.search(line):
                    hits.append(ScanHit(
                        file=path, line=lineno, snippet=line[:500], kind="signature",
                        provider=_infer_provider(api_name),
                        symbols=[api_name], message=f"Signature match for '{api_name}'",
                    ))
                    break
    # dedupe by (line, kind, message)
    seen: set[tuple] = set()
    unique: list[ScanHit] = []
    for h in hits:
        key = (h.line, h.kind, h.message, h.provider)
        if key not in seen:
            seen.add(key)
            unique.append(h)
    unique.sort(key=lambda h: h.line)
    return unique