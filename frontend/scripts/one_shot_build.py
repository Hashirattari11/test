"""One-shot cold build with bulletproof output:
- writes raw stdout+stderr bytes to  build_raw.bin   (no decode, bytes)
- writes an ASCII-only "RC=<n>" line to build_rc.txt
- prints nothing except "RC=<n>" to the console (pure ASCII, encoding-safe)
- deletes .next first to guarantee a genuinely cold fresh build
"""
import io
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# 1) Nuke the cache so this is a truly cold build.
for name in (".next",):
    p = os.path.join(ROOT, name)
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)

# 2) Run the build, capture raw bytes.
start = time.time()
proc = subprocess.run(
    "npx next build",
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
dur = int(time.time() - start)
rc = proc.returncode

# 3) Write raw bytes to build_raw.bin (decode happens at read time, never here).
with open("build_raw.bin", "wb") as fh:
    fh.write(proc.stdout or b"")
if proc.stderr:
    with open("build_stderr.bin", "wb") as fh:
        fh.write(proc.stderr)

# 4) ASCII-only status line.
status = "RC=%d DURATION_S=%d BYTES=%d\n" % (
    rc,
    dur,
    len(proc.stdout or b""),
)
with io.open("build_rc.txt", "w", encoding="ascii", newline="\n") as fh:
    fh.write(status)

# 5) Console: ASCII-only.
sys.stdout.write("RC=%d DURATION_S=%d\n" % (rc, dur))
