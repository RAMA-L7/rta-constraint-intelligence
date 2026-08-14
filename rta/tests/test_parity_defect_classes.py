"""
Regression protection for the five original SDC Validator defect classes.

Source: docs/migration/FULL_SDC_VALIDATOR_PARITY_AUDIT.md §5. Each class is a
defect of the legacy validator that current Ṛta fixes; these tests pin the
correct Ṛta behavior so the defects can never regress back in. Expected values
are taken from verified current behavior on the evidence fixtures, NOT from
the legacy implementation's (buggy) output.

Defect classes:
  1. Comment parsing      — commands/values inside comments must never produce
                            findings (false SDC-002 / SDC-008 / SDC-011, and the
                            legacy `float('.')` crash on comment text).
  2. Tcl continuations    — backslash-continued commands must join into one
                            logical command (no false SDC-003 / SDC-028 /
                            SDC-029 / SDC-031; correct counts for generated
                            clocks, false paths, multicycle paths, clock groups).
  3. Numeric / variables  — scientific notation parsed correctly; Tcl variables
                            resolved before value checks (SDC-008 fires where
                            the legacy validator missed or misread the value).
  4. Finding classification — dedicated codes stay dedicated: SDC-046
                            (undefined clock), SDC-047 (undefined master clock),
                            SDC-049 (contradictory case analysis) must not
                            regress into the legacy codes SDC-008 / SDC-003 /
                            SDC-011.
  5. Clock relationship inference — generated-clock master chains and declared
                            clock groups must infer synchronous/exclusive
                            relationships without the legacy false SDC-062
                            mismatches.
"""

from pathlib import Path

import pytest

from checker import check_sdc
from clock_relations import analyze_clock_relations
from converter import parse_sdc

EVIDENCE = (
    Path(__file__).resolve().parent.parent.parent / "rta" / "evidence"
)


def _text(rel_path: str) -> str:
    """Read a corpus fixture by path relative to rta/evidence/."""
    return (EVIDENCE / rel_path).read_text(encoding="utf-8")


def _codes(result) -> list:
    return [i.code for i in result.issues]


# ══════════════════════════════════════════════════════════════════════════
# Defect class 1 — comments must never create phantom constraints
# ══════════════════════════════════════════════════════════════════════════

class TestCommentParsing:
    """The legacy validator ran regexes on raw text including comments, so a
    comment that merely *mentioned* a command produced false findings — and on
    `s01` a comment mentioning `set_input_delay` crashed it (`float('.')`).
    Ṛta strips comments before parsing; none of these may reappear."""

    def test_comments_mentioning_commands_produce_no_false_findings(self):
        """comment_mentions_commands.sdc: 'create_clock', 'set_clock_groups',
        'set_input_delay 9.0' appear ONLY in comments. No SDC-002 duplicate
        clock, no SDC-008 (9.0 read out of a comment), no SDC-011/024."""
        r = check_sdc(_text("edge_cases/comment_mentions_commands.sdc"))
        assert r.errors == [], [str(e) for e in r.errors]
        assert not {"SDC-002", "SDC-008", "SDC-011", "SDC-024"} & set(_codes(r))
        # converter agrees: exactly one real clock, one input delay
        p = parse_sdc(_text("edge_cases/comment_mentions_commands.sdc"))
        assert p.clocks_count == 1
        assert len(p.input_delays) == 1

    def test_c19_comment_commands_fixture(self):
        """golden/12_regressions/c19: same guarantee on the golden regression."""
        r = check_sdc(_text("golden/12_regressions/c19_comment_commands.sdc"))
        assert r.errors == [], [str(e) for e in r.errors]
        assert not {"SDC-002", "SDC-008", "SDC-011"} & set(_codes(r))
        p = parse_sdc(_text("golden/12_regressions/c19_comment_commands.sdc"))
        assert p.clocks_count == 1

    def test_comment_value_not_read_as_delay(self):
        """HR04: the comment '… → SDC-064' must not be read as an input delay of
        64ns. The real delay is 2.0 < period 10.0 → no SDC-008, one delay."""
        r = check_sdc(_text("readiness/HR04_unconstrained_io.sdc"))
        assert "SDC-008" not in _codes(r)
        p = parse_sdc(_text("readiness/HR04_unconstrained_io.sdc"))
        assert len(p.input_delays) == 1
        assert p.input_delays[0].value == pytest.approx(2.0)

    def test_comment_case_analysis_word_not_invalid_value(self):
        """HR06: the comment 'set_case_analysis on the same pin' must not make
        'on' an invalid case value. The real issue is the 0-vs-1 contradiction
        → SDC-049 (see class 4), never SDC-011."""
        r = check_sdc(_text("readiness/HR06_contradictory_case.sdc"))
        codes = _codes(r)
        assert "SDC-011" not in codes, "legacy invalid-value from comment"
        assert "SDC-049" in codes
        p = parse_sdc(_text("readiness/HR06_contradictory_case.sdc"))
        assert len(p.case_analysis) == 2  # the two real assignments, not 3

    def test_comment_mentioning_set_input_delay_does_not_crash(self):
        """s01: the legacy validator crashed (ValueError: float('.') on the
        sentence-ending period of a comment mentioning 'set_input_delay'). Ṛta
        must return the correct finding instead."""
        r = check_sdc(_text("golden_semantic/undefined_references/s01_io_delay_undefined_clock.sdc"))
        codes = _codes(r)
        assert "SDC-046" in codes, "undefined clock must be reported"
        assert "SDC-008" not in codes  # no delay-vs-period against a ghost clock


# ══════════════════════════════════════════════════════════════════════════
# Defect class 2 — Tcl backslash continuations must join into one command
# ══════════════════════════════════════════════════════════════════════════

class TestTclContinuations:
    """The legacy validator parsed per physical line, so content on a `\\`
    continuation line was invisible: false 'missing -source' (SDC-003), false
    'no -min' (SDC-028/029), false 'missing group type' (SDC-031), truncated
    virtual clocks, and under-counted exceptions. Ṛta joins continuations."""

    def test_generated_clock_source_on_continuation(self):
        """rd03: `create_generated_clock -name div2 \\` with -source on the next
        line. Legacy fired SDC-003 'missing -source'; Ṛta must not."""
        rel = "reference_designs/rd03_generated_hierarchy/rd03_generated_hierarchy.sdc"
        r = check_sdc(_text(rel))
        assert "SDC-003" not in _codes(r)
        p = parse_sdc(_text(rel))
        assert p.clocks_count == 4
        assert sum(1 for c in p.clocks if c.is_generated) == 3

    def test_input_output_delay_min_on_continuation(self):
        """multiline_continuation_content: -min lives on a continuation line.
        Legacy fired SDC-028/029 'no -min'; Ṛta must not, and must count the
        delays exactly."""
        rel = "edge_cases/multiline_continuation_content.sdc"
        r = check_sdc(_text(rel))
        codes = _codes(r)
        assert "SDC-028" not in codes
        assert "SDC-029" not in codes
        p = parse_sdc(_text(rel))
        assert len(p.input_delays) == 1
        assert len(p.output_delays) == 1
        assert p.input_delays[0].value == pytest.approx(1.0)

    def test_clock_groups_across_continuation(self):
        """multi_clock_sync_groups: `set_clock_groups -asynchronous \\` spans
        lines. Legacy fired SDC-031 'missing exclusion type'; Ṛta must not, and
        must see the single joined group."""
        rel = "valid/multi_clock_sync_groups.sdc"
        r = check_sdc(_text(rel))
        assert "SDC-031" not in _codes(r)
        p = parse_sdc(_text(rel))
        assert p.clocks_count == 2
        assert len(p.clock_groups) == 1

    def test_false_path_across_continuation(self):
        text = (
            "create_clock -name clk -period 10.0 [get_ports clk]\n"
            "set_false_path \\\n"
            "    -from [get_ports a] \\\n"
            "    -to [get_ports b]\n"
        )
        p = parse_sdc(text)
        assert len(p.false_paths) == 1

    def test_multicycle_setup_hold_across_continuation(self):
        """A -setup and its matching -hold spanning continuations must be seen
        as one paired multicycle — no legacy SDC-021, both commands counted."""
        text = (
            "create_clock -name clk -period 10.0 [get_ports clk]\n"
            "set_multicycle_path \\\n"
            "    -setup 2 \\\n"
            "    -from [get_ports a] \\\n"
            "    -to [get_ports b]\n"
            "set_multicycle_path \\\n"
            "    -hold 1 \\\n"
            "    -from [get_ports a] \\\n"
            "    -to [get_ports b]\n"
        )
        r = check_sdc(text)
        assert "SDC-021" not in _codes(r)
        p = parse_sdc(text)
        assert len(p.multicycle_paths) == 2

    def test_generated_clock_continuation_inline(self):
        text = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "create_generated_clock -name div2 \\\n"
            "    -source [get_ports clk] \\\n"
            "    -divide_by 2 [get_pins U_DIV/clkout]\n"
        )
        r = check_sdc(text)
        assert "SDC-003" not in _codes(r)
        p = parse_sdc(text)
        assert sum(1 for c in p.clocks if c.is_generated) == 1


# ══════════════════════════════════════════════════════════════════════════
# Defect class 3 — scientific notation + Tcl variable resolution
# ══════════════════════════════════════════════════════════════════════════

class TestNumericAndVariableParsing:
    """Legacy: `1.0e1` read as period 1.0 (false SDC-008/009 on RDIF04) and
    `$VAR` values invisible (SDC-008 missed on RDIF05 / c08 / tcl_variables).
    Ṛta parses scientific notation and resolves variables before value checks."""

    def test_scientific_notation_parsed_correctly(self):
        """RDIF04: period 1.0e1 = 10.0, input delay 1.1e1 = 11.0, output 3.0.
        SDC-008 fires with the TRUE values; SDC-009 must NOT (3.0 < 10.0)."""
        rel = "readiness_diff/RDIF04_cur.sdc"
        r = check_sdc(_text(rel))
        codes = _codes(r)
        assert "SDC-008" in codes
        assert "SDC-009" not in codes
        msg = next(i.msg for i in r.issues if i.code == "SDC-008")
        assert "11.0ns" in msg and "period 10.0ns" in msg

    def test_variable_period_resolved_for_delay_check(self):
        """RDIF05: `set PERIOD 10.0` + `-period $PERIOD` + delay 11.0 → SDC-008
        after resolution (the legacy validator missed this entirely)."""
        rel = "readiness_diff/RDIF05_base.sdc"
        r = check_sdc(_text(rel))
        assert "SDC-008" in _codes(r)

    def test_golden_c08_var_period(self):
        """c08: $CLK_PERIOD=2.5, $IN_DLY=6.0 → SDC-008 (6.0 >= 2.5)."""
        rel = "golden/04_variables/c08_var_period.sdc"
        r = check_sdc(_text(rel))
        assert "SDC-008" in _codes(r)

    def test_tcl_variables_fixture(self):
        """tcl_variables: 6.0 (via $IN_DLY) >= period 5.0 → SDC-008."""
        rel = "edge_cases/tcl_variables.sdc"
        r = check_sdc(_text(rel))
        assert "SDC-008" in _codes(r)


# ══════════════════════════════════════════════════════════════════════════
# Defect class 4 — dedicated finding codes must stay dedicated
# ══════════════════════════════════════════════════════════════════════════

class TestFindingClassification:
    """The legacy validator mis-coded findings: undefined master clock as
    SDC-003, undefined clock in I/O delay as SDC-008, contradictory case
    analysis as SDC-011. Ṛta uses the dedicated SDC-047 / SDC-046 / SDC-049."""

    def test_undefined_master_clock_is_sdc047(self):
        """s02: `-master_clock ghost_clk` → SDC-047, never the legacy SDC-003."""
        rel = "golden_semantic/undefined_references/s02_generated_undefined_master.sdc"
        r = check_sdc(_text(rel))
        codes = _codes(r)
        assert "SDC-047" in codes
        assert "SDC-003" not in codes

    def test_undefined_clock_in_io_delay_is_sdc046(self):
        """RDIF06 / RDIF22: `-clock ghost_clk` on an input delay → SDC-046,
        never the legacy SDC-008 (a delay-vs-period check against a ghost
        clock is meaningless)."""
        for rel in ("readiness_diff/RDIF06_cur.sdc", "readiness_diff/RDIF22_base.sdc"):
            r = check_sdc(_text(rel))
            codes = _codes(r)
            assert "SDC-046" in codes, rel
            assert "SDC-008" not in codes, rel

    def test_contradictory_case_analysis_is_sdc049(self):
        """HR06: 0 then 1 on the same pin → SDC-049, never the legacy SDC-011."""
        r = check_sdc(_text("readiness/HR06_contradictory_case.sdc"))
        codes = _codes(r)
        assert "SDC-049" in codes
        assert "SDC-011" not in codes

    def test_clock_on_data_port_is_sdc007(self):
        """c22: create_clock on data_in → SDC-007 (the dedicated data-port
        check), not the legacy SDC-024."""
        rel = "golden/12_regressions/c22_data_port_sdc007.sdc"
        r = check_sdc(_text(rel))
        codes = _codes(r)
        assert "SDC-007" in codes
        assert "SDC-024" not in codes


# ══════════════════════════════════════════════════════════════════════════
# Defect class 5 — clock relationship inference
# ══════════════════════════════════════════════════════════════════════════

class TestClockRelationshipInference:
    """Legacy could not trace generated-clock master chains or see declared
    groups, so it emitted false SDC-062 mismatches on valid files. Ṛta infers
    the correct relationships; the known-good mismatch counts must hold."""

    def test_generated_clock_chain_all_synchronous(self):
        """clk → div2 → div4: every pair is synchronous, zero mismatches
        (legacy reported clk/div4 as asynchronous SDC-062)."""
        rel = "clock_relations/generated_clock_chain.sdc"
        cr = analyze_clock_relations(_text(rel))
        assert len(cr.clocks) == 3
        assert len(cr.pairs) == 3
        assert len(cr.mismatches) == 0, [str(m) for m in cr.mismatches]
        rels = {(p.clock_a, p.clock_b): p.inferred_relation for p in cr.pairs}
        assert rels[("clk", "div2")] == "synchronous"
        assert rels[("clk", "div4")] == "synchronous"
        assert rels[("div2", "div4")] == "synchronous"

    def test_three_clocks_mixed_declared_groups(self):
        """Declared groups honored: same-port pair physically_exclusive, others
        asynchronous, zero mismatches (legacy reported 2 false SDC-062)."""
        rel = "clock_relations/three_clocks_mixed.sdc"
        cr = analyze_clock_relations(_text(rel))
        assert len(cr.clocks) == 3
        assert len(cr.pairs) == 3
        assert len(cr.mismatches) == 0, [str(m) for m in cr.mismatches]
        rels = {(p.clock_a, p.clock_b): p.inferred_relation for p in cr.pairs}
        assert rels[("clk_a", "clk_b")] == "physically_exclusive"
        assert rels[("clk_a", "clk_c")] == "asynchronous"
        assert rels[("clk_b", "clk_c")] == "asynchronous"

    def test_full_featured_generated_pairs_synchronous(self):
        """full_featured: clk_sys vs its two generated clocks are synchronous;
        clk_io vs the generated clocks asynchronous; zero mismatches (legacy
        reported 4 false SDC-062, calling clk_sys/clk_sys_div2 async)."""
        rel = "valid/full_featured.sdc"
        cr = analyze_clock_relations(_text(rel))
        assert len(cr.clocks) == 4
        assert len(cr.pairs) == 6
        assert len(cr.mismatches) == 0, [str(m) for m in cr.mismatches]
        rels = {(p.clock_a, p.clock_b): p.inferred_relation for p in cr.pairs}
        assert rels[("clk_sys", "clk_sys_div2")] == "synchronous"
        assert rels[("clk_sys", "clk_sys_div4")] == "synchronous"
        assert rels[("clk_io", "clk_sys_div2")] == "asynchronous"

    def test_real_design_full_generated_pairs_synchronous(self):
        """real_design_full: 7 clocks / 21 pairs. The three generated-clock
        pairs (clk_core/div2, clk_core/div4, div2/div4) are synchronous and
        must NOT be flagged (legacy: 21 findings). The remaining 18 findings
        are SDC-062 MISSING CONSTRAINTS — per the P1-2 semantic model they
        live in ``missing_constraints``, never in ``mismatches``, and
        stats.mismatches == len(mismatches) == 0."""
        rel = "regression/real_design_full.sdc"
        cr = analyze_clock_relations(_text(rel))
        assert len(cr.clocks) == 7
        assert len(cr.pairs) == 21
        # P1-2: mismatches are warning-severity conflicts only; SDC-062
        # findings are missing constraints — each stats key equals its list.
        assert len(cr.mismatches) == 0, [str(m) for m in cr.mismatches]
        assert len(cr.missing_constraints) == 18, len(cr.missing_constraints)
        assert cr.stats["mismatches"] == len(cr.mismatches)
        assert cr.stats["missing"] == len(cr.missing_constraints)
        assert all(m.code == "SDC-062" for m in cr.missing_constraints)
        rels = {(p.clock_a, p.clock_b): p.inferred_relation for p in cr.pairs}
        assert rels[("clk_core", "clk_core_div2")] == "synchronous"
        assert rels[("clk_core", "clk_core_div4")] == "synchronous"
        assert rels[("clk_core_div2", "clk_core_div4")] == "synchronous"
