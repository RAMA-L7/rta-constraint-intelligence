#!/usr/bin/env python3
"""
Phase 6 — Stage 11: Mutation testing (rule sensitivity).

Take a known-good SDC and mutate ONE thing at a time. Each mutation maps to a
rule that MUST fire. If the intended rule does not fire, that rule is
insensitive (a false negative).

Usage:
    python benchmarks/test_reference_mutation.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc  # noqa: E402

GOOD = """set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]
create_clock -name clk_io -period 10.0 [get_ports clk_io]
create_generated_clock -name div2 -master_clock clk_core \\
    -source [get_ports clk] -divide_by 2 [get_pins U_DIV/clkout]
set_clock_groups -asynchronous -group [get_clocks clk_core] \\
    -group [get_clocks clk_io]
set_input_delay -max 1.0 -min 0.2 -clock clk_core [get_ports data_in]
set_output_delay -max 1.5 -min 0.5 -clock clk_core [get_ports data_out]
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_core]
set_false_path -from [get_clocks clk_core] -to [get_clocks clk_io]
set_multicycle_path -setup 2 -hold 1 -from [get_ports data_in]
set_case_analysis 0 [get_ports test_mode]
"""

# (name, mutation, expected_rule, severity)
MUTATIONS = [
    # undefined clock in I/O delay → SDC-046
    ("io_delay_undefined_clock", GOOD.replace("-clock clk_core [get_ports data_in]",
                                               "-clock ghost_clock [get_ports data_in]"),
     "SDC-046", "error"),
    # undefined master clock → SDC-047
    ("generated_undefined_master", GOOD.replace("-master_clock clk_core",
                                                "-master_clock ghost_master"),
     "SDC-047", "warning"),
    # undefined clock in group → SDC-048
    ("group_undefined_clock", GOOD.replace("-group [get_clocks clk_io]",
                                           "-group [get_clocks ghost_io]"),
     "SDC-048", "warning"),
    # contradictory case analysis → SDC-049
    ("contradictory_case_analysis", GOOD + "set_case_analysis 1 [get_ports test_mode]\n",
     "SDC-049", "warning"),
    # input delay >= period → SDC-008
    ("input_delay_over_period", GOOD.replace("set_input_delay -max 1.0 -min 0.2",
                                             "set_input_delay -max 6.0 -min 0.2"),
     "SDC-008", "error"),
    # duplicate create_clock → SDC-002
    ("duplicate_create_clock", GOOD + "create_clock -name clk_core -period 5.0 [get_ports clk]\n",
     "SDC-002", "error"),
    # multicycle WITHOUT hold fix → SDC-021 (GOOD has -hold 1; mutation removes it)
    ("multicycle_no_hold", GOOD.replace("set_multicycle_path -setup 2 -hold 1",
                                         "set_multicycle_path -setup 2"),
     "SDC-021", "warning"),
]


def main():
    print("MUTATION TEST — one mutation at a time, expected rule must fire")
    total = passed = 0
    for name, text, rule, sev in MUTATIONS:
        total += 1
        r = check_sdc(text)
        found = [i for i in r.issues if i.code == rule]
        ok = bool(found)
        passed += ok
        print(f"  {'✅' if ok else '❌'} {name:<30} expected {rule:>7} → "
              f"{'FIRED' if ok else 'MISSED'}")
        if not ok:
            actual = sorted({i.code for i in r.issues})
            print(f"      actual rules: {actual}")
    print(f"\nMUTATION: {passed}/{total} mutations correctly trigger their rule")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
