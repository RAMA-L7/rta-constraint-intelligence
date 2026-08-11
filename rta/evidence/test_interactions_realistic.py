"""
Phase 10 — Realistic-design benchmark for the constraint-interaction analyzer.

Two designs:
  - CLEAN: a realistic multi-clock block with MANY legal repeated constraints
    (min/max, rise/fall, setup/hold, add_delay, different clocks, bus subsets,
    virtual clocks). Expected: ZERO interaction findings.
  - PROBLEM: the same design with exactly FOUR known semantic defects injected.
    Expected: each intended defect detected, no extras.

Ground truth is derived from SDC semantics, not from analyzer output.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from constraint_interactions import analyze_interactions


CLEAN_DESIGN = (
    "# SoC block: 2 primary clocks + 2 virtual interface clocks\n"
    "set sdc_version 2.1\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk_core]\n"
    "create_clock -name clk_io -period 10.0 [get_ports clk_io]\n"
    "create_clock -name vclk_src -period 3.33\n"
    "create_clock -name vclk_dst -period 6.66\n"
    "set_clock_groups -asynchronous -group [get_clocks clk_core] "
    "-group [get_clocks clk_io] -group [get_clocks vclk_src] "
    "-group [get_clocks vclk_dst]\n"
    "set_clock_uncertainty -setup 0.15 -hold 0.05 [get_clocks clk_core]\n"
    "set_clock_uncertainty -setup 0.2 -hold 0.1 [get_clocks clk_io]\n"
    "set_clock_uncertainty -setup 0.1 [get_clocks vclk_src]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk_core "
    "[get_ports {d0 d1 d2 d3}]\n"
    "set_input_delay -rise -max 2.2 -clock clk_core [get_ports d0]\n"
    "set_input_delay -fall -max 2.2 -clock clk_core [get_ports d0]\n"
    "set_input_delay -max 3.0 -clock clk_io [get_ports {din_a din_b}]\n"
    "set_input_delay -max 1.0 -clock vclk_src [get_ports data_in] -add_delay\n"
    "set_input_delay -max 0.5 -clock vclk_src [get_ports data_in] -add_delay\n"
    "set_output_delay -max 4.0 -min 1.0 -clock clk_core [get_ports {q0 q1}]\n"
    "set_output_delay -max 5.0 -min 1.5 -clock clk_io [get_ports qout]\n"
    "set_false_path -from [get_clocks clk_test_fp] -to [get_clocks clk_core]\n"
    "set_multicycle_path 2 -setup -from [get_clocks clk_io] "
    "-to [get_clocks clk_core]\n"
    "set_multicycle_path 1 -hold -from [get_clocks clk_io] "
    "-to [get_clocks clk_core]\n"
    "set_max_delay 12 -from [get_clocks clk_io] -to [get_clocks clk_core]\n"
    "set_min_delay 3 -from [get_clocks clk_io] -to [get_clocks clk_core]\n"
    "set_case_analysis 0 [get_ports mode]\n"
    "set_load 0.05 [get_ports q0]\n"
    "set_load 0.05 [get_ports q1]\n"
    "set_input_transition 0.2 [get_ports clk_core]\n"
)

# The same design with exactly 4 injected defects:
#   1. duplicate:  din_a delay stated twice verbatim
#   2. override:   qout output delay max 5.0 -> 6.0 (no -add_delay)
#   3. conflict:   set_max_delay 12 -> 4, set_min_delay 3 -> 8 (4 < 8)
#   4. exception:  set_false_path between clk_io -> clk_core overlapping the
#                  existing multicycle pair on the same clocks
PROBLEM_DESIGN = (
    "# SoC block with 4 injected semantic defects\n"
    "set sdc_version 2.1\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk_core]\n"
    "create_clock -name clk_io -period 10.0 [get_ports clk_io]\n"
    "create_clock -name vclk_src -period 3.33\n"
    "create_clock -name vclk_dst -period 6.66\n"
    "set_clock_groups -asynchronous -group [get_clocks clk_core] "
    "-group [get_clocks clk_io] -group [get_clocks vclk_src] "
    "-group [get_clocks vclk_dst]\n"
    "set_clock_uncertainty -setup 0.15 -hold 0.05 [get_clocks clk_core]\n"
    "set_clock_uncertainty -setup 0.2 -hold 0.1 [get_clocks clk_io]\n"
    "set_clock_uncertainty -setup 0.1 [get_clocks vclk_src]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk_core "
    "[get_ports {d0 d1 d2 d3}]\n"
    "set_input_delay -rise -max 2.2 -clock clk_core [get_ports d0]\n"
    "set_input_delay -fall -max 2.2 -clock clk_core [get_ports d0]\n"
    "set_input_delay -max 3.0 -clock clk_io [get_ports din_a]\n"      # defect 1a
    "set_input_delay -max 3.0 -clock clk_io [get_ports din_a]\n"      # defect 1b
    "set_output_delay -max 4.0 -min 1.0 -clock clk_core [get_ports {q0 q1}]\n"
    "set_output_delay -max 5.0 -min 1.5 -clock clk_io [get_ports qout]\n"
    "set_output_delay -max 6.0 -clock clk_io [get_ports qout]\n"      # defect 2
    "set_false_path -from [get_clocks clk_io] -to [get_clocks clk_core]\n"  # defect 4
    "set_multicycle_path 2 -setup -from [get_clocks clk_io] "
    "-to [get_clocks clk_core]\n"
    "set_multicycle_path 1 -hold -from [get_clocks clk_io] "
    "-to [get_clocks clk_core]\n"
    "set_max_delay 4 -from [get_clocks clk_io] -to [get_clocks clk_core]\n"  # defect 3a
    "set_min_delay 8 -from [get_clocks clk_io] -to [get_clocks clk_core]\n"  # defect 3b
    "set_case_analysis 0 [get_ports mode]\n"
    "set_load 0.05 [get_ports q0]\n"
    "set_load 0.05 [get_ports q1]\n"
)


def main() -> int:
    print("INTERACTION REALISTIC DESIGNS")
    failures = 0

    # ── CLEAN ──────────────────────────────────────────────────────────────
    clean = analyze_interactions(CLEAN_DESIGN)
    clean_findings = clean.findings
    if clean_findings:
        failures += 1
        print(f"  ❌ clean: {len(clean_findings)} false finding(s)")
        for f in clean_findings:
            print(f"      [{f['code']}] {f['category']} L{f['line']}/L{f['line2']}: {f['msg'][:80]}")
    else:
        print(f"  ✅ clean: zero findings across {clean.constraints_analyzed} constraints "
              f"({clean.legal_multiples} legal multiple groups)")

    # ── PROBLEM ────────────────────────────────────────────────────────────
    prob = analyze_interactions(PROBLEM_DESIGN)
    s = prob.summary()
    # The false path on clk_io->clk_core overlaps FOUR distinct exception
    # commands on the same domain (mcp-setup, mcp-hold, max-delay, min-delay)
    # — each pair is a separate possible conflict (a false path makes every
    # other exception on that domain contradictory).
    expect = {
        "exact_duplicates": 1,     # din_a pair
        "overrides": 1,            # qout 5.0 -> 6.0
        "definite_conflicts": 1,   # max 4 < min 8
        "possible_conflicts": 4,   # fp vs mcp-setup / mcp-hold / max / min
    }
    for k, want in expect.items():
        got = s[k]
        if got != want:
            failures += 1
            print(f"  ❌ problem: {k} expected {want}, got {got}")
    got_codes = sorted({f["code"] for f in prob.findings})
    want_codes = ["SDC-067", "SDC-068", "SDC-069", "SDC-070"]
    if got_codes != want_codes:
        failures += 1
        print(f"  ❌ problem: codes expected {want_codes}, got {got_codes}")
    n_070 = sum(1 for f in prob.findings if f["code"] == "SDC-070")
    if n_070 != 4:
        failures += 1
        print(f"  ❌ problem: SDC-070 count expected 4, got {n_070}")
    for f in prob.findings:
        if not f.get("line") or not f.get("line2"):
            failures += 1
            print(f"  ❌ problem: {f['code']} missing dual-line provenance")
    if not failures:
        print("  ✅ problem: all 4 injected defects detected, no extras, "
              "dual-line provenance on all findings")

    print("INTERACTION REALISTIC: " + ("PASS" if not failures else "FAIL"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
