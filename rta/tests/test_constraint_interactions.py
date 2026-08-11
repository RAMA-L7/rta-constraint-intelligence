"""
Phase 10 — constraint_interactions.py unit tests.

Covers exact duplicates, legal multiples, overrides, provable max<min
conflicts, timing-exception overlaps (object overlap ≠ path overlap), variable
and scientific-notation equivalence, dual-line provenance, and the
SDC-only / design-aware behaviors.
"""

import pytest

from constraint_interactions import (
    analyze_interactions, extract_records,
    EXACT_DUPLICATE, OVERRIDE, DEFINITE_CONFLICT, POSSIBLE_CONFLICT,
)


def _codes(sdc):
    return [f["code"] for f in analyze_interactions(sdc).findings]


def _cats(sdc):
    return [f["category"] for f in analyze_interactions(sdc).findings]


class TestExactDuplicates:
    def test_identical_input_delay(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n")
        assert EXACT_DUPLICATE in _cats(sdc)
        assert _codes(sdc) == ["SDC-067"]

    def test_identical_output_delay(self):
        sdc = ("set_output_delay -max 2.0 -clock c [get_ports dout]\n"
               "set_output_delay -max 2.0 -clock c [get_ports dout]\n")
        assert _codes(sdc) == ["SDC-067"]

    def test_identical_false_path(self):
        sdc = ("set_false_path -from [get_ports a] -to [get_ports b]\n"
               "set_false_path -from [get_ports a] -to [get_ports b]\n")
        assert _codes(sdc) == ["SDC-067"]

    def test_identical_uncertainty(self):
        sdc = ("set_clock_uncertainty -setup 0.1 -hold 0.05 [get_clocks c]\n"
               "set_clock_uncertainty -setup 0.1 -hold 0.05 [get_clocks c]\n")
        # The whole command (setup AND hold) is restated verbatim → ONE
        # redundant command pair, one finding (per-pair dedup, anti-flooding).
        assert _codes(sdc).count("SDC-067") == 1

    def test_anchor_after_mode_mismatch(self):
        # Regression: A='-max 2.0 -min 0.5', B='-max 2.0', C='-max 2.0'.
        # B is a partial re-specification of A (NOT a duplicate), but C is an
        # exact duplicate of B and must still be detected — the duplicate
        # anchor must advance past the mode-mismatched record.
        sdc = ("set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n")
        assert _codes(sdc).count("SDC-067") == 1

    def test_separate_setup_hold_duplicates_two_findings(self):
        # Two DISTINCT redundant command pairs → two findings, each pair
        # deduped internally but never collapsed across pairs.
        sdc = ("set_clock_uncertainty -setup 0.1 [get_clocks c]\n"
               "set_clock_uncertainty -setup 0.1 [get_clocks c]\n"
               "set_clock_uncertainty -hold 0.05 [get_clocks c]\n"
               "set_clock_uncertainty -hold 0.05 [get_clocks c]\n")
        assert _codes(sdc).count("SDC-067") == 2

    def test_identical_case_analysis_not_double_reported(self):
        # SDC-049 owns case-analysis contradictions; same-value repeats are
        # harmless and intentionally NOT flagged by the interaction engine.
        sdc = ("set_case_analysis 0 [get_ports mode]\n"
               "set_case_analysis 0 [get_ports mode]\n")
        assert _codes(sdc) == []


class TestLegalMultiples:
    def test_min_max_pair_legal(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -min 0.5 -clock c [get_ports din]\n")
        assert _codes(sdc) == []

    def test_rise_fall_pair_legal(self):
        sdc = ("set_input_delay -max 2.0 -rise -clock c [get_ports din]\n"
               "set_input_delay -max 2.5 -fall -clock c [get_ports din]\n")
        assert _codes(sdc) == []

    def test_setup_hold_legal(self):
        sdc = ("set_clock_uncertainty -setup 0.1 [get_clocks c]\n"
               "set_clock_uncertainty -hold 0.05 [get_clocks c]\n")
        assert _codes(sdc) == []

    def test_different_ports_legal(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports dout]\n")
        assert _codes(sdc) == []

    def test_different_clocks_legal(self):
        sdc = ("set_input_delay -max 2.0 -clock c1 [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c2 [get_ports din]\n")
        assert _codes(sdc) == []

    def test_add_delay_accumulation_legal(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din] -add_delay\n"
               "set_input_delay -max 3.0 -clock c [get_ports din] -add_delay\n")
        assert _codes(sdc) == []

    def test_max_min_delay_window_legal(self):
        sdc = ("set_max_delay 10 -from [get_ports a] -to [get_ports b]\n"
               "set_min_delay 5 -from [get_ports a] -to [get_ports b]\n")
        assert _codes(sdc) == []

    def test_clock_groups_plus_false_path_not_flagged(self):
        # Redundant but common valid practice — never a finding.
        sdc = ("set_clock_groups -asynchronous -group [get_clocks a] -group [get_clocks b]\n"
               "set_false_path -from [get_clocks a] -to [get_clocks b]\n")
        assert _codes(sdc) == []

    def test_duplicate_clock_definition_not_flagged(self):
        # SDC-002 owns duplicate clock names.
        sdc = ("create_clock -name c -period 5.0 [get_ports clk]\n"
               "create_clock -name c -period 5.0 [get_ports clk]\n")
        assert _codes(sdc) == []


class TestOverrides:
    def test_input_delay_override(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 3.0 -clock c [get_ports din]\n")
        assert OVERRIDE in _cats(sdc)
        assert _codes(sdc) == ["SDC-068"]

    def test_override_dual_line(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 3.0 -clock c [get_ports din]\n")
        f = analyze_interactions(sdc).findings[0]
        assert f["line"] == 2 and f["line2"] == 1

    def test_output_delay_override(self):
        sdc = ("set_output_delay -max 2.0 -clock c [get_ports dout]\n"
               "set_output_delay -max 1.0 -clock c [get_ports dout]\n")
        assert _codes(sdc) == ["SDC-068"]

    def test_override_skips_none_value_last(self):
        # Malformed trailing '-max' with no number must not produce an
        # "overridden by value None" finding.
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max -clock c [get_ports din]\n")
        assert _codes(sdc) == []

    def test_electrical_override(self):
        sdc = ("set_load 0.05 [get_ports dout]\n"
               "set_load 0.08 [get_ports dout]\n")
        assert _codes(sdc) == ["SDC-068"]

    def test_multicycle_repeat_not_override(self):
        # Repeated MCP with a different cycle count is high false-positive risk
        # (edge/phase variants) — only exact duplicates are reported.
        sdc = ("set_multicycle_path -setup 2 -from [get_ports a] -to [get_ports b]\n"
               "set_multicycle_path -setup 3 -from [get_ports a] -to [get_ports b]\n")
        assert _codes(sdc) == []


class TestDefiniteConflicts:
    def test_max_less_than_min(self):
        sdc = ("set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
               "set_min_delay 10 -from [get_ports a] -to [get_ports b]\n")
        assert DEFINITE_CONFLICT in _cats(sdc)
        assert _codes(sdc) == ["SDC-069"]

    def test_max_equal_min_legal(self):
        sdc = ("set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
               "set_min_delay 5 -from [get_ports a] -to [get_ports b]\n")
        assert _codes(sdc) == []

    def test_different_endpoints_no_conflict(self):
        sdc = ("set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
               "set_min_delay 10 -from [get_ports x] -to [get_ports y]\n")
        assert _codes(sdc) == []

    def test_wildcard_endpoint_not_provable(self):
        sdc = ("set_max_delay 5 -from [get_ports a] -to [get_ports *]\n"
               "set_min_delay 10 -from [get_ports a] -to [get_ports *]\n")
        # Wildcards cannot be proven identical without design context.
        assert _codes(sdc) == []


class TestExceptionInteractions:
    def test_fp_mcp_overlap(self):
        sdc = ("set_false_path -from [get_ports a] -to [get_ports b]\n"
               "set_multicycle_path 2 -from [get_ports a] -to [get_ports b]\n")
        assert POSSIBLE_CONFLICT in _cats(sdc)
        assert _codes(sdc) == ["SDC-070"]
        f = analyze_interactions(sdc).findings[0]
        assert f["line"] == 2 and f["line2"] == 1

    def test_fp_after_mcp_line_convention(self):
        # Regression: when the false path appears AFTER the other exception,
        # line must still be the LATER command and line2 the EARLIER
        # (SDC-049 convention), independent of which command is the fp.
        sdc = ("set_multicycle_path 2 -from [get_ports a] -to [get_ports b]\n"
               "set_false_path -from [get_ports a] -to [get_ports b]\n")
        assert _codes(sdc) == ["SDC-070"]
        f = analyze_interactions(sdc).findings[0]
        assert f["line"] == 2 and f["line2"] == 1

    def test_fp_max_delay_overlap(self):
        sdc = ("set_false_path -from [get_ports a] -to [get_ports b]\n"
               "set_max_delay 5 -from [get_ports a] -to [get_ports b]\n")
        assert _codes(sdc) == ["SDC-070"]

    def test_disjoint_objects_no_finding(self):
        sdc = ("set_false_path -from [get_ports a] -to [get_ports b]\n"
               "set_multicycle_path 2 -from [get_ports x] -to [get_ports y]\n")
        assert _codes(sdc) == []

    def test_partial_overlap_no_finding(self):
        # Same -from but different -to → no path overlap provable.
        sdc = ("set_false_path -from [get_ports a] -to [get_ports b]\n"
               "set_multicycle_path 2 -from [get_ports a] -to [get_ports z]\n")
        assert _codes(sdc) == []

    def test_wildcard_not_provable(self):
        sdc = ("set_false_path -from [get_ports a] -to [get_ports *]\n"
               "set_multicycle_path 2 -from [get_ports a] -to [get_ports *]\n")
        assert _codes(sdc) == []


class TestSemanticEquivalence:
    def test_scientific_notation_duplicate(self):
        sdc = ("set_input_delay -max 2.5e-1 -clock c [get_ports din]\n"
               "set_input_delay -max 0.25 -clock c [get_ports din]\n")
        assert _codes(sdc) == ["SDC-067"]

    def test_variable_derived_duplicate(self):
        sdc = ("set D 2.0\n"
               "set_input_delay -max $D -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n")
        assert _codes(sdc) == ["SDC-067"]

    def test_multiline_duplicate(self):
        sdc = ("set_input_delay -max 2.0 \\\n"
               "  -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n")
        assert _codes(sdc) == ["SDC-067"]

    def test_braced_collection_duplicate(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports {din dout}]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din dout]\n")
        assert _codes(sdc) == ["SDC-067"]

    def test_option_reorder_duplicate(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay 2.0 -clock c -max [get_ports din]\n")
        assert _codes(sdc) == ["SDC-067"]


class TestNoCrash:
    def test_empty(self):
        assert analyze_interactions("").findings == []

    def test_unsupported_commands_inert(self):
        sdc = ("foreach clk {a b} { puts $clk }\n"
               "exec rm -rf /\n"
               "source evil.tcl\n")
        assert analyze_interactions(sdc).findings == []

    def test_malformed(self):
        sdc = "set_input_delay -max\nset_input_delay\n"
        assert analyze_interactions(sdc).findings == []


class TestSummary:
    def test_summary_counts(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -min 0.5 -clock c [get_ports din]\n")
        s = analyze_interactions(sdc).summary()
        assert s["exact_duplicates"] == 1
        assert s["constraints_analyzed"] == 3
        assert s["confidence_is_not_correctness"] is True

    def test_to_dict_machine_readable(self):
        sdc = ("set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n")
        d = analyze_interactions(sdc).to_dict()
        assert "summary" in d and "findings" in d
        f = d["findings"][0]
        assert {"category", "code", "severity", "msg", "line", "line2"} <= set(f)


class TestCheckerIntegration:
    def test_issues_appended_with_dual_line(self):
        from checker import check_sdc
        sdc = ("create_clock -name c -period 10.0 [get_ports clk]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n")
        r = check_sdc(sdc)
        dups = [i for i in r.issues if i.code == "SDC-067"]
        assert dups and dups[0].line == 3 and dups[0].line2 == 2
        assert r.interactions["summary"]["exact_duplicates"] == 1

    def test_sdc_only_and_design_aware_both_run(self):
        from checker import check_sdc
        sdc = ("create_clock -name c -period 10.0 [get_ports clk]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n"
               "set_input_delay -max 2.0 -clock c [get_ports din]\n")
        r1 = check_sdc(sdc)
        r2 = check_sdc(sdc, context=None)
        assert r1.interactions and r2.interactions
        assert r1.interactions["summary"]["exact_duplicates"] == \
               r2.interactions["summary"]["exact_duplicates"]
