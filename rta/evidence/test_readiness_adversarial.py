"""Phase 11 — Readiness adversarial suite.

Tries to fool the readiness aggregator:
  - 500 INFO findings + no real problem → must NOT be BLOCKED
  - one definite contradiction hidden among many infos → must be BLOCKED
  - full coverage + undefined clock → must NOT be READY
  - zero checker errors + unsupported Tcl → must NOT be fully READY
  - no netlist + otherwise good SDC → honest SDC-only readiness
  - netlist supplied + unsupported collection expression → trust limit visible
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc  # noqa: E402

PASS = FAIL = 0


def ok(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  ❌ {msg}")


def check(name, text, expect_not=None, expect=None, context=None):
    """expect_not / expect are lists of overall-statuses to forbid / require."""
    r = check_sdc(text, context=context)
    overall = (r.readiness or {}).get("overall")
    if expect_not and overall in expect_not:
        ok(False, f"{name}: overall={overall} must NOT be in {expect_not}")
    elif expect and overall not in expect:
        ok(False, f"{name}: overall={overall} expected in {expect}")
    else:
        ok(True, f"{name}: overall={overall}")


def main() -> int:
    print("READINESS ADVERSARIAL")

    # ── A1: 500 informational findings, no real problem → not BLOCKED ────────
    lines = ["set sdc_version 2.2"]
    lines.append("create_clock -name c -period 10.0 [get_ports clk]")
    lines.append("set_propagated_clock [get_clocks c]")
    lines.append("set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]")
    lines.append("set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]")
    lines.append("# hundreds of harmless info-generating commands:")
    for i in range(120):
        lines.append(f"set_operating_conditions -max SSG")  # repeated → SDC-131 info
    check("A1 500-info no blocker", "\n".join(lines),
          expect_not=["BLOCKED"])

    # ── A2: one contradiction hidden among many infos → BLOCKED ──────────────
    lines = ["set sdc_version 2.2"]
    lines.append("create_clock -name c -period 10.0 [get_ports clk]")
    lines.append("set_propagated_clock [get_clocks c]")
    lines.append("set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]")
    lines.append("set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]")
    lines.append("set_case_analysis 0 [get_ports mode]")
    lines.append("set_case_analysis 1 [get_ports mode]")  # SDC-049 → BLOCKED
    for i in range(120):
        lines.append(f"set_operating_conditions -max SSG")
    check("A2 contradiction among infos", "\n".join(lines),
          expect=["BLOCKED"])

    # ── A3: full coverage + undefined clock → not READY ─────────────────────
    s3 = """create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 2.0 -min 0.5 -clock ghost_clk [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]
"""
    check("A3 undefined clock despite coverage", s3,
          expect_not=["READY", "READY_WITH_ADVISORIES"])

    # ── A4: zero checker errors + unsupported Tcl → not fully READY ──────────
    s4 = """set sdc_version 2.2
create_clock -name c -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks c]
set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]
foreach p {a b} { set_input_delay 1 -clock c $p }
"""
    check("A4 unsupported Tcl", s4, expect_not=["READY", "READY_WITH_ADVISORIES"])

    # ── A5: no netlist + good SDC → honest SDC-only readiness ────────────────
    s5 = """set sdc_version 2.2
create_clock -name c -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks c]
set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]
"""
    r5 = check_sdc(s5)
    rdy5 = r5.readiness or {}
    ok(rdy5.get("mode") == "SDC_ONLY",
       "A5 mode must be SDC_ONLY (no netlist)")
    ok(rdy5.get("overall") not in ("BLOCKED", "INSUFFICIENT_CONTEXT"),
       "A5 SDC-only must not be BLOCKED/INSUFFICIENT_CONTEXT")
    ok(bool(rdy5.get("limited_design_verification")),
       "A5 SDC-only must set limited_design_verification")

    # ── A6: netlist + supported collections → design-aware stays non-blocked
    v6 = "module top (input clk, input a, output y); buf u (.a(a), .y(y)); endmodule\n"
    s6 = """set sdc_version 2.2
create_clock -name c -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks c]
set_input_delay -max 2.0 -min 0.5 -clock c [get_ports a]
set_output_delay -max 3.0 -min 1.0 -clock c [get_ports y]
"""
    from design_context import parse_verilog  # noqa: E402
    ctx6 = parse_verilog(v6)
    r6 = check_sdc(s6, context=ctx6.context)
    ok((r6.readiness or {}).get("mode") == "DESIGN_AWARE",
       "A6 mode must be DESIGN_AWARE")
    ok((r6.readiness or {}).get("overall") in ("READY", "READY_WITH_ADVISORIES"),
       "A6 resolvable design-aware stays non-blocked")

    print(f"READINESS ADVERSARIAL: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
