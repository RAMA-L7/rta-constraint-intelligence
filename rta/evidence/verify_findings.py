#!/usr/bin/env python3
"""
Phase-2 verification: minimal reproducers for every prior benchmark finding.

For each finding we build the SMALLEST possible SDC input, run it through every
analyzer (checker / converter / clock_relations / linter), and print the exact
output so we can classify CONFIRMED BUG / LIMITATION / FALSE POSITIVE / EXPECTED.

Usage:
    PYTHONIOENCODING=utf-8 python benchmarks/verify_findings.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc            # noqa: E402
from converter import parse_sdc          # noqa: E402
from clock_relations import analyze_clock_relations  # noqa: E402
from linter import lint_sdc              # noqa: E402


def run_all(text, label):
    print("=" * 78)
    print(f"REPRO: {label}")
    print("-" * 78)
    print(text)
    print("-" * 78)
    try:
        r = check_sdc(text)
        errs = [(i.code, i.line, i.msg[:110]) for i in r.issues if i.sev == "error"]
        warns = [(i.code, i.line, i.msg[:110]) for i in r.issues if i.sev == "warning"]
        infos = [(i.code, i.msg[:80]) for i in r.info]
        print(f"[checker]       clocks={r.stats.get('Clocks')} gen={r.stats.get('Generated clocks')} "
              f"in_dly={r.stats.get('Input delays')} out_dly={r.stats.get('Output delays')}")
        print(f"[checker]       errors={errs}")
        print(f"[checker]       warns ={warns}")
        print(f"[checker]       info  ={infos}")
    except Exception as e:  # noqa: BLE001
        print(f"[checker]       CRASH {type(e).__name__}: {e}")
    try:
        p = parse_sdc(text, label)
        print(f"[converter]     clocks={[(c.name, c.period, c.port) for c in p.clocks]} "
              f"in={len(p.input_delays)} out={len(p.output_delays)}")
    except Exception as e:  # noqa: BLE001
        print(f"[converter]     CRASH {type(e).__name__}: {e}")
    try:
        cr = analyze_clock_relations(text)
        print(f"[clock_rel]     clocks={[c.name for c in cr.clocks]} "
              f"pairs={len(cr.pairs)} stats={cr.stats}")
        for m in cr.mismatches[:6]:
            print(f"                MISMATCH {m.code} {m.severity}: {m.clock_a}/{m.clock_b} "
                  f"spec={m.specified} exp={m.expected}")
        for m in cr.missing_constraints[:6]:
            print(f"                MISSING  {m.code} {m.severity}: {m.clock_a}/{m.clock_b} "
                  f"spec={m.specified} exp={m.expected}")
    except Exception as e:  # noqa: BLE001
        print(f"[clock_rel]     CRASH {type(e).__name__}: {e}")
    try:
        lt = lint_sdc(text, fix=False)
        print(f"[linter]        warnings={lt.warnings} issues={lt.issues[:5]}")
    except Exception as e:  # noqa: BLE001
        print(f"[linter]        CRASH {type(e).__name__}: {e}")


F01_COMMENT_FULL_LINE = """\
# create_clock -name fake_clk -period 1.0 [get_ports fake_clk]
create_clock -name real_clk -period 10 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock real_clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock real_clk [all_outputs]
"""

F02_COMMENT_INLINE = """\
create_clock -name real_clk -period 10 [get_ports clk] # master clock
set_input_delay -max 1.0 -min 0.2 -clock real_clk [all_inputs] # setup
set_output_delay -max 1.0 -min 0.2 -clock real_clk [all_outputs] # load
"""

F03_MULTILINE_CLOCK = """\
create_clock \\
    -name sys_clk \\
    -period 10.0 \\
    [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock sys_clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock sys_clk [all_outputs]
"""

F04_MULTILINE_DELAY = """\
create_clock -name sys_clk -period 10.0 [get_ports clk]
set_input_delay \\
    -max 2.0 \\
    -min 0.3 \\
    -clock sys_clk \\
    [get_ports data_in]
set_output_delay -max 1.0 -min 0.2 -clock sys_clk [all_outputs]
"""

F05_NUM_SCI = """\
create_clock -name c -period 2.5e-1 [get_ports clk]
set_input_delay -max 3.0e-1 -min 1.0e-2 -clock c [all_inputs]
set_output_delay -max 1.0e-1 -min 1.0e-2 -clock c [all_outputs]
"""

F06_NUM_INT_FLOAT = """\
create_clock -name c_int -period 10 [get_ports clk_int]
create_clock -name c_f -period 10.0 [get_ports clk_f]
set_input_delay -max 1.0 -min 0.2 -clock c_int [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c_int [all_outputs]
"""

F07_NUM_LEADING_DOT = """\
create_clock -name c -period .25 [get_ports clk]
set_input_delay -max .1 -min .02 -clock c [all_inputs]
set_output_delay -max .1 -min .02 -clock c [all_outputs]
"""

F08_NUM_NEGATIVE = """\
create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 1.0 -min -0.25 -clock c [all_inputs]
set_output_delay -max 1.0 -min -0.25 -clock c [all_outputs]
"""

F09_VARIABLES = """\
set CLK_PERIOD 2.5
set IN_DLY 6.0
create_clock -name core_clk -period $CLK_PERIOD [get_ports clk]
set_input_delay -max $IN_DLY -min 0.2 -clock core_clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock core_clk [all_outputs]
"""

F10_SDC007_DATA_IN = """\
create_clock -name c -period 5.0 [get_ports data_in]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
"""

F11_BRACED_GROUPS = """\
create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 7.5 [get_ports clk_b]
create_clock -name clk_c -period 3.3 [get_ports clk_c]
set_clock_groups -asynchronous -group [get_clocks {clk_a clk_b}] -group [get_clocks clk_c]
set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_c [all_outputs]
"""

F12_UNCERTAINTY_ORDER = """\
create_clock -name c -period 5.0 [get_ports clk]
set_clock_uncertainty -setup 100.0 -hold 50.0 [get_clocks c]
set_clock_uncertainty 0.01 [get_clocks c]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
"""

F13_CONFLICTS = """\
create_clock -name clk_a -period 5.0 [get_ports clk_a]
set_false_path -from [get_pins U_A/Q] -to [get_pins U_B/D]
set_max_delay 1.0 -from [get_pins U_A/Q] -to [get_pins U_B/D]
set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
"""

F14_FALSE_PATH_RESET = """\
create_clock -name c -period 5.0 [get_ports clk]
set_false_path -from [get_ports rst_n] -to [get_pins U1/D]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
"""


def main():
    cases = [
        ("F01 comment full-line (comment mentions create_clock)", F01_COMMENT_FULL_LINE),
        ("F02 comment inline after command", F02_COMMENT_INLINE),
        ("F03 multiline create_clock (backslash)", F03_MULTILINE_CLOCK),
        ("F04 multiline set_input_delay (backslash)", F04_MULTILINE_DELAY),
        ("F05 numeric scientific notation 2.5e-1 / 3.0e-1", F05_NUM_SCI),
        ("F06 numeric int 10 vs float 10.0", F06_NUM_INT_FLOAT),
        ("F07 numeric leading-dot .25 (Tcl-invalid literal)", F07_NUM_LEADING_DOT),
        ("F08 numeric negative -0.25 (legal for -min)", F08_NUM_NEGATIVE),
        ("F09 Tcl variables $CLK_PERIOD / $IN_DLY", F09_VARIABLES),
        ("F10 SDC-007 data port name data_in", F10_SDC007_DATA_IN),
        ("F11 braced clock-group list {clk_a clk_b}", F11_BRACED_GROUPS),
        ("F12 uncertainty option order (flag-first + flagless)", F12_UNCERTAINTY_ORDER),
        ("F13 conflicting false_path + max_delay same path", F13_CONFLICTS),
        ("F14 false_path on reset (heuristic noise?)", F14_FALSE_PATH_RESET),
    ]
    for label, text in cases:
        run_all(text, label)


if __name__ == "__main__":
    main()
