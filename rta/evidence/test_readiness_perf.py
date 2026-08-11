"""Phase 11 — Readiness aggregation performance.

The readiness layer CONSUMES existing results; it must not reparse the SDC or
do anything O(N²). Aggregation should be negligible vs the underlying analysis
even when the checker already emitted thousands of findings.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc  # noqa: E402
from constraint_readiness import analyze_readiness  # noqa: E402

PASS = FAIL = 0


def ok(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  ❌ {msg}")


def main() -> int:
    print("READINESS PERFORMANCE")

    # 2000-command SDC: 1000 clock pairs is cheap; force many interactions by
    # repeating the same delay (duplicates) so the checker emits many findings.
    lines = ["set sdc_version 2.2",
             "create_clock -name c -period 10.0 [get_ports clk]",
             "set_propagated_clock [get_clocks c]"]
    for i in range(1000):
        lines.append(f"set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din_{i % 20}]")
    lines.append("set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]")
    text = "\n".join(lines)

    t0 = time.time()
    r = check_sdc(text)
    t_check = time.time() - t0

    t0 = time.time()
    rdy = analyze_readiness(r)
    t_agg = time.time() - t0

    n_findings = len(r.issues)
    ok(t_agg < 0.5, f"aggregation must be <0.5s for {n_findings} findings (got {t_agg:.3f}s)")
    ok(t_agg < t_check, f"aggregation must be cheaper than check ({t_agg:.3f}s vs {t_check:.3f}s)")
    ok(rdy.overall in ("BLOCKED", "REVIEW_REQUIRED", "READY_WITH_ADVISORIES", "READY"),
       f"readiness overall={rdy.overall}")

    # Large coverage + scope must not slow aggregation.
    print(f"  findings={n_findings} check={t_check:.3f}s agg={t_agg:.3f}s")
    print(f"READINESS PERFORMANCE: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
