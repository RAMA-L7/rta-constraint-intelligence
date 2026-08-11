"""
Phase 12 — CI quality-gate policy suite.

Each row: baseline status / current status / delta / expected gate result and
exit code per policy. Policies are opt-in only; default CLI behavior never
runs a gate. Engine failure can never PASS. Incompatible baselines fail with
exit 2. Old warnings unchanged by the baseline must not fail a
baseline-aware gate (baseline is context, not an excuse).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc
import readiness_diff as rd

PASS, FAIL = "PASS", "FAIL"
E_PASS, E_GATE, E_INV, E_ENG = rd.EXIT_PASS, rd.EXIT_GATE_FAILED, rd.EXIT_INVALID, rd.EXIT_ENGINE_FAILURE


def _snap(sdc_text, engine_failed=False):
    r = check_sdc(sdc_text)
    s = rd.build_snapshot(r, source_name="t.sdc")
    if engine_failed:
        s["analysis"]["engine_failed"] = True
    return s


CLEAN = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
"""

BLOCKED = CLEAN + "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]\n"

DUP = CLEAN + "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"

REVIEW = CLEAN + "set_false_path -from [get_ports din] -to [get_ports dout]\n"


def run():
    fails = []

    def check(label, cond, detail=""):
        if not cond:
            fails.append(f"{label}: {detail}")

    # ── Policy: BLOCKERS_ONLY (works without a baseline) ────────────────────
    g = rd.evaluate_gate(rd.POLICY_BLOCKERS_ONLY, None, _snap(CLEAN), {})
    check("BLOCKERS_ONLY clean", g["result"] == PASS and g["exit_code"] == E_PASS,
          f"{g['result']}/{g['exit_code']}")
    g = rd.evaluate_gate(rd.POLICY_BLOCKERS_ONLY, None, _snap(BLOCKED), {})
    check("BLOCKERS_ONLY blocked", g["result"] == FAIL and g["exit_code"] == E_GATE,
          f"{g['result']}/{g['exit_code']}")
    # A duplicate-only (advisory) design is NOT blocked.
    g = rd.evaluate_gate(rd.POLICY_BLOCKERS_ONLY, None, _snap(DUP), {})
    check("BLOCKERS_ONLY advisory-not-blocked", g["result"] == PASS, g["result"])

    # ── Policy: NO_READINESS_REGRESSION (baseline-aware) ────────────────────
    b_clean = _snap(CLEAN)

    # Old blocker unchanged by baseline → PASS (baseline-aware adoption).
    b_blk = _snap(BLOCKED)
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b_blk, _snap(BLOCKED),
                         rd.diff_snapshots(b_blk, _snap(BLOCKED)))
    check("NO_REGRESSION old-blocker-unchanged", g["result"] == PASS, g["result"])

    # Old warnings unchanged → PASS.
    b_dup = _snap(DUP)
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b_dup, _snap(DUP),
                         rd.diff_snapshots(b_dup, _snap(DUP)))
    check("NO_REGRESSION old-advisory-unchanged", g["result"] == PASS, g["result"])

    # New blocker → FAIL.
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b_clean, _snap(BLOCKED),
                         rd.diff_snapshots(b_clean, _snap(BLOCKED)))
    check("NO_REGRESSION new-blocker", g["result"] == FAIL and g["exit_code"] == E_GATE,
          f"{g['result']}/{g['exit_code']}")

    # Resolved blocker → PASS (improvement).
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, _snap(BLOCKED), b_clean,
                         rd.diff_snapshots(_snap(BLOCKED), b_clean))
    check("NO_REGRESSION resolved-blocker", g["result"] == PASS, g["result"])

    # New review item (exception overlap) → FAIL under NO_REGRESSION.
    b_clean2 = _snap(CLEAN)
    c_rev = _snap(REVIEW)
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b_clean2, c_rev,
                         rd.diff_snapshots(b_clean2, c_rev))
    check("NO_REGRESSION new-review-item", g["result"] == FAIL, g["result"])

    # New advisory-only → PASS under NO_REGRESSION (advisories are allowed).
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b_clean, _snap(DUP),
                         rd.diff_snapshots(b_clean, _snap(DUP)))
    check("NO_REGRESSION new-advisory-only", g["result"] == PASS, g["result"])

    # Baseline required: NO_REGRESSION without a baseline → FAIL exit 2.
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, None, _snap(CLEAN), {})
    check("NO_REGRESSION no-baseline", g["result"] == FAIL and g["exit_code"] == E_INV,
          f"{g['result']}/{g['exit_code']}")

    # ── Policy: STRICT ──────────────────────────────────────────────────────
    g = rd.evaluate_gate(rd.POLICY_STRICT, b_clean, _snap(CLEAN),
                         rd.diff_snapshots(b_clean, _snap(CLEAN)))
    check("STRICT clean", g["result"] == PASS, g["result"])
    g = rd.evaluate_gate(rd.POLICY_STRICT, b_clean, _snap(BLOCKED),
                         rd.diff_snapshots(b_clean, _snap(BLOCKED)))
    check("STRICT new-blocker", g["result"] == FAIL, g["result"])
    g = rd.evaluate_gate(rd.POLICY_STRICT, b_clean, _snap(REVIEW),
                         rd.diff_snapshots(b_clean, _snap(REVIEW)))
    check("STRICT new-review", g["result"] == FAIL, g["result"])
    # Old review item unchanged in baseline → PASS (baseline-aware).
    b_rev = _snap(REVIEW)
    g = rd.evaluate_gate(rd.POLICY_STRICT, b_rev, _snap(REVIEW),
                         rd.diff_snapshots(b_rev, _snap(REVIEW)))
    check("STRICT old-review-unchanged", g["result"] == PASS, g["result"])

    # ── Engine failure: never PASS, exit 3, every policy ───────────────────
    for policy in (rd.POLICY_BLOCKERS_ONLY, rd.POLICY_NO_REGRESSION, rd.POLICY_STRICT):
        g = rd.evaluate_gate(policy, b_clean, _snap(CLEAN, engine_failed=True),
                             rd.diff_snapshots(b_clean, _snap(CLEAN, engine_failed=True)))
        check(f"engine-failure {policy}",
              g["result"] == FAIL and g["exit_code"] == E_ENG,
              f"{g['result']}/{g['exit_code']}")

    # ── Incompatible baseline: exit 2, never silently trusted ───────────────
    bad = _snap(CLEAN)
    bad["schema_version"] = 99
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, bad, _snap(CLEAN),
                         rd.diff_snapshots(bad, _snap(CLEAN)))
    check("incompatible-baseline", g["result"] == FAIL and g["exit_code"] == E_INV,
          f"{g['result']}/{g['exit_code']}")

    # ── Unknown policy / CUSTOM: exit 2, NOT_CONFIGURED ─────────────────────
    g = rd.evaluate_gate("BOGUS", b_clean, _snap(CLEAN), {})
    check("unknown-policy", g["result"] == "NOT_CONFIGURED" and g["exit_code"] == E_INV,
          f"{g['result']}/{g['exit_code']}")
    g = rd.evaluate_gate(rd.POLICY_CUSTOM, b_clean, _snap(CLEAN), {})
    check("custom-policy", g["result"] == "NOT_CONFIGURED" and g["exit_code"] == E_INV,
          f"{g['result']}/{g['exit_code']}")

    # ── Baseline file safety (untrusted input) ──────────────────────────────
    snap, errs = rd.load_snapshot('{"schema_version": 1}')          # missing keys
    check("snapshot-missing-keys", snap is None and errs, str(errs))
    snap, errs = rd.load_snapshot("not json at all")                 # invalid JSON
    check("snapshot-bad-json", snap is None and errs, str(errs))
    snap, errs = rd.load_snapshot("")                                # empty
    check("snapshot-empty", snap is None and errs, str(errs))
    huge = '{"x": "' + "a" * (rd.MAX_SNAPSHOT_BYTES + 100) + '"}'
    snap, errs = rd.load_snapshot(huge)                              # oversized
    check("snapshot-oversized", snap is None and errs, str(errs))

    print(f"CI GATE SUITE: {'ALL PASS' if not fails else 'FAILURES'}")
    for f in fails:
        print("  ❌", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
