#!/usr/bin/env python3
"""
Phase 6 — Stage 14: Performance at clock counts 10/25/50/100/200/400.

Pair analysis is inherently O(N^2) (pairs = N*(N-1)/2). This measures
check_sdc + clock_relations at each count, records pair counts, and checks for
freezes / pathological scaling beyond the inherent O(N^2) pair workload.

Usage:
    python benchmarks/test_reference_perf.py
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc                      # noqa: E402
from clock_relations import analyze_clock_relations  # noqa: E402


def make_design(n_clocks):
    """Deterministic synthetic design with N clocks + 2N delays + 2 groups."""
    lines = ["set sdc_version 2.1"]
    for i in range(n_clocks):
        lines.append(f"create_clock -name clk_{i:03d} -period {2.0 + (i % 8) * 0.5} "
                     f"[get_ports clk_{i:03d}]")
        lines.append(f"set_input_delay -max 1.0 -min 0.2 -clock clk_{i:03d} "
                     f"[get_ports din_{i:03d}]")
        lines.append(f"set_output_delay -max 1.5 -min 0.5 -clock clk_{i:03d} "
                     f"[get_ports dout_{i:03d}]")
    half = n_clocks // 2
    lines.append("set_clock_groups -asynchronous "
                 f"-group [get_clocks {{clk_000}}] -group [get_clocks *]")
    return "\n".join(lines) + "\n"


def main():
    print("PHASE 6 PERFORMANCE — clock count scaling (pairs = N*(N-1)/2)")
    print(f"{'clocks':>8} {'pairs':>8} {'check(s)':>10} {'clockrel(s)':>12} {'total(s)':>10}")
    times = []
    for n in (10, 25, 50, 100, 200, 400):
        text = make_design(n)
        pairs = n * (n - 1) // 2
        t0 = time.perf_counter()
        check_sdc(text)
        t_check = time.perf_counter() - t0
        t0 = time.perf_counter()
        cr = analyze_clock_relations(text)
        t_cr = time.perf_counter() - t0
        assert len(cr.pairs) == pairs, f"expected {pairs} pairs, got {len(cr.pairs)}"
        total = t_check + t_cr
        times.append(total)
        print(f"{n:>8} {pairs:>8} {t_check:>10.2f} {t_cr:>12.2f} {total:>10.2f}")

    # Scaling check: 100→200 clocks = 4x pairs; 100→400 = 16x pairs.
    # Total time should scale ~quadratically (inherent), not worse.
    t100, t400 = times[3], times[5]
    ratio = t400 / t100 if t100 else 0
    expected = (400 * 399 / 2) / (100 * 99 / 2)  # = 16.1
    print(f"\n  100→400 clocks: time x{ratio:.1f} vs pairs x{expected:.1f} "
          f"(quadratic-in-pairs is expected)")
    ok = ratio < expected * 3  # allow 3x headroom over pure pair scaling
    print(f"  scaling: {'PASS' if ok else 'FAIL'} (no super-quadratic blowup)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
