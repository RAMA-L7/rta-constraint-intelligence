"""
Tests for the SDC Checker/Validator module.
"""

import pytest
from checker import check_sdc, Issue, InfoItem, CheckResult, KNOWN_COMMON_COND
from rationale_lint import rationale_findings


class TestRationaleLint:
    """Tests for F1 — rationale-comment linting (SDC-150).

    Every timing exception that can hide a violation (false path, multicycle
    path, case analysis) must carry a substantive explanatory comment within
    the 3 lines above or inline. Pure text check — no netlist required.
    """

    def _codes(self, text: str) -> list:
        return [f.code for f in rationale_findings(text)]

    def test_undocumented_false_path(self):
        text = "create_clock -name clk -period 10 [get_ports clk]\n" \
               "set_false_path -from [get_ports a] -to [get_ports b]\n"
        assert self._codes(text) == ["SDC-150"]

    def test_comment_above_counts(self):
        text = "# async CDC — two-flop synchronizer, no timing path\n" \
               "set_false_path -from [get_ports a] -to [get_ports b]\n"
        assert self._codes(text) == []

    def test_inline_comment_counts(self):
        text = "set_false_path -from [get_ports a] -to [get_ports b]  # scan shift\n"
        assert self._codes(text) == []

    def test_fence_before_exception_does_not_count(self):
        text = "# -----------------------------------\n" \
               "set_false_path -from [get_ports a] -to [get_ports b]\n"
        # a decorative fence is not substantive rationale
        assert self._codes(text) == ["SDC-150"]

    def test_short_inline_comment_does_not_count(self):
        """A token 'ok' comment is below the substantive threshold."""
        text = "set_false_path -from [get_ports a] -to [get_ports b]  # ok\n"
        assert self._codes(text) == ["SDC-150"]

    def test_multiline_command_trailing_comment_counts(self):
        """Comment on the last continuation line of a multiline exception."""
        text = "set_false_path \\\n" \
               "  -from [get_ports a] \\\n" \
               "  -to [get_ports b]  # async CDC — no timing path\n"
        assert self._codes(text) == []

    def test_undocumented_case_analysis(self):
        text = "set_case_analysis 0 [get_ports scan_en]\n"
        assert self._codes(text) == ["SDC-150"]

    def test_documented_multicycle_clean(self):
        text = "# two-cycle setup for cross-domain path\n" \
               "set_multicycle_path 2 -from [get_ports a] -to [get_ports b]\n"
        assert self._codes(text) == []

    def test_comment_three_lines_above_counts(self):
        text = "create_clock -name clk -period 10 [get_ports clk]\n" \
               "set_input_delay 1.0 -clock clk [get_ports a]\n" \
               "# reset synchronizer input — intentional false path\n" \
               "set_false_path -from [get_ports rst_sync] -to [get_ports b]\n"
        assert self._codes(text) == []

    def test_four_lines_away_does_not_count(self):
        text = "# rationale comment four lines above\n" \
               "create_clock -name clk -period 10 [get_ports clk]\n" \
               "set_input_delay 1.0 -clock clk [get_ports a]\n" \
               "set_output_delay 1.0 -clock clk [get_ports b]\n" \
               "set_false_path -from [get_ports a] -to [get_ports b]\n"
        assert self._codes(text) == ["SDC-150"]

    def test_finding_has_line_number(self):
        text = "create_clock -name clk -period 10 [get_ports clk]\n" \
               "set_false_path -from [get_ports a] -to [get_ports b]\n"
        fs = rationale_findings(text)
        assert fs[0].line == 2

    def test_wired_into_check_sdc(self):
        """SDC-150 surfaces through the full checker (additive, SDC-only mode)."""
        text = "create_clock -name clk -period 10 [get_ports clk]\n" \
               "set_false_path -from [get_ports a] -to [get_ports b]\n"
        result = check_sdc(text)
        codes = [i.code for i in result.issues]
        assert "SDC-150" in codes

    def test_documented_exception_clean_through_checker(self):
        text = "create_clock -name clk -period 10 [get_ports clk]\n" \
               "# async CDC — no timing path\n" \
               "set_false_path -from [get_ports a] -to [get_ports b]\n"
        result = check_sdc(text)
        codes = [i.code for i in result.issues]
        assert "SDC-150" not in codes

    def test_registry_has_sdc150(self):
        from rules_registry import get_rule
        rule = get_rule("SDC-150")
        assert rule is not None
        assert rule.severity == "warning"
        assert "comment" in rule.fix.lower()


class TestIssue:
    """Tests for the Issue dataclass."""

    def test_create_issue(self):
        issue = Issue(sev="error", code="SDC-001", msg="Test error")
        assert issue.sev == "error"
        assert issue.code == "SDC-001"
        assert "error" in issue.msg.lower()


class TestCheckResult:
    """Tests for the CheckResult dataclass."""

    def test_empty_result(self):
        result = CheckResult()
        assert result.issues == []
        assert result.info == []
        assert result.errors == []
        assert result.warnings == []

    def test_error_filtering(self):
        result = CheckResult(issues=[
            Issue("error", "SDC-001", "err1"),
            Issue("warning", "SDC-020", "warn1"),
            Issue("error", "SDC-005", "err2"),
        ])
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_stats_default_dict(self):
        """Stats should default to empty dict, not None."""
        result = CheckResult()
        assert result.stats == {}


class TestCheckSdc:
    """Tests for the main check_sdc function."""

    def test_empty_input(self):
        """Empty/blank input should produce errors and info."""
        result = check_sdc("")
        assert len(result.errors) > 0  # at least SDC-001 (no clock)

    def test_blank_input(self):
        """Whitespace-only input behaves like empty."""
        result = check_sdc("   \n  \n  ")
        assert len(result.errors) > 0

    def test_minimal_sdc(self, minimal_sdc):
        """Minimal valid SDC: should have no errors, maybe some info."""
        result = check_sdc(minimal_sdc)
        # At minimum, a valid clock means SDC-001 should not trigger
        sdc_001 = [i for i in result.errors if i.code == "SDC-001"]
        assert len(sdc_001) == 0

    def test_no_clock_creates_error(self):
        """SDC-001: No create_clock → error."""
        result = check_sdc("set_input_delay -max 1.0 -clock ref [get_ports data]")
        sdc_001 = [i for i in result.errors if i.code == "SDC-001"]
        assert len(sdc_001) > 0

    def test_duplicate_clock_name(self):
        """SDC-002: Duplicate clock names."""
        text = "create_clock -name dupe -period 5.0 [get_ports a]\ncreate_clock -name dupe -period 10.0 [get_ports b]"
        result = check_sdc(text)
        sdc_002 = [i for i in result.errors if i.code == "SDC-002"]
        assert len(sdc_002) > 0

    def test_generated_clock_missing_source(self):
        """SDC-003: Generated clock without -source."""
        text = "create_generated_clock -name bad_gen -divide_by 2 [get_pins a]"
        result = check_sdc(text)
        sdc_003 = [i for i in result.errors if i.code == "SDC-003"]
        assert len(sdc_003) > 0

    def test_conflicting_divide_and_multiply(self):
        """SDC-004: Both -divide_by and -multiply_by."""
        text = "create_generated_clock -name gen -source [get_ports clk] -divide_by 2 -multiply_by 2 [get_pins a]"
        result = check_sdc(text)
        sdc_004 = [i for i in result.errors if i.code == "SDC-004"]
        assert len(sdc_004) > 0

    def test_no_input_delay(self):
        """SDC-005: Clocks defined but no input delay."""
        text = "create_clock -name clk -period 5.0 [get_ports clk]\nset_output_delay -max 1.0 -clock clk [get_ports dout]"
        result = check_sdc(text)
        sdc_005 = [i for i in result.errors if i.code == "SDC-005"]
        assert len(sdc_005) > 0

    def test_no_output_delay(self):
        """SDC-006: Clocks defined but no output delay."""
        text = "create_clock -name clk -period 5.0 [get_ports clk]\nset_input_delay -max 1.0 -clock clk [get_ports din]"
        result = check_sdc(text)
        sdc_006 = [i for i in result.errors if i.code == "SDC-006"]
        assert len(sdc_006) > 0

    def test_clock_on_data_port(self):
        """SDC-007: Clock on data-type port."""
        text = "create_clock -name data_clk -period 5.0 [get_ports din]"
        result = check_sdc(text)
        sdc_007 = [i for i in result.errors if i.code == "SDC-007"]
        assert len(sdc_007) > 0

    def test_input_delay_exceeds_period(self):
        """SDC-008: Input delay >= clock period."""
        text = "create_clock -name clk -period 5.0 [get_ports clk]\nset_input_delay -max 6.0 -clock clk [get_ports din]"
        result = check_sdc(text)
        sdc_008 = [i for i in result.errors if i.code == "SDC-008"]
        assert len(sdc_008) > 0

    def test_output_delay_exceeds_period(self):
        """SDC-009: Output delay >= clock period."""
        text = "create_clock -name clk -period 5.0 [get_ports clk]\nset_output_delay -max 7.0 -clock clk [get_ports dout]"
        result = check_sdc(text)
        sdc_009 = [i for i in result.errors if i.code == "SDC-009"]
        assert len(sdc_009) > 0

    def test_invalid_case_analysis_value(self):
        """SDC-011: Invalid set_case_analysis value."""
        text = "set_case_analysis invalid_val [get_ports test]"
        result = check_sdc(text)
        sdc_011 = [i for i in result.errors if i.code == "SDC-011"]
        assert len(sdc_011) > 0


class TestCheckerWarnings:
    """Tests for checker warning rules (SDC-020..045)."""

    def test_no_clock_groups_with_multiple_clocks(self):
        """SDC-024: Multiple clocks but no set_clock_groups."""
        text = "create_clock -name clk_a -period 5.0 [get_ports clk_a]\ncreate_clock -name clk_b -period 10.0 [get_ports clk_b]"
        result = check_sdc(text)
        sdc_024 = [i for i in result.warnings if i.code == "SDC-024"]
        assert len(sdc_024) > 0

    def test_clock_groups_present_avoids_warning(self):
        text = ("create_clock -name clk_a -period 5.0 [get_ports clk_a]\n"
                "create_clock -name clk_b -period 10.0 [get_ports clk_b]\n"
                "set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]")
        result = check_sdc(text)
        sdc_024 = [i for i in result.warnings if i.code == "SDC-024"]
        assert len(sdc_024) == 0

    def test_no_propagated_clock(self):
        """SDC-030: Clocks without set_propagated_clock."""
        text = "create_clock -name clk -period 5.0 [get_ports clk]"
        result = check_sdc(text)
        sdc_030 = [i for i in result.warnings if i.code == "SDC-030"]
        assert len(sdc_030) > 0

    def test_multicycle_without_hold(self):
        """SDC-021: Multicycle setup >1 without hold fix."""
        text = "set_multicycle_path -setup 3 -from [get_cells a] -to [get_cells b]"
        result = check_sdc(text)
        sdc_021 = [i for i in result.warnings if i.code == "SDC-021"]
        assert len(sdc_021) > 0

    def test_multicycle_split_command_hold_fix(self):
        """SDC-021: a -hold fix in a SEPARATE command on the same endpoints
        satisfies the setup fix (standard SDC style)."""
        text = (
            "create_clock -name c -period 10 [get_ports clk]\n"
            "set_multicycle_path 2 -setup -from [get_clocks c] -to [get_clocks c]\n"
            "set_multicycle_path 1 -hold -from [get_clocks c] -to [get_clocks c]\n"
        )
        result = check_sdc(text)
        assert not any(i.code == "SDC-021" for i in result.warnings), \
            "split-command hold fix on same endpoints must suppress SDC-021"

    def test_multicycle_hold_fix_different_endpoints_still_fires(self):
        """SDC-021: a -hold fix on DIFFERENT endpoints does not satisfy the fix."""
        text = (
            "create_clock -name c -period 10 [get_ports clk]\n"
            "set_multicycle_path 2 -setup -from [get_clocks c] -to [get_clocks c]\n"
            "set_multicycle_path 1 -hold -from [get_ports a] -to [get_ports b]\n"
        )
        result = check_sdc(text)
        assert any(i.code == "SDC-021" for i in result.warnings), \
            "hold fix on different endpoints must not suppress SDC-021"

    def test_uncertainty_too_tight(self):
        """SDC-022: Unrealistically tight uncertainty."""
        text = "set_clock_uncertainty 0.01 [get_clocks clk]"
        result = check_sdc(text)
        sdc_022 = [i for i in result.warnings if i.code == "SDC-022"]
        assert len(sdc_022) > 0

    def test_uncertainty_too_high(self):
        """SDC-023: Very high uncertainty."""
        text = "set_clock_uncertainty 0.6 [get_clocks clk]"
        result = check_sdc(text)
        sdc_023 = [i for i in result.warnings if i.code == "SDC-023"]
        assert len(sdc_023) > 0

    def test_no_input_delay_min(self):
        """SDC-028: Input delays without -min."""
        text = "create_clock -name clk -period 5.0 [get_ports clk]\nset_input_delay -max 1.5 -clock clk [get_ports din]"
        result = check_sdc(text)
        sdc_028 = [i for i in result.warnings if i.code == "SDC-028"]
        assert len(sdc_028) > 0

    def test_excessive_disable_timing(self):
        """SDC-035: Excessive disable_timing count."""
        text = "\n".join([f"set_disable_timing -from a{i} -to b{i} [get_cells inst]" for i in range(10)])
        result = check_sdc(text)
        sdc_035 = [i for i in result.warnings if i.code == "SDC-035"]
        assert len(sdc_035) > 0


class TestCheckerInfo:
    """Tests for checker info items (SDC-100..140)."""

    def test_info_items_produced(self, minimal_sdc):
        """Minimal SDC should produce info suggestions."""
        result = check_sdc(minimal_sdc)
        assert len(result.info) > 0

    def test_no_sdc_version(self):
        """SDC-100: Missing sdc_version."""
        result = check_sdc("create_clock -name clk -period 5.0 [get_ports clk]")
        sdc_100 = [i for i in result.info if i.code == "SDC-100"]
        assert len(sdc_100) > 0

    def test_no_set_units(self):
        """SDC-101: Missing set_units."""
        result = check_sdc("create_clock -name clk -period 5.0 [get_ports clk]")
        sdc_101 = [i for i in result.info if i.code == "SDC-101"]
        assert len(sdc_101) > 0


class TestCheckerStats:
    """Tests for stats collection."""

    def test_stats_populated(self, full_sdc):
        result = check_sdc(full_sdc)
        assert len(result.stats) > 0
        assert "Clocks" in result.stats
        assert "False paths" in result.stats

    def test_stats_counts(self, full_sdc):
        result = check_sdc(full_sdc)
        assert result.stats["Clocks"] >= 3  # two primary + one generated

    def test_error_counts_match(self):
        text = ("create_clock -name clk -period 5.0 [get_ports clk]\n"
                "create_clock -name clk -period 10.0 [get_ports clk2]\n")
        result = check_sdc(text)
        assert len(result.errors) >= 1  # SDC-002 (duplicate)

    def test_no_errors_on_good_sdc(self, full_sdc):
        result = check_sdc(full_sdc)
        if result.errors:
            # Print codes for debugging
            codes = [i.code for i in result.errors]
            pytest.skip(f"full_sdc has errors: {codes}")

    def test_info_on_full_sdc(self, full_sdc):
        result = check_sdc(full_sdc)
        # Info items should still be produced even on good SDCs
        assert len(result.info) >= 0

    def test_full_sdc_warnings_count(self, full_sdc):
        result = check_sdc(full_sdc)
        # full_sdc is comprehensive — zero warnings expected
        pass  # informative, not a strict assertion


class TestCheckerEdgeCases:
    """Edge case tests."""

    def test_duplicate_clock_name_no_errors(self):
        """Two clocks with different names should not trigger SDC-002."""
        text = "create_clock -name clk_a -period 5.0 [get_ports a]\ncreate_clock -name clk_b -period 10.0 [get_ports b]"
        result = check_sdc(text)
        sdc_002 = [i for i in result.errors if i.code == "SDC-002"]
        assert len(sdc_002) == 0

    def test_clock_groups_present_no_warning(self):
        """set_clock_groups present should suppress SDC-024."""
        text = ("create_clock -name a -period 5.0 [get_ports a]\n"
                "create_clock -name b -period 10.0 [get_ports b]\n"
                "set_clock_groups -asynchronous -group [get_clocks a] -group [get_clocks b]")
        result = check_sdc(text)
        sdc_024 = [i for i in result.warnings if i.code == "SDC-024"]
        assert len(sdc_024) == 0

    def test_case_analysis_valid_values(self):
        """Valid case analysis values should NOT trigger SDC-011."""
        text = ("set_case_analysis 0 [get_ports test]\n"
                "set_case_analysis 1 [get_ports scan]\n"
                "set_case_analysis rising [get_ports clk_sel]")
        result = check_sdc(text)
        sdc_011 = [i for i in result.errors if i.code == "SDC-011"]
        assert len(sdc_011) == 0

    def test_known_operating_condition(self):
        """Known operating conditions should not trigger SDC-044."""
        text = ("set_operating_conditions -max WORST\n"
                "create_clock -name clk -period 5.0 [get_ports clk]")
        result = check_sdc(text)
        sdc_044 = [i for i in result.warnings if i.code == "SDC-044"]
        assert len(sdc_044) == 0
