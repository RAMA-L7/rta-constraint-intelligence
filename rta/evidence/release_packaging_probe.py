"""Phase 14 — packaging audit probe: build wheel + sdist and inspect contents."""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

# 1. Clean prior build artifacts
for d in ("dist", "build", "sdc_tools.egg-info"):
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
for f in glob.glob("*.egg-info"):
    if os.path.isdir(f):
        shutil.rmtree(f, ignore_errors=True)

# 2. Build wheel + sdist
try:
    import build  # noqa
    HAVE_BUILD = True
except ImportError:
    HAVE_BUILD = False

if not HAVE_BUILD:
    r = subprocess.run([sys.executable, "-m", "pip", "install", "build"],
                       capture_output=True, text=True)
    print("install build:", r.returncode, r.stderr[-200:] if r.returncode else "")

r = subprocess.run([sys.executable, "-m", "build", "--wheel", "--sdist"],
                   capture_output=True, text=True, cwd=ROOT)
print("build rc:", r.returncode)
if r.returncode != 0:
    print("STDOUT tail:", r.stdout[-1500:])
    print("STDERR tail:", r.stderr[-1500:])
    sys.exit(1)

wheels = glob.glob(os.path.join("dist", "*.whl"))
sdists = glob.glob(os.path.join("dist", "*.tar.gz"))
print("artifacts:", wheels, sdists)

# 3. Wheel contents
wheel = wheels[0]
print("=== WHEEL CONTENTS ===")
with zipfile.ZipFile(wheel) as z:
    names = sorted(z.namelist())
    for n in names:
        print(" ", n)

# 4. Which critical modules made it into the wheel?
CRITICAL = ["checker", "cli", "sdc_preprocess", "design_context",
            "support_boundary", "design_coverage", "constraint_interactions",
            "constraint_readiness", "readiness_diff", "finding_identity",
            "policy_engine", "reporter", "rules_registry", "ui"]
with zipfile.ZipFile(wheel) as z:
    names = set(z.namelist())
print("=== CRITICAL MODULE CHECK ===")
for mod in CRITICAL:
    present = any(n.startswith(f"{mod}/") or n == f"{mod}.py" for n in names)
    print(f"  {mod}: {'OK' if present else 'MISSING'}")

# 5. sdist contents (top-level only)
if sdists:
    sdist = sdists[0]
    print("=== SDIST TOP-LEVEL ===")
    r = subprocess.run(["tar", "-tzf", sdist], capture_output=True, text=True)
    top = sorted({p.split("/")[0] for p in r.stdout.splitlines()})
    print(" ", ", ".join(top))
