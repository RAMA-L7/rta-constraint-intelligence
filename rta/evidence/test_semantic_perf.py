#!/usr/bin/env python3
"""
Phase 5 Stage 17 — Semantic analysis performance.

Measures check_sdc (which includes the Phase-5 semantic checks) at ~100 /
~1,000 / ~10,000 constraints. The semantic checks use dict indexing (no
N^2 cross-comparison), so scaling should be near-linear in constraint count
modulo the inherent O(N^2) clock-pair analysis for large clock counts.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc  # noqa: E402


def make_sdc(n_constraints):
    """Synthetic SDC with n_constraints total (1 clock + delays + groups)."""
    lines = ["create_clock -name clk0 -period 10.0 [get_ports clk]",
             "set_output_delay -max 1.0 -min 0.2 -clock clk0 [all_outputs]"]
    n_clocks = max(1, n_constraints // 40)
    for i in range(n_clocks):
        lines.append(f"create_clock -name c{i} -period {5.0 + i % 7} [get_ports p{i}]")
    for i in range(n_constraints - n_clocks - 2):
        lines.append(f"set_input_delay -max 1.5 -min 0.3 -clock c{i % n_clocks} [get_ports din{i}]")
    return "\n".join(lines) + "\n"


def bench(name, n):
    text = make_sdc(n)
    t0 = time.perf_counter()
    r = check_sdc(text)
    dt = time.perf_counter() - t0
    sem = sum(1 for i in r.issues if i.code.startswith("SDC-04"))
    print(f"  {name:>6} constraints → {dt*1000:8.1f} ms (semantic findings: {sem})")
    return dt


def main():
    print("PHASE 5 SEMANTIC PERFORMANCE")
    t100 = bench("100", 100)
    t1k = bench("1k", 1000)
    t10k = bench("10k", 10000)
    s1 = t1k / t100 if t100 else 0
    s2 = t10k / t1k if t1k else 0
    print(f"  scaling: 100→1k x{s1:.1f}, 1k→10k x{s2:.1f} (linear ≈ x10)")
    ok = s2 < 60  # tolerate O(N^2) clock pairs but not worse
    print(f"  SEMANTIC PERF {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
