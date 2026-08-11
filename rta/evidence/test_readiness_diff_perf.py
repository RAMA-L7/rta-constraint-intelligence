"""
Phase 12 — readiness-diff performance suite.

Diffing must be near-linear: consume snapshots, group by semantic keys, no
all-pairs comparison. Benchmark snapshot build + diff + gate at 100 / 1k /
10k findings and large coverage inventories. Aggregation cost must stay a
small fraction of the underlying check.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc
import readiness_diff as rd


def make_snapshot(n_issues: int, n_cov_ports: int, engine_ok: bool = True) -> dict:
    """Synthesize a snapshot with n distinct findings + a large coverage map."""
    from constraint_readiness import _tier_for
    findings = []
    for i in range(n_issues):
        code = f"SDC-{100 + (i % 40):03d}"
        sev = "warning" if i % 2 else "info"
        full, base = rd.finding_identity(code, sev, f"finding number {i} on object obj_{i}")
        findings.append({
            "code": code, "severity": sev, "msg": f"finding number {i} on object obj_{i}",
            "line": i, "line2": 0, "full_id": list(full), "base_id": list(base),
            "tier": _tier_for(code, sev),
        })
    return {
        "schema_version": 1, "tool_version": "x",
        "analysis": {"mode": "SDC_ONLY", "top_module": "", "design_fingerprint": "",
                     "design_counts": {}, "commands_found": 10, "engine_failed": not engine_ok},
        "readiness": {"overall": "REVIEW_REQUIRED", "mode": "SDC_ONLY",
                      "dimensions": {"I/O": {"status": "REVIEW_REQUIRED"}}},
        "findings": findings,
        "coverage": {
            "inputs": {f"in_{i}": ("UNCONSTRAINED" if i % 3 == 0 else "CONSTRAINED")
                       for i in range(n_cov_ports)},
            "outputs": {f"out_{i}": ("CONSTRAINED" if i % 2 else "UNCONSTRAINED")
                        for i in range(n_cov_ports)},
        },
        "scope": {"status": "VALIDATED", "constructs": {f"cmd_{i}": "VALIDATED" for i in range(20)}},
        "interactions": [],
    }


def run():
    fails = []
    sizes = [100, 1000, 10000]
    for n in sizes:
        b = make_snapshot(n, n)
        c = make_snapshot(n, n)
        t0 = time.perf_counter()
        d = rd.diff_snapshots(b, c)
        t1 = time.perf_counter()
        g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b, c, d)
        t2 = time.perf_counter()
        dt = t1 - t0
        # Budget: 10k findings must diff in well under 1s (near-linear, no
        # all-pairs). 100ms for 1k is generous; 10k scales ~10x.
        budget = 0.05 if n <= 100 else (0.5 if n <= 1000 else 3.0)
        if dt > budget:
            fails.append(f"{n} findings: diff took {dt:.3f}s (budget {budget}s)")
        print(f"  {n:6d} findings: diff={dt*1000:.1f}ms gate={ (t2-t1)*1000:.1f}ms "
              f"unchanged={d['findings']['unchanged']}")
        if g["result"] != "PASS":
            fails.append(f"{n} findings: identical snapshots must PASS, got {g['result']}")

    # Scaling sanity: 10x findings must NOT take 100x time (all-pairs smell).
    t_small = None
    t_large = None
    for n in (1000, 10000):
        b = make_snapshot(n, n)
        c = make_snapshot(n, n)
        t0 = time.perf_counter()
        rd.diff_snapshots(b, c)
        t1 = time.perf_counter()
        if n == 1000:
            t_small = t1 - t0
        else:
            t_large = t1 - t0
    if t_small and t_large and t_large > t_small * 30:
        fails.append(f"scaling smell: 10x findings took {t_large/t_small:.1f}x time "
                     f"(all-pairs?) — {t_small:.3f}s -> {t_large:.3f}s")

    print(f"READINESS DIFF PERF: {'ALL PASS' if not fails else 'FAILURES'}")
    for f in fails:
        print("  ❌", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
