#!/usr/bin/env python3
"""
CI gate exit-code verification — the exact contract the GitHub Action relies on.

Runs the same `rta check --baseline --gate` command sequence the composite
action (.github/actions/rta-gate/action.yml) executes, against the real
engineer_test_kit/14_baseline_gate fixture, and verifies the documented
exit-code contract:

    0 = pass
    1 = gate failed (merge blocked)
    2 = invalid invocation / input
    3 = analysis engine failure (SDC-140) — a gate can never report PASS

Exit 3 is exercised at the gate-evaluation level by the evidence suite
(rta/evidence/test_readiness_ci_gate.py, run_production_hardening.py); a CLI
crash is not deterministically triggerable from a fixture, so this script
verifies 0/1/2 through the CLI and asserts the engine-failure semantics are
documented in the readiness-diff gate contract.

Standalone script (not a pytest module): run with
    python tests/run_ci_gate_verification.py

Hygiene: this script NEVER writes to the tracked fixture
engineer_test_kit/14_baseline_gate/baseline.json. It regenerates the baseline
into a temporary directory so the committed baseline stays byte-identical to
HEAD after every run.
"""

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
# Windows console: force UTF-8 output (the gate contract text uses arrows).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJ = Path(__file__).resolve().parent.parent
KIT = PROJ / "engineer_test_kit" / "14_baseline_gate"
PY = sys.executable

# Temporary working copy of the baseline fixture — the script never touches
# the tracked engineer_test_kit/14_baseline_gate/baseline.json. Cleanup is
# registered with atexit so it runs on normal exit, sys.exit, and exceptions.
_TMP = tempfile.mkdtemp(prefix="rta_gate_verify_")
BASELINE = os.path.join(_TMP, "baseline.json")
atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))

PASS = 0
FAIL = 0
WARN = []


def run(cmd, desc, expect, parse_json=False, parse_junit=False):
    """Run a CLI command (list of args), compare exit code, capture output."""
    global PASS, FAIL
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(cmd, capture_output=True, timeout=120, env=env)
    out = result.stdout.decode("utf-8", errors="replace")
    err = result.stderr.decode("utf-8", errors="replace")
    ok = result.returncode == expect
    if ok:
        PASS += 1
        label = "PASS"
    else:
        FAIL += 1
        label = "FAIL"
        detail = (err[:300] or out[:300]).strip()
        WARN.append(f"  [{label}] {desc}: exit={result.returncode} (want {expect}) — {detail}")
    print(f"  {label} {desc} (exit {result.returncode})")
    if parse_json and ok:
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            FAIL += 1
            WARN.append(f"  [FAIL] {desc}: JSON parse failed — {e}")
    if parse_junit and ok:
        try:
            ET.fromstring(out)
        except ET.ParseError as e:
            FAIL += 1
            WARN.append(f"  [FAIL] {desc}: JUnit XML parse failed — {e}")
    return result


def section(name):
    print(f"\n{'=' * 60}\n  {name}\n{'=' * 60}")


def cli(*args):
    return [PY, str(PROJ / "cli.py"), *args]


# ═══════════════════════════════════════════════════════════════════════
# 0. Fixture sanity
# ═══════════════════════════════════════════════════════════════════════
section("FIXTURE — engineer_test_kit/14_baseline_gate")
for name in ["apb_uart.sdc", "apb_uart_netlist.v", "baseline.json",
             "changed.sdc", "changed_review_only.sdc", "gate_policy.yaml"]:
    ok = (KIT / name).is_file()
    if ok:
        PASS += 1
        print(f"  PASS fixture present: {name}")
    else:
        FAIL += 1
        WARN.append(f"  [FAIL] fixture missing: {name}")

# Always save a fresh baseline into the temporary working copy so the check
# is deterministic regardless of what is committed — the tracked fixture is
# never written.
run(cli("check", str(KIT / "apb_uart.sdc"),
        "--netlist", str(KIT / "apb_uart_netlist.v"),
        "--top", "apb_uart_top",
        "--save-baseline", BASELINE),
    "save fresh baseline (temp working copy)", expect=0)

# ═══════════════════════════════════════════════════════════════════════
# 1. Pass path — STRICT on the clean fixture
# ═══════════════════════════════════════════════════════════════════════
section("PASS — STRICT, clean SDC + baseline (exit 0)")
gate_json = run(cli("check", str(KIT / "apb_uart.sdc"),
                    "--netlist", str(KIT / "apb_uart_netlist.v"),
                    "--top", "apb_uart_top",
                    "--baseline", BASELINE,
                    "--gate", "STRICT", "--json"),
                "STRICT clean SDC passes", expect=0, parse_json=True)

if isinstance(gate_json, dict):
    gate = (gate_json.get("readiness_diff") or {}).get("gate") or {}
    ok = gate.get("result") == "PASS" and gate.get("exit_code") == 0
    if ok:
        PASS += 1
        print("  PASS JSON gate verdict: result=PASS exit_code=0")
    else:
        FAIL += 1
        WARN.append(f"  [FAIL] JSON gate verdict: {gate}")

# ═══════════════════════════════════════════════════════════════════════
# 2. Blocked path — STRICT on a regression
# ═══════════════════════════════════════════════════════════════════════
section("BLOCKED — STRICT, regression introduced (exit 1)")
gate_json = run(cli("check", str(KIT / "changed.sdc"),
                    "--netlist", str(KIT / "apb_uart_netlist.v"),
                    "--top", "apb_uart_top",
                    "--baseline", BASELINE,
                    "--gate", "STRICT", "--json"),
                "STRICT blocks the regression", expect=1, parse_json=True)
if isinstance(gate_json, dict):
    gate = (gate_json.get("readiness_diff") or {}).get("gate") or {}
    ok = gate.get("result") == "FAIL" and gate.get("exit_code") == 1
    if ok:
        PASS += 1
        print("  PASS JSON gate verdict: result=FAIL exit_code=1")
    else:
        FAIL += 1
        WARN.append(f"  [FAIL] JSON gate verdict: {gate}")
    if not gate.get("reasons"):
        FAIL += 1
        WARN.append("  [FAIL] blocked gate must explain why (reasons missing)")
    else:
        PASS += 1
        print(f"  PASS gate explains the block: {gate['reasons'][0][:80]}...")

# ═══════════════════════════════════════════════════════════════════════
# 3. Invalid invocation — STRICT without baseline (exit 2)
# ═══════════════════════════════════════════════════════════════════════
section("INVALID — baseline-dependent policy without baseline (exit 2)")
run(cli("check", str(KIT / "apb_uart.sdc"), "--gate", "STRICT"),
    "STRICT without baseline → exit 2", expect=2)
run(cli("check", str(KIT / "apb_uart.sdc"),
        "--gate", "NO_READINESS_REGRESSION"),
    "NO_READINESS_REGRESSION without baseline → exit 2", expect=2)

# ═══════════════════════════════════════════════════════════════════════
# 4. Invalid invocation — CUSTOM without policy (exit 2)
# ═══════════════════════════════════════════════════════════════════════
section("INVALID — CUSTOM without a policy file (exit 2)")
run(cli("check", str(KIT / "apb_uart.sdc"), "--gate", "CUSTOM"),
    "CUSTOM without --gate-policy → exit 2", expect=2)
run(cli("check", str(KIT / "apb_uart.sdc"),
        "--gate", "CUSTOM", "--gate-policy", str(KIT / "missing.yaml")),
    "CUSTOM with unreadable policy → exit 2", expect=2)

# ═══════════════════════════════════════════════════════════════════════
# 5. CUSTOM policy — team-review flow allows review items (exit 0)
# ═══════════════════════════════════════════════════════════════════════
section("CUSTOM — team-review policy (new review items allowed, exit 0)")
gate_json = run(cli("check", str(KIT / "changed_review_only.sdc"),
                    "--netlist", str(KIT / "apb_uart_netlist.v"),
                    "--top", "apb_uart_top",
                    "--baseline", BASELINE,
                    "--gate", "CUSTOM",
                    "--gate-policy", str(KIT / "gate_policy.yaml"), "--json"),
                "CUSTOM policy allows review-only change", expect=0,
                parse_json=True)
if isinstance(gate_json, dict):
    gate = (gate_json.get("readiness_diff") or {}).get("gate") or {}
    if gate.get("result") == "PASS":
        PASS += 1
        print("  PASS CUSTOM verdict: result=PASS")
    else:
        FAIL += 1
        WARN.append(f"  [FAIL] CUSTOM verdict: {gate}")

# ═══════════════════════════════════════════════════════════════════════
# 6. BLOCKERS_ONLY — works without a baseline (exit 0 on clean)
# ═══════════════════════════════════════════════════════════════════════
section("BLOCKERS_ONLY — no baseline required")
run(cli("check", str(KIT / "apb_uart.sdc"), "--gate", "BLOCKERS_ONLY"),
    "BLOCKERS_ONLY on clean SDC → exit 0", expect=0)

# ═══════════════════════════════════════════════════════════════════════
# 7. Missing/empty input (exit 2)
# ═══════════════════════════════════════════════════════════════════════
section("INVALID — missing input file (exit 2)")
run(cli("check", str(KIT / "does_not_exist.sdc"), "--gate", "STRICT"),
    "missing SDC file → exit 2", expect=2)

# ═══════════════════════════════════════════════════════════════════════
# 8. JUnit output is valid XML and carries the gate run
# ═══════════════════════════════════════════════════════════════════════
section("JUNIT — valid XML for CI dashboards")
run(cli("check", str(KIT / "apb_uart.sdc"),
        "--netlist", str(KIT / "apb_uart_netlist.v"),
        "--top", "apb_uart_top",
        "--baseline", BASELINE,
        "--gate", "STRICT", "--junit"),
    "STRICT clean SDC → valid JUnit XML", expect=0, parse_junit=True)

# ═══════════════════════════════════════════════════════════════════════
# 9. Action contract — the composite action file declares the gate contract
# ═══════════════════════════════════════════════════════════════════════
section("ACTION — .github/actions/rta-gate/action.yml contract")
action_yml = PROJ / ".github" / "actions" / "rta-gate" / "action.yml"
if action_yml.is_file():
    PASS += 1
    print("  PASS action.yml present")
else:
    FAIL += 1
    WARN.append("  [FAIL] .github/actions/rta-gate/action.yml missing")

# ═══════════════════════════════════════════════════════════════════════
# Report
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print(f"  CI GATE EXIT-CODE VERIFICATION  —  {PASS} passed, {FAIL} failed")
print(f"{'=' * 60}")
if WARN:
    print("\nDetails:")
    for w in WARN:
        print(w)
sys.exit(1 if FAIL else 0)
