"""Determine whether force-dynamic actually fires Prerender errors.
Updated copy targeting the fresh log captured in fresh_build_ascii.txt."""
import io, re, os

LOG = os.path.abspath(os.path.join("scripts", "fresh_build_ascii.txt"))

def rel(path):
    try:
        return os.path.relpath(path, os.path.abspath("app"))
    except Exception:
        return path

def main():
    out = io.StringIO()
    count = 0
    pages = []
    if not os.path.exists(LOG):
        print("NO FRESH BUILD LOG FOUND (build not run yet)")
        return
    raw = io.open(LOG, encoding="utf-8", errors="replace").read()
    out.write("LOG_BYTES=%d\n" % len(raw))
    # Extract the pages mentioned in prerender/suspense errors.
    for m in re.finditer(r'/dashboard/[a-z0-9/_]+', raw):
        p = m.group(0)
        # only pages with an error context nearby
        idx = max(0, m.start() - 260)
        ctx = raw[idx:m.end()]
        if "Error" not in ctx and "suspense" not in ctx and "prerender" not in ctx:
            continue
        if p not in pages:
            pages.append(p)
    out.write("PAGES_IN_ERRORS=%d\n" % len(pages))
    for p in pages:
        out.write("  - %s\n" % p)
    # Check each page file for force-dynamic
    out.write("\nFORCE_DYNAMIC_PRESENT:\n")
    for p in sorted(set(pages)):
        base = p[len("/dashboard/"):]
        f = os.path.join("app", "dashboard", base.replace("/", os.sep), "page.tsx")
        checked = []
        # page + any page.tsx ancestor dirs
        cur = os.path.join("app", "dashboard", base)
        while cur:
            cand = os.path.join(cur, "page.tsx")
            if os.path.exists(cand):
                s = io.open(cand, encoding="utf-8", errors="replace").read()
                checked.append((rel(cand), "force-dynamic" in s or "force-dynamic" in s))
            cur = os.path.dirname(cur)
        for f2, has in checked:
            out.write("  %-45s dynamic=%s\n" % (f2, has))
    out.write("\nHAS_COMPILED_OK=%s\n" % ("Compiled successfully" in raw))
    out.write("HAS_ERRORS=%s\n" % ("should be wrapped in a suspense boundary" in raw))
    out.write("FORCE_DYNAMIC_COUNT=%d\n" % raw.count("force-dynamic"))
    s = out.getvalue()
    io.open(os.path.join("scripts", "audit_fresh.txt"), "w", encoding="utf-8", newline="\n").write(s)
    # ASCII-only safe print
    safe = s.encode("ascii", "replace").decode("ascii")
    print(safe)

main()
