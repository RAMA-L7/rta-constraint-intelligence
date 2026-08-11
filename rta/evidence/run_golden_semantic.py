#!/usr/bin/env python3
"""
Golden semantic benchmark runner (Phase 5).

Reads benchmarks/golden_semantic/manifest.json, runs check_sdc on every case,
and compares against the CORRECT semantic expectations. Failing cases are
confirmed-bug regression targets.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GS = ROOT / "rta" / "evidence" / "golden_semantic"
sys.path.insert(0, str(ROOT))

from checker import check_sdc  # noqa: E402


def evaluate(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        r = check_sdc(text)
        return {
            "errors": sorted({i.code for i in r.issues if i.sev == "error"}),
            "warnings": sorted({i.code for i in r.issues if i.sev == "warning"}),
            "issues": r.issues,
        }
    except Exception as exc:  # noqa: BLE001
        return {"crash": f"{type(exc).__name__}: {exc}"}


def check_case(exp, act):
    fails = []
    if "errors_include" in exp:
        for e in exp["errors_include"]:
            if e not in act.get("errors", []):
                fails.append(f"error {e}: expected present, got {act.get('errors')}")
    if "errors_exclude" in exp:
        for e in exp["errors_exclude"]:
            if e in act.get("errors", []):
                fails.append(f"error {e}: expected absent, got {act.get('errors')}")
    if "warnings_include" in exp:
        for w in exp["warnings_include"]:
            if w not in act.get("warnings", []):
                fails.append(f"warning {w}: expected present, got {act.get('warnings')}")
    if "warnings_exclude" in exp:
        for w in exp["warnings_exclude"]:
            if w in act.get("warnings", []):
                fails.append(f"warning {w}: expected absent, got {act.get('warnings')}")
    if exp.get("dual_line"):
        sdc049 = [i for i in act.get("issues", []) if i.code == "SDC-049"]
        if not (sdc049 and getattr(sdc049[0], "line2", 0)):
            fails.append("SDC-049 must carry line2 (both source lines)")
    if "sdc048_names" in exp:
        sdc048 = [i for i in act.get("issues", []) if i.code == "SDC-048"]
        for name in exp["sdc048_names"]:
            if not any(f'"{name}"' in i.msg for i in sdc048):
                fails.append(f"SDC-048 must mention {name}")
        for name in exp.get("sdc048_exclude_names", []):
            if any(f'"{name}"' in i.msg for i in sdc048):
                fails.append(f"SDC-048 must NOT mention {name}")
    if "crash" in act:
        fails.append(f"checker crashed: {act['crash']}")
    return fails


def main():
    manifest = json.loads((GS / "manifest.json").read_text(encoding="utf-8"))
    total = passed = 0
    for case in manifest["cases"]:
        fpath = GS / case["file"]
        act = evaluate(fpath)
        fails = check_case(case.get("expected", {}), act)
        total += 1
        ok = not fails
        passed += ok
        print(f"{'✅' if ok else '❌'} {case['id']} [{case['classification']:<24}] {case['file']}")
        for f in fails:
            print(f"      ⚠ {f}")
    print(f"\nGOLDEN SEMANTIC BENCHMARK — {passed}/{total} cases match expected behavior")
    summary = {"total": total, "passed": passed, "failed": total - passed}
    (GS / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
