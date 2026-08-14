"""
Test Drive parity regression — real_design_full.sdc.

Protects the known-good behavior of the repaired fixture against every
Test Drive metric. The expected values are the Original SDC Validator's
verified counts (see docs/migration/TEST_DRIVE_PARITY_INVESTIGATION.md):
the fixture was repaired so that current Ṛta reproduces them EXACTLY.

The repaired fixture must remain valid input; these numbers are the
semantic contract, not formatting snapshots.

Expected (Original == Ṛta after fixture repair):
  converter: 7 clocks (3 primary, 2 generated, 2 virtual), 25 constraints,
             4 input delays, 4 output delays, 5 false paths,
             5 multicycle+max-delay exceptions, 2 clock groups
  clock relations: 7 clocks, 21 pairs (nC2 of 7)
  coverage: 82.1% (32/39)
  checker: 0 errors; rule IDs SDC-020 ×2, SDC-027, SDC-150 ×5
           (SDC-150 is the intentional F1 enhancement; SDC-021 correctly
            does NOT fire because Ṛta pairs setup/hold across commands)
"""

from pathlib import Path

import pytest

from checker import check_sdc
from converter import parse_sdc
from clock_relations import analyze_clock_relations
from coverage import parse_sdc_coverage
from sdc_preprocess import preprocess_sdc, collect_diagnostics

FIXTURE = (
    Path(__file__).resolve().parent.parent.parent
    / "samples" / "real_design_full.sdc"
)

@pytest.fixture(scope="module")
def fixture_text():
    return FIXTURE.read_text(encoding="utf-8")


def test_fixture_exists_and_is_valid_input(fixture_text):
    """The repaired fixture must preprocess cleanly (no unclosed constructs)."""
    assert len(fixture_text) > 1000
    cmds = preprocess_sdc(fixture_text)
    assert collect_diagnostics(cmds) == [], collect_diagnostics(cmds)
    # sanity: both generated clocks and both virtual clocks are present
    joined = "\n".join(c.text for c in cmds)
    assert joined.count("create_generated_clock") == 2
    assert joined.count("create_clock -name vclk") == 2


def test_converter_clock_counts(fixture_text):
    p = parse_sdc(fixture_text, "real_design_full.sdc")
    assert p.clocks_count == 7
    primary = [c for c in p.clocks if not c.is_generated and not c.is_virtual]
    generated = [c for c in p.clocks if c.is_generated]
    virtual = [c for c in p.clocks if c.is_virtual]
    assert len(primary) == 3
    assert {c.name for c in generated} == {"clk_core_div2", "clk_core_div4"}
    assert {c.name for c in virtual} == {"vclk_core", "vclk_axi"}


def test_converter_constraint_counts(fixture_text):
    p = parse_sdc(fixture_text, "real_design_full.sdc")
    assert p.constraints_count == 25
    assert len(p.input_delays) == 4
    assert len(p.output_delays) == 4
    assert len(p.false_paths) == 5
    # 4 real set_multicycle_path + 1 set_max_delay (reused exception slot)
    mc = [e for e in p.multicycle_paths if e.command == "set_multicycle_path"]
    assert len(mc) == 4
    assert len(p.clock_groups) == 2
    # both clock groups carry the intended CDC content
    groups = [g["groups"] for g in p.clock_groups]
    assert any(["clk_core", "clk_core_div2", "clk_core_div4"] in g for g in groups)
    assert any(["clk_core"] in g for g in groups)


def test_clock_relations_pairs(fixture_text):
    cr = analyze_clock_relations(fixture_text)
    assert len(cr.clocks) == 7
    assert len(cr.pairs) == 21  # nC2 of 7 clocks


def test_coverage_score(fixture_text):
    cov = parse_sdc_coverage(fixture_text, "real_design_full.sdc")
    assert round(cov.score, 1) == pytest.approx(82.1)
    assert cov.total_present == 32
    assert cov.total_items == 39


def test_checker_findings(fixture_text):
    r = check_sdc(fixture_text)
    assert len(r.errors) == 0, [str(e) for e in r.errors]
    codes = [i.code for i in r.warnings]
    # Original-derived contract: the two clock-to-clock false paths are the
    # genuinely suspicious ones, plus max_delay missing -datapath_only.
    assert codes.count("SDC-020") == 2
    assert "SDC-027" in codes
    # Intentional enhancement (F1): rationale-comment linting fires on the
    # undocumented false paths / multicycle paths.
    assert codes.count("SDC-150") == 5
    # SDC-021 correctly does NOT fire: every -setup multicycle has a matching
    # -hold on identical endpoints (checked across commands, not lines).
    assert "SDC-021" not in codes
    # No spurious undefined-clock finding: the repaired fixture keeps both
    # generated clocks, so SDC-048 must not fire.
    assert "SDC-048" not in codes
