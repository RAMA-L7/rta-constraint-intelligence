"""
Phase 10 — Adversarial false-positive suite for the constraint-interaction
analyzer.

Every case here is LEGAL SDC that *looks* conflicting. The analyzer must
produce ZERO findings on all of them. Also includes a realistic clean design
with many legal repeated constraints (the classic false-positive trap).

Expected result: 0 false findings across all cases.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from constraint_interactions import analyze_interactions

LEGAL_CASES = {
    # different clocks
    "diff_clocks": (
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
        "set_input_delay -max 2.0 -clock clk_b [get_ports din]\n"
    ),
    # different ports
    "diff_ports": (
        "set_input_delay -max 2.0 -clock clk_a [get_ports din_a]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din_b]\n"
    ),
    # min vs max
    "min_max": (
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
        "set_input_delay -min 0.5 -clock clk_a [get_ports din]\n"
    ),
    # rise vs fall
    "rise_fall": (
        "set_input_delay -rise -max 2.0 -clock clk_a [get_ports din]\n"
        "set_input_delay -fall -max 2.0 -clock clk_a [get_ports din]\n"
    ),
    # setup vs hold
    "setup_hold": (
        "set_clock_uncertainty -setup 0.1 [get_clocks clk_a]\n"
        "set_clock_uncertainty -hold 0.05 [get_clocks clk_a]\n"
    ),
    # -add_delay accumulation
    "add_delay": (
        "set_input_delay -max 1.0 -clock clk_a [get_ports din] -add_delay\n"
        "set_input_delay -max 0.5 -clock clk_a [get_ports din] -add_delay\n"
    ),
    # different hierarchy (pin vs port)
    "pin_vs_port": (
        "set_input_delay -max 2.0 -clock clk_a [get_pins u_core/din]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
    ),
    # different wildcard collections
    "wildcard_sets": (
        "set_input_delay -max 2.0 -clock clk_a [get_ports {din_a din_b}]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports {din_a din_c}]\n"
    ),
    # virtual clocks (independent references)
    "virtual_clocks": (
        "create_clock -name vclk_a -period 5.0\n"
        "create_clock -name vclk_b -period 7.0\n"
        "set_input_delay -max 2.0 -clock vclk_a [get_ports din]\n"
        "set_input_delay -max 2.0 -clock vclk_b [get_ports din]\n"
    ),
    # generated clocks (different masters)
    "generated_clocks": (
        "create_clock -name clk_a -period 10.0 [get_ports clk_a]\n"
        "create_generated_clock -name div2_a -source [get_ports clk_a] "
        "-divide_by 2 [get_pins u_a/q]\n"
        "create_generated_clock -name div2_b -source [get_ports clk_a] "
        "-divide_by 2 [get_pins u_b/q]\n"
    ),
    # bus subsets (different bit ranges)
    "bus_subsets": (
        "set_input_delay -max 2.0 -clock clk_a [get_ports {data[7:4]}]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports {data[3:0]}]\n"
    ),
    # variables resolving to different objects
    "var_ports": (
        "set P1 din_a\n"
        "set P2 din_b\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports $P1]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports $P2]\n"
    ),
    # one command carrying both -max and -min
    "combined_min_max": (
        "set_input_delay -max 2.0 -min 0.5 -clock clk_a [get_ports din]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
    ),
    # MCP setup vs MCP hold (same value, different mode)
    "mcp_setup_hold": (
        "set_multicycle_path 2 -setup -from [get_ports a] -to [get_ports b]\n"
        "set_multicycle_path 2 -hold -from [get_ports a] -to [get_ports b]\n"
    ),
    # max delay on different endpoints
    "max_diff_endpoints": (
        "set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
        "set_max_delay 5 -from [get_ports a] -to [get_ports c]\n"
    ),
    # max delay -from only vs -from/-to
    "max_from_only": (
        "set_max_delay 5 -from [get_ports a]\n"
        "set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
    ),
    # uncertainty on different clocks
    "uncertainty_diff_clocks": (
        "set_clock_uncertainty -setup 0.1 [get_clocks clk_a]\n"
        "set_clock_uncertainty -setup 0.1 [get_clocks clk_b]\n"
    ),
    # case analysis on different pins (SDC-049 territory only for same pin)
    "case_diff_pins": (
        "set_case_analysis 0 [get_ports mode_a]\n"
        "set_case_analysis 1 [get_ports mode_b]\n"
    ),
    # clock groups + false path redundancy (legal practice)
    "group_fp_redundancy": (
        "set_clock_groups -asynchronous -group [get_clocks clk_a] "
        "-group [get_clocks clk_b]\n"
        "set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]\n"
    ),
    # identical delay on two separate wildcard-expanded commands (equivalent
    # braced vs repeated collection form) — same objects, so a duplicate IS
    # expected; this case instead uses DIFFERENT objects via two commands.
    "multi_object_same_value": (
        "set_input_delay -max 2.0 -clock clk_a [get_ports din_a] "
        "[get_ports din_b]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din_c]\n"
    ),
}

# A realistic CLEAN design with many legal repeated constraints.
CLEAN_DESIGN = (
    "# realistic clean block\n"
    "set sdc_version 2.1\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk_core]\n"
    "create_clock -name clk_io -period 10.0 [get_ports clk_io]\n"
    "create_clock -name clk_test -period 100.0 [get_ports clk_test]\n"
    "set_clock_groups -asynchronous -group [get_clocks clk_core] "
    "-group [get_clocks clk_io] -group [get_clocks clk_test]\n"
    "set_clock_uncertainty -setup 0.15 -hold 0.05 [get_clocks clk_core]\n"
    "set_clock_uncertainty -setup 0.2 -hold 0.1 [get_clocks clk_io]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk_core "
    "[get_ports {d0 d1 d2 d3}]\n"
    "set_input_delay -max 3.0 -min 1.0 -clock clk_io [get_ports {din_a din_b}]\n"
    "set_input_delay -rise -max 2.2 -clock clk_core [get_ports d0]\n"
    "set_input_delay -fall -max 2.2 -clock clk_core [get_ports d0]\n"
    "set_output_delay -max 4.0 -min 1.0 -clock clk_core [get_ports {q0 q1}]\n"
    "set_output_delay -max 5.0 -min 1.5 -clock clk_io [get_ports qout]\n"
    "set_false_path -from [get_clocks clk_test] -to [get_clocks clk_core]\n"
    "set_multicycle_path 2 -setup -from [get_clocks clk_io] "
    "-to [get_clocks clk_core]\n"
    "set_multicycle_path 1 -hold -from [get_clocks clk_io] "
    "-to [get_clocks clk_core]\n"
    "set_max_delay 12 -from [get_clocks clk_io] -to [get_clocks clk_core]\n"
    "set_min_delay 3 -from [get_clocks clk_io] -to [get_clocks clk_core]\n"
)


def main() -> int:
    print("INTERACTION ADVERSARIAL (FALSE-POSITIVE)")
    failures = 0
    for name, sdc in LEGAL_CASES.items():
        ia = analyze_interactions(sdc)
        findings = ia.findings
        if findings:
            failures += 1
            print(f"  ❌ {name}: {len(findings)} false finding(s)")
            for f in findings:
                print(f"      [{f['code']}] {f['category']} L{f['line']}/L{f['line2']}: {f['msg'][:90]}")
        else:
            print(f"  ✅ {name}")
    ia = analyze_interactions(CLEAN_DESIGN)
    if ia.findings:
        failures += 1
        print(f"  ❌ clean_design: {len(ia.findings)} false finding(s)")
        for f in ia.findings:
            print(f"      [{f['code']}] {f['category']} L{f['line']}/L{f['line2']}: {f['msg'][:90]}")
    else:
        print(f"  ✅ clean_design ({len(LEGAL_CASES) + 1} legal repeated constraints)")
    total = len(LEGAL_CASES) + 1
    print(f"INTERACTION ADVERSARIAL: {total - failures}/{total} cases produce zero false findings")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
