"""Transform each failing dashboard page to satisfy Next.js prerender rules.

For every page under app/dashboard (and app/dashboard/health) whose page.tsx
is a client component using useSearchParams, the component must be rendered
inside a <Suspense> boundary for static prerendering to succeed.

Transformation applied (only when needed):
1. Add `Suspense` to the `from "react"` import (idempotent).
2. Rename `export default function <Name>(`  ->  `function <Name>(`.
3. Append:
     export default function Page() {
       return <Suspense fallback={<div />}>{<Name />}</Suspense>;
     }

The inner component is unchanged; we only add the boundary + a wrapper. Any
pre-existing `export const dynamic = "force-dynamic";` is left intact.

Output is a UTF-8 report listing what changed per file (ASCII-safe).
"""
import io
import os
import re

CWD = os.getcwd()
REPORT = "tc_report.txt"
lines_out = []


def log(s: str) -> None:
    lines_out.append(s)


def rel(p: str) -> str:
    return os.path.relpath(p, CWD)


def patch_page(path: str) -> str:
    raw = io.open(path, encoding="utf-8-sig").read()
    had_bom = raw.startswith("\ufeff")
    if had_bom:
        raw = raw[1:]

    # 1) Suspense import
    if not re.search(r"\bSuspense\b", raw):
        m = re.search(r"(import\s*\{[^}]*)\}\s*from\s*\"react\";", raw)
        if m:
            inner = m.group(1)
            if "Suspense" not in inner:
                new_inner = inner.rstrip() + ", Suspense"
            else:
                new_inner = inner
            raw = raw[: m.start()] + new_inner + '} from "react";' + raw[m.end():]
        else:
            log("  ?? no react import in %s" % rel(path))
            return "UNCHANGED_NO_REACT"

    # 2) default export rename
    m = re.search(r"export\s+default\s+function\s+(\w+)", raw)
    if not m:
        log("  ?? no default function in %s" % rel(path))
        return "UNCHANGED_NO_DEF"
    name = m.group(1)

    # 3) wrap: only if a wrapper is not already present
    if "export default function Page()" in raw and re.search(
        r"return <Suspense", raw
    ):
        log("  == already wrapped: %s" % rel(path))
        return "ALREADY"

    raw = raw.replace("export default function " + name + "(", "function " + name + "(", 1)
    wrapped = (
        "export default function Page() {\n"
        "  return <Suspense fallback={<div />}>{%s}</Suspense>;\n"
        "}\n"
    ) % (name,)
    raw = raw.rstrip() + "\n\n" + wrapped

    if had_bom:
        raw = "\ufeff" + raw

    io.open(path, "w", encoding="utf-8", newline="\n").write(raw)
    return "PATCHED_" + name


def main() -> None:
    targets = []
    for base in ("app",):
        for root, _dirs, files in os.walk(base):
            for f in files:
                if f == "page.tsx":
                    targets.append(os.path.join(root, f))
    log("SEARCHED: %d page.tsx under app/" % len(targets))
    changed = 0
    for path in sorted(targets):
        try:
            raw = io.open(path, encoding="utf-8").read()
        except Exception:
            continue
        if ("useSearchParams" in raw) and ('"use client"' in raw or '"use client";' in raw):
            res = patch_page(path)
            log("  %-8s %s" % (res, rel(path)))
            if res.startswith("PATCHED_"):
                changed += 1
            continue
        # no change needed
    log("PAGES_WRAPPED=%d" % changed)


if __name__ == "__main__":
    main()
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write("\n".join(lines_out))
