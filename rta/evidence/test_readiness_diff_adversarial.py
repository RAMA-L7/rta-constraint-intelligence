"""
Phase 12 — adversarial readiness-diff suite.

Attempts to fool finding identity / delta logic:
  - same rule on different objects must NOT pair
  - same object with changed value must classify CHANGED, not NEW+RESOLVED
  - line reordering / duplicate identical commands / clock+object renaming
  - bus ranges, wildcards, variables, hierarchy changes
  - baseline/current context switches must not silently pair unrelated findings
Target: no false NEW for semantically identical findings; no false UNCHANGED
for genuinely different findings.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc
import readiness_diff as rd

CLEAN = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
"""


def _s(t):
    return rd.build_snapshot(check_sdc(t), source_name="t.sdc")


def _codes(items):
    return sorted({(x.get("code"), x.get("msg", "")[:60]) for x in items})


def run():
    fails = []

    def check(label, cond, detail=""):
        if not cond:
            fails.append(f"{label}: {detail}")

    # 1. Identical design, different object names → distinct findings, no pairing.
    a = _s(CLEAN + "set_input_delay -max 12.0 -clock ghost_a [get_ports din_a2]\n")
    b = _s(CLEAN + "set_input_delay -max 12.0 -clock ghost_b [get_ports din_b2]\n")
    d = rd.diff_snapshots(a, b)
    check("same-rule-different-objects: no UNCHANGED pairing",
          d["findings"]["unchanged"] == 0,
          f"unchanged={d['findings']['unchanged']} (must be 0: different objects)")
    check("same-rule-different-objects: 1 resolved + 1 new",
          len(d["findings"]["resolved"]) == 1 and len(d["findings"]["new"]) == 1,
          f"resolved={len(d['findings']['resolved'])} new={len(d['findings']['new'])}")

    # 2. Same object, value changed → CHANGED, not NEW+RESOLVED. Both the
    #    SDC-008 (delay>=period) and SDC-068 (override) findings change value,
    #    so both must pair as CHANGED (two candidates in two different
    #    base_id groups — exercises the per-key index bookkeeping).
    v1 = CLEAN + "set_input_delay -max 11.0 -clock clk_core [get_ports din]\n"
    v2 = CLEAN + "set_input_delay -max 12.5 -clock clk_core [get_ports din]\n"
    d = rd.diff_snapshots(_s(v1), _s(v2))
    check("value-change: 2 CHANGED", len(d["findings"]["changed"]) == 2,
          f"changed={[(c['code']) for c in d['findings']['changed']]}")
    check("value-change: 0 NEW 0 RESOLVED",
          len(d["findings"]["new"]) == 0 and len(d["findings"]["resolved"]) == 0,
          f"new={len(d['findings']['new'])} resolved={len(d['findings']['resolved'])}")

    # 3. Line reordering of identical commands → no delta.
    t1 = CLEAN
    t2 = ("set sdc_version 2.2\nset_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n"
          "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
          "set_propagated_clock [get_clocks clk_core]\n"
          "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n")
    d = rd.diff_snapshots(_s(t1), _s(t2))
    check("line-reorder: no delta",
          d["classification"] in (rd.NEUTRAL_CHANGE,),
          f"class={d['classification']} new={len(d['findings']['new'])}")

    # 4. Duplicate identical commands added → advisory regression only.
    d = rd.diff_snapshots(_s(CLEAN), _s(CLEAN + "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"))
    check("dup-added: advisory", d["classification"] == rd.ADVISORY_REGRESSION,
          f"class={d['classification']}")

    # 5. Clock renamed while a finding mentions the clock name → the SDC-008
    #    finding ("clock clk_core period ...") is a semantic rename: its
    #    identity differs, so it must pair as RESOLVED+NEW (never CHANGED,
    #    never UNCHANGED). Phase 13 structured identity treats the CLOCK as a
    #    semantic identity field ("same rule + different clock" must never
    #    collide), so SDC-068's override is also NEW+RESOLVED: the override
    #    now applies to a different clock domain. The overall classification
    #    must be BLOCKING_REGRESSION (a like blocker appeared under a new
    #    name) — the gate fails, which is the safe behavior for renames.
    c1 = CLEAN + "set_input_delay -max 11.0 -clock clk_core [get_ports din]\n"
    c2 = CLEAN.replace("clk_core", "clk_renamed") + \
        "set_input_delay -max 11.0 -clock clk_renamed [get_ports din]\n"
    d = rd.diff_snapshots(_s(c1), _s(c2))
    check("clock-rename: SDC-008 appears in new",
          "SDC-008" in {f["code"] for f in d["findings"]["new"]},
          str([f["code"] for f in d["findings"]["new"]]))
    check("clock-rename: SDC-008 appears in resolved",
          "SDC-008" in {f["code"] for f in d["findings"]["resolved"]},
          str([f["code"] for f in d["findings"]["resolved"]]))
    # Phase 13 contract: clock is part of structured identity (collision rule),
    # so the SDC-068 override on the renamed clock is NEW+RESOLVED as well.
    check("clock-rename: SDC-068 appears in new (clock-aware identity)",
          "SDC-068" in {f["code"] for f in d["findings"]["new"]},
          str([f["code"] for f in d["findings"]["new"]]))
    check("clock-rename: SDC-068 appears in resolved (clock-aware identity)",
          "SDC-068" in {f["code"] for f in d["findings"]["resolved"]},
          str([f["code"] for f in d["findings"]["resolved"]]))
    check("clock-rename: classification BLOCKING_REGRESSION",
          d["classification"] == rd.BLOCKING_REGRESSION, d["classification"])

    # 6. Wildcard vs explicit bus reference — different objects, no pairing.
    w1 = _s(CLEAN + "set_input_delay -max 3.0 -clock clk_core [get_ports {din[3:0]}]\n")
    w2 = _s(CLEAN + "set_input_delay -max 3.0 -clock clk_core [get_ports din*]\n")
    d = rd.diff_snapshots(w1, w2)
    # SDC-only: both are distinct unresolved collections → likely no overlap pairing.
    check("wildcard-vs-bus: no false CHANGED pairing",
          len(d["findings"]["changed"]) == 0,
          f"changed={len(d['findings']['changed'])}")

    # 7. Design-context change (new port) is not blamed on the SDC.
    from design_context import parse_verilog
    v1 = "module top (input clk, input din_a, output dout_a); reg r; always @(posedge clk) r <= din_a; assign dout_a = r; endmodule\n"
    v2 = "module top (input clk, input din_a, input din_b, output dout_a); reg r; always @(posedge clk) r <= din_a & din_b; assign dout_a = r; endmodule\n"
    sdc = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_a]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout_a]
"""
    ctx1 = parse_verilog(v1).context
    ctx2 = parse_verilog(v2).context
    sb = rd.build_snapshot(check_sdc(sdc, context=ctx1), context=ctx1)
    sc = rd.build_snapshot(check_sdc(sdc, context=ctx2), context=ctx2)
    d = rd.diff_snapshots(sb, sc)
    check("design-port-added: CONTEXT_CHANGE not BLOCKING",
          d["classification"] == rd.CONTEXT_CHANGE,
          f"class={d['classification']}")
    check("design-port-added: compat flagged",
          d["compatibility"]["status"] == rd.COMPATIBLE_WITH_CONTEXT_CHANGE,
          d["compatibility"]["status"])

    # 8. Removed constraint → finding disappears BUT coverage worsens in
    #    design-aware mode → must NOT be a blanket improvement.
    #    Uses the 4-port design (clk, din_a, din_b, dout_a) so din_b is real.
    v4 = ("module top (input clk, input din_a, input din_b, output dout_a); "
          "reg r; always @(posedge clk) r <= din_a & din_b; "
          "assign dout_a = r; endmodule\n")
    ctx4 = parse_verilog(v4).context
    sdc_full = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_a]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_b]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout_a]
"""
    sdc_less = sdc_full.replace("set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_b]\n", "")
    sb = rd.build_snapshot(check_sdc(sdc_full, context=ctx4), context=ctx4)
    sc = rd.build_snapshot(check_sdc(sdc_less, context=ctx4), context=ctx4)
    d = rd.diff_snapshots(sb, sc)
    check("removed-constraint-coverage-worse: REVIEW_REGRESSION (not IMPROVEMENT)",
          d["classification"] == rd.REVIEW_REGRESSION,
          f"class={d['classification']} (must not be IMPROVEMENT when coverage worsened)")
    check("removed-constraint-coverage-worse: din_b flagged",
          "din_b" in d["coverage"]["inputs"]["newly_unconstrained"],
          d["coverage"]["inputs"]["newly_unconstrained"])

    # 9. Semantic identity is stable under numeric canonicalization.
    a = _s(CLEAN + "set_input_delay -max 11.0 -clock clk_core [get_ports din]\n")
    b = _s(CLEAN + "set_input_delay -max 1.1e1 -clock clk_core [get_ports din]\n")
    d = rd.diff_snapshots(a, b)
    check("sci-notation: UNCHANGED", d["findings"]["unchanged"] >= 1,
          f"unchanged={d['findings']['unchanged']}")

    # 10. Duplicate identical commands within one file — snapshot counts them.
    s = _s(CLEAN + CLEAN)
    check("duplicate-in-one-file: two SDC-067 advisories",
          sum(1 for f in s["findings"] if f["code"] == "SDC-067") >= 2,
          str([f["code"] for f in s["findings"]]))

    print(f"READINESS DIFF ADVERSARIAL: {'ALL PASS' if not fails else 'FAILURES'}")
    for f in fails:
        print("  ❌", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
