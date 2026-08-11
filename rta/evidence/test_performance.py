#!/usr/bin/env python3
"""
Phase 4 — Performance benchmark for the shared preprocessor + full validation.

Measures preprocessing time and full check_sdc time at 100 / 1k / 10k lines.
Looks for O(N^2) substitution, repeated whole-file scanning, catastrophic
regex backtracking, or excessive object creation.
"""

import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from sdc_preprocess import preprocess_sdc  # noqa: E402
from checker import check_sdc              # noqa: E402


def make_sdc(n_lines):
    """Build a synthetic-but-realistic SDC with ~n_lines of content."""
    lines = ["set sdc_version 2.1", "# header"]
    for i in range(max(1, n_lines // 5)):
        lines.append(f"set CLK_P{i} {2.0 + (i % 7) * 0.25}")
        lines.append(f"create_clock -name c{i} -period $CLK_P{i} \\")
        lines.append(f"    -waveform {{0 1.0}} [get_ports clk_{i}]")
        lines.append(f"set_input_delay -max 1.0 -min 0.2 -clock c{i} [get_ports in_{i}]")
        lines.append(f"set_output_delay -max 1.0 -min 0.2 -clock c{i} [get_ports out_{i}]")
    return "\n".join(lines) + "\n"


def bench(name, n_lines):
    text = make_sdc(n_lines)
    # preprocess only
    t0 = time.perf_counter()
    cmds = preprocess_sdc(text)
    t_pre = time.perf_counter() - t0
    # full check
    t0 = time.perf_counter()
    r = check_sdc(text)
    t_check = time.perf_counter() - t0
    tracemalloc.start()
    preprocess_sdc(text)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"  {name:>8} lines: {len(cmds):>4} cmds | preprocess {t_pre*1000:7.1f} ms | "
          f"check {t_check*1000:7.1f} ms | peak {peak/1024:8.1f} KiB")
    return t_pre, t_check


def main():
    print("PHASE 4 PERFORMANCE BENCHMARK")
    print("(line counts approximate; SDC blocks are 5 lines each)")
    results = [bench("100", 100), bench("1k", 1000), bench("10k", 10000)]
    t100, t1k, t10k = results
    # Scaling sanity: 10x input should NOT blow up super-linearly in preprocessing
    scale_pre = (t10k[0] / t1k[0]) if t1k[0] else 0
    scale_check = (t10k[1] / t1k[1]) if t1k[1] else 0
    print(f"\n  scaling 1k→10k: preprocess x{scale_pre:.1f}, check x{scale_check:.1f} (linear ≈ x10)")
    # The preprocessor (the Phase 4 shared infrastructure) must be near-linear.
    # check_sdc scales faster because clock-relations analyzes every clock PAIR
    # (inherently O(N^2) — 2000 clocks -> ~2M pairs); the former O(N^3) ancestor
    # scan was eliminated in Phase 4 (see PHASE4 report, perf section).
    ok_pre = scale_pre < 30
    print(f"  preprocess scaling: {'PASS' if ok_pre else 'FAIL'} (near-linear)")
    print("  check scaling: O(N^2) pair analysis is inherent; reported for information.")
    sys.exit(0 if ok_pre else 1)


if __name__ == "__main__":
    main()
