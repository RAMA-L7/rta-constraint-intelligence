"""
Tests for the SDC Linter module.
"""

import pytest
from linter import lint_sdc, lint_sdc_file, _classify_line, SdcLine


class TestClassifyLine:
    """Tests for SDC line classification."""

    def test_blank_line(self):
        line = _classify_line("")
        assert line.is_blank is True

    def test_comment_line(self):
        line = _classify_line("# This is a comment")
        assert line.is_comment is True

    def test_sdc_version_command(self):
        line = _classify_line("set sdc_version 2.2")
        assert line.category == "sdc_version"
        assert line.command == "set_sdc_version"

    def test_clock_command(self):
        line = _classify_line("create_clock -name clk -period 5.0 [get_ports clk]")
        assert line.category == "clocks"
        assert line.command == "create_clock"

    def test_false_path(self):
        line = _classify_line("set_false_path -from [get_ports rst] -to [get_cells sync]")
        assert line.category == "false_paths"

    def test_continuation_line(self):
        line = _classify_line("  -group [get_clocks clk_a]")
        assert line.is_continuation is True


class TestLintSdc:
    """Tests for the main lint function."""

    def test_lint_with_issues(self):
        text = "create_clock -name clk -period 5.0 [get_ports clk]\n"
        result = lint_sdc(text, fix=True)
        assert result.formatted_text is not None

    def test_lint_no_fix_mode(self):
        text = "create_clock -name clk -period 5.0 [get_ports clk]"
        result = lint_sdc(text, fix=False)
        assert result.formatted_text == ""

    def test_lint_detects_trailing_whitespace(self):
        text = "create_clock -name clk -period 5.0 [get_ports clk]  \n"
        result = lint_sdc(text, fix=False)
        assert result.warnings > 0

    def test_lint_detects_long_lines(self):
        text = "create_clock " + "-" * 200 + "\n"
        result = lint_sdc(text, fix=False)
        assert result.warnings > 0

    def test_lint_formatted_includes_section_headers(self, minimal_sdc):
        result = lint_sdc(minimal_sdc, fix=True)
        assert "SDC Lint" in result.formatted_text
        assert "Clock Definitions" in result.formatted_text
        assert "create_clock" in result.formatted_text

    def test_lint_preserves_original(self):
        text = "set sdc_version 2.2\ncreate_clock -name clk -period 5.0\n"
        result = lint_sdc(text, fix=True)
        assert "2.2" in result.formatted_text

    def test_lint_preserves_full_sdc(self, full_sdc):
        result = lint_sdc(full_sdc, fix=True)
        assert result.formatted_text is not None
        assert "create_clock" in result.formatted_text
        assert "set_false_path" in result.formatted_text or "False Paths" in result.formatted_text

    def test_lint_counts_correctly(self, minimal_sdc):
        result = lint_sdc(minimal_sdc, fix=True)
        assert result.line_count_original > 0
        assert result.line_count_formatted > 0

    def test_empty_text(self):
        result = lint_sdc("", fix=True)
        assert result.line_count_original == 0


class TestLintSdcFile:
    """Tests for the file-based lint function."""

    def test_lint_file(self, sample_sdc_path):
        result = lint_sdc_file(sample_sdc_path, fix=False)
        assert result.line_count_original > 0
        assert isinstance(result.warnings, int)

    def test_lint_file_with_output(self, sample_sdc_path, tmp_path):
        out = tmp_path / "linted.sdc"
        result = lint_sdc_file(sample_sdc_path, fix=True, output_path=str(out))
        assert out.exists()
