"""Run next build and capture a clean UTF-8 log for reliable analysis."""
import io
import subprocess
import os
import time

log_path = os.path.join(os.path.dirname(__file__), "build_clean.txt")

# Always run with the CWD set to the frontend root (script lives in frontend/scripts).
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

start = time.time()
proc = subprocess.Popen(
    ["npx", "next", "build"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    shell=True,
)
buf = []
with proc.stdout as so:
    for line in io.TextIOWrapper(so, encoding="utf-8", errors="replace"):
        buf.append(line.rstrip("\r\n"))
proc.wait()
with io.open(log_path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(buf))

elapsed = int(time.time() - start)
errors = [ln for ln in buf if "prerender" in ln.lower() or "Error" in ln and "prerender" in ln.lower()]
print("EXITCODE:", proc.returncode)
print("DURATION_S:", elapsed)
print("LINES:", len(buf))
print("LOG_WRITTEN:", log_path)
print("PRERENDER_ERROR_LINES:", len([ln for ln in buf if "prerender" in ln.lower()]))
# List any page with a suspense/useSearchParams bailout
for ln in buf:
    low = ln.lower()
    if "should be wrapped" in low or "prerender-error" in low or "export encountered" in low:
        print("  >>", ln.strip()[:160])
