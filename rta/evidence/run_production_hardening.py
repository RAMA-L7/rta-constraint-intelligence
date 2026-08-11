"""Phase 13 — Production Hardening golden suite (PH13-01..25).

Each case asserts independently-derived expectations about structured finding
identity, snapshot v2 / migration, structural fingerprint v2, the declarative
policy engine, and CI gate behavior.

Run:  python benchmarks/run_production_hardening.py
Exit: 0 = all pass, 1 = failures.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from checker import check_sdc
from design_context import parse_verilog
from finding_identity import (
    IDENTITY_VERSION, STRENGTH_STRUCTURED, identity_from_commands,
    identity_from_interaction, identity_legacy, identity_simple,
    make_identity_key,
)
from policy_engine import (
    load_policy, validate_policy, _builtin_policy,
)
from readiness_diff import (
    SCHEMA_VERSION, EXIT_PASS, EXIT_GATE_FAILED, EXIT_INVALID,
    EXIT_ENGINE_FAILURE, BLOCKING_REGRESSION, IMPROVEMENT,
    COMPATIBLE, COMPATIBLE_WITH_CONTEXT_CHANGE, PARTIALLY_COMPARABLE,
    build_snapshot, classify_compatibility, design_fingerprint,
    diff_snapshots, evaluate_gate, load_snapshot, snapshot_to_json,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "production_hardening", "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


CLEAN = _read("clean.sdc")
BLOCKER = _read("blocker.sdc")
MCP = _read("mcp.sdc")
TOP_V = _read("top.v")


def _snap(text, ctx=None, name="t.sdc"):
    return build_snapshot(check_sdc(text, context=ctx), context=ctx,
                          source_name=name)


def _ctx(text=TOP_V, top=""):
    out = parse_verilog(text, top=top)
    assert not out.errors, out.errors
    return out.context


def _new_resolved(d):
    return (d["findings"]["new"], d["findings"]["resolved"])


PASSED = []
FAILED = []


def check(case, cond, detail=""):
    if cond:
        PASSED.append(case)
        print(f"  PASS {case}")
    else:
        FAILED.append(case)
        print(f"  FAIL {case}  {detail}")


def main():
    print("== PH13-01 message changed / identity same ==")
    cmd = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
    f1, b1, i1, s1 = make_identity_key("SDC-046", "error", "wording A", cmd)
    f2, b2, i2, s2 = make_identity_key("SDC-046", "error", "wording B", cmd)
    check("PH13-01", f1 == f2 and b1 == b2 and s1 == s2 == STRENGTH_STRUCTURED,
          f"keys differ: {f1} vs {f2}")

    print("== PH13-02 severity changed ==")
    fw, bw, _, _ = make_identity_key("SDC-046", "warning", "m", cmd)
    fe, be, _, _ = make_identity_key("SDC-046", "error", "m", cmd)
    check("PH13-02", fw != fe and bw == be,
          "severity must be in full key only (CHANGED semantics)")

    print("== PH13-03 same rule / different object ==")
    fa, _, _, _ = make_identity_key("SDC-046", "error", "m",
                                    cmd.replace("din", "dina"))
    check("PH13-03", fa != f1, "different object must not collide")

    print("== PH13-04 different bus ranges ==")
    ra = "set_input_delay -max 2.0 -clock clk_core [get_ports {data[3:0]}]"
    rb = "set_input_delay -max 2.0 -clock clk_core [get_ports {data[7:4]}]"
    fra, _, _, _ = make_identity_key("SDC-066", "warning", "m", ra)
    frb, _, _, _ = make_identity_key("SDC-066", "warning", "m", rb)
    check("PH13-04", fra != frb, "ranges are object identity")

    print("== PH13-05 symmetric interaction reordered ==")
    i1 = identity_from_interaction("SDC-069", "DEFINITE_CONFLICT",
                                   "set_max_delay", frozenset({"a"}),
                                   frozenset({"b"}), "clk", "4", "6", "max",
                                   direction_preserved=False)
    i2 = identity_from_interaction("SDC-069", "DEFINITE_CONFLICT",
                                   "set_max_delay", frozenset({"b"}),
                                   frozenset({"a"}), "clk", "4", "6", "max",
                                   direction_preserved=False)
    check("PH13-05", i1.full_key() == i2.full_key(),
          "symmetric pair must canonicalize")

    print("== PH13-06 order-sensitive override ==")
    o1 = identity_from_interaction("SDC-068", "OVERRIDE", "set_input_delay",
                                   frozenset({"din"}), frozenset(), "clk",
                                   "2", "4", "max", direction_preserved=True)
    o2 = identity_from_interaction("SDC-068", "OVERRIDE", "set_input_delay",
                                   frozenset({"din"}), frozenset(), "clk",
                                   "4", "2", "max", direction_preserved=True)
    check("PH13-06", o1.full_key() != o2.full_key(),
          "override direction must be preserved")

    print("== PH13-07 schema v1 vs v2 ==")
    from readiness_diff import finding_identity as _legacy_key
    v2 = _snap(CLEAN)
    v1 = json.loads(json.dumps(v2))
    v1["schema_version"] = 1
    v1.pop("identity_version", None)
    v1.pop("capabilities", None)
    for f in v1["findings"]:
        # A real Phase 12 v1 baseline stored the legacy message-normalized key
        # directly in full_id/base_id — recompute it exactly as Phase 12 did.
        lf, lb = _legacy_key(f.get("code", ""), f.get("severity", "info"),
                             f.get("msg", ""))
        f["full_id"], f["base_id"] = list(lf), list(lb)
        f.pop("identity", None)
        f.pop("identity_strength", None)
        f.pop("tier", None)
        f.pop("legacy_full_id", None)
        f.pop("legacy_base_id", None)
    loaded, errs = load_snapshot(snapshot_to_json(v1))
    check("PH13-07a", loaded is not None and errs == [], str(errs))
    if loaded is not None:
        st, _ = classify_compatibility(loaded, v2)
        d = diff_snapshots(loaded, v2)
        check("PH13-07b", st == PARTIALLY_COMPARABLE, st)
        new, resolved = _new_resolved(d)
        check("PH13-07c", not new and not resolved,
              f"false regression: new={new} resolved={resolved}")

    print("== PH13-08 malformed snapshot ==")
    bad = load_snapshot("{not json")
    check("PH13-08a", bad[0] is None and bad[1], "must fail safely")
    bad2 = load_snapshot(json.dumps({"schema_version": 99}))
    check("PH13-08b", bad2[0] is None, "unknown schema rejected")

    print("== PH13-09 same design reformatted ==")
    v_fmt = TOP_V.replace("wire [3:0] din_q;", "wire [3:0] din_q; // note").replace("\n", "\n\n")
    fp_a = design_fingerprint(_ctx())
    fp_b = design_fingerprint(_ctx(v_fmt))
    check("PH13-09", fp_a == fp_b, f"{fp_a} vs {fp_b}")

    print("== PH13-10 design port added ==")
    ctx_a = _ctx()
    v_add = TOP_V.replace("output [1:0] dout", "input en,\n    output [1:0] dout")
    ctx_b = _ctx(v_add)
    check("PH13-10a", design_fingerprint(ctx_a) != design_fingerprint(ctx_b),
          "added port must change fingerprint")
    # SDC-only SDC with design contexts differing → context change flagged.
    base = _snap(CLEAN, ctx=ctx_a)
    cur = _snap(CLEAN, ctx=ctx_b)
    d = diff_snapshots(base, cur)
    check("PH13-10b", d["design"]["context_changed"] is True,
          "diff must flag design context change")
    check("PH13-10c", d["classification"] == "CONTEXT_CHANGE", d["classification"])

    print("== PH13-11 hierarchy changed ==")
    v_hier = TOP_V.replace("dff u0 (.c(clk), .d(din[0]), .q(din_q[0]));",
                           "dff u0 (.c(clk), .d(din[0]), .q(din_q[0]));\n    dff u0b (.c(clk), .d(din_q[0]), .q(din_q[1]));")
    check("PH13-11", design_fingerprint(_ctx(v_hier)) != fp_a,
          "hierarchy change must change fingerprint")

    print("== PH13-12 BLOCKERS_ONLY ==")
    g = evaluate_gate("BLOCKERS_ONLY", None, _snap(CLEAN), {})
    check("PH13-12a", g["result"] == "PASS", g)
    g = evaluate_gate("BLOCKERS_ONLY", None, _snap(BLOCKER), {})
    check("PH13-12b", g["result"] == "FAIL" and g["exit_code"] == EXIT_GATE_FAILED, g)

    print("== PH13-13 NO_READINESS_REGRESSION ==")
    base = _snap(CLEAN)
    cur_clean = _snap(CLEAN)
    cur_blocked = _snap(BLOCKER)
    d = diff_snapshots(base, cur_clean)
    g = evaluate_gate("NO_READINESS_REGRESSION", base, cur_clean, d)
    check("PH13-13a", g["result"] == "PASS", g)
    d = diff_snapshots(base, cur_blocked)
    g = evaluate_gate("NO_READINESS_REGRESSION", base, cur_blocked, d)
    check("PH13-13b", g["result"] == "FAIL" and g["exit_code"] == EXIT_GATE_FAILED,
          f"{g} class={d['classification']}")

    print("== PH13-14 STRICT ==")
    d = diff_snapshots(base, cur_clean)
    g = evaluate_gate("STRICT", base, cur_clean, d)
    check("PH13-14a", g["result"] == "PASS", g)
    d = diff_snapshots(base, cur_blocked)
    g = evaluate_gate("STRICT", base, cur_blocked, d)
    check("PH13-14b", g["result"] == "FAIL", g)

    print("== PH13-15 CUSTOM legacy policy ==")
    legacy, errs = load_policy(open(os.path.join(HERE, "..", "..", "rta", "examples", "policies",
                                                 "legacy_project.yml"),
                                    encoding="utf-8").read())
    assert errs == [], errs
    # existing debt unchanged → PASS
    d = diff_snapshots(base, cur_blocked)  # baseline clean, current blocked: NEW blocker
    g = evaluate_gate("CUSTOM", base, cur_blocked, d, policy_data=legacy)
    check("PH13-15a", g["result"] == "FAIL", "new blocker must fail legacy policy")
    # baseline blocked, current blocked (same blocker) → PASS (debt, not new)
    d = diff_snapshots(cur_blocked, cur_blocked)
    g = evaluate_gate("CUSTOM", cur_blocked, cur_blocked, d, policy_data=legacy)
    check("PH13-15b", g["result"] == "PASS",
          f"pre-existing debt must not fail legacy policy: {g}")

    print("== PH13-16 CUSTOM mature policy ==")
    mature, errs = load_policy(open(os.path.join(HERE, "..", "..", "rta", "examples", "policies",
                                                 "mature_project.yml"),
                                    encoding="utf-8").read())
    assert errs == [], errs
    d = diff_snapshots(base, cur_blocked)
    g = evaluate_gate("CUSTOM", base, cur_blocked, d, policy_data=mature)
    check("PH13-16a", g["result"] == "FAIL", g)

    print("== PH13-17 invalid policy ==")
    errs = validate_policy({"policy": "CUSTOM", "policy_version": 1, "evil": 1})
    check("PH13-17a", any("unknown policy field" in e for e in errs), str(errs))
    errs = validate_policy({"policy": "CUSTOM", "policy_version": 99})
    check("PH13-17b", any("unsupported policy_version" in e for e in errs), str(errs))
    data, errs = load_policy("policy: CUSTOM\npolicy_version: 1\nfail_on:\n  new_blockers: maybe\n")
    check("PH13-17c", data is None and any("must be boolean" in e for e in errs), str(errs))

    print("== PH13-18 engine failure ==")
    cur_failed = json.loads(json.dumps(_snap(CLEAN)))
    cur_failed["analysis"]["engine_failed"] = True
    for pol in ("BLOCKERS_ONLY", "NO_READINESS_REGRESSION", "STRICT"):
        g = evaluate_gate(pol, base, cur_failed, diff_snapshots(base, cur_failed))
        check(f"PH13-18-{pol}", g["result"] == "FAIL" and g["exit_code"] == EXIT_ENGINE_FAILURE,
              g)
    g = evaluate_gate("CUSTOM", base, cur_failed,
                      diff_snapshots(base, cur_failed), policy_data=legacy)
    check("PH13-18-CUSTOM", g["result"] == "FAIL" and g["exit_code"] == EXIT_ENGINE_FAILURE,
          g)

    print("== PH13-19 trust regression ==")
    unsup = CLEAN + "set_clock_unknown_option 1\n"
    base_t = _snap(CLEAN)
    cur_t = _snap(unsup)
    d = diff_snapshots(base_t, cur_t)
    check("PH13-19a", d["trust"]["regressions"], "trust regression must be detected")
    g = evaluate_gate("CUSTOM", base_t, cur_t, d, policy_data=mature)
    check("PH13-19b", g["result"] == "FAIL", "mature policy must fail on trust regression")
    g = evaluate_gate("CUSTOM", base_t, cur_t, d, policy_data=legacy)
    check("PH13-19c", g["result"] == "PASS", "legacy policy may allow trust regression")

    print("== PH13-20 coverage regression ==")
    sdc_no_in = "create_clock -name clk_core -period 10.0 [get_ports clk]\n" \
                "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n"
    base_c = _snap(CLEAN, ctx=ctx_a)
    cur_c = _snap(sdc_no_in, ctx=ctx_a)
    d = diff_snapshots(base_c, cur_c)
    newly = d["coverage"]["inputs"]["newly_unconstrained"]
    check("PH13-20a", "din" in newly, f"din should be newly unconstrained: {newly}")
    g = evaluate_gate("CUSTOM", base_c, cur_c, d, policy_data=mature)
    check("PH13-20b", g["result"] == "FAIL", "mature policy must fail on coverage regression")

    print("== PH13-21 existing debt unchanged ==")
    d = diff_snapshots(cur_blocked, cur_blocked)
    check("PH13-21a", d["debt"]["existing"]["blockers"] >= 1, str(d["debt"]))
    check("PH13-21b", d["debt"]["new_debt"]["blockers"] == 0, str(d["debt"]))
    g = evaluate_gate("NO_READINESS_REGRESSION", cur_blocked, cur_blocked, d)
    check("PH13-21c", g["result"] == "PASS", g)

    print("== PH13-22 resolved debt ==")
    d = diff_snapshots(cur_blocked, cur_clean)
    check("PH13-22a", d["debt"]["resolved_debt"]["blockers"] >= 1, str(d["debt"]))
    check("PH13-22b", d["classification"] == IMPROVEMENT, d["classification"])
    g = evaluate_gate("NO_READINESS_REGRESSION", cur_blocked, cur_clean, d)
    check("PH13-22c", g["result"] == "PASS", g)

    print("== PH13-23 false-new attack (line movement) ==")
    moved = "\n".join(f"# filler {i}" for i in range(50)) + "\n" + CLEAN
    base = _snap(CLEAN)
    cur = _snap(moved)
    d = diff_snapshots(base, cur)
    new, resolved = _new_resolved(d)
    check("PH13-23", not new and not resolved,
          f"line movement must be neutral: new={new} resolved={resolved}")

    print("== PH13-24 false-resolved attack (formatting) ==")
    # Semantically-equivalent transformations ONLY: numeric formatting, extra
    # whitespace, comments. (Splitting a command mid-line would change the
    # analysis, so that is NOT part of this invariant test.)
    fmt = (
        "# header comment added\n\n"
        + CLEAN.replace("10.0", "10")
               .replace("2.0", "2")
               .replace("set_input_delay", " set_input_delay   ")
               .replace(" -clock", "   -clock")
    )
    base = _snap(CLEAN)
    cur = _snap(fmt)
    d = diff_snapshots(base, cur)
    new, resolved = _new_resolved(d)
    check("PH13-24", not new and not resolved,
          f"formatting must be neutral: new={new} resolved={resolved}")

    print("== PH13-25 realistic CI workflow ==")
    snap = _snap(CLEAN)
    d = diff_snapshots(snap, _snap(CLEAN))
    g = evaluate_gate("NO_READINESS_REGRESSION", snap, _snap(CLEAN), d)
    check("PH13-25a", g["exit_code"] == EXIT_PASS, g)
    d = diff_snapshots(snap, _snap(BLOCKER))
    g = evaluate_gate("NO_READINESS_REGRESSION", snap, _snap(BLOCKER), d)
    check("PH13-25b", g["exit_code"] == EXIT_GATE_FAILED, g)
    check("PH13-25c", d["classification"] == BLOCKING_REGRESSION, d["classification"])
    # baseline round-trip through JSON (artifact preservation)
    js = snapshot_to_json(_snap(CLEAN))
    loaded, errs = load_snapshot(js)
    check("PH13-25d", loaded is not None and errs == [], str(errs))

    print()
    print(f"PH13 golden: {len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("FAILED:", ", ".join(FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
