"""
Phase 12 — SDC Readiness Diff golden suite runner (RDIF01..RDIF22).

For each case: build baseline + current readiness snapshots (optionally with
design context), diff them, and compare the classification / deltas against
the INDEPENDENTLY derived manifest expectations.

Expectations were derived from SDC semantics, the blocker/review/advisory
tier mapping, and the documented finding-identity / delta rules — NOT from
validator output.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc
import readiness_diff as rd

HERE = os.path.dirname(os.path.abspath(__file__))
RD = os.path.join(HERE, "readiness_diff")


def _load(name: str) -> str:
    with open(os.path.join(RD, name), encoding="utf-8") as f:
        return f.read()


def build_snap(sdc_name, netlist_name, source_name):
    text = _load(sdc_name)
    ctx = None
    if netlist_name:
        from design_context import parse_verilog
        outcome = parse_verilog(_load(netlist_name))
        if outcome.errors:
            raise RuntimeError(f"netlist {netlist_name}: {outcome.errors[0]}")
        ctx = outcome.context
    r = check_sdc(text, context=ctx)
    return rd.build_snapshot(r, context=ctx, source_name=source_name)


def _check_list_contains(name, got, want_include):
    got_codes = {x.get("code") or x.get("command") for x in got}
    for code in want_include:
        if code not in got_codes:
            raise AssertionError(f"{name}: missing {code} (got {sorted(got_codes)})")


def _check_list_count(name, got, count):
    if len(got) != count:
        raise AssertionError(f"{name}: expected {count} items, got {len(got)}")


def run_case(case: dict) -> list:
    fails = []
    exp = case["expected"]

    # Synthetic cases (RDIF18 incompatible schema, RDIF19 engine failure).
    if case.get("synthetic") == "incompatible_schema":
        base = rd.build_snapshot(check_sdc(_load("RDIF01_base.sdc")))
        base["schema_version"] = 99
        cur = rd.build_snapshot(check_sdc(_load("RDIF01_base.sdc")))
        diff = rd.diff_snapshots(base, cur)
        compat = diff["compatibility"]["status"]
        if compat != exp["compatibility"]:
            fails.append(f"compat: expected {exp['compatibility']}, got {compat}")
        g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, base, cur, diff)
        if g["result"] != exp["gate_result"] or g["exit_code"] != exp["gate_exit"]:
            fails.append(f"gate: expected {exp['gate_result']}/{exp['gate_exit']}, "
                         f"got {g['result']}/{g['exit_code']}")
        return fails

    if case.get("synthetic") == "engine_failure":
        base = rd.build_snapshot(check_sdc(_load("RDIF01_base.sdc")))
        cur = rd.build_snapshot(check_sdc(_load("RDIF01_base.sdc")))
        cur["analysis"]["engine_failed"] = True
        diff = rd.diff_snapshots(base, cur)
        if diff["classification"] != exp["classification"]:
            fails.append(f"classification: expected {exp['classification']}, "
                         f"got {diff['classification']}")
        for policy in (rd.POLICY_BLOCKERS_ONLY, rd.POLICY_NO_REGRESSION, rd.POLICY_STRICT):
            g = rd.evaluate_gate(policy, base, cur, diff)
            if g["result"] != "FAIL" or g["exit_code"] != rd.EXIT_ENGINE_FAILURE:
                fails.append(f"gate {policy}: must FAIL exit {rd.EXIT_ENGINE_FAILURE} "
                             f"on engine failure, got {g['result']}/{g['exit_code']}")
        return fails

    base = build_snap(case["base_sdc"], case["base_netlist"], case["base_sdc"])
    cur = build_snap(case["cur_sdc"], case["cur_netlist"], case["cur_sdc"])
    diff = rd.diff_snapshots(base, cur)

    if exp.get("classification") is not None and diff["classification"] != exp["classification"]:
        fails.append(f"classification: expected {exp['classification']}, "
                     f"got {diff['classification']}")
    compat = diff["compatibility"]["status"]
    if compat != exp["compatibility"]:
        fails.append(f"compat: expected {exp['compatibility']}, got {compat}")

    fd = diff["findings"]
    if "new_findings" in exp:
        _check_list_count("new_findings", fd["new"], exp["new_findings"])
    if "resolved_findings" in exp:
        _check_list_count("resolved_findings", fd["resolved"], exp["resolved_findings"])
    if "new_blockers" in exp:
        _check_list_count("new_blockers", fd["new_blockers"], exp["new_blockers"])
    _check_list_contains("new_blockers", fd["new_blockers"], exp.get("new_blockers_include", []))
    _check_list_contains("resolved_blockers", fd["resolved_blockers"],
                         exp.get("resolved_blockers_include", []))
    _check_list_contains("new_review", fd["new_review"], exp.get("new_review_include", []))
    _check_list_contains("resolved_review", fd["resolved_review"],
                         exp.get("resolved_review_include", []))
    # Advisories live in the general new list (tier READY_WITH_ADVISORIES).
    if exp.get("new_advisory_include"):
        adv = [f for f in fd["new"] if f.get("tier") == rd.READY_WITH_ADVISORIES
               or f.get("severity") == "info"]
        _check_list_contains("new_advisories", adv, exp["new_advisory_include"])

    if "overall_delta" in exp:
        got_delta = diff["readiness"]["overall_delta"]
        if got_delta != exp["overall_delta"]:
            fails.append(f"overall_delta: expected {exp['overall_delta']}, got {got_delta}")

    cov_in = diff["coverage"]["inputs"]
    if exp.get("coverage_inputs_newly_unconstrained") is not None:
        want = set(exp["coverage_inputs_newly_unconstrained"])
        got = set(cov_in["newly_unconstrained"])
        if got != want:
            fails.append(f"coverage new-unconstrained inputs: expected {sorted(want)}, "
                         f"got {sorted(got)}")

    trust = diff["trust"]
    _check_list_contains("trust regressions", trust["regressions"],
                         exp.get("trust_regressions_include", []))
    _check_list_contains("trust improvements", trust["improvements"],
                         exp.get("trust_improvements_include", []))
    return fails


def main() -> int:
    with open(os.path.join(RD, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    passed = 0
    print("READINESS DIFF GOLDEN")
    for case in manifest["cases"]:
        try:
            fails = run_case(case)
        except Exception as exc:  # noqa: BLE001 — report any case-level failure
            fails = [f"exception: {exc}"]
        if fails:
            print(f"  ❌ {case['id']}: {'; '.join(fails)}")
        else:
            passed += 1
            print(f"  ✅ {case['id']} — {case['purpose']}")
    print(f"READINESS DIFF GOLDEN: {passed}/{len(manifest['cases'])} cases match expected behavior")
    return 0 if passed == len(manifest["cases"]) else 1


if __name__ == "__main__":
    sys.exit(main())
