"""
Tests for the Constraint Coverage Gap Analyzer module.
"""

import pytest
from coverage import (
    CoverageItem, CoverageCategory, CoverageResult,
    parse_sdc_coverage,
)


class TestCoverageItem:
    """Tests for the CoverageItem dataclass."""

    def test_create_item(self):
        item = CoverageItem(name="test", cmd="test_cmd", present=True)
        assert item.name == "test"
        assert item.present is True
        assert item.is_critical is True

    def test_not_critical(self):
        item = CoverageItem(name="test", cmd="test_cmd", present=False, is_critical=False)
        assert item.is_critical is False


class TestCoverageCategory:
    """Tests for the CoverageCategory dataclass."""

    def test_empty_category(self):
        cat = CoverageCategory(name="Test", icon="🔵")
        assert cat.total == 0
        assert cat.covered == 0
        assert cat.missing == 0
        assert cat.score == 0.0
        assert cat.status == "bad"

    def test_all_covered(self):
        cat = CoverageCategory(name="Test", icon="🔵", items=[
            CoverageItem(name="a", cmd="a", present=True),
            CoverageItem(name="b", cmd="b", present=True),
        ])
        assert cat.total == 2
        assert cat.covered == 2
        assert cat.missing == 0
        assert cat.score == 100.0
        assert cat.status == "good"

    def test_partial_covered(self):
        cat = CoverageCategory(name="Test", icon="🔵", items=[
            CoverageItem(name="a", cmd="a", present=True),
            CoverageItem(name="b", cmd="b", present=False),
        ])
        assert cat.score == 50.0
        assert cat.status == "warn"

    def test_bad_score(self):
        cat = CoverageCategory(name="Test", icon="🔵", items=[
            CoverageItem(name="a", cmd="a", present=True),
            CoverageItem(name="b", cmd="b", present=False),
            CoverageItem(name="c", cmd="c", present=False),
            CoverageItem(name="d", cmd="d", present=False),
        ])
        assert cat.score == 25.0
        assert cat.status == "bad"


class TestParseSdcCoverage:
    """Tests for the main coverage analysis function."""

    def test_empty_sdc(self):
        result = parse_sdc_coverage("", "empty.sdc")
        assert result.total_items > 0  # still has items
        # "Multicycle hold fix" is present=True when no multicycle paths exist
        # (nothing to fix = nothing missing), so total_present is >= 1
        assert result.total_missing == result.total_items - result.total_present
        assert result.score < 10.0  # almost everything missing
        assert result.filename == "empty.sdc"

    def test_full_sdc(self, full_sdc):
        result = parse_sdc_coverage(full_sdc, "full.sdc")
        assert result.total_present > 0
        assert result.score > 0
        assert result.filename == "full.sdc"

    def test_full_sdc_coverage_score(self, full_sdc):
        result = parse_sdc_coverage(full_sdc, "full.sdc")
        # A comprehensive SDC should have decent coverage
        assert result.score >= 50.0

    def test_minimal_sdc(self, minimal_sdc):
        result = parse_sdc_coverage(minimal_sdc)
        assert result.total_present >= 1  # at least the clock
        assert result.score < 30.0  # many missing items

    def test_six_categories(self, full_sdc):
        result = parse_sdc_coverage(full_sdc)
        assert len(result.categories) == 6

    def test_clocks_category_present(self, full_sdc):
        result = parse_sdc_coverage(full_sdc)
        clock_cat = result.categories[0]
        assert clock_cat.name == "Clocks"
        assert clock_cat.covered > 0

    def test_stats_are_populated(self, full_sdc):
        result = parse_sdc_coverage(full_sdc)
        assert "categories" in result.stats
        assert "total_items" in result.stats
        assert "present" in result.stats
        assert "missing" in result.stats
        assert "score_pct" in result.stats

    def test_stats_match_totals(self, full_sdc):
        result = parse_sdc_coverage(full_sdc)
        assert result.stats["total_items"] == result.total_items
        assert result.stats["present"] == result.total_present
        assert result.stats["missing"] == result.total_missing

    def test_missing_items_detail(self, full_sdc):
        result = parse_sdc_coverage(full_sdc)
        # Count missing items across all categories
        missing_items = sum(1 for cat in result.categories for it in cat.items if not it.present)
        assert result.total_missing == missing_items

    def test_coverage_totals_consistent(self, full_sdc):
        result = parse_sdc_coverage(full_sdc)
        assert result.total_items == result.total_present + result.total_missing

    # ── Phase 4 — commented-out constraints must not create phantom items ──

    def test_commented_out_clocks_not_counted(self):
        text = (
            "# create_clock -name clk -period 5.0 [get_ports clk]\n"
            "# create_clock -name clk2 -period 7.5 [get_ports clk2]\n"
        )
        result = parse_sdc_coverage(text, "all_commented.sdc")
        clk_item = next(i for c in result.categories if c.name == "Clocks" for i in c.items
                        if i.name.startswith("Primary clock"))
        assert clk_item.present is False, "commented-out clocks must not count as present"

    def test_multiline_and_variables_seen(self):
        text = (
            "set CLK_PERIOD 5.0\n"
            "create_clock -name clk -period $CLK_PERIOD \\\n"
            "    [get_ports clk]\n"
            "set_clock_uncertainty -setup 0.1 -hold 0.05 [get_clocks clk]\n"
        )
        result = parse_sdc_coverage(text)
        clk_item = next(i for c in result.categories if c.name == "Clocks" for i in c.items
                        if i.name.startswith("Primary clock"))
        unc_item = next(i for c in result.categories if c.name == "Clocks" for i in c.items
                        if "uncertainty" in i.name.lower())
        assert clk_item.present is True
        assert unc_item.present is True, "multiline/variable clock_uncertainty must be seen"
