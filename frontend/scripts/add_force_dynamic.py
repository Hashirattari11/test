"""Add `export const dynamic = "force-dynamic";` to every dashboard page (client
components) that uses useSearchParams(), so Next.js skips static prerendering
(avoids the "useSearchParams() should be wrapped in a suspense boundary"
build error on Vercel). Idempotent: skips pages that already export `dynamic`.
CRLF-safe: reads/writes with explicit newline handling.
"""
import io, glob, os

patched: list[str] = []
already: list[str] = []
skipped: list[str] = []

for p in glob.glob(r"app\dashboard\**\page.tsx", recursive=True):
    raw = io.open(p, encoding="utf-8").read()
    if "useSearchParams" not in raw:
        continue
    if not raw.startswith('"use client";'):
        skipped.append(p)
        continue
    if "export const dynamic" in raw:
        already.append(p)
        continue
    # Insert right after the "use client" directive.
    marker = '"use client";'
    assert raw.startswith(marker), p
    tail = raw[len(marker):]
    # Drop a single leading newline if present, then re-add our block cleanly.
    if tail.startswith("\r\n"):
        tail = tail[2:]
    elif tail.startswith("\n"):
        tail = tail[1:]
    nw = marker + '\n\nexport const dynamic = "force-dynamic";\n' + tail
    io.open(p, "w", encoding="utf-8", newline="\n").write(nw)
    patched.append(p)

print("PATCHED: %d" % len(patched))
for x in patched:
    print("  +", os.path.relpath(x, "app"))
print("ALREADY_DYNAMIC: %d" % len(already))
for x in already:
    print("  =", os.path.relpath(x, "app"))
print("SKIPPED(no use client): %d" % len(skipped))
for x in skipped:
    print("  -", os.path.relpath(x, "app"))
