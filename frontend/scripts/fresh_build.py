"""Fresh build: rm -rf .next, run next build via subprocess, capture ALL output to a
UTF-8 file, then write an ASCII-only summary (exit code, prerender/suspense lines,
failing page paths) to a second file. Nothing non-ASCII ever hits the console."""
import io, os, shutil, subprocess, re, time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)

# 1. Nuke cache to defeat stale-prerender caching
for name in (".next",):
    p = os.path.join(root, name)
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)

# 2. Run the build
start = time.time()
proc = subprocess.run(
    "npx next build",
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
raw = proc.stdout
dur = int(time.time() - start)
out_path = os.path.join(root, "scripts", "fb_fresh.txt")
io.open(out_path, "wb").write(raw)
text = raw.decode("utf-8", errors="replace")
lines = text.splitlines()

# 3. ASCII-only summary
summary = []
summary.append("EXIT=%d DURATION_S=%d LINES=%d" % (proc.returncode, dur, len(lines)))
prerender = []
for ln in lines:
    low = ln.lower()
    if "prerender" in low or "suspense" in low or "useSearchParams" in low:
        prerender.append(ln)
summary.append("PRERENDER_SUSPENSE_LINES=%d" % len(prerender))
seen = set()
pages = []
for ln in prerender:
    m = re.findall(r'/dashboard/[a-z0-9/_]+', ln)
    for x in m:
        if x not in seen:
            seen.add(x)
            pages.append(x)
summary.append("DISTINCT_DASHBOARD_PATHS:")
for x in sorted(pages):
    summary.append("   " + x)
summary.append("LAST_TEN:")
for ln in prerender[-10:]:
    a = ln.encode("ascii", "replace").decode("ascii")[:150]
    summary.append("   | " + a)
summary.append("COMPILED=" + ("yes" if "Compiled successfully" in text else "no"))
summary.append("ALLDONE")

sum_path = os.path.join(root, "scripts", "fb_summary.txt")
io.open(sum_path, "w", encoding="utf-8", newline="\n").write("\n".join(summary))
print("WROTE:", os.path.basename(sum_path))
