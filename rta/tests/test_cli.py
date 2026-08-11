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
CLI_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cli.py")


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
        """--version should show the Ṛta version string (Unicode brand)."""
        from rules_registry import APP_VERSION
        result = run_cli("--version")
        assert result.returncode == 0
        assert "Ṛta v" in result.stdout
        assert APP_VERSION in result.stdout

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
        assert "Ṛta v" in result.stdout or "Error" in result.stdout

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


CLEAN_SDC = (
    "set sdc_version 2.2\n"
    "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n"
    "set_propagated_clock [get_clocks clk_core]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
    "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n"
)

BLOCKED_SDC = CLEAN_SDC + (
    "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]\n"
)


class TestCliReadinessBaseline:
    """Phase 12 — readiness baseline / diff / CI gate CLI contract."""

    def _write(self, tmp_path, name, text):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_save_baseline_writes_snapshot(self, tmp_path):
        sdc = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        bl = str(tmp_path / "baseline.json")
        result = run_cli("check", sdc, "--save-baseline", bl)
        assert result.returncode == 0
        assert os.path.exists(bl)
        data = json.loads(open(bl, encoding="utf-8").read())
        # Phase 13: snapshot schema v2 (structured finding identity).
        assert data["schema_version"] == 2
        assert data.get("identity_version") == 1
        assert data["readiness"]["overall"]
        assert "findings" in data
        assert data["capabilities"]["structured_identity"] is True

    def test_save_baseline_in_json_output(self, tmp_path):
        sdc = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        bl = str(tmp_path / "baseline.json")
        result = run_cli("check", sdc, "--save-baseline", bl, "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # Without --baseline there is no diff yet, but the snapshot was
        # written and the regular readiness payload is present.
        assert os.path.exists(bl)
        assert "constraint_readiness" in data

    def test_baseline_no_regression_passes(self, tmp_path):
        base = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        cur = self._write(tmp_path, "cur.sdc", CLEAN_SDC.replace("10.0", "10.000"))
        bl = str(tmp_path / "baseline.json")
        run_cli("check", base, "--save-baseline", bl)
        result = run_cli("check", cur, "--baseline", bl,
                         "--gate", "NO_READINESS_REGRESSION")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Readiness diff" in result.stdout or "READINESS DIFF" in result.stdout

    def test_baseline_new_blocker_fails_gate(self, tmp_path):
        base = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        cur = self._write(tmp_path, "cur.sdc", BLOCKED_SDC)
        bl = str(tmp_path / "baseline.json")
        run_cli("check", base, "--save-baseline", bl)
        result = run_cli("check", cur, "--baseline", bl,
                         "--gate", "NO_READINESS_REGRESSION")
        assert result.returncode == 1, result.stdout + result.stderr

    def test_blockers_only_gate_on_blocked(self, tmp_path):
        sdc = self._write(tmp_path, "bad.sdc", BLOCKED_SDC)
        result = run_cli("check", sdc, "--gate", "BLOCKERS_ONLY")
        assert result.returncode == 1

    def test_blockers_only_gate_on_clean(self, tmp_path):
        sdc = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        result = run_cli("check", sdc, "--gate", "BLOCKERS_ONLY")
        assert result.returncode == 0

    def test_missing_baseline_fails_gate(self, tmp_path):
        sdc = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        result = run_cli("check", sdc, "--baseline", "/nonexistent/baseline.json",
                         "--gate", "NO_READINESS_REGRESSION")
        assert result.returncode == 2

    def test_baseline_dependent_gate_without_baseline_fails(self, tmp_path):
        # A baseline-dependent policy must NOT silently pass when --baseline is
        # omitted — the gate is evaluated even without a baseline and exits 2.
        sdc = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        result = run_cli("check", sdc, "--gate", "NO_READINESS_REGRESSION")
        assert result.returncode == 2

    def test_blockers_only_gate_without_baseline_ok(self, tmp_path):
        # BLOCKERS_ONLY needs no baseline — evaluates the current revision.
        good = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        assert run_cli("check", good, "--gate", "BLOCKERS_ONLY").returncode == 0
        bad = self._write(tmp_path, "bad.sdc", BLOCKED_SDC)
        assert run_cli("check", bad, "--gate", "BLOCKERS_ONLY").returncode == 1

    def test_malformed_baseline_fails_safely(self, tmp_path):
        sdc = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        bad = self._write(tmp_path, "bad.json", "not json at all")
        result = run_cli("check", sdc, "--baseline", bad,
                         "--gate", "NO_READINESS_REGRESSION")
        assert result.returncode == 2

    def test_unknown_gate_policy(self, tmp_path):
        sdc = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        result = run_cli("check", sdc, "--gate", "BOGUS_POLICY")
        assert result.returncode == 2

    def test_json_output_includes_readiness_diff(self, tmp_path):
        base = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        cur = self._write(tmp_path, "cur.sdc", BLOCKED_SDC)
        bl = str(tmp_path / "baseline.json")
        run_cli("check", base, "--save-baseline", bl)
        result = run_cli("check", cur, "--baseline", bl, "--gate",
                         "NO_READINESS_REGRESSION", "--json")
        data = json.loads(result.stdout)
        diff = data.get("readiness_diff", {})
        assert diff.get("classification") == "BLOCKING_REGRESSION"
        assert diff.get("findings", {}).get("new_blockers")

    def test_no_gate_keeps_legacy_exit_behavior(self, tmp_path):
        # Without --gate, a BLOCKED file exits 1 (legacy), clean exits 0.
        bad = self._write(tmp_path, "bad.sdc", BLOCKED_SDC)
        assert run_cli("check", bad).returncode == 1
        good = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        assert run_cli("check", good).returncode == 0


class TestCliCustomPolicy:
    """Phase 13 — declarative CUSTOM policy engine CLI contract."""

    def _write(self, tmp_path, name, text):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_custom_policy_new_blocker_fails(self, tmp_path):
        base = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        cur = self._write(tmp_path, "cur.sdc", BLOCKED_SDC)
        bl = str(tmp_path / "baseline.json")
        pol = self._write(tmp_path, "policy.json",
                          '{"policy": "CUSTOM", "policy_version": 1, '
                          '"name": "legacy", "fail_on": {"new_blockers": true}}')
        run_cli("check", base, "--save-baseline", bl)
        result = run_cli("check", cur, "--baseline", bl,
                         "--gate", "CUSTOM", "--gate-policy", pol)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "1 NEW blocker" in result.stdout

    def test_custom_policy_permissive_passes(self, tmp_path):
        base = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        cur = self._write(tmp_path, "cur.sdc", BLOCKED_SDC)
        bl = str(tmp_path / "baseline.json")
        # A policy that does NOT fail on new blockers must pass (the blocker is
        # new, but the policy chose not to gate on new blockers — the diff
        # still exposes it as new debt, never hiding it).
        pol = self._write(tmp_path, "policy.json",
                          '{"policy": "CUSTOM", "policy_version": 1, '
                          '"name": "permissive", "fail_on": {"new_blockers": false}}')
        run_cli("check", base, "--save-baseline", bl)
        result = run_cli("check", cur, "--baseline", bl,
                         "--gate", "CUSTOM", "--gate-policy", pol)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "NEW BLOCKER" in result.stdout

    def test_existing_debt_visible_in_output(self, tmp_path):
        # Baseline already carries the blocker; current is unchanged → the
        # diff must show it as pre-existing debt, not as a new blocker.
        bl = str(tmp_path / "baseline.json")
        run_cli("check", self._write(tmp_path, "base.sdc", BLOCKED_SDC),
                "--save-baseline", bl)
        cur = self._write(tmp_path, "cur.sdc", BLOCKED_SDC)
        pol = self._write(tmp_path, "policy.json",
                          '{"policy": "CUSTOM", "policy_version": 1, '
                          '"name": "permissive", "fail_on": {"new_blockers": false}}')
        result = run_cli("check", cur, "--baseline", bl,
                         "--gate", "CUSTOM", "--gate-policy", pol)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "baseline debt" in result.stdout

    def test_custom_gate_without_policy_fails(self, tmp_path):
        sdc = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        result = run_cli("check", sdc, "--gate", "CUSTOM")
        assert result.returncode == 2
        assert "--gate-policy" in result.stderr

    def test_invalid_policy_rejected_exit_2(self, tmp_path):
        sdc = self._write(tmp_path, "good.sdc", CLEAN_SDC)
        pol = self._write(tmp_path, "bad.json",
                          '{"policy": "CUSTOM", "policy_version": 1, "evil": 1}')
        result = run_cli("check", sdc, "--gate", "CUSTOM", "--gate-policy", pol)
        assert result.returncode == 2
        assert "invalid" in result.stderr

    def test_yaml_policy_supported(self, tmp_path):
        base = self._write(tmp_path, "base.sdc", CLEAN_SDC)
        cur = self._write(tmp_path, "cur.sdc", BLOCKED_SDC)
        bl = str(tmp_path / "baseline.json")
        pol = self._write(tmp_path, "policy.yaml",
                          "policy: CUSTOM\n"
                          "policy_version: 1\n"
                          "name: legacy\n"
                          "fail_on:\n  new_blockers: true\n")
        run_cli("check", base, "--save-baseline", bl)
        result = run_cli("check", cur, "--baseline", bl,
                         "--gate", "CUSTOM", "--gate-policy", pol)
        assert result.returncode == 1, result.stdout + result.stderr