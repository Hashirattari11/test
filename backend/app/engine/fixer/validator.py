"""Syntax validation for candidate fixes. Never create a PR on invalid output."""
from __future__ import annotations

import os


def validate_syntax(path: str, content: str) -> tuple[bool, str]:
    """Return (ok, detail). Python is checked with a real AST parse; JS/TS with
    delimiter-balance + quote sanity (a full JS parser is out of scope)."""
    ext = os.path.splitext(path)[1].lower()
    if not content.strip():
        return False, "Empty file"

    if ext == ".py":
        try:
            import ast
            ast.parse(content)
            return True, "Python AST parse OK"
        except SyntaxError as exc:
            return False, f"Python syntax error: {exc.msg} at line {exc.lineno}"
        except Exception as exc:
            return False, f"Python parse failed: {exc}"

    # JS/TS-family + others: delimiter & quote balance (comment-aware-lite).
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    quote: str | None = None
    i = 0
    line = 1
    while i < len(content):
        ch = content[i]
        if ch == "\n":
            line += 1
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            continue
        if ch == "//" and i + 1 < len(content) and content[i + 1] == "/":
            nl = content.find("\n", i)
            if nl == -1:
                break
            i = nl
            continue
        if ch == "/*":
            end = content.find("*/", i + 2)
            if end == -1:
                return False, f"Unterminated block comment (line {line})"
            line += content[i:end].count("\n")
            i = end + 2
            continue
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in ")]}":
            if not stack or stack[-1] != ch:
                return False, f"Unbalanced delimiter '{ch}' (line {line})"
            stack.pop()
        i += 1

    if quote:
        return False, "Unterminated string literal"
    if stack:
        return False, f"Unclosed delimiter(s): {''.join(stack[:5])}"
    return True, "Delimiter balance OK"