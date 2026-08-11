"""
Tests for the Clock Relation Analyzer module.
"""

import pytest
from clock_relations import (
    ClockDefCK, ClockPair, ClockMismatch, RelationAnalysisResult,
    analyze_clock_relations,
)


class TestClockDef:
    """Tests for the ClockDefCK dataclass."""

    def test_basic_clock(self):
        ck = ClockDefCK(name="clk", period=5.0, source_port="clk_port")
        assert ck.name == "clk"
        assert ck.period == 5.0
        assert ck.source_port == "clk_port"
        assert ck.is_generated is False

    def test_generated_clock(self):
        ck = ClockDefCK(name="gen", period=2.5, source_port="gen_out",
                         is_generated=True, master_clock="clk", divide_by=2)
        assert ck.is_generated is True
        assert ck.master_clock == "clk"
        assert ck.divide_by == 2

    def test_virtual_clock(self):
        ck = ClockDefCK(name="vclk", period=10.0, source_port="",
                         is_virtual=True)
        assert ck.is_virtual is True


class TestAnalyzeClockRelations:
    """Tests for the main clock relation analysis function."""

    def test_no_clocks(self):
        result = analyze_clock_relations("")
        assert len(result.clocks) == 0
        assert len(result.pairs) == 0
        assert len(result.mismatches) == 0

    def test_single_clock(self, minimal_sdc):
        result = analyze_clock_relations(minimal_sdc)
        assert len(result.clocks) >= 1
        assert result.stats.get("clocks", 0) >= 1

    def test_multiple_clocks_inferred(self, full_sdc):
        result = analyze_clock_relations(full_sdc)
        # full_sdc has clk_core and clk_slow
        assert result.stats.get("clocks", 0) >= 2

    def test_clock_groups_detected(self, full_sdc):
        result = analyze_clock_relations(full_sdc)
        # full_sdc has set_clock_groups -asynchronous
        groups = result.existing_groups
        assert len(groups) > 0

    def test_stats_structure(self, full_sdc):
        result = analyze_clock_relations(full_sdc)
        assert "clocks" in result.stats
        assert "pairs" in result.stats

    def test_pairs_are_clock_combinations(self, full_sdc):
        """Number of pairs should be C(n,2) for n clocks."""
        result = analyze_clock_relations(full_sdc)
        n = result.stats.get("clocks", 0)
        expected_pairs = n * (n - 1) // 2
        assert result.stats.get("pairs", 0) == expected_pairs

    def test_result_is_relation_analysis_result(self, minimal_sdc):
        result = analyze_clock_relations(minimal_sdc)
        assert isinstance(result, RelationAnalysisResult)

    def test_clock_definitions_parsed(self, full_sdc):
        """Clocks should have their names extracted."""
        result = analyze_clock_relations(full_sdc)
        names = [c.name for c in result.clocks]
        assert "clk_core" in names or any("clk" in name.lower() for name in names)


class TestRelationAnalysisEdgeCases:
    """Edge case tests for clock relation analysis."""

    def test_generated_clock_detected(self, full_sdc):
        """Generated clocks should be flagged."""
        result = analyze_clock_relations(full_sdc)
        gen_clocks = [c for c in result.clocks if c.is_generated]
        # full_sdc has a create_generated_clock
        assert len(gen_clocks) >= 1

    def test_buggy_sdc(self, buggy_sdc):
        """Buggy SDCs should still produce results (no crashes)."""
        result = analyze_clock_relations(buggy_sdc)
        # At minimum, no crash
        assert result is not None

    def test_clock_names_preserved(self):
        """Clock names should be correctly extracted."""
        text = "create_clock -name clk_A -period 5.0 [get_ports clk_A]\ncreate_clock -name clk_B -period 10.0 [get_ports clk_B]"
        result = analyze_clock_relations(text)
        names = [c.name for c in result.clocks]
        assert "clk_A" in names
        assert "clk_B" in names

    def test_mismatches_empty_when_no_conflicts(self, minimal_sdc):
        """A single clock should have zero mismatches."""
        result = analyze_clock_relations(minimal_sdc)
        assert len(result.mismatches) == 0
