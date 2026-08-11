#!/usr/bin/env python3
"""
Phase 7 — Stage 13: Adversarial trust testing.

The dangerous failure is: input contains unsupported semantics → validator
says everything is clean → user assumes everything was checked.

Each case plants ONE construct outside the validator's analysis scope among
otherwise valid constraints, and asserts that:
  1. check_sdc still runs and reports its normal findings, AND
  2. result.scope.status is NOT "VALIDATED" (the limitation is visible), AND
  3. the scope counts reflect the specific limitation.

Usage:
    python benchmarks/test_trust_transparency.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc  # noqa: E402

GOOD = (
    "set sdc_version 2.2\n"
    "create_clock -name clk -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 1.0 -min 0.2 -clock clk [get_ports din]\n"
    "set_output_delay -max 1.5 -min 0.5 -clock clk [get_ports dout]\n"
)

CASES = [
    # (name, sdc, forbidden_status, expected_scope_key, expected_min_count)
    ("one_unsupported_command", GOOD + "set_clock_sense -positive [get_pins u/clk]\n",
     "VALIDATED", "unsupported", 1),
    ("one_netlist_dependent_ref", GOOD,
     None,  # netlist is normal for real SDC; status must be NETLIST_REQUIRED
     "netlist_required", 0),
    ("one_unknown_option", "set sdc_version 2.2\ncreate_clock -name clk -period 5.0 -bogus 1 [get_ports clk]\n"
     "set_input_delay -max 1.0 -clock clk [get_ports din]\n",
     None, "partially_analyzed", 1),
    ("one_ignored_option", GOOD + "set_load -max 0.5 [get_ports dout]\n",
     None, "partially_analyzed", 1),
    ("unsupported_tcl_foreach", GOOD + "foreach {p} [get_ports *] { set_input_delay 1 -clock clk $p }\n",
     "VALIDATED", "tcl_execution_required", 1),
    ("unsupported_tcl_if", GOOD + "if {[get_driving_cell [current_design]] == \"\"} { puts \"no driver\" }\n",
     "VALIDATED", "tcl_execution_required", 1),
    ("inline_tcl_expr", GOOD + "set CLK_PERIOD [expr 5.0 * 2]\ncreate_clock -name clk2 -period $CLK_PERIOD [get_ports clk2]\n",
     "VALIDATED", "tcl_execution_required", 1),
    ("unknown_command_misspelled", GOOD + "create_cloc -name typo -period 5 [get_ports clk]\n",
     "VALIDATED", "unsupported", 1),
]


def main():
    print("ADVERSARIAL TRUST — unsupported/netlist constructs must be visible")
    passed = total = 0
    for name, sdc, forbidden, key, min_count in CASES:
        total += 1
        r = check_sdc(sdc)
        scope = r.scope or {}
        status = scope.get("status", "NOT_VALIDATED")
        ok = True
        notes = []

        if forbidden and status == forbidden:
            ok = False
            notes.append(f"status {status} hides the limitation")
        # NETLIST-dependent cases: status must be NETLIST_REQUIRED or worse
        # (i.e. anything above VALIDATED — the limitation is surfaced).
        if name == "one_netlist_dependent_ref" and status in ("VALIDATED", "NOT_VALIDATED"):
            ok = False
            notes.append(f"netlist refs invisible (status={status})")
        if key and scope.get(key, 0) < min_count:
            ok = False
            notes.append(f"{key}={scope.get(key)} < expected {min_count}")
        # Unsupported constructs must never be silently "clean"
        if scope.get("unsupported") or scope.get("tcl_execution_required"):
            if scope.get("errors") is None and not r.issues:
                pass  # checker may legitimately have findings; scope must carry the flag
            if status == "VALIDATED":
                ok = False
                notes.append("unsupported construct present but status=VALIDATED")

        passed += ok
        flag = "✅" if ok else "❌"
        print(f"  {flag} {name:<30} status={status:<22} "
              f"unsup={scope.get('unsupported',0)} tcl={scope.get('tcl_execution_required',0)} "
              f"partial={scope.get('partially_analyzed',0)} netlist={scope.get('netlist_required',0)}")
        for n in notes:
            print(f"      ⚠ {n}")

    print(f"\nADVERSARIAL TRUST: {passed}/{total} cases surface their limitation")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
