#!/usr/bin/env python3
"""
Phase 8 — Netlist-aware golden runner.

Validates NA01..NA09 against the independently-derived manifest:
  - parse expectations (top module, ambiguity)
  - SDC-055/056/057/059 issue presence + needles
  - trust-status expectations

Exit 0 only if every case matches. Usage:
    python benchmarks/run_netlist_aware.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
NA = ROOT / "rta" / "evidence" / "netlist_aware"
sys.path.insert(0, str(ROOT))

from checker import check_sdc                                   # noqa: E402
from design_context import parse_verilog, resolve_collection    # noqa: E402


def _load(p):
    return (NA / p).read_text(encoding="utf-8", errors="replace")


def _check_issues(case, issues) -> list:
    """Every expected issue (code + needle) must be present at min_count."""
    problems = []
    for exp in case["expected"].get("issues", []):
        got = [i for i in issues if i.code == exp["code"] and exp.get("needle", "") in i.msg]
        if len(got) < exp.get("min_count", 1):
            problems.append(f"expected {exp['code']} ({exp.get('needle', '')}) "
                            f"x{exp.get('min_count', 1)}, got {len(got)}")
    return problems


def main():
    manifest = json.loads((NA / "manifest.json").read_text(encoding="utf-8"))
    total = passed = 0
    fails = []

    for case in manifest["cases"]:
        total += 1
        cid = case["id"]
        exp = case["expected"]
        problems = []

        # ── Parse the netlist ──────────────────────────────────────────────
        v = _load(case["verilog"])
        outcome = parse_verilog(v, top=case.get("top_module", ""))
        if exp.get("parse_ok"):
            if outcome.context is None:
                problems.append(f"parse failed: {outcome.errors}")
            else:
                ctx = outcome.context
                # module/port/instance counts
                for key in ("modules", "ports", "instances"):
                    if key in exp and ctx.object_counts().get(key) != exp[key]:
                        problems.append(f"{key} count {ctx.object_counts().get(key)} != {exp[key]}")
                # nested hierarchy facts
                for inst in exp.get("instances_nested", []):
                    if inst not in ctx.instances:
                        problems.append(f"missing nested instance {inst}")
                for pin in exp.get("pins_nested", []):
                    if pin not in ctx.pins:
                        problems.append(f"missing nested pin {pin}")
                for bus, (msb, lsb) in exp.get("ports_bus", {}).items():
                    dp = ctx.ports.get(bus)
                    if dp is None or dp.msb != msb or dp.lsb != lsb:
                        problems.append(f"bus {bus} range mismatch")
                # explicit resolvable refs
                for ref in exp.get("resolvable", []):
                    kind, args = ref.split(" ", 1)
                    r = resolve_collection(kind, args, ctx)
                    if r.kind != "RESOLVED":
                        problems.append(f"{ref} not resolved ({r.kind})")
                # run checker in design-aware mode
                sdc = _load(case["sdc"])
                result = check_sdc(sdc, context=ctx)
                problems += _check_issues(case, result.issues)
                if "trust_status" in exp:
                    got_st = result.scope.get("status")
                    if got_st != exp["trust_status"]:
                        problems.append(f"trust {got_st} != {exp['trust_status']}")
        else:
            # parse must fail
            if outcome.context is not None:
                problems.append("expected parse failure but context built")
            if exp.get("ambiguity") and not outcome.errors:
                problems.append("expected ambiguity error")
            if exp.get("top_candidates") and sorted(outcome.top_candidates) != sorted(exp["top_candidates"]):
                problems.append(f"top_candidates {outcome.top_candidates} != {exp['top_candidates']}")

        ok = not problems
        passed += ok
        print(f"  {'✅' if ok else '❌'} {cid} — {case['name']}")
        for p in problems:
            print(f"      ⚠ {p}")

    print(f"\nNETLIST-AWARE GOLDEN: {passed}/{total} cases match expected behavior")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
