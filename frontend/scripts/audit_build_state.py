"""Find the newest build log, extract failing pages, cross-check force-dynamic.
Writes results to a UTF-8 file; prints only ASCII-safe summary."""
import io, glob, os, re

# 1. Newest build log produced by build_clean-style runs
cands = []
for pat in [r"scripts\build_clean.txt", r"scripts\*.txt", r"build_clean.txt", r"build_log.txt", r"build_log_decoded.txt"]:
    for p in glob.glob(pat):
        try:
            cands.append((os.path.getmtime(p), p))
        except OSError:
            pass
cands.sort(reverse=True)
out = io.open(os.path.join("scripts", "audit_out.txt"), "w", encoding="utf-8", newline="\n")
out.write("BUILD LOG CANDIDATES (newest first):\n")
for m, p in cands[:5]:
    out.write("   %s  %s\n" % (p, m))
out.write("\n")

failing = set()
for m, p in cands[:5]:
    try:
        raw = io.open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    for mo in re.finditer(r'/dashboard/([a-z0-9/_]+)"', raw):
        seg = mo.group(1)
        for s in re.split(r'[./]', seg):
            if s:
                failing.add(s)

out.write("FAILING-PAGE-SEGMENTS (union across logs):\n")
for s in sorted(failing):
    out.write("   - %s\n" % s)
out.write("count=%d\n\n" % len(failing))

# 2. Which of those segments' page.tsx have force-dynamic
out.write("FORCE-DYNAMIC CROSS-CHECK:\n")
for seg in sorted(failing):
    p = os.path.join("app", seg, "page.tsx")
    if not os.path.exists(p):
        out.write("   %-28s NO PAGE FILE\n" % seg)
        continue
    s = io.open(p, encoding="utf-8", errors="replace").read()
    had = "force-dynamic" in s
    out.write("   %-28s dynamic=%s\n" % (seg, had))
out.write("\nDONE\n")
out.close()
print("AUDIT WRITTEN: scripts/audit_out.txt (%d segments)" % len(failing))
