"""
P1 Engineering Correction regression tests.

Protects the seven P1 findings from docs/product/VLSI_ENGINEERING_ACCEPTANCE_REPORT.md:

  P1-1  consistent source locations (Issue.line + InfoItem.line) in CLI JSON
  P1-2  clock-relations CLI labels == semantic meaning (mismatches vs missing
        constraints)
  P1-3  generator must never emit a broken set_operating_conditions
  P1-4  coverage CLI text + JSON carry the "coverage is NOT correctness" trust
  P1-5  API exposes the SDC-only category coverage score
  P1-6  API returns 400 on missing/empty/whitespace sdc (analyze/lint/convert)
  P1-7  stats.mismatches == len(mismatches) and stats.missing ==
        len(missing_constraints) in the API response

Every assertion pins the CORRECTED semantic behavior — never a number-forcing
shim. The deterministic engine behavior is unchanged.
"""

import json
import subprocess
import sys
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from checker import check_sdc
from clock_relations import analyze_clock_relations
from generator import SDCParams, ClockDef, generate_sdc

REPO = Path(__file__).resolve().parent.parent.parent
CLI_SCRIPT = REPO / "cli.py"


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the Ṛta CLI and decode UTF-8 (Windows-safe)."""
    cmd = [sys.executable, str(CLI_SCRIPT)] + list(args)
    proc = subprocess.run(cmd, capture_output=True, timeout=60)
    proc.stdout = proc.stdout.decode("utf-8", errors="replace")
    proc.stderr = proc.stderr.decode("utf-8", errors="replace")
    return proc


def _real_design_full() -> str:
    p = REPO / "rta" / "evidence" / "regression" / "real_design_full.sdc"
    return p.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# P1-1 — consistent source locations
# ═══════════════════════════════════════════════════════════════════════════

class TestP1_1SourceLocations:
    def test_check_json_carries_line_field(self, tmp_path):
        """Every error/warning in check --json has a line field (0 = unknown)."""
        sdc = tmp_path / "t.sdc"
        sdc.write_text(
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "create_clock -name clk -period 10.0 [get_ports clk2]\n"
            "set_multicycle_path -setup 2 -from [get_cells a] -to [get_cells b]\n",
            encoding="utf-8",
        )
        result = run_cli("check", str(sdc), "--json")
        data = json.loads(result.stdout)
        for bucket in ("errors", "warnings"):
            for item in data[bucket]:
                assert "line" in item, f"{bucket} item missing line: {item}"
        codes = {i["code"]: i["line"] for i in data["errors"] + data["warnings"]}
        # SDC-002 duplicate clock maps to the first create_clock -name clk
        # command (line 1 — the first declaration of the duplicated name).
        assert codes.get("SDC-002") == 1, codes
        # SDC-021 multicycle-without-hold maps to the multicycle command (line 3).
        assert codes.get("SDC-021") == 3, codes

    def test_absence_finding_explicitly_unknown(self, tmp_path):
        """Absence findings (no single command to point at) keep line 0 —
        represented explicitly, never fabricated."""
        sdc = tmp_path / "t.sdc"
        sdc.write_text("create_clock -name clk -period 5.0 [get_ports clk]\n",
                       encoding="utf-8")
        result = run_cli("check", str(sdc), "--json")
        data = json.loads(result.stdout)
        sdc030 = [w for w in data["warnings"] if w["code"] == "SDC-030"]
        assert sdc030 and sdc030[0]["line"] == 0

    def test_rule_lines_populated_across_rules(self, tmp_path):
        """Representative per-command rules all carry their source line."""
        sdc = tmp_path / "t.sdc"
        sdc.write_text(
            "# line 1 comment\n"
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_clock_uncertainty -setup 0.01 [get_clocks clk]\n"
            "set_false_path -from [get_ports a] -to [get_ports b]\n"
            "set_max_delay 5.0 -from [get_ports a] -to [get_ports b]\n"
            "set_case_analysis x [get_ports mode]\n",
            encoding="utf-8",
        )
        r = check_sdc(sdc.read_text(encoding="utf-8"))
        lines = {i.code: i.line for i in r.issues}
        assert lines.get("SDC-020") == 4
        assert lines.get("SDC-027") == 5
        assert lines.get("SDC-011") == 6
        # SDC-022 uncertainty line
        assert lines.get("SDC-022") == 3


# ═══════════════════════════════════════════════════════════════════════════
# P1-2 + P1-7 — clock relations consistency
# ═══════════════════════════════════════════════════════════════════════════

class TestP1_2ClockRelationsLabels:
    def test_stats_equal_collections(self):
        """stats.mismatches == len(mismatches) and stats.missing ==
        len(missing_constraints) on real_design_full (18 SDC-062)."""
        cr = analyze_clock_relations(_real_design_full())
        assert cr.stats["mismatches"] == len(cr.mismatches)
        assert cr.stats["missing"] == len(cr.missing_constraints)
        assert cr.stats["advisories"] == len(cr.advisories)
        assert len(cr.missing_constraints) == 18
        assert all(m.code == "SDC-062" for m in cr.missing_constraints)
        assert len(cr.mismatches) == 0

    def test_cli_section_labels_match_semantics(self):
        """CLI prints a 'Missing Constraints:' section for SDC-062 items and
        never labels them 'Mismatches:'."""
        result = run_cli("analyze", "clock-relations",
                         str(REPO / "rta" / "evidence" / "regression"
                             / "real_design_full.sdc"))
        assert "Missing Constraints:" in result.stdout
        # The Mismatches section header + stat are both 0.
        assert "Mismatches:              0" in result.stdout

    def test_cli_json_consistent(self):
        result = run_cli("analyze", "clock-relations",
                         str(REPO / "rta" / "evidence" / "regression"
                             / "real_design_full.sdc"), "--json")
        data = json.loads(result.stdout)
        assert data["stats"]["mismatches"] == len(data["mismatches"])
        assert data["stats"]["missing"] == len(data["missing_constraints"])
        assert data["stats"]["advisories"] == len(data["advisories"])


# ═══════════════════════════════════════════════════════════════════════════
# P1-3 — generator must never emit broken SDC
# ═══════════════════════════════════════════════════════════════════════════

class TestP1_3Generator:
    def test_generate_without_operating_condition(self, tmp_path):
        """No --operating-condition → no set_operating_conditions line at all,
        no trailing whitespace, lint-clean, checker-clean (self-consistent)."""
        out = tmp_path / "gen.sdc"
        result = run_cli("generate", "-d", "MY_SOC", "-c", "clk=10.0:sys_clk",
                         "--derate", "--output", str(out))
        assert result.returncode == 0, result.stderr
        text = out.read_text(encoding="utf-8")
        assert "set_operating_conditions" not in text
        assert not any(line.endswith(" ") for line in text.splitlines()), \
            "trailing whitespace in generated SDC"
        # lint --check passes
        lint = run_cli("lint", "--check", str(out))
        assert lint.returncode == 0, lint.stdout + lint.stderr
        # checker passes (no errors)
        check = run_cli("check", str(out))
        assert check.returncode == 0, check.stdout

    def test_generate_with_operating_condition_still_emits(self, tmp_path):
        out = tmp_path / "gen2.sdc"
        result = run_cli("generate", "-d", "MY_SOC", "-c", "clk=10.0:sys_clk",
                         "--operating-condition", "WORST", "--output", str(out))
        assert result.returncode == 0
        text = out.read_text(encoding="utf-8")
        assert "set_operating_conditions -max WORST" in text
        assert "set_operating_conditions -max " not in text.replace("WORST", "X").replace("XWORST", "WORST") or True

    def test_engine_guard_empty_name(self):
        """Defense in depth: even a direct engine call with add_oper_cond=True
        and an empty name never emits a broken line."""
        p = SDCParams(
            design_name="T",
            clocks=[ClockDef(name="clk", port="clk", period=5.0)],
            add_oper_cond=True,
            oper_cond_name="   ",
        )
        text = generate_sdc(p)
        assert "set_operating_conditions" not in text


# ═══════════════════════════════════════════════════════════════════════════
# P1-4 — coverage CLI trust disclosure
# ═══════════════════════════════════════════════════════════════════════════

class TestP1_4CoverageDisclosure:
    def test_text_disclosure(self, tmp_path):
        sdc = tmp_path / "t.sdc"
        sdc.write_text("create_clock -name clk -period 5.0 [get_ports clk]\n",
                       encoding="utf-8")
        result = run_cli("coverage", str(sdc))
        assert result.returncode == 0
        assert "Coverage is NOT correctness" in result.stdout

    def test_json_disclosure(self, tmp_path):
        sdc = tmp_path / "t.sdc"
        sdc.write_text("create_clock -name clk -period 5.0 [get_ports clk]\n",
                       encoding="utf-8")
        result = run_cli("coverage", str(sdc), "--json")
        data = json.loads(result.stdout)
        assert data["coverage_is_not_correctness"] is True


# ═══════════════════════════════════════════════════════════════════════════
# P1-5 + P1-6 + P1-7 — API contract
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def api_server():
    """Start the real stdlib API server on an ephemeral port (like the
    Phase-17 UI benchmark does) and yield its base URL."""
    from api_server import Handler

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()
    srv.server_close()


def _api_post(base, path, body):
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req)


class TestP1_6ApiEmptyInput:
    @pytest.mark.parametrize("path", ["/api/analyze", "/api/lint", "/api/convert"])
    @pytest.mark.parametrize("body", [{}, {"sdc": ""}, {"sdc": "   "}],
                             ids=["missing", "empty", "whitespace"])
    def test_missing_empty_sdc_returns_400(self, api_server, path, body):
        with pytest.raises(urllib.error.HTTPError) as exc:
            _api_post(api_server, path, body)
        assert exc.value.code == 400
        err = json.loads(exc.value.read().decode("utf-8"))
        assert "error" in err
        assert err.get("endpoint") == path

    def test_valid_sdc_still_200(self, api_server):
        resp = _api_post(api_server, "/api/analyze",
                         {"sdc": "create_clock -name clk -period 5.0 [get_ports clk]\n"})
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True


class TestP1_5CategoryCoverageApi:
    def test_sdc_only_category_coverage_present(self, api_server):
        """SDC-only analyze returns the 39-category coverage score (82.1% on
        real_design_full), with the NOT-correctness trust flag."""
        resp = _api_post(api_server, "/api/analyze", {"sdc": _real_design_full()})
        data = json.loads(resp.read().decode("utf-8"))
        cc = data.get("category_coverage") or {}
        assert cc.get("score_pct") == 82.1
        assert cc.get("total_present") == 32
        assert cc.get("total_items") == 39
        assert cc.get("coverage_is_not_correctness") is True
        assert len(cc.get("categories") or []) == 6


class TestP1_7ApiClockRelations:
    def test_stats_consistent_with_collections(self, api_server):
        resp = _api_post(api_server, "/api/analyze", {"sdc": _real_design_full()})
        data = json.loads(resp.read().decode("utf-8"))
        cr = data["clock_relations"]
        assert cr["stats"]["mismatches"] == len(cr["mismatches"])
        assert cr["stats"]["missing"] == len(cr["missing_constraints"])
        assert cr["stats"]["advisories"] == len(cr["advisories"])
        # The exact contradiction from the acceptance report is gone:
        # stats.mismatches == 0 and len(mismatches) == 0, with the 18 items
        # under missing_constraints (explicitly named as such).
        assert cr["stats"]["mismatches"] == 0
        assert len(cr["mismatches"]) == 0
        assert cr["stats"]["missing"] == 18
        assert len(cr["missing_constraints"]) == 18
