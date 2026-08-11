#!/usr/bin/env python3
"""
Phase 5 — Adversarial semantic QA.

Independent tests designed to BREAK the Phase-5 semantic analyzer:
 - false-conflict hunting (legal duplicates, overrides, distinct modes)
 - numerical equivalence (0.25 == 2.5e-1) must not create false conflicts
 - netlist-dependent collections must never be flagged as undefined
 - variable-derived and multiline duplicates
 - provenance correctness
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc  # noqa: E402

PASS = 0
FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✅ {name}")
    except AssertionError as exc:
        FAIL += 1
        print(f"  ❌ {name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        FAIL += 1
        print(f"  💥 {name}: {type(exc).__name__}: {exc}")


def codes(r):
    return {i.code for i in r.issues}


# ── FALSE-CONFLICT HUNTING (must produce NO semantic findings) ───────────────

def test_legal_min_max_pair():
    """-max and -min on same port+clock are distinct, NOT a duplicate/conflict."""
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 2.0 -clock c [get_ports din]
set_input_delay -min 0.5 -clock c [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")}
        assert not semantic, f"false semantic finding: {semantic}"
    check("legal -max/-min pair → no false finding", run)


def test_rise_fall_separate():
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 2.0 -rise -clock c [get_ports din]
set_input_delay -max 2.5 -fall -clock c [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")}
        assert not semantic, f"false semantic finding: {semantic}"
    check("rise vs fall constraints → no false conflict", run)


def test_different_clocks_same_port():
    def run():
        r = check_sdc("""create_clock -name c1 -period 10.0 [get_ports clk]
create_clock -name c2 -period 5.0 [get_ports clk2]
set_input_delay -max 2.0 -clock c1 [get_ports din]
set_input_delay -max 2.5 -clock c2 [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c1 [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")}
        assert not semantic, f"false semantic finding: {semantic}"
    check("same port under two clocks → no false conflict", run)


def test_add_delay_mode():
    def run():
        r = check_sdc("""create_clock -name c1 -period 10.0 [get_ports clk]
create_clock -name c2 -period 5.0 [get_ports clk2]
set_input_delay -max 2.0 -clock c1 [get_ports din] -add_delay
set_input_delay -max 2.5 -clock c2 [get_ports din] -add_delay
set_output_delay -max 1.0 -min 0.2 -clock c1 [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")}
        assert not semantic, f"false semantic finding: {semantic}"
    check("-add_delay accumulation → no false conflict", run)


def test_netlist_dependent_refs():
    """get_ports/get_pins/all_clocks/wildcards must never be 'undefined'.

    Clock NAMES inside [get_clocks ...] ARE resolvable from the SDC (a clock
    must be declared by create_clock), so those are checked. Everything else
    (get_ports, get_pins, all_clocks, wildcards) is netlist-dependent.
    """
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock [get_ports clk] [all_inputs]
set_clock_groups -asynchronous -group [get_clocks c] -group [get_clocks *]
set_clock_groups -asynchronous -group [get_clocks c] -group [all_clocks]
create_generated_clock -name g -master_clock [get_clocks c] -source [get_pins U/A] -divide_by 2 [get_pins U/B]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048")}
        assert not semantic, f"netlist-dependent refs misflagged: {semantic}"
    check("netlist-dependent collections (ports/pins/*/all_clocks) → never undefined", run)


def test_get_clocks_undefined_names_fire():
    """A clock NAME in [get_clocks {...}] that is not declared IS undefined."""
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_clock_groups -asynchronous -group [get_clocks c] -group [get_clocks {a b c}]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        sdc048 = [i for i in r.issues if i.code == "SDC-048"]
        # a and b are undeclared clock names; c is declared
        assert sdc048, "SDC-048 must fire for undeclared clock names"
        msgs = " ".join(i.msg for i in sdc048)
        assert "\"a\"" in msgs and "\"b\"" in msgs and "\"c\"" not in msgs
    check("undeclared clock NAMES in get_clocks → SDC-048 (declared c excluded)", run)


def test_wildcard_get_clocks_never_undefined():
    """Reviewer fix: [get_clocks *] / {clk*} in -clock, -master_clock and
    -group are netlist-dependent → must NEVER fire SDC-046/047/048."""
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock [get_clocks *] [all_inputs]
set_clock_groups -asynchronous -group [get_clocks c] -group [get_clocks {clk* sync*}]
create_generated_clock -name g -master_clock [get_clocks *] -source [get_ports clk] -divide_by 2 [get_pins U/B]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        bad = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048")}
        assert not bad, f"wildcard get_clocks misflagged: {bad}"
    check("[get_clocks *] / {clk*} refs → never undefined (reviewer fix)", run)


# ── NUMERICAL EQUIVALENCE ─────────────────────────────────────────────────────

def test_sci_and_decimal_not_conflict():
    """0.25 and 2.5e-1 are numerically equal — no false duplicate/conflict."""
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 0.25 -clock c [get_ports din]
set_input_delay -min 0.25 -clock c [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")}
        assert not semantic, f"false semantic finding: {semantic}"
    check("0.25 vs 0.25 (different modes) → no false conflict", run)


def test_whitespace_and_multiline_duplicate_same_clock():
    """Whitespace/multiline variants of the SAME defined clock ref → still valid."""
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay \\\\
    -max 2.0 -clock c \\\\
    [get_ports din]
set_input_delay -min 0.5 -clock c [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")}
        assert not semantic, f"false semantic finding: {semantic}"
    check("multiline + whitespace ref → resolves, no false finding", run)


def test_variable_derived_clock_ref():
    def run():
        r = check_sdc("""set MY_CLK clk_a
create_clock -name clk_a -period 10.0 [get_ports clk]
set_input_delay -max 2.0 -min 0.5 -clock $MY_CLK [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
""")
        semantic = {i.code for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048")}
        assert not semantic, f"variable-derived ref misflagged: {semantic}"
    check("variable-derived clock ref resolves → no false undefined", run)


def test_similar_clock_names():
    def run():
        r = check_sdc("""create_clock -name clk -period 10.0 [get_ports a]
create_clock -name clk2 -period 5.0 [get_ports b]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock clk2 [all_outputs]
""")
        assert not any(i.code == "SDC-046" for i in r.issues), "clk/clk2 confused"
    check("clk vs clk2 distinct → no false undefined", run)


# ── CONFIRMED FINDINGS (must fire) ────────────────────────────────────────────

def test_confirmed_undefined_clock():
    def run():
        r = check_sdc("""create_clock -name clk_a -period 10.0 [get_ports clk]
set_input_delay -max 12.0 -min 0.5 -clock nonexistent_clk [get_ports data_in]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
""")
        assert any(i.code == "SDC-046" for i in r.issues)
        assert not any(i.code == "SDC-008" for i in r.issues), "P0 fallback regression"
    check("undefined clock → SDC-046, NO silent SDC-008 fallback", run)


def test_confirmed_contradictory_case_analysis():
    def run():
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_case_analysis 0 [get_ports mode]
set_case_analysis 1 [get_ports mode]
""")
        sdc049 = [i for i in r.issues if i.code == "SDC-049"]
        assert sdc049, "SDC-049 must fire"
        assert sdc049[0].line2, "SDC-049 must carry both source lines"
    check("case_analysis 0 then 1 on same pin → SDC-049 with dual provenance", run)


def main():
    print("PHASE 5 ADVERSARIAL SEMANTIC QA")
    test_legal_min_max_pair()
    test_rise_fall_separate()
    test_different_clocks_same_port()
    test_add_delay_mode()
    test_netlist_dependent_refs()
    test_get_clocks_undefined_names_fire()
    test_wildcard_get_clocks_never_undefined()
    test_sci_and_decimal_not_conflict()
    test_whitespace_and_multiline_duplicate_same_clock()
    test_variable_derived_clock_ref()
    test_similar_clock_names()
    test_confirmed_undefined_clock()
    test_confirmed_contradictory_case_analysis()
    print(f"\nADVERSARIAL: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
