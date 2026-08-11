"""
Phase 10 — Performance suite for the constraint-interaction analyzer.

Generates N-constraint SDC files (a mix of duplicates, overrides, legal
min/max pairs, and a few timing exceptions) and times analyze_interactions.

The analyzer groups by semantic identity (dict keyed by normalized tuple), so
the common path is near-linear. 100 / 1,000 / 10,000 constraints.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from constraint_interactions import analyze_interactions


def make_sdc(n: int) -> str:
    """Deterministic N-constraint SDC: unique clocks/ports, legal min/max,
    exactly ONE duplicated pair (2 identical lines), one max<min conflict, one
    fp/mcp pair. The duplicated pair, the conflict, and the fp/mcp pair are on
    disjoint objects so the expected counts are exact."""
    lines = []
    lines.append("create_clock -name clk0 -period 10.0 [get_ports clk0]")
    # per-block: a pair of input delays (min/max) + output delay on unique ports
    for i in range(1, max(2, n // 3) + 1):
        lines.append(f"set_input_delay -max 2.0 -clock clk0 [get_ports din_{i}]")
        lines.append(f"set_input_delay -min 0.5 -clock clk0 [get_ports din_{i}]")
        lines.append(f"set_output_delay -max 3.0 -clock clk0 [get_ports dout_{i}]")
    # one duplicate pair (exactly two identical commands, on din_0 which the
    # loop above never touches)
    lines.append("set_input_delay -max 2.0 -clock clk0 [get_ports din_0]")
    lines.append("set_input_delay -max 2.0 -clock clk0 [get_ports din_0]")
    # one conflict on disjoint endpoints x/y (so it never overlaps the fp/mcp
    # pair on a/b)
    lines.append("set_max_delay 5 -from [get_ports x] -to [get_ports y]")
    lines.append("set_min_delay 10 -from [get_ports x] -to [get_ports y]")
    # one possible conflict
    lines.append("set_false_path -from [get_ports a] -to [get_ports b]")
    lines.append("set_multicycle_path 2 -from [get_ports a] -to [get_ports b]")
    return "\n".join(lines) + "\n"


def main() -> int:
    print("INTERACTION PERFORMANCE")
    failures = 0
    for n in (100, 1000, 10000):
        sdc = make_sdc(n)
        t0 = time.perf_counter()
        ia = analyze_interactions(sdc)
        dt = time.perf_counter() - t0
        expect = {
            "exact_duplicates": 1,
            "overrides": 0,
            "definite_conflicts": 1,
            "possible_conflicts": 1,
        }
        s = ia.summary()
        mismatches = [k for k, v in expect.items() if s[k] != v]
        status = "OK" if not mismatches else f"MISMATCH {mismatches}"
        print(f"  {n:>6} constraints: {dt*1000:8.1f} ms  ({status})")
        if mismatches:
            failures += 1
    print("INTERACTION PERFORMANCE: " + ("PASS" if not failures else "FAIL"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
