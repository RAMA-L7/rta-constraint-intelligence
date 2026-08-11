"""
Tests for the Wildcard Pattern Analyzer module.
"""

import pytest
from wildcard_analyzer import (
    parse_wildcard, compare_wildcards, flag_overly_broad,
    WildcardPattern, WildcardComparison,
)


class TestParseWildcard:
    """Tests for wildcard pattern parsing and classification."""

    def test_exact_pattern(self):
        """No wildcard characters → exact."""
        wc = parse_wildcard("data_bus")
        assert wc.specificity == "exact"
        assert wc.has_wildcards is False
        assert wc.risk_score == 0

    def test_broad_all_inputs(self):
        wc = parse_wildcard("[all_inputs]")
        assert wc.specificity == "broad"
        # [ is matched by the wildcard regex (bracket characters)
        assert wc.has_wildcards is True
        assert wc.risk_score == 9

    def test_broad_all_outputs(self):
        wc = parse_wildcard("[all_outputs]")
        assert wc.specificity == "broad"
        assert wc.risk_score == 9

    def test_broad_star_bracket(self):
        wc = parse_wildcard("[*]")
        assert wc.specificity == "broad"
        assert wc.risk_score == 8

    def test_moderate_double_star(self):
        wc = parse_wildcard("*/*/data*")
        assert wc.specificity == "moderate"
        assert wc.risk_score == 4

    def test_specific_single_star(self):
        wc = parse_wildcard("data_*")
        assert wc.specificity == "specific"
        assert wc.risk_score == 2

    def test_pattern_type_pins(self):
        wc = parse_wildcard("[get_pins *static*]")
        assert wc.pattern_type == "pin"

    def test_pattern_type_ports(self):
        wc = parse_wildcard("[get_ports data_*]")
        assert wc.pattern_type == "port"

    def test_pattern_type_clocks(self):
        wc = parse_wildcard("[get_clocks clk_*]")
        assert wc.pattern_type == "clock"

    def test_pattern_type_cells(self):
        wc = parse_wildcard("[get_cells */inst*]")
        assert wc.pattern_type == "cell"

    def test_pattern_type_nets(self):
        wc = parse_wildcard("[get_nets net_*]")
        assert wc.pattern_type == "net"

    def test_pattern_type_unknown(self):
        wc = parse_wildcard("some_pattern")
        assert wc.pattern_type == "unknown"

    def test_has_wildcards_star(self):
        assert parse_wildcard("data_*").has_wildcards is True

    def test_has_wildcards_question(self):
        assert parse_wildcard("data_?").has_wildcards is True

    def test_empty_text(self):
        wc = parse_wildcard("")
        assert wc.raw == ""
        assert wc.specificity == "exact"


class TestCompareWildcards:
    """Tests for comparing two wildcard patterns."""

    def test_identical_patterns(self):
        wc = compare_wildcards("data_*", "data_*", "set_false_path")
        assert wc.change_type == "same"
        assert "No change" in wc.risk_explanation

    def test_narrowed_pattern(self):
        wc = compare_wildcards("data_*", "data_bus", "set_false_path")
        assert wc.change_type == "narrowed"

    def test_broadened_pattern(self):
        wc = compare_wildcards("data_bus", "data_*", "set_false_path")
        assert wc.change_type == "broadened"

    def test_rewritten_pattern(self):
        """When both stars change count, it's rewritten."""
        wc = compare_wildcards("*/data_*", "*/ctrl_*", "set_max_delay")
        assert wc.change_type in ("rewritten", "narrowed", "broadened")

    def test_command_type_stored(self):
        wc = compare_wildcards("old_path", "new_path", "set_multicycle_path")
        assert wc.command_type == "set_multicycle_path"

    def test_v1_v2_objects(self):
        wc = compare_wildcards("v1_*", "v2_*", "")
        assert isinstance(wc.v1_pattern, WildcardPattern)
        assert isinstance(wc.v2_pattern, WildcardPattern)

    def test_low_similarity_noted(self):
        wc = compare_wildcards("aaaaaa", "bbbbbb", "")
        assert "similarity" in wc.risk_explanation.lower()


class TestFlagOverlyBroad:
    """Tests for flagging overly broad patterns."""

    def test_flag_broad_patterns(self):
        patterns = [
            "[all_inputs]",
            "data_bus",
            "[all_nets]",
            "specific_pin",
        ]
        flagged = flag_overly_broad(patterns)
        assert len(flagged) == 2  # all_inputs and all_nets

    def test_no_broad_patterns(self):
        flagged = flag_overly_broad(["data_a", "data_b"])
        assert flagged == []

    def test_empty_list(self):
        assert flag_overly_broad([]) == []

    def test_returns_wildcard_objects(self):
        flagged = flag_overly_broad(["[all_outputs]"])
        assert len(flagged) == 1
        assert isinstance(flagged[0], WildcardPattern)
        assert flagged[0].risk_score >= 7
