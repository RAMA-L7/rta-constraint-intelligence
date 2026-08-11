"""
Integration tests for the CLI interface.
Tests that CLI commands run without errors and produce expected output.
"""

import subprocess
import sys
import os
import json
import pytest

# Path to the CLI module
CLI_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cli.py")


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run sdc-tools CLI and return the result (handles Unicode on Windows)."""
    cmd = [sys.executable, CLI_SCRIPT] + list(args)
    proc = subprocess.run(cmd, capture_output=True, timeout=30)
    # Decode with UTF-8, replacing un-decodable chars (Windows cp1252 workaround)
    proc.stdout = proc.stdout.decode("utf-8", errors="replace")
    proc.stderr = proc.stderr.decode("utf-8", errors="replace")
    return proc


class TestCliHelp:
    """Tests for help and version commands."""

    def test_help_exits_zero(self):
        """Running without args should show help and exit 0."""
        result = run_cli()
        assert result.returncode == 0
        assert "SDC constraint" in result.stdout or "usage:" in result.stdout.lower()

    def test_version(self):
        """--version should show version string."""
        result = run_cli("--version")
        assert result.returncode == 0
        assert "SDC Tools" in result.stdout

    def test_help_flag(self):
        result = run_cli("--help")
        assert result.returncode == 0


class TestCliCheck:
    """Tests for the `check` command."""

    def test_check_empty_file(self, sample_sdc_path):
        """Check returns JSON-parseable output even on problematic SDCs."""
        result = run_cli("check", sample_sdc_path)
        # Sample SDC has no output delay → exit code 1 (correct)
        # Output should still contain checker info
        assert "SDC Tools" in result.stdout or "Error" in result.stdout

    def test_check_nonexistent_file(self):
        """Non-existent file should produce an error."""
        result = run_cli("check", "nonexistent.sdc")
        assert result.returncode != 0

    def test_check_json_output(self, sample_sdc_path):
        """JSON output should parse correctly even with errors."""
        result = run_cli("check", sample_sdc_path, "--json")
        # Exit code is 1 (check found issues) but JSON should still be valid
        data = json.loads(result.stdout)
        assert "version" in data
        assert "errors" in data
        assert "warnings" in data

    def test_check_json_has_stats(self, sample_sdc_path):
        """JSON output should include stats."""
        result = run_cli("check", sample_sdc_path, "--json")
        data = json.loads(result.stdout) if result.stdout else {}
        assert "stats" in data
        assert "summary" in data

    def test_check_junit_output(self, sample_sdc_path):
        """JUnit XML output should be valid XML."""
        result = run_cli("check", sample_sdc_path, "--junit")
        # Even with errors, JUnit XML should be well-formed
        assert "<?xml" in result.stdout
        assert "<testsuite" in result.stdout

    def test_check_with_output_file(self, sample_sdc_path, tmp_path):
        """Output written to file instead of stdout."""
        out_file = tmp_path / "output.txt"
        result = run_cli("check", sample_sdc_path, "--output", str(out_file))
        assert out_file.exists()


class TestCliGenerate:
    """Tests for the `generate` command."""

    def test_generate_basic(self):
        """Generate SDC with a clock definition."""
        result = run_cli("generate", "--design", "TEST", "--clock", "clk=10.0:sys_clk")
        assert result.returncode == 0
        assert "TEST" in result.stdout
        assert "create_clock" in result.stdout
        assert "10.000" in result.stdout

    def test_generate_with_clock(self):
        """Generate with a custom clock definition."""
        result = run_cli("generate", "--design", "TEST", "--clock", "clk=10.0:sys_clk")
        assert result.returncode == 0
        assert "clk" in result.stdout
        assert "10.000" in result.stdout

    def test_generate_with_derate(self):
        result = run_cli("generate", "--design", "TEST", "--derate")
        assert result.returncode == 0
        assert "set_timing_derate" in result.stdout

    def test_generate_output_file(self, tmp_path):
        out_file = tmp_path / "gen.sdc"
        result = run_cli("generate", "--design", "OUT", "--output", str(out_file))
        assert result.returncode == 0
        assert out_file.exists()


class TestCliDiff:
    """Tests for the `diff` command."""

    def test_diff_basic(self, sample_sdc_path):
        """Diff a file against itself should produce output."""
        result = run_cli("diff", sample_sdc_path, sample_sdc_path)
        assert result.returncode == 0


class TestCliRules:
    """Tests for the `rules` command."""

    def test_rules_list(self):
        """List all rules."""
        result = run_cli("rules", "list")
        assert result.returncode == 0
        assert "SDC-001" in result.stdout

    def test_rules_show(self):
        """Show a specific rule."""
        result = run_cli("rules", "show", "SDC-060")
        assert result.returncode == 0
        assert "SDC-060" in result.stdout

    def test_rules_list_json(self):
        """JSON output for rules list."""
        result = run_cli("rules", "list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "code" in data[0]

    def test_rules_list_filter_module(self):
        """Filter rules by module."""
        result = run_cli("rules", "list", "--module", "checker")
        assert result.returncode == 0

    def test_rules_list_search(self):
        """Search for a keyword in rules."""
        result = run_cli("rules", "list", "--search", "clock")
        assert result.returncode == 0


class TestCliCoverage:
    """Tests for the `coverage` command."""

    def test_coverage_basic(self, sample_sdc_path):
        result = run_cli("coverage", sample_sdc_path)
        assert result.returncode == 0
        assert "Coverage" in result.stdout

    def test_coverage_json(self, sample_sdc_path):
        result = run_cli("coverage", sample_sdc_path, "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "score_pct" in data
        assert "categories" in data

    def test_coverage_missing_only(self, sample_sdc_path):
        result = run_cli("coverage", sample_sdc_path, "--missing-only")
        assert result.returncode == 0


class TestCliAnalyze:
    """Tests for the `analyze` command."""

    def test_analyze_clock_relations(self, sample_sdc_path):
        result = run_cli("analyze", "clock-relations", sample_sdc_path)
        assert result.returncode == 0
        # At least some output
        assert len(result.stdout) > 0

    def test_analyze_json(self, sample_sdc_path):
        result = run_cli("analyze", "clock-relations", sample_sdc_path, "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "clocks" in data
        assert "stats" in data


class TestCliCorners:
    """Tests for the `corners` command."""

    def test_corners_list(self):
        result = run_cli("corners", "list")
        assert result.returncode == 0
        assert "preset" in result.stdout.lower()

    def test_corners_show(self):
        result = run_cli("corners", "show", "Classic 3-corner")
        assert result.returncode == 0


class TestCliReport:
    """Tests for the `report` command."""

    def test_report_check(self, sample_sdc_path, tmp_path):
        out_file = tmp_path / "report.html"
        result = run_cli("report", "check", sample_sdc_path, "--output", str(out_file))
        assert result.returncode == 0
        assert out_file.exists()
        assert out_file.read_text().strip().startswith("<!DOCTYPE html>")


class TestCliLint:
    """Tests for the `lint` command."""

    def test_lint_check_mode(self, sample_sdc_path):
        result = run_cli("lint", sample_sdc_path, "--check")
        # lint may find issues; verify it runs without crash
        assert result.returncode in (0, 1)

    def test_lint_output_file(self, sample_sdc_path, tmp_path):
        out = tmp_path / "linted.sdc"
        result = run_cli("lint", sample_sdc_path, "--output", str(out))
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Reorganized Constraint File" in content
        assert "set" in content


class TestCliConvert:
    """Tests for the `convert` command."""

    def test_convert_json(self, sample_sdc_path):
        result = run_cli("convert", sample_sdc_path, "--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "clocks" in data

    def test_convert_with_output(self, sample_sdc_path, tmp_path):
        out = tmp_path / "out.json"
        result = run_cli("convert", sample_sdc_path, "--format", "json", "--output", str(out))
        assert result.returncode == 0
        assert out.exists()
        json.loads(out.read_text())  # must parse


class TestCliBatch:
    """Tests for the `batch` command."""

    def test_batch_check_directory(self, tmp_path):
        d = tmp_path / "sdcs"
        d.mkdir()
        s = d / "test.sdc"
        s.write_text("create_clock -name clk -period 5.0 [get_ports clk]\n"
                     "set_input_delay -max 1.0 -clock clk [get_ports din]\n"
                     "set_output_delay -max 1.5 -clock clk [get_ports dout]")
        result = run_cli("batch", "check", str(d))
        assert result.returncode == 0
        assert "Batch Summary" in result.stdout
