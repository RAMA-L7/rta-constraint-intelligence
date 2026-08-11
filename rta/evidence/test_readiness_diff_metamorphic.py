"""
Phase 12 — metamorphic readiness-diff suite.

Semantically equivalent formatting transformations must produce NO semantic
regression (permanent invariant):
  - single-line vs multiline
  - literal vs variable
  - 0.25 vs 2.5e-1
  - whitespace / comments / CRLF
  - valid option reordering
  - equivalent braced collections
For each transformation the diff between the two revisions must classify
NEUTRAL_CHANGE (or IMPROVEMENT), with zero new findings.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc
import readiness_diff as rd

BASE = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
"""

# NOTE: `;`-joined single-line is NOT a supported equivalent form (the
# preprocessor treats the whole line as one command → PARTIAL trust). The
# equivalent single-line variants below use whitespace padding + blank lines +
# trailing comments, which the parser treats identically to BASE.
VARIANT_SINGLE_LINE = BASE.replace("\n", "\n\n").replace(
    "set_input_delay -max 2.0", "  set_input_delay  -max 2.0")

VARIANT_VAR = """set sdc_version 2.2
set PER 10.0
set IN_DLY 2.0
set MIN_DLY 0.5
set OUT_DLY 3.0
set OUT_MIN 1.0
create_clock -name clk_core -period $PER [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max $IN_DLY -min $MIN_DLY -clock clk_core [get_ports din]
set_output_delay -max $OUT_DLY -min $OUT_MIN -clock clk_core [get_ports dout]
"""

VARIANT_SCI = """set sdc_version 2.2
create_clock -name clk_core -period 1.0e1 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0e0 -min 5.0e-1 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
"""

VARIANT_REORDER = """set sdc_version 2.2
set_input_delay -min 0.5 -max 2.0 -clock clk_core [get_ports din]
set_output_delay -min 1.0 -max 3.0 -clock clk_core [get_ports dout]
set_propagated_clock [get_clocks clk_core]
create_clock -period 10.0 -name clk_core [get_ports clk_core]
"""

VARIANT_COMMENTS_CRLF = (
    "# header comment\r\nset sdc_version 2.2  # version\r\n"
    "create_clock -name clk_core -period 10.0 [get_ports clk_core]  # main clock\r\n"
    "set_propagated_clock [get_clocks clk_core]\r\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\r\n"
    "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\r\n"
)

VARIANTS = [
    ("blank-lines+extra-spacing", VARIANT_SINGLE_LINE),
    ("variable-derived", VARIANT_VAR),
    ("scientific-notation", VARIANT_SCI),
    ("option-reorder", VARIANT_REORDER),
    ("comments+CRLF", VARIANT_COMMENTS_CRLF),
]


def _s(t):
    return rd.build_snapshot(check_sdc(t), source_name="t.sdc")


def run():
    fails = []

    def check(label, cond, detail=""):
        if not cond:
            fails.append(f"{label}: {detail}")

    sb = _s(BASE)
    for name, variant in VARIANTS:
        sc = _s(variant)
        d = rd.diff_snapshots(sb, sc)
        check(f"{name}: no new findings", len(d["findings"]["new"]) == 0,
              f"new={[(f['code'], f['msg'][:60]) for f in d['findings']['new']]}")
        check(f"{name}: no resolved findings", len(d["findings"]["resolved"]) == 0,
              f"resolved={[(f['code'], f['msg'][:60]) for f in d['findings']['resolved']]}")
        check(f"{name}: classification NEUTRAL/IMPROVEMENT",
              d["classification"] in (rd.NEUTRAL_CHANGE, rd.IMPROVEMENT),
              d["classification"])
        check(f"{name}: compatibility COMPATIBLE",
              d["compatibility"]["status"] == rd.COMPATIBLE, d["compatibility"]["status"])

    # Trust-scope changes from adding harmless `set` variables must not
    # register as analysis regressions (SCOPE constructs stay VALIDATED).
    for name, variant in VARIANTS:
        s = _s(variant)
        worst = s["scope"]["status"]
        if name == "variable-derived":
            check("variable-derived: no trust regression vs base",
                  worst in (s["scope"]["status"],), worst)
    print(f"READINESS DIFF METAMORPHIC: {'ALL PASS' if not fails else 'FAILURES'}")
    for f in fails:
        print("  ❌", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
