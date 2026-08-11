"""
Phase 7 — Support-boundary (analysis-coverage / trust model) tests.

Verifies that the validator distinguishes "no problems found" from
"everything was fully analyzed", and that limitations are always visible
in the machine-readable scope attached to CheckResult.
"""

import pytest

from checker import check_sdc
from support_boundary import (
    analyze_scope, AnalysisScope, ConstructStatus,
    RECOGNIZED_COMMANDS, STANDARD_OPTIONS, INTERPRETED_OPTIONS,
)


class TestScopeStatus:
    """Trust status precedence and classification."""

    def test_fully_analyzed_status(self):
        # Only supported constructs, no netlist refs, no ignored options.
        s = analyze_scope("set sdc_version 2.2\n"
                          "set_units -time ns -capacitance pF\n")
        assert s.status == "VALIDATED"
        assert s.fully_analyzed == 2
        assert s.commands_found == 2

    def test_netlist_required_status(self):
        s = analyze_scope("create_clock -name clk -period 5.0 [get_ports clk]\n")
        assert s.status == "NETLIST_REQUIRED"
        assert s.netlist_required == 1

    def test_partial_when_ignored_option(self):
        # -comment is standard SDC but not value-analyzed by any module.
        # (-waveform IS credited: constraint_diff parses it for change detection.)
        s = analyze_scope("create_clock -name clk -period 5.0 -comment my_clk [get_ports clk]\n")
        assert s.status == "PARTIALLY_VALIDATED"
        assert s.partially_analyzed == 1
        assert "-comment" in s.ignored_options

    def test_unsupported_command_status(self):
        # set_clock_sense is standard SDC but no module parses it.
        s = analyze_scope("set_clock_sense -positive [get_pins u/clk]\n")
        assert s.status == "UNSUPPORTED"
        assert s.unsupported == 1
        assert s.constructs[0].level == "UNSUPPORTED"

    def test_unknown_option_detected(self):
        s = analyze_scope("create_clock -name c -period 5 -bogus 1 [get_ports p]\n")
        assert s.status == "PARTIALLY_VALIDATED"
        assert "-bogus" in s.unknown_options

    def test_tcl_construct_status(self):
        s = analyze_scope("foreach {p} [get_ports *] { puts $p }\n")
        assert s.status == "TCL_EXECUTION_REQUIRED"
        assert s.tcl_execution_required == 1

    def test_inline_expr_substitution(self):
        s = analyze_scope("set CLK_PERIOD [expr 5.0 * 2]\n")
        assert s.status == "TCL_EXECUTION_REQUIRED"

    def test_tcl_variable_assignment_supported(self):
        s = analyze_scope("set PERIOD 2.5\n"
                          "create_clock -name c -period $PERIOD [get_ports p]\n")
        assert s.status == "NETLIST_REQUIRED"  # variable itself is FULL
        assert any(c.command == "set (variable)" and c.level == "FULL"
                   for c in s.constructs)

    def test_empty_input_not_validated(self):
        s = analyze_scope("")
        assert s.status == "NOT_VALIDATED"
        assert s.commands_found == 0

    def test_current_design_netlist_query(self):
        s = analyze_scope("current_design\n")
        assert s.status == "NETLIST_REQUIRED"

    def test_status_precedence_unsupported_over_netlist(self):
        s = analyze_scope("create_clock -name c -period 5 [get_ports p]\n"
                          "set_clock_sense -positive [get_pins u/x]\n")
        assert s.status == "UNSUPPORTED"  # even though netlist refs also present

    def test_status_precedence_partial_over_netlist(self):
        s = analyze_scope("create_clock -name c -period 5 -comment x [get_ports p]\n")
        assert s.status == "PARTIALLY_VALIDATED"


class TestOptionAudit:
    """Option-level support: recognized / ignored / unknown."""

    def test_all_recognized_commands_have_standard_option_docs(self):
        for cmd in RECOGNIZED_COMMANDS:
            assert cmd in STANDARD_OPTIONS, f"{cmd} missing standard option docs"
            assert cmd in INTERPRETED_OPTIONS, f"{cmd} missing interpreted option docs"

    def test_interpreted_is_subset_of_standard(self):
        for cmd in RECOGNIZED_COMMANDS:
            assert INTERPRETED_OPTIONS[cmd] <= STANDARD_OPTIONS[cmd]

    def test_create_clock_period_name_interpreted(self):
        interp = INTERPRETED_OPTIONS["create_clock"]
        assert {"-name", "-period"} <= interp

    def test_input_delay_clock_max_min_interpreted(self):
        interp = INTERPRETED_OPTIONS["set_input_delay"]
        assert {"-clock", "-max", "-min"} <= interp
        # standard-but-uninterpreted options are documented, not hidden
        assert "-add_delay" in STANDARD_OPTIONS["set_input_delay"]
        assert "-add_delay" not in interp

    def test_bogus_option_not_in_standard(self):
        assert "-bogus" not in STANDARD_OPTIONS["create_clock"]


class TestCheckerIntegration:
    """The checker attaches scope to CheckResult and never regresses issues."""

    def test_checker_attaches_scope(self):
        r = check_sdc("create_clock -name c -period 5.0 [get_ports p]\n")
        assert r.scope.get("status") == "NETLIST_REQUIRED"

    def test_scope_does_not_change_issue_counts(self):
        text = ("create_clock -name c -period 5.0 [get_ports p]\n"
                "set_input_delay -max 6.0 -clock c [get_ports din]\n")
        r = check_sdc(text)
        # SDC-008 still fires exactly once (scope is an additive, separate dim)
        assert len([i for i in r.issues if i.code == "SDC-008"]) == 1
        assert r.scope["commands_found"] >= 2

    def test_unsupported_construct_never_clean(self):
        r = check_sdc("create_clock -name c -period 5.0 [get_ports p]\n"
                      "set_clock_sense -positive [get_pins u/x]\n")
        assert r.scope["status"] != "VALIDATED"
        assert r.scope["unsupported"] >= 1

    def test_scope_serializes_to_dict(self):
        r = check_sdc("create_clock -name c -period 5.0 [get_ports p]\n")
        assert isinstance(r.scope, dict)
        assert "status" in r.scope and "constructs" in r.scope

    def test_scope_summary_lines_are_specific(self):
        s = analyze_scope("create_clock -name c -period 5 -waveform {0 2} [get_ports p]\n"
                          "set_clock_sense -positive [get_pins u/x]\n")
        lines = s.summary_lines()
        joined = "\n".join(lines)
        assert "Commands found" in joined
        assert "Unsupported" in joined


class TestTrustBoundaryNoFalseConfidence:
    """The core principle: limitations are always visible, never silent."""

    @pytest.mark.parametrize("sdc", [
        # unsupported construct among valid constraints
        "set sdc_version 2.2\ncreate_clock -name c -period 5 [get_ports p]\nset_clock_sense -positive [get_pins u/x]\n",
        # netlist-dependent reference
        "create_clock -name c -period 5 [get_ports p]\nset_false_path -from [get_pins u_a/Q] -to [get_pins u_b/D]\n",
        # unknown option
        "create_clock -name c -period 5 -frobnicate 3 [get_ports p]\n",
        # ignored option
        "create_clock -name c -period 5 -waveform {0 2.5} [get_ports p]\n",
        # unsupported Tcl
        "foreach {p} [get_ports *] { set_input_delay 1 -clock c $p }\n",
    ])
    def test_limitation_never_hidden(self, sdc):
        s = analyze_scope(sdc)
        r = check_sdc(sdc)
        # If the input was not fully understood, BOTH the analyzer and the
        # checker-attached scope must say so (not VALIDATED).
        assert s.status != "VALIDATED"
        assert r.scope["status"] != "VALIDATED"
