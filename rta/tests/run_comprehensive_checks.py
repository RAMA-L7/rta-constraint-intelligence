#!/usr/bin/env python3
"""
Comprehensive Ṛta feature test.
Runs every feature with multiple file variants and reports all issues.
"""

import sys, os, json, subprocess, tempfile, shutil
from pathlib import Path

# Fix Windows encoding for Unicode output
os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLES = os.path.join(PROJ, "samples")

PASS = 0
FAIL = 0
WARN = []


def run(cmd, desc="", expect=0, parse_json=False):
    global PASS, FAIL
    result = subprocess.run(cmd, capture_output=True, timeout=30, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    # Decode with utf-8, replacing un-decodable chars
    result.stdout = result.stdout.decode("utf-8", errors="replace")
    result.stderr = result.stderr.decode("utf-8", errors="replace")
    ok = result.returncode == expect
    if ok:
        PASS += 1
        label = "PASS"
    else:
        FAIL += 1
        label = "FAIL"
        detail = result.stderr[:200] or result.stdout[:200]
        WARN.append(f"  [{label}] {desc}: exit={result.returncode}, {detail}")
    status = "PASS" if ok else "FAIL"
    print(f"  {status} {desc}")
    if parse_json and ok:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return result


def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════════
# 1. CHECKER
# ═══════════════════════════════════════════════════════════════════
section("CHECKER — Validate SDC files")

# Each file + expected error count range
check_files = [
    ("rta/examples/samples/check_variants/good_complex.sdc", 0, 3, "Good complex SDC"),
    ("rta/examples/samples/check_variants/minimal_but_valid.sdc", 0, 5, "Minimal valid SDC"),
    ("rta/examples/samples/real_design_full.sdc", 0, 10, "Real design full"),
    ("rta/examples/samples/buggy_no_clocks.sdc", 1, 10, "Buggy — no clocks"),
    ("rta/examples/samples/edge_case_malformed.sdc", 1, 20, "Malformed SDC"),
    ("rta/examples/samples/edge_case_empty.sdc", 1, 10, "Empty file"),
    ("rta/examples/samples/edge_case_extreme_values.sdc", 1, 20, "Extreme values"),
]

for fpath, min_err, max_err, label in check_files:
    f = os.path.join(PROJ, fpath)
    # Buggy files exit 1 (errors found), good files exit 0
    exit_expect = 0 if min_err == 0 else 1
    r = run(["python", os.path.join(PROJ, "cli.py"), "check", f, "--json"],
            f"check {label}", expect=exit_expect, parse_json=True)
    if isinstance(r, dict):
        errors = r.get("summary", {}).get("errors", -1)
        ok = min_err <= errors <= max_err
        if not ok:
            FAIL -= 1
            WARN.append(f"  FAIL {label}: {errors} errors (expected {min_err}-{max_err})")
            print(f"  FAIL {label}: {errors} errors (expected {min_err}-{max_err})")

# Check CSV output
run(["python", os.path.join(PROJ, "cli.py"), "check",
     os.path.join(PROJ, "samples", "real_design_full.sdc"), "--format", "csv"],
    "check CSV output")

# Check Markdown output
run(["python", os.path.join(PROJ, "cli.py"), "check",
     os.path.join(PROJ, "samples", "real_design_full.sdc"), "--format", "markdown"],
    "check Markdown output")

# ═══════════════════════════════════════════════════════════════════
# 2. GENERATOR
# ═══════════════════════════════════════════════════════════════════
section("GENERATOR — SDC generation")

# Variant A: Minimal
r = run(["python", os.path.join(PROJ, "cli.py"), "generate", "--design", "TEST_A",
         "--clock", "clk=5.0:sys_clk"],
        "generate minimal", expect=0)
if "create_clock" in r.stdout and "TEST_A" in r.stdout:
    print("  PASS Minimal gen has clock + design name")
else:
    WARN.append("  ❌ Minimal gen missing expected content")

# Variant B: Full featured
r = run(["python", os.path.join(PROJ, "cli.py"), "generate", "--design", "TEST_B",
         "--clock", "clk_a=3.0:core_clk", "--clock", "clk_b=10.0:io_clk",
         "--derate", "--propagated", "--ideal-reset", "--scan",
         "--operating-condition", "WORST"],
        "generate full featured", expect=0)
checks = ["create_clock", "TEST_B", "set_timing_derate", "set_propagated_clock",
          "set_ideal_network", "set_case_analysis"]
for c in checks:
    if c not in r.stdout:
        WARN.append(f"  ❌ Full gen missing: {c}")

# Variant C: Virtual clock
r = run(["python", os.path.join(PROJ, "cli.py"), "generate", "--design", "TEST_C",
         "--clock", "vclk=10.0:--virtual"],
        "generate virtual clock", expect=0)

# ═══════════════════════════════════════════════════════════════════
# 3. LINTER
# ═══════════════════════════════════════════════════════════════════
section("LINTER — SDC formatting")

# Lint --check: exit 0 = lint-clean, exit 1 = has formatting issues
# Our files are well-formatted, so expect exit 0 (clean)
f1 = os.path.join(PROJ, "samples", "real_design_full.sdc")
run(["python", os.path.join(PROJ, "cli.py"), "lint", f1, "--check"],
    "lint --check real design (expect clean)", expect=0)
f2 = os.path.join(PROJ, "samples", "check_variants", "good_complex.sdc")
run(["python", os.path.join(PROJ, "cli.py"), "lint", f2, "--check"],
    "lint --check good complex (expect clean)", expect=0)

# Lint with output
td = tempfile.mkdtemp()
tmp_out = os.path.join(td, "linted.sdc")
r = run(["python", os.path.join(PROJ, "cli.py"), "lint",
         os.path.join(PROJ, "samples", "minimal_sdc.sdc"), "--output", tmp_out],
        "lint with output file")
shutil.rmtree(td, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════
# 4. CONVERTER
# ═══════════════════════════════════════════════════════════════════
section("CONVERTER — SDC to JSON/YAML")

rf = os.path.join(PROJ, "samples", "real_design_full.sdc")
r = run(["python", os.path.join(PROJ, "cli.py"), "convert", rf, "--format", "json"],
        "convert to JSON", parse_json=True)
if isinstance(r, dict):
    for key in ["clocks", "input_delays", "output_delays", "false_paths"]:
        if key not in r:
            WARN.append(f"  ❌ JSON missing key: {key}")

r = run(["python", os.path.join(PROJ, "cli.py"), "convert", rf, "--format", "yaml"],
        "convert to YAML")

# Convert minimal SDC
mf = os.path.join(PROJ, "samples", "check_variants", "minimal_but_valid.sdc")
run(["python", os.path.join(PROJ, "cli.py"), "convert", mf, "--format", "json"],
     "convert minimal SDC to JSON")

# ═══════════════════════════════════════════════════════════════════
# 5. DIFF
# ═══════════════════════════════════════════════════════════════════
section("DIFF — Constraint change analysis")

v1 = os.path.join(PROJ, "samples", "diff", "design_v1.sdc")
v2 = os.path.join(PROJ, "samples", "diff", "design_v2.sdc")

r = run(["python", os.path.join(PROJ, "cli.py"), "diff", v1, v2, "--json"],
        "diff V1 vs V2", parse_json=True)
if isinstance(r, dict):
    added = r.get("stats", {}).get("added", -1)
    if added < 1:
        WARN.append(f"  ❌ Diff should detect additions (got {added})")

# Diff identical files (should have 0 changes)
r = run(["python", os.path.join(PROJ, "cli.py"), "diff", v1, v1, "--json"],
        "diff identical files", parse_json=True)

# ═══════════════════════════════════════════════════════════════════
# 6. COVERAGE
# ═══════════════════════════════════════════════════════════════════
section("COVERAGE — Gap analysis")

rf = os.path.join(PROJ, "samples", "real_design_full.sdc")
r = run(["python", os.path.join(PROJ, "cli.py"), "coverage", rf, "--json"],
        "coverage real design", parse_json=True)
if isinstance(r, dict):
    score = r.get("score_pct", -1)
    if score < 50:
        WARN.append(f"  ❌ Coverage too low: {score}%")

mf = os.path.join(PROJ, "samples", "check_variants", "minimal_but_valid.sdc")
run(["python", os.path.join(PROJ, "cli.py"), "coverage", mf],
     "coverage minimal SDC")

ef = os.path.join(PROJ, "samples", "edge_case_empty.sdc")
run(["python", os.path.join(PROJ, "cli.py"), "coverage", ef],
     "coverage empty SDC")

# ═══════════════════════════════════════════════════════════════════
# 7. CLOCK RELATIONS
# ═══════════════════════════════════════════════════════════════════
section("CLOCK RELATIONS — Clock analysis")

cf = os.path.join(PROJ, "samples", "real_design_full.sdc")
r = run(["python", os.path.join(PROJ, "cli.py"), "analyze", "clock-relations",
         cf, "--json"], "clock relations real design", parse_json=True)
if isinstance(r, dict):
    n_clocks = r.get("stats", {}).get("clocks", -1)
    if n_clocks < 3:
        WARN.append(f"  ❌ Expected >=3 clocks, got {n_clocks}")

# Empty SDC
ef = os.path.join(PROJ, "samples", "edge_case_empty.sdc")
run(["python", os.path.join(PROJ, "cli.py"), "analyze", "clock-relations",
     ef, "--json"], "clock relations empty SDC")

# ═══════════════════════════════════════════════════════════════════
# 8. RULES REGISTRY
# ═══════════════════════════════════════════════════════════════════
section("RULES — Registry lookup")

r = run(["python", os.path.join(PROJ, "cli.py"), "rules", "list"],
        "rules list")
if "SDC-001" not in r.stdout:
    WARN.append("  ❌ rules list missing SDC-001")

run(["python", os.path.join(PROJ, "cli.py"), "rules", "show", "SDC-060"],
     "rules show SDC-060")

r = run(["python", os.path.join(PROJ, "cli.py"), "rules", "list", "--search", "clock"],
        "rules search 'clock'")

# ═══════════════════════════════════════════════════════════════════
# 9. CUSTOM RULES
# ═══════════════════════════════════════════════════════════════════
section("CUSTOM RULES — YAML policies")

rf = os.path.join(PROJ, "samples", "real_design_full.sdc")
crf = os.path.join(PROJ, "samples", "test_custom_rules.yaml")
r = run(["python", os.path.join(PROJ, "cli.py"), "check", rf,
         "--custom-rules", crf, "--json"],
        "custom rules with real design", parse_json=True)
if isinstance(r, dict):
    cr = r.get("summary", {}).get("custom_rules_total", 0)
    if cr < 8:
        WARN.append(f"  ❌ Expected 8 custom rules, got {cr}")

# ═══════════════════════════════════════════════════════════════════
# 10. BATCH
# ═══════════════════════════════════════════════════════════════════
section("BATCH — Directory processing")

sd = os.path.join(PROJ, "samples")
run(["python", os.path.join(PROJ, "cli.py"), "batch", "check", sd],
     "batch check samples dir (expect errors from buggy files)", expect=1)

run(["python", os.path.join(PROJ, "cli.py"), "batch", "lint", sd],
     "batch lint samples dir")

# ═══════════════════════════════════════════════════════════════════
# 11. REPORT
# ═══════════════════════════════════════════════════════════════════
section("REPORT — HTML generation")

td = tempfile.mkdtemp()
out = os.path.join(td, "report.html")
run(["python", os.path.join(PROJ, "cli.py"), "report", "coverage",
     os.path.join(PROJ, "samples", "real_design_full.sdc"), "--output", out],
     "report coverage")
if os.path.exists(out):
    with open(out, encoding="utf-8", errors="replace") as f:
        if "<!DOCTYPE html>" in f.read():
            print("  PASS Report is valid HTML")
else:
    WARN.append(f"  ❌ Report file not created at {out}")
shutil.rmtree(td, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════
# 12. FEEDBACK SYSTEM
# ═══════════════════════════════════════════════════════════════════
section("FEEDBACK — Save/Load")

from ui.feedback import save_feedback, load_feedback, FeedbackEntry
from datetime import datetime

# Save test entries
test_entries = [
    FeedbackEntry(timestamp=datetime.now().isoformat(), feature="checker",
                  rating=1, comment="Great checker!", sdc_file="test.sdc",
                  results_summary="0 errors, 0 warnings"),
    FeedbackEntry(timestamp=datetime.now().isoformat(), feature="linter",
                  rating=-1, comment="Linter found false positives",
                  sdc_file="bad.sdc", results_summary="3 warnings"),
    FeedbackEntry(timestamp=datetime.now().isoformat(), feature="converter",
                  rating=1, comment="", sdc_file="test.sdc",
                  results_summary="5 clocks parsed"),
]

for e in test_entries:
    save_feedback(e)
    print(f"  SAVED: {e.feature} — {'UP' if e.rating==1 else 'DOWN'} {e.comment[:30] if e.comment else '(no comment)'}")

loaded = load_feedback()
recent = [e for e in loaded if e.comment or e.results_summary]
if len(recent) >= 3:
    print(f"  Feedback loaded {len(loaded)} entries")
else:
    WARN.append(f"  ❌ Feedback only loaded {len(loaded)} entries (expected >=3)")

# Verify feature names are specific (not "features")
for e in loaded:
    if e.feature == "features":
        WARN.append(f"  FAIL Generic feature name 'features' found in feedback")
        break

# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════
section("SUMMARY")
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
print(f"  Warnings: {len(WARN)}")
if WARN:
    print(f"\n  Issues found:")
    for w in WARN:
        print(f"  {w}")

sys.exit(0 if FAIL == 0 else 1)
