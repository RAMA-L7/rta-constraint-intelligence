"""
Phase 9 — Design constraint coverage golden suite runner (DC01..DC12).

For each case: parse the design, run analyze_coverage + coverage_findings,
and compare against the INDEPENDENTLY derived manifest expectations. A case
matches only when every expected fact holds. Existing SDC-only behavior is
verified separately by the other suites — this runner is design-aware only.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from design_context import parse_verilog
from design_coverage import analyze_coverage, coverage_findings

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name: str) -> str:
    with open(os.path.join(HERE, "design_coverage", name), encoding="utf-8") as f:
        return f.read()


def run_case(case: dict) -> list:
    """Return list of failure strings (empty = pass)."""
    fails = []
    ctx = parse_verilog(_load(case["design"]))
    if ctx.errors:
        return [f"design parse: {ctx.errors[0]}"]
    ctx = ctx.context
    cov = analyze_coverage(_load(case["sdc"]), ctx)
    s = cov.summary()
    exp = case["expected"]

    inb, outb = s["inputs"], s["outputs"]
    checks = [
        ("inputs_constrained", inb["constrained"], exp.get("inputs_constrained")),
        ("inputs_exempt", inb["exempt"], exp.get("inputs_exempt")),
        ("inputs_unconstrained", inb["unconstrained"], exp.get("inputs_unconstrained")),
        ("inputs_partial", inb["partial"], exp.get("inputs_partial")),
        ("outputs_constrained", outb["constrained"], exp.get("outputs_constrained")),
        ("outputs_unconstrained", outb["unconstrained"], exp.get("outputs_unconstrained")),
        ("outputs_partial", outb["partial"], exp.get("outputs_partial")),
        ("clocks_defined", s["clocks"]["defined"], exp.get("clocks_defined")),
        ("clocks_resolved", s["clocks"]["structurally_resolved"], exp.get("clocks_resolved")),
        ("clocks_virtual", sum(1 for c in cov.clocks if c.is_virtual), exp.get("clocks_virtual")),
        ("exceptions_total", s["exceptions"]["total"], exp.get("exceptions_total")),
        ("exceptions_resolved", s["exceptions"]["objects_resolved"], exp.get("exceptions_resolved")),
        ("exceptions_empty", s["exceptions"]["empty_collection"], exp.get("exceptions_empty")),
    ]
    for key, actual, want in checks:
        if want is None:
            continue
        if actual != want:
            fails.append(f"{key}: expected {want}, got {actual}")

    findings = coverage_findings(_load(case["sdc"]), ctx)
    got_codes = {}
    for f in findings:
        got_codes[f["code"]] = got_codes.get(f["code"], 0) + 1
    for want in exp.get("findings", []):
        n = got_codes.get(want["code"], 0)
        if n < want.get("min", 1):
            fails.append(f"finding {want['code']}: expected >= {want.get('min', 1)}, got {n}")
        if "max" in want and n > want["max"]:
            fails.append(f"finding {want['code']}: expected <= {want['max']}, got {n}")
    unexpected = [c for c in got_codes if c not in {w["code"] for w in exp.get("findings", [])}]
    if unexpected:
        fails.append(f"unexpected findings: {unexpected}")
    return fails


def main() -> int:
    with open(os.path.join(HERE, "design_coverage", "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    cases = manifest["cases"]
    passed = 0
    print("DESIGN COVERAGE GOLDEN")
    for case in cases:
        fails = run_case(case)
        if fails:
            print(f"  ❌ {case['id']}: {'; '.join(fails)}")
        else:
            passed += 1
            print(f"  ✅ {case['id']} — {case['purpose']}")
    print(f"DESIGN COVERAGE GOLDEN: {passed}/{len(cases)} cases match expected behavior")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
