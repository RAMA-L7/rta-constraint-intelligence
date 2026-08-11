"""Phase 13 — performance suite.

Targets:
  - structured identity generation must be cheap (per-finding, regex only)
  - finding diff must be near-linear on 10k / 50k findings (no all-pairs)
  - custom policy evaluation must be negligible
  - design fingerprint must be practical on 100k-object designs

Run:  python benchmarks/test_ph13_perf.py
Exit: 0 = all pass (soft limits; failures are reported loudly).
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from finding_identity import make_identity_key
from readiness_diff import (
    build_snapshot, diff_snapshots, snapshot_to_json,
)
from checker import check_sdc

# Soft budget (seconds). Generous so slow CI machines don't flake, but tight
# enough to catch an accidental O(N^2).
BUDGETS = {
    "identity_10k": 2.0,
    "diff_10k": 1.0,
    "diff_50k": 6.0,
    "policy_1k": 0.5,
    "fingerprint_100k": 10.0,
}

PASSED = []
FAILED = []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + ("  " + detail if detail else ""))


def _synthetic_findings(n, base_line=1):
    """n findings spread over a realistic mix of rule codes/objects."""
    return [
        {
            "code": f"SDC-{46 if i % 5 == 0 else 30}",
            "severity": "error" if i % 5 == 0 else "warning",
            "msg": f"finding {i} on object obj_{i % 100}",
            "line": base_line + i,
            "line2": 0,
            "full_id": [1, f"SDC-{46 if i % 5 == 0 else 30}",
                        "CLOCK_REFERENCE", "set_input_delay",
                        f"obj_{i % 100}", "", "clk_core", str(i % 7),
                        "max", "", "", "", "error"],
            "base_id": [1, f"SDC-{46 if i % 5 == 0 else 30}",
                        "CLOCK_REFERENCE", "set_input_delay",
                        f"obj_{i % 100}", "", "clk_core", "", "max",
                        "", "", "", ""],
            "identity_strength": "STRUCTURED",
            "tier": "BLOCKED" if i % 5 == 0 else "REVIEW_REQUIRED",
        }
        for i in range(n)
    ]


def main():
    print("== Identity generation (10k findings) ==")
    t0 = time.perf_counter()
    for i in range(10000):
        make_identity_key("SDC-046", "error", f"msg {i}",
                          "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]")
    dt = time.perf_counter() - t0
    check("perf-identity-10k", dt < BUDGETS["identity_10k"], f"{dt:.3f}s")

    print("== Finding diff (10k and 50k) ==")
    base = {"schema_version": 2, "findings": _synthetic_findings(10000, 1),
            "readiness": {"overall": "READY", "dimensions": {}},
            "coverage": {"inputs": {}, "outputs": {}},
            "scope": {"constructs": {}}, "interactions": [],
            "analysis": {"mode": "SDC_ONLY", "top_module": "",
                         "design_fingerprint": "f", "engine_failed": False},
            "migration": {"migration_status": "NATIVE"}}
    cur = {"schema_version": 2,
           "findings": _synthetic_findings(10000, 1) + [{
               "code": "SDC-046", "severity": "error",
               "msg": "one new blocker", "line": 99999, "line2": 0,
               "full_id": [1, "SDC-046", "CLOCK_REFERENCE", "set_input_delay",
                           "new_obj", "", "ghost", "12", "max", "", "", "", "error"],
               "base_id": [1, "SDC-046", "CLOCK_REFERENCE", "set_input_delay",
                           "new_obj", "", "ghost", "", "max", "", "", "", ""],
               "identity_strength": "STRUCTURED", "tier": "BLOCKED"}],
           "readiness": {"overall": "READY", "dimensions": {}},
           "coverage": {"inputs": {}, "outputs": {}},
           "scope": {"constructs": {}}, "interactions": [],
           "analysis": {"mode": "SDC_ONLY", "top_module": "",
                        "design_fingerprint": "f", "engine_failed": False},
           "migration": {"migration_status": "NATIVE"}}
    t0 = time.perf_counter()
    d = diff_snapshots(base, cur)
    dt = time.perf_counter() - t0
    check("perf-diff-10k", dt < BUDGETS["diff_10k"], f"{dt:.3f}s")
    check("perf-diff-10k-correct",
          len(d["findings"]["new"]) == 1 and len(d["findings"]["resolved"]) == 0,
          f"new={len(d['findings']['new'])} resolved={len(d['findings']['resolved'])}")

    base50 = {"schema_version": 2, "findings": _synthetic_findings(50000, 1),
              "readiness": {"overall": "READY", "dimensions": {}},
              "coverage": {"inputs": {}, "outputs": {}},
              "scope": {"constructs": {}}, "interactions": [],
              "analysis": {"mode": "SDC_ONLY", "top_module": "",
                           "design_fingerprint": "f", "engine_failed": False},
              "migration": {"migration_status": "NATIVE"}}
    t0 = time.perf_counter()
    diff_snapshots(base50, base50)
    dt = time.perf_counter() - t0
    check("perf-diff-50k", dt < BUDGETS["diff_50k"], f"{dt:.3f}s")

    print("== Policy evaluation (1000 evaluations) ==")
    from policy_engine import load_policy
    import json as _json
    policy, errs = load_policy(_json.dumps({
        "policy": "CUSTOM", "policy_version": 1, "name": "perf",
        "fail_on": {"new_blockers": True, "new_review_items": True,
                    "trust_regression": True, "coverage_regression": True}}))
    assert errs == [], errs
    from policy_engine import evaluate_policy
    fake_diff = {"findings": {"new_blockers": [], "new_review": [], "new": []},
                 "trust": {"regressions": []},
                 "coverage": {"inputs": {"newly_unconstrained": []},
                              "outputs": {"newly_unconstrained": []}},
                 "compatibility": {"status": "COMPATIBLE"},
                 "debt": {"existing": {}, "new_debt": {}, "resolved_debt": {}}}
    fake_cur = {"readiness": {"overall": "READY"},
                "analysis": {"engine_failed": False}}
    t0 = time.perf_counter()
    for _ in range(1000):
        evaluate_policy(policy, None, fake_cur, fake_diff)
    dt = time.perf_counter() - t0
    check("perf-policy-1k", dt < BUDGETS["policy_1k"], f"{dt:.3f}s")

    print("== Design fingerprint (100k objects) ==")
    from design_context import DesignContext, DesignPort
    ctx = DesignContext()
    ctx.top_module = "top"
    ctx.modules = {"top", "leaf"}
    for i in range(50000):
        ctx.ports[f"p{i}"] = DesignPort(f"p{i}", "input", 7, 0)
    for i in range(50000):
        ctx.instances[f"u{i}"] = type("I", (), {"module": "leaf", "path": f"u{i}"})()
    ctx.nets = {f"n{i}" for i in range(50000)}
    t0 = time.perf_counter()
    from readiness_diff import design_fingerprint
    fp = design_fingerprint(ctx)
    dt = time.perf_counter() - t0
    check("perf-fingerprint-100k", dt < BUDGETS["fingerprint_100k"] and len(fp) > 0,
          f"{dt:.3f}s")

    print("== Snapshot JSON serialization (10k findings) ==")
    snap = {"schema_version": 2, "findings": _synthetic_findings(10000),
            "readiness": {"overall": "READY", "dimensions": {}},
            "coverage": {"inputs": {}, "outputs": {}},
            "scope": {"constructs": {}}, "interactions": [],
            "analysis": {"mode": "SDC_ONLY", "top_module": "",
                         "design_fingerprint": "", "engine_failed": False}}
    t0 = time.perf_counter()
    text = snapshot_to_json(snap)
    dt = time.perf_counter() - t0
    check("perf-serialization-10k", dt < 3.0 and len(text) > 1000, f"{dt:.3f}s")

    print()
    print(f"PH13 performance: {len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("FAILED:", ", ".join(FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
