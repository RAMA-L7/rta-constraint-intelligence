"""
Phase 12 — false-confidence suite for readiness diff.

FALSE-IMPROVEMENT: a removed warning is NOT automatically an improvement if
constraint coverage actually became worse (design-aware), or if the construct
that produced the warning is no longer analyzed (trust regression hidden).
FALSE-REGRESSION: semantically identical findings that moved lines or changed
formatting must NEVER appear as NEW.
Also: a new deterministic blocker must never be hidden by hundreds of
unchanged baseline findings; a harmless reformat must never fail CI.
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


def _s(t, ctx=None):
    return rd.build_snapshot(check_sdc(t, context=ctx), context=ctx, source_name="t.sdc")


def run():
    fails = []

    def check(label, cond, detail=""):
        if not cond:
            fails.append(f"{label}: {detail}")

    # ── FALSE-IMPROVEMENT (design-aware) ───────────────────────────────────
    from design_context import parse_verilog
    v = "module top (input clk, input din_a, input din_b, output dout_a); reg r; always @(posedge clk) r <= din_a & din_b; assign dout_a = r; endmodule\n"
    ctx = parse_verilog(v).context
    full = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_a]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_b]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout_a]
"""
    less = full.replace("set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_b]\n", "")
    sb = _s(full, ctx)
    sc = _s(less, ctx)
    d = rd.diff_snapshots(sb, sc)
    check("false-improvement: coverage regression is REVIEW_REGRESSION not IMPROVEMENT",
          d["classification"] == rd.REVIEW_REGRESSION,
          f"class={d['classification']}")
    check("false-improvement: din_b listed newly unconstrained",
          "din_b" in d["coverage"]["inputs"]["newly_unconstrained"],
          d["coverage"]["inputs"]["newly_unconstrained"])

    # Removing a constraint that suppressed a warning must not be "improvement"
    # when the design object becomes unconstrained (covered above by delta).

    # ── FALSE-REGRESSION: line movement + reformat = UNCHANGED ─────────────
    # Both revisions carry the SAME semantic constraints in the SAME order
    # (override detection is order-sensitive, so reordering would NOT be
    # equivalent). Only whitespace, comments, line positions and numeric
    # forms change (11.0 vs 1.1e1 canonicalize to the same value).
    t1 = CLEAN + "set_input_delay -max 11.0 -clock clk_core [get_ports din]\n"
    t2 = ("# moved far below\nset sdc_version 2.2\n"
          "create_clock -name clk_core -period 10.000 [get_ports clk_core]\n"
          "set_propagated_clock [get_clocks clk_core]\n"
          "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
          "set_input_delay -max 1.1e1 -clock clk_core [get_ports din]\n"
          "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n")
    d = rd.diff_snapshots(_s(t1), _s(t2))
    check("false-regression: moved+reformatted finding is UNCHANGED",
          len(d["findings"]["new"]) == 0 and len(d["findings"]["resolved"]) == 0,
          f"new={len(d['findings']['new'])} resolved={len(d['findings']['resolved'])}")
    check("false-regression: classification NEUTRAL",
          d["classification"] in (rd.NEUTRAL_CHANGE, rd.IMPROVEMENT), d["classification"])

    # ── New blocker hidden among many unchanged findings → still BLOCKING ──
    noisy_base = CLEAN
    for i in range(150):
        noisy_base += f"# informational comment {i}\n"
    noisy_cur = noisy_base + "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]\n"
    d = rd.diff_snapshots(_s(noisy_base), _s(noisy_cur))
    check("blocker-among-noise: BLOCKING_REGRESSION",
          d["classification"] == rd.BLOCKING_REGRESSION, d["classification"])
    check("blocker-among-noise: SDC-046 in new blockers",
          "SDC-046" in {f["code"] for f in d["findings"]["new_blockers"]},
          str([f["code"] for f in d["findings"]["new_blockers"]]))

    # ── Unsupported Tcl (trust) hidden as "clean" → not READY, not NEUTRAL ─
    t_clean = _s(CLEAN)
    t_unsup = _s(CLEAN + "foreach x {a b} { set y $x }\n")
    d = rd.diff_snapshots(t_clean, t_unsup)
    check("trust-regression: REVIEW_REGRESSION despite zero errors",
          d["classification"] == rd.REVIEW_REGRESSION, d["classification"])
    check("trust-regression: SCOPE-UNSUPPORTED present",
          "SCOPE-UNSUPPORTED" in {f["code"] for f in d["findings"]["new"]},
          str([f["code"] for f in d["findings"]["new"]]))

    # ── Harmless reformat must not fail a NO_REGRESSION gate ───────────────
    b = _s(CLEAN)
    c = _s(CLEAN.replace("10.0", "10.000").replace("\n", "\r\n"))
    d = rd.diff_snapshots(b, c)
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b, c, d)
    check("gate-on-reformat: PASS", g["result"] == "PASS" and g["exit_code"] == rd.EXIT_PASS,
          f"{g['result']}/{g['exit_code']}")

    # ── Changed netlist + unchanged SDC: honest CONTEXT_CHANGE ─────────────
    v2 = "module top (input clk, input din_a, input din_b, input din_c, output dout_a); reg r; always @(posedge clk) r <= din_a & din_b & din_c; assign dout_a = r; endmodule\n"
    ctx2 = parse_verilog(v2).context
    sdc_ab = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_a]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_b]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout_a]
"""
    sb = _s(sdc_ab, ctx)
    sc = _s(sdc_ab, ctx2)  # same SDC, design gained din_c
    d = rd.diff_snapshots(sb, sc)
    check("netlist-change: CONTEXT_CHANGE",
          d["classification"] == rd.CONTEXT_CHANGE, d["classification"])

    # ── Incompatible baseline must not silently PASS a gate ────────────────
    bad = _s(CLEAN)
    bad["schema_version"] = 99
    g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, bad, _s(CLEAN),
                         rd.diff_snapshots(bad, _s(CLEAN)))
    check("incompatible-gate: FAIL exit 2",
          g["result"] == "FAIL" and g["exit_code"] == rd.EXIT_INVALID,
          f"{g['result']}/{g['exit_code']}")

    print(f"READINESS DIFF CONFIDENCE: {'ALL PASS' if not fails else 'FAILURES'}")
    for f in fails:
        print("  ❌", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
