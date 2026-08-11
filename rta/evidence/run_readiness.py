"""
Phase 11 — Constraint Readiness golden suite runner (HR01..HR15).

For each case: run check_sdc (optionally with netlist context) and compare the
readiness verdict against the INDEPENDENTLY derived manifest expectations.

Expectations were derived from SDC semantics + the documented blocker/review/
advisory mapping — NOT from validator output.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc

HERE = os.path.dirname(os.path.abspath(__file__))
RD = os.path.join(HERE, "readiness")


def _load(name: str) -> str:
    with open(os.path.join(RD, name), encoding="utf-8") as f:
        return f.read()


def run_case(case: dict) -> list:
    fails = []
    text = _load(case["sdc"])
    ctx = None
    if case.get("netlist"):
        from design_context import parse_verilog
        outcome = parse_verilog(_load(case["netlist"]))
        if outcome.errors:
            return [f"netlist failed: {outcome.errors[0]}"]
        ctx = outcome.context

    r = check_sdc(text, context=ctx)
    rdy = getattr(r, "readiness", None) or {}
    exp = case["expected"]

    if "overall" in exp and rdy.get("overall") != exp["overall"]:
        fails.append(f"overall: expected {exp['overall']}, got {rdy.get('overall')}")
    if "overall_in" in exp and rdy.get("overall") not in exp["overall_in"]:
        fails.append(f"overall: expected in {exp['overall_in']}, got {rdy.get('overall')}")
    if "mode" in exp and rdy.get("mode") != exp["mode"]:
        fails.append(f"mode: expected {exp['mode']}, got {rdy.get('mode')}")
    if "limited_design_verification" in exp and \
            bool(rdy.get("limited_design_verification")) != exp["limited_design_verification"]:
        fails.append(f"limited_design_verification: expected "
                     f"{exp['limited_design_verification']}, got "
                     f"{rdy.get('limited_design_verification')}")

    blk = {b["code"] for b in rdy.get("blockers", [])}
    rev = {b["code"] for b in rdy.get("review_items", [])}
    adv = {b["code"] for b in rdy.get("advisories", [])}

    if "blockers" in exp and blk != set(exp["blockers"]):
        fails.append(f"blockers: expected {sorted(exp['blockers'])}, got {sorted(blk)}")
    for code in exp.get("blockers_include", []):
        if code not in blk:
            fails.append(f"blockers missing {code} (got {sorted(blk)})")
    for code in exp.get("review_items_include", []):
        if code not in rev:
            fails.append(f"review_items missing {code} (got {sorted(rev)})")
    for code in exp.get("review_items_exclude", []):
        if code in rev:
            fails.append(f"review_items should NOT contain {code}")
    for code in exp.get("advisories_include", []):
        if code not in adv:
            fails.append(f"advisories missing {code} (got {sorted(adv)})")

    for dim, want in exp.get("dimension", {}).items():
        got = (rdy.get("dimensions", {}).get(dim, {}) or {}).get("status")
        if got != want:
            fails.append(f"dimension {dim}: expected {want}, got {got}")

    # Every blocker/review/advisory must carry an action + priority.
    for bucket in ("blockers", "review_items", "advisories"):
        for it in rdy.get(bucket, []):
            if not it.get("action"):
                fails.append(f"{bucket} {it['code']} missing action")
            if not it.get("priority"):
                fails.append(f"{bucket} {it['code']} missing priority")
    return fails


def main() -> int:
    with open(os.path.join(RD, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    cases = manifest["cases"]
    passed = 0
    print("CONSTRAINT READINESS GOLDEN")
    for case in cases:
        fails = run_case(case)
        if fails:
            print(f"  ❌ {case['id']}: {'; '.join(fails)}")
        else:
            passed += 1
            print(f"  ✅ {case['id']} — {case['purpose']}")
    print(f"CONSTRAINT READINESS GOLDEN: {passed}/{len(cases)} cases match expected behavior")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
