#!/usr/bin/env python3
"""
Ṛta — Engine Smoke Test
========================
Run this after ANY change (yours, mine, or another agent's) to check every
core engine module actually still works — in seconds, with no browser and
no Streamlit required.

Usage:
    python3 smoke_test.py

Exit code 0 = everything passed. Exit code 1 = something broke, with a
plain-English description of exactly what and where.

This is NOT a replacement for the full pytest suite in rta/tests/ (which is
much more thorough) — it's a fast first line of defense you can run in
under 2 seconds after every edit, before you even open a browser.
"""

import sys
import traceback

# Force UTF-8 on stdout/stderr — Windows consoles default to cp1252, which
# cannot encode the ✅/⚠️ glyphs used below (same guard as api_server.py).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

PASS = []
FAIL = []


def check(name, fn):
    """Run one test. Records pass/fail, never raises — always continues."""
    try:
        fn()
        PASS.append(name)
        print(f"  ✅ {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  ❌ {name}")
        print(f"      → {e}")
    except Exception as e:
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"  💥 {name} (crashed, not just failed)")
        print(f"      → {type(e).__name__}: {e}")
        print(f"      {traceback.format_exc().splitlines()[-2].strip()}")


def section(title):
    print(f"\n── {title} " + "─" * max(0, 60 - len(title)))


# ═══════════════════════════════════════════════════════════════════════════
# CHECKER
# ═══════════════════════════════════════════════════════════════════════════
section("checker.py")

from checker import check_sdc


def test_checker_clean():
    sdc = (
        "create_clock -name clk -period 5.0 [get_ports clk]\n"
        "set_input_delay 1.0 -max -clock clk [get_ports din]\n"
        "set_input_delay 0.3 -min -clock clk [get_ports din]\n"
        "set_output_delay 1.0 -max -clock clk [get_ports dout]\n"
        "set_output_delay 0.3 -min -clock clk [get_ports dout]\n"
    )
    r = check_sdc(sdc)
    assert len(r.errors) == 0, f"expected 0 errors on a clean file, got {[i.code for i in r.errors]}"


check("checker: clean SDC has no errors", test_checker_clean)


def test_checker_duplicate_clock():
    sdc = (
        "create_clock -name clk -period 5.0 [get_ports a]\n"
        "create_clock -name clk -period 3.0 [get_ports b]\n"
    )
    r = check_sdc(sdc)
    codes = [i.code for i in r.issues]
    assert "SDC-002" in codes, f"expected SDC-002 (duplicate clock name), got {codes}"


check("checker: catches duplicate clock names (SDC-002)", test_checker_duplicate_clock)


def test_checker_no_clock():
    r = check_sdc("set_input_delay 1.0 [get_ports din]\n")
    codes = [i.code for i in r.issues]
    assert "SDC-001" in codes, f"expected SDC-001 (no clock), got {codes}"


check("checker: catches missing clock (SDC-001)", test_checker_no_clock)

# ═══════════════════════════════════════════════════════════════════════════
# GENERATOR
# ═══════════════════════════════════════════════════════════════════════════
section("generator.py")

from generator import SDCParams, ClockDef, generate_sdc


def test_generator_basic():
    p = SDCParams(
        design_name="SMOKE_TEST",
        clocks=[ClockDef(name="clk", clk_type="primary", port="clk", period=5.0)],
    )
    text = generate_sdc(p)
    assert "create_clock" in text, "generated SDC missing create_clock"
    assert "SMOKE_TEST" in text, "generated SDC missing design name"
    assert len(text) > 200, f"generated SDC suspiciously short ({len(text)} chars)"


check("generator: produces a valid SDC with expected content", test_generator_basic)

# ═══════════════════════════════════════════════════════════════════════════
# CORNER MANAGER + MMC
# ═══════════════════════════════════════════════════════════════════════════
section("corner_manager.py + mmc.py")

from corner_manager import Corner, validate_corner, CORNER_PRESETS
from mmc import generate_corner_sdcs, check_sdc_multi


def test_corner_presets_exist():
    assert len(CORNER_PRESETS) > 0 or CORNER_PRESETS, "no corner presets found"


check("corner_manager: presets exist", test_corner_presets_exist)


def test_mmc_generates_per_corner():
    p = SDCParams(design_name="MMC_TEST", clocks=[ClockDef(name="clk", port="clk", period=5.0)])
    c1 = Corner(name="WORST", voltage=0.9, temperature=125, process_type="SS")
    c2 = Corner(name="BEST", voltage=1.1, temperature=-40, process_type="FF")
    sdcs = generate_corner_sdcs(p, [c1, c2])
    assert set(sdcs.keys()) == {"WORST", "BEST"}, f"expected 2 corner SDCs, got {list(sdcs.keys())}"
    multi_result = check_sdc_multi(sdcs)
    assert multi_result is not None, "check_sdc_multi returned nothing"


check("mmc: generates and checks per-corner SDCs", test_mmc_generates_per_corner)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTRAINT DIFF
# ═══════════════════════════════════════════════════════════════════════════
section("constraint_diff.py")

from constraint_diff import analyze_constraint_changes


def test_constraint_diff_detects_period_change():
    v1 = "create_clock -name clk -period 5.0 [get_ports clk]\n"
    v2 = "create_clock -name clk -period 4.0 [get_ports clk]\n"
    r = analyze_constraint_changes(v1, v2)
    codes = [c.rule.rule_id for c in r.changes]
    assert "CHG-CK-001" in codes, f"expected CHG-CK-001 (period decreased), got {codes}"


check("constraint_diff: detects clock period change", test_constraint_diff_detects_period_change)

# ═══════════════════════════════════════════════════════════════════════════
# CLOCK RELATIONS
# ═══════════════════════════════════════════════════════════════════════════
section("clock_relations.py")

import clock_relations


def test_clock_relations_pair_count():
    sdc = (
        "create_clock -name clka -period 5.0 [get_ports a]\n"
        "create_clock -name clkb -period 3.0 [get_ports b]\n"
    )
    r = clock_relations.analyze_clock_relations(sdc)
    assert len(r.clocks) == 2, f"expected 2 clocks, got {len(r.clocks)}"
    assert len(r.pairs) == 1, f"expected 1 pair, got {len(r.pairs)}"


check("clock_relations: finds clocks and pairs correctly", test_clock_relations_pair_count)

# ═══════════════════════════════════════════════════════════════════════════
# COVERAGE
# ═══════════════════════════════════════════════════════════════════════════
section("coverage.py")

from coverage import parse_sdc_coverage


def test_coverage_categories():
    sdc = "create_clock -name clk -period 5.0 [get_ports clk]\n"
    r = parse_sdc_coverage(sdc)
    assert len(r.categories) > 0, "no coverage categories returned"


check("coverage: returns categories", test_coverage_categories)

# ═══════════════════════════════════════════════════════════════════════════
# DESIGN CONTEXT (netlist parsing) — new in v1.5.0
# ═══════════════════════════════════════════════════════════════════════════
section("design_context.py (netlist-aware)")

from design_context import parse_verilog, validate_design_references

GATE_NETLIST = """
module smoke_block ( clk, rst_n, data_in, data_out );
input clk;
input rst_n;
input [7:0] data_in;
output [7:0] data_out;
DFF_X1 u_ff0 ( .CK(clk), .D(data_in[0]), .Q(data_out[0]) );
endmodule
"""


def test_design_context_parses_ports():
    outcome = parse_verilog(GATE_NETLIST)
    ctx = outcome.context
    assert ctx.top_module == "smoke_block", f"expected top module 'smoke_block', got {ctx.top_module!r}"
    assert len(ctx.ports) == 4, f"expected 4 ports, got {len(ctx.ports)}: {list(ctx.ports.keys())}"


check("design_context: parses module/ports/instances", test_design_context_parses_ports)


def test_design_context_catches_typo():
    outcome = parse_verilog(GATE_NETLIST)
    ctx = outcome.context
    sdc = "create_clock -name clk_core -period 5.0 [get_ports clkTYPO]\n"
    findings = validate_design_references(sdc, ctx)
    codes = [f.code for f in findings]
    assert "SDC-055" in codes, f"expected SDC-055 (port not found), got {codes}"


check("design_context: catches a typo'd port name against the netlist", test_design_context_catches_typo)

# ═══════════════════════════════════════════════════════════════════════════
# DESIGN COVERAGE — new in v1.5.0
# ═══════════════════════════════════════════════════════════════════════════
section("design_coverage.py (netlist-aware)")

from design_coverage import analyze_coverage


def test_design_coverage_flags_unconstrained_output():
    outcome = parse_verilog(GATE_NETLIST)
    ctx = outcome.context
    sdc = (
        "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
        "set_input_delay 1.0 -clock clk_core [get_ports data_in]\n"
    )
    cov = analyze_coverage(sdc, ctx)
    out_statuses = {p.name: p.status for p in cov.outputs}
    assert out_statuses.get("data_out") == "UNCONSTRAINED", (
        f"expected data_out UNCONSTRAINED (no set_output_delay given), got {out_statuses}"
    )


check("design_coverage: flags a real output port with no set_output_delay", test_design_coverage_flags_unconstrained_output)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTRAINT INTERACTIONS — new in v1.5.0
# ═══════════════════════════════════════════════════════════════════════════
section("constraint_interactions.py")

from constraint_interactions import analyze_interactions


def test_interactions_catches_duplicate():
    sdc = (
        "create_clock -name clk -period 5.0 [get_ports clk]\n"
        "set_clock_uncertainty -setup 0.15 [get_clocks clk]\n"
        "set_clock_uncertainty -setup 0.15 [get_clocks clk]\n"
    )
    ia = analyze_interactions(sdc, None)
    codes = [f["code"] for f in ia.findings]
    assert "SDC-067" in codes, f"expected SDC-067 (exact duplicate), got {codes}"


check("constraint_interactions: catches an exact duplicate constraint", test_interactions_catches_duplicate)


def test_interactions_catches_conflict():
    sdc = (
        "create_clock -name clk -period 5.0 [get_ports clk]\n"
        "set_max_delay 2.0 -from [get_ports a]\n"
        "set_min_delay 3.0 -from [get_ports a]\n"
    )
    ia = analyze_interactions(sdc, None)
    codes = [f["code"] for f in ia.findings]
    assert "SDC-069" in codes, f"expected SDC-069 (max<min conflict), got {codes}"


check("constraint_interactions: catches a max<min delay conflict", test_interactions_catches_conflict)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTRAINT READINESS — new in v1.5.0
# ═══════════════════════════════════════════════════════════════════════════
section("constraint_readiness.py")

from constraint_readiness import analyze_readiness


def test_readiness_blocks_on_missing_output_delay():
    sdc = "create_clock -name clk -period 5.0 [get_ports clk]\n"
    r = check_sdc(sdc)
    rd = analyze_readiness(r)
    assert rd.overall in ("BLOCKED", "REVIEW_REQUIRED"), (
        f"a clock with no I/O delays at all should not be READY, got {rd.overall}"
    )
    assert "I/O" in rd.dimensions, "expected an I/O dimension in the readiness result"


check("constraint_readiness: correctly blocks an incomplete SDC", test_readiness_blocks_on_missing_output_delay)

# ═══════════════════════════════════════════════════════════════════════════
# LINTER / CONVERTER / WILDCARD / TCL RESOLVER — quick existence + shape checks
# ═══════════════════════════════════════════════════════════════════════════
section("linter.py / converter.py / wildcard_analyzer.py / tcl_resolver.py")

from linter import lint_sdc
from converter import sdc_to_json
from wildcard_analyzer import parse_wildcard
from tcl_resolver import parse_variables, build_symbol_table, resolve_variables


def test_linter_runs():
    r = lint_sdc("create_clock -name clk -period 5.0 [get_ports clk]\n\n\n\n")
    assert r is not None


check("linter: runs without error", test_linter_runs)


def test_converter_produces_valid_json():
    import json
    j = sdc_to_json("create_clock -name clk -period 5.0 [get_ports clk]\n")
    json.loads(j)  # raises if invalid


check("converter: produces parseable JSON", test_converter_produces_valid_json)


def test_wildcard_parses():
    wp = parse_wildcard("get_ports data_bus*")
    assert wp is not None


check("wildcard_analyzer: parses a wildcard pattern", test_wildcard_parses)


def test_tcl_resolver_substitutes():
    text = "set CLK_PERIOD 5.0\ncreate_clock -period $CLK_PERIOD [get_ports clk]\n"
    symtab = build_symbol_table(text)
    resolved = resolve_variables(text, symtab)
    assert "5.0" in resolved and "$CLK_PERIOD" not in resolved, (
        f"variable substitution failed: {resolved!r}"
    )


check("tcl_resolver: substitutes $VARNAME correctly", test_tcl_resolver_substitutes)

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
total = len(PASS) + len(FAIL)
print("\n" + "═" * 70)
print(f"RESULT: {len(PASS)}/{total} passed")
if FAIL:
    print(f"\n{len(FAIL)} FAILURE(S):")
    for name, msg in FAIL:
        print(f"  ❌ {name}")
        print(f"     {msg}")
    print("\nSomething regressed. Do not ship this build until these are fixed.")
    sys.exit(1)
else:
    print("Everything passed. Core engine behavior is intact.")
    sys.exit(0)
