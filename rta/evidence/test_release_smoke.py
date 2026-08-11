"""Phase 14 — Release-candidate smoke suite.

Fast, end-to-end checks that Ṛta can be installed and used for
the documented workflow. Complements (does not replace) the 689-test pytest
suite, golden runners and benchmark suites. Intended to run on every release:
    python -m pytest benchmarks/test_release_smoke.py -q

Each test exercises the PUBLIC CLI / Python API (never repository-relative
internals), so the suite is equally valid against an installed wheel.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOOD_SDC = (
    "set sdc_version 2.2\n"
    "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
    "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n"
)


def run_cli(*args, cwd=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, "-m", "cli", *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd or ROOT, env=env)


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


class TestSmoke:
    def test_imports(self):
        """Core public modules import without UI/internal packages."""
        import checker
        import readiness_diff
        import policy_engine
        import finding_identity
        assert callable(checker.check_sdc)
        assert callable(readiness_diff.build_snapshot)
        assert callable(policy_engine.load_policy)
        assert callable(finding_identity.identity_from_commands)

    def test_cli_help(self):
        r = run_cli("--help")
        assert r.returncode == 0
        assert "check" in r.stdout and "report" in r.stdout

    def test_version(self):
        r = run_cli("--version")
        assert r.returncode == 0
        assert "Ṛta v" in r.stdout

    def test_check_valid(self, tmp_path):
        sdc = _write(tmp_path / "good.sdc", GOOD_SDC)
        r = run_cli("check", str(sdc))
        assert r.returncode == 0, r.stderr

    def test_check_json_purity(self, tmp_path):
        sdc = _write(tmp_path / "good.sdc", GOOD_SDC)
        r = run_cli("check", str(sdc), "--json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)          # stdout must be pure JSON
        assert data["version"]
        assert "constraint_readiness" in data

    def test_report_html(self, tmp_path):
        sdc = _write(tmp_path / "good.sdc", GOOD_SDC)
        rpt = tmp_path / "report.html"
        r = run_cli("report", "check", str(sdc), "--output", str(rpt))
        assert r.returncode == 0
        html = rpt.read_text(encoding="utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert "NOT an STA timing signoff" in html

    def test_baseline_save_gate_pass_fail(self, tmp_path):
        good = _write(tmp_path / "good.sdc", GOOD_SDC)
        base = tmp_path / "base.json"
        r = run_cli("check", str(good), "--save-baseline", str(base))
        assert r.returncode == 0 and base.exists()

        # Same SDC vs baseline → gate PASS (exit 0)
        r = run_cli("check", str(good), "--baseline", str(base),
                    "--gate", "NO_READINESS_REGRESSION")
        assert r.returncode == 0, r.stderr

        # New blocker vs baseline → gate FAIL (exit 1)
        bad = _write(tmp_path / "bad.sdc",
                     GOOD_SDC + "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]\n")
        r = run_cli("check", str(bad), "--baseline", str(base),
                    "--gate", "NO_READINESS_REGRESSION")
        assert r.returncode == 1

    def test_netlist_aware(self, tmp_path):
        sdc = _write(tmp_path / "d.sdc", GOOD_SDC)
        nl = _write(tmp_path / "top.v",
                    "module top (input clk_core, input din, output dout);\n"
                    "  assign dout = din;\nendmodule\n")
        r = run_cli("check", str(sdc), "--netlist", str(nl))
        assert r.returncode == 0, r.stderr

    def test_engine_failure_never_passes(self, tmp_path):
        """A malformed policy must exit 2 — never a silent PASS."""
        good = _write(tmp_path / "good.sdc", GOOD_SDC)
        pol = _write(tmp_path / "pol.json", "{ not json")
        r = run_cli("check", str(good), "--gate", "CUSTOM", "--gate-policy", str(pol))
        assert r.returncode == 2

    def test_html_report_escapes_sdc_content(self, tmp_path):
        """Untrusted SDC content must render as data in HTML reports."""
        evil = _write(tmp_path / "evil.sdc",
                      "set sdc_version 2.2\n"
                      "create_clock -name clk_good -period 10.0 [get_ports clk_core]\n"
                      "set_input_delay -max 2.0 -clock <script>alert(1)</script> [get_ports din]\n")
        rpt = tmp_path / "evil.html"
        r = run_cli("report", "check", str(evil), "--output", str(rpt))
        assert r.returncode == 0
        html = rpt.read_text(encoding="utf-8")
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        assert "<script>alert(1)</script>" not in html
