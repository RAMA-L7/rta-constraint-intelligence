"""
Phase 10 — Constraint-interaction golden suite runner (CI01..CI20).

For each case: run analyze_interactions(sdc) and compare against the
INDEPENDENTLY derived manifest expectations. A case matches only when every
expected fact holds (category counts and finding codes).

The expectations were derived from SDC semantics — NOT from validator output.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from constraint_interactions import analyze_interactions

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name: str) -> str:
    with open(os.path.join(HERE, "constraint_interactions", name),
              encoding="utf-8") as f:
        return f.read()


def run_case(case: dict) -> list:
    """Return list of failure strings (empty = pass)."""
    fails = []
    ia = analyze_interactions(_load(case["sdc"]))
    s = ia.summary()
    exp = case["expected"]

    for key in ("exact_duplicates", "overrides", "definite_conflicts",
                "possible_conflicts"):
        if key in exp and s[key] != exp[key]:
            fails.append(f"{key}: expected {exp[key]}, got {s[key]}")

    got_codes = {}
    for f in ia.findings:
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

    # Every finding must carry dual-line provenance.
    for f in ia.findings:
        if not f.get("line") or not f.get("line2"):
            fails.append(f"finding {f['code']} missing dual-line provenance")
    return fails


def main() -> int:
    with open(os.path.join(HERE, "constraint_interactions", "manifest.json"),
              encoding="utf-8") as f:
        manifest = json.load(f)
    cases = manifest["cases"]
    passed = 0
    print("CONSTRAINT INTERACTION GOLDEN")
    for case in cases:
        fails = run_case(case)
        if fails:
            print(f"  ❌ {case['id']}: {'; '.join(fails)}")
        else:
            passed += 1
            print(f"  ✅ {case['id']} — {case['purpose']}")
    print(f"CONSTRAINT INTERACTION GOLDEN: {passed}/{len(cases)} cases match expected behavior")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
