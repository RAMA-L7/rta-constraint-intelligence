#!/usr/bin/env python3
"""
Golden benchmark runner.

Reads benchmarks/golden/manifest.json, runs checker / converter / clock_relations
on every golden .sdc, and compares actual output against the EXPECTED (correct)
behavior encoded in the manifest. Cases whose expected behavior differs from the
current tool output are reported as FAIL — these are the confirmed bug backlog,
encoded as permanent regression targets.

Usage:
    PYTHONIOENCODING=utf-8 python benchmarks/run_golden.py [-v]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN = ROOT / "rta" / "evidence" / "golden"
sys.path.insert(0, str(ROOT))

from checker import check_sdc                       # noqa: E402
from converter import parse_sdc                     # noqa: E402
from clock_relations import analyze_clock_relations  # noqa: E402


def _safe(fn, *a, **k):
    try:
        return True, fn(*a, **k)
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def evaluate(file_path: Path):
    text = file_path.read_text(encoding="utf-8", errors="replace")
    out = {}

    ok, r = _safe(check_sdc, text)
    if ok:
        out["errors"] = sorted({i.code for i in r.issues if i.sev == "error"})
        out["warnings"] = sorted({i.code for i in r.issues if i.sev == "warning"})
        out["clocks"] = r.stats.get("Clocks", 0)               # primary clocks only
        out["generated"] = r.stats.get("Generated clocks", 0)  # generated clocks, tracked separately
    else:
        out["crash"] = r

    ok, p = _safe(parse_sdc, text, file_path.name)
    if ok:
        out["periods"] = {c.name: c.period for c in p.clocks}
        out["conv_clocks"] = len(p.clocks)
    else:
        out["conv_crash"] = p

    ok, cr = _safe(analyze_clock_relations, text)
    if ok:
        out["pairs"] = len(cr.pairs)
        out["mismatches"] = cr.stats.get("mismatches", 0)
        out["missing"] = cr.stats.get("missing", 0)
        out["relations"] = {frozenset((p.clock_a, p.clock_b)): p.inferred_relation for p in cr.pairs}
        out["mismatch_codes"] = sorted({m.code for m in cr.mismatches if m.severity == "warning"})
    else:
        out["cr_crash"] = cr

    return out


def check_case(exp: dict, act: dict) -> list:
    """Return list of failure strings; empty = pass."""
    fails = []
    if "errors" in exp and act.get("errors") != exp["errors"]:
        fails.append(f"errors: expected {exp['errors']} got {act.get('errors')}")
    if "warnings_include" in exp:
        for w in exp["warnings_include"]:
            if w not in act.get("warnings", []):
                fails.append(f"warning {w}: expected present, got {act.get('warnings')}")
    if "warnings_exclude" in exp:
        for w in exp["warnings_exclude"]:
            if w in act.get("warnings", []):
                fails.append(f"warning {w}: expected absent, got {act.get('warnings')}")
    if "clocks" in exp and act.get("clocks") != exp["clocks"]:
        fails.append(f"clocks: expected {exp['clocks']} got {act.get('clocks')}")
    if "generated" in exp and act.get("generated") != exp["generated"]:
        fails.append(f"generated: expected {exp['generated']} got {act.get('generated')}")
    if "conv_clocks" in exp and act.get("conv_clocks") != exp["conv_clocks"]:
        fails.append(f"conv_clocks: expected {exp['conv_clocks']} got {act.get('conv_clocks')}")
    if "periods" in exp:
        got = act.get("periods", {})
        for name, val in exp["periods"].items():
            if abs(got.get(name, -1) - val) > 1e-9:
                fails.append(f"period {name}: expected {val} got {got.get(name)}")
    if "pairs" in exp and act.get("pairs") != exp["pairs"]:
        fails.append(f"pairs: expected {exp['pairs']} got {act.get('pairs')}")
    if "mismatches" in exp and act.get("mismatches") != exp["mismatches"]:
        fails.append(f"mismatches: expected {exp['mismatches']} got {act.get('mismatches')}")
    if "missing" in exp and act.get("missing") != exp["missing"]:
        fails.append(f"missing: expected {exp['missing']} got {act.get('missing')}")
    if "mismatch_codes" in exp and act.get("mismatch_codes") != exp["mismatch_codes"]:
        fails.append(f"mismatch_codes: expected {exp['mismatch_codes']} got {act.get('mismatch_codes')}")
    if "relation" in exp:
        rels = act.get("relations", {})
        names = [k for k in act.get("relations", {}) if k]
        # match by first pair whose name set has 2 members
        match = [v for k, v in rels.items() if len(k) == 2]
        if match and match[0] != exp["relation"]:
            fails.append(f"relation: expected {exp['relation']} got {match[0]}")
    if "crash" in act or "conv_crash" in act or "cr_crash" in act:
        fails.append("analyzer crashed")
    return fails


def main():
    verbose = "-v" in sys.argv
    manifest = json.loads((GOLDEN / "manifest.json").read_text(encoding="utf-8"))
    total = passed = 0
    results = []
    for case in manifest["cases"]:
        fpath = GOLDEN / case["file"]
        act = evaluate(fpath)
        fails = check_case(case.get("expected", {}), act)
        total += 1
        ok = not fails
        passed += ok
        results.append((case["id"], case["classification"], ok, fails, act))
        flag = "✅" if ok else "❌"
        print(f"{flag} {case['id']} [{case['classification']:<28}] {case['file']}")
        for f in fails:
            print(f"      ⚠ {f}")
        if verbose:
            print(f"      actual: E={act.get('errors')} W={act.get('warnings')} "
                  f"clk={act.get('clocks')} pairs={act.get('pairs')} "
                  f"miss={act.get('missing')} periods={act.get('periods')}")

    print(f"\nGOLDEN BENCHMARK — {passed}/{total} cases match expected (correct) behavior")
    print("Note: cases that FAIL here encode confirmed-bug regression targets;")
    print("they are expected to keep failing until production code is fixed.")

    # Persist machine-readable summary
    summary = {
        "total": total, "passed": passed, "failed": total - passed,
        "cases": [
            {"id": cid, "classification": cls, "matches_expected": ok, "failures": fails}
            for cid, cls, ok, fails, _ in results
        ],
    }
    (GOLDEN / "results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
