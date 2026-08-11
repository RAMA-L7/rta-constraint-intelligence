"""
Regression tests for tester-reported issues.

Covers the SDC-008/009 duplication bug, validation-run isolation,
clock pair counting, clock-relation semantics, packaging smoke checks,
and file-vs-text input parity.
"""

import os
import re
import subprocess
import sys
import tempfile

import pytest

from checker import check_sdc
from clock_relations import analyze_clock_relations


# ── A. Duplicate issue test ─────────────────────────────────────────────────────

def _sdc_three_clocks_one_delay():
    """Three clocks; ONE set_input_delay 3.0ns on clk_a (period 2.5ns)."""
    return """set sdc_version 2.2
create_clock -name clk_a -period 2.5 [get_ports clka]
create_clock -name clk_b -period 2.0 [get_ports clkb]
create_clock -name clk_c -period 1.5 [get_ports clkc]
set_input_delay -max 3.0 -clock clk_a [get_ports din]
set_output_delay -max 3.0 -clock clk_a [get_ports dout]
"""


class TestNoDuplicateIssues:
    """A single SDC-008 violation must produce exactly one finding."""

    def test_sdc008_single_finding_per_statement(self):
        """One set_input_delay that violates its own clock → exactly 1 SDC-008."""
        result = check_sdc(_sdc_three_clocks_one_delay())
        sdc_008 = [i for i in result.issues if i.code == "SDC-008"]
        # The delay names clk_a; it must NOT be reported against clk_b/clk_c.
        assert len(sdc_008) == 1, [i.msg for i in sdc_008]
        assert "clk_a" in sdc_008[0].msg

    def test_sdc009_single_finding_per_statement(self):
        """One set_output_delay that violates its own clock → exactly 1 SDC-009."""
        result = check_sdc(_sdc_three_clocks_one_delay())
        sdc_009 = [i for i in result.issues if i.code == "SDC-009"]
        assert len(sdc_009) == 1, [i.msg for i in sdc_009]
        assert "clk_a" in sdc_009[0].msg

    def test_sdc008_has_line_provenance(self):
        """SDC-008 should carry the source line number."""
        result = check_sdc(_sdc_three_clocks_one_delay())
        sdc_008 = [i for i in result.issues if i.code == "SDC-008"]
        assert sdc_008 and sdc_008[0].line > 0

    def test_delay_on_non_violating_clock_not_reported(self):
        """A delay below every period produces zero SDC-008."""
        text = ("create_clock -name clk_a -period 5.0 [get_ports a]\n"
                "create_clock -name clk_b -period 10.0 [get_ports b]\n"
                "set_input_delay -max 1.5 -clock clk_a [get_ports din]\n")
        result = check_sdc(text)
        sdc_008 = [i for i in result.issues if i.code == "SDC-008"]
        assert len(sdc_008) == 0


# ── B. Legitimate repeated-constraint test ─────────────────────────────────────

class TestLegitimateSeparateFindings:
    """Two genuinely separate violations must both be preserved."""

    def test_two_separate_input_delays_two_findings(self):
        text = ("create_clock -name clk_a -period 2.0 [get_ports a]\n"
                "create_clock -name clk_b -period 1.0 [get_ports b]\n"
                "set_input_delay -max 3.0 -clock clk_a [get_ports din_a]\n"
                "set_input_delay -max 2.0 -clock clk_b [get_ports din_b]\n")
        result = check_sdc(text)
        sdc_008 = [i for i in result.issues if i.code == "SDC-008"]
        assert len(sdc_008) == 2
        msgs = " | ".join(i.msg for i in sdc_008)
        assert "clk_a" in msgs and "clk_b" in msgs


# ── C. Repeated validation test ────────────────────────────────────────────────

class TestRepeatedValidation:
    """Re-running the same SDC must produce identical counts (no accumulation)."""

    def test_identical_counts_across_runs(self):
        text = _sdc_three_clocks_one_delay()
        first = check_sdc(text)
        for _ in range(5):
            again = check_sdc(text)
            assert len(again.issues) == len(first.issues)
            assert len(again.info) == len(first.info)
            assert [i.code for i in again.issues] == [i.code for i in first.issues]

    def test_no_cross_file_leak(self):
        """Validating file A then file B must not bleed A's results into B."""
        a = _sdc_three_clocks_one_delay()
        b = ("create_clock -name clk -period 10.0 [get_ports clk]\n"
             "set_input_delay -max 1.0 -clock clk [get_ports din]\n")
        ra = check_sdc(a)
        rb = check_sdc(b)
        # B is clean of SDC-008/009; A has exactly one of each.
        assert len([i for i in rb.issues if i.code in ("SDC-008", "SDC-009")]) == 0
        assert len([i for i in ra.issues if i.code in ("SDC-008", "SDC-009")]) == 2


# ── D. Checker clock-relation aggregation ──────────────────────────────────────

class TestCheckerClockRelationAggregation:
    """Info-level clock-relation findings are aggregated in check_sdc."""

    def test_many_missing_pairs_produce_one_info_item(self):
        clocks = "\n".join(
            f"create_clock -name clk{i:02d} -period {5.0 + i / 10} [get_ports p{i:02d}]"
            for i in range(22)
        )
        result = check_sdc(clocks)
        rel_infos = [i for i in result.info if i.code.startswith("SDC-06")]
        assert len(rel_infos) == 1, len(rel_infos)


# ── E. Clock pair count test ───────────────────────────────────────────────────

class TestClockPairCount:
    """C(n,2) unordered pairs for n clocks."""

    def test_22_clocks_yield_231_pairs(self):
        clocks = "\n".join(
            f"create_clock -name clk{i:02d} -period {5.0 + i / 10} [get_ports p{i:02d}]"
            for i in range(22)
        )
        result = analyze_clock_relations(clocks)
        assert len(result.clocks) == 22
        assert result.stats["pairs"] == 231
        assert len(result.pairs) == 231


# ── F. Clock relation semantics test ───────────────────────────────────────────

class TestClockRelationSemantics:
    """Classification must follow SDC semantics, not raw pair enumeration."""

    def test_related_generated_clocks_are_synchronous(self):
        """A multi-level generated clock chain shares one domain."""
        text = """
create_clock -name clkA -period 5.0 [get_ports clkA]
create_generated_clock -name clkA_div2 -source [get_ports clkA] -divide_by 2 [get_pins g1]
create_generated_clock -name clkA_div4 -source [get_pins g1] -divide_by 2 [get_pins g2]
"""
        result = analyze_clock_relations(text)
        by_pair = {(p.clock_a, p.clock_b): p for p in result.pairs}
        # every pair in the derived chain must be synchronous
        assert by_pair[("clkA", "clkA_div2")].inferred_relation == "synchronous"
        assert by_pair[("clkA", "clkA_div4")].inferred_relation == "synchronous"
        assert by_pair[("clkA_div2", "clkA_div4")].inferred_relation == "synchronous"

    def test_same_port_different_period_physically_exclusive(self):
        text = ("create_clock -name CLKA -period 1.00 [get_ports CLKAB]\n"
                "create_clock -name CLKB -period 1.50 [get_ports CLKAB] -add\n")
        result = analyze_clock_relations(text)
        pair = result.pairs[0]
        assert pair.inferred_relation == "physically_exclusive"

    def test_declared_asynchronous_groups_counted(self):
        text = ("create_clock -name a -period 5.0 [get_ports a]\n"
                "create_clock -name b -period 10.0 [get_ports b]\n"
                "set_clock_groups -asynchronous -group [get_clocks a] -group [get_clocks b]\n")
        result = analyze_clock_relations(text)
        assert len(result.existing_groups) == 1
        # Declared async pair → not a warning mismatch.
        warnings = [m for m in result.mismatches if m.severity == "warning"]
        assert warnings == []

    def test_infer_relation_backward_compatible_signature(self):
        """infer_relation(a, b) without clocks still works."""
        from clock_relations import infer_relation, ClockDefCK
        a = ClockDefCK(name="a", period=5.0, source_port="pa")
        b = ClockDefCK(name="b", period=10.0, source_port="pb")
        pair = infer_relation(a, b)
        assert pair.inferred_relation == "asynchronous"

    def test_undefined_clock_in_io_delay_no_fallback(self):
        """P0 fix (SDC-046): -clock referencing an undefined clock must emit
        SDC-046 and MUST NOT silently fall back to the tightest defined clock."""
        from checker import check_sdc
        r = check_sdc("""create_clock -name clk_a -period 10.0 [get_ports clk]
set_input_delay -max 12.0 -min 0.5 -clock nonexistent_clk [get_ports data_in]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
""")
        assert any(i.code == "SDC-046" for i in r.issues)
        assert not any(i.code == "SDC-008" for i in r.issues), "silent fallback regression"

    def test_undefined_master_clock_and_group_refs(self):
        from checker import check_sdc
        r = check_sdc("""create_clock -name clk_a -period 10.0 [get_ports clk]
create_generated_clock -name div2 -master_clock ghost -source [get_ports clk] -divide_by 2 [get_pins U/CLK]
set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks ghost2]
set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
""")
        codes = {i.code for i in r.issues}
        assert "SDC-047" in codes and "SDC-048" in codes

    def test_contradictory_case_analysis_dual_provenance(self):
        from checker import check_sdc
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_case_analysis 0 [get_ports mode]
set_case_analysis 1 [get_ports mode]
""")
        sdc049 = [i for i in r.issues if i.code == "SDC-049"]
        assert sdc049 and sdc049[0].line2  # both source lines reported

    def test_netlist_dependent_refs_not_flagged(self):
        from checker import check_sdc
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock [get_ports clk] [all_inputs]
set_clock_groups -asynchronous -group [get_clocks c] -group [get_clocks *]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        assert not any(i.code in ("SDC-046", "SDC-047", "SDC-048") for i in r.issues)

    def test_wildcard_get_clocks_not_flagged_undefined(self):
        """Reviewer fix: [get_clocks *] and {clk*} refs are netlist-dependent
        and must never fire SDC-046/047/048."""
        from checker import check_sdc
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock [get_clocks *] [all_inputs]
set_clock_groups -asynchronous -group [get_clocks c] -group [get_clocks {clk* sync*}]
create_generated_clock -name g -master_clock [get_clocks *] -source [get_ports clk] -divide_by 2 [get_pins U/B]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        assert not any(i.code in ("SDC-046", "SDC-047", "SDC-048") for i in r.issues)

    def test_legal_io_constraint_multiples_not_conflicts(self):
        from checker import check_sdc
        r = check_sdc("""create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 2.0 -clock c [get_ports din]
set_input_delay -min 0.5 -clock c [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
""")
        assert not any(i.code == "SDC-049" for i in r.issues)
        assert not any(i.code in ("SDC-046", "SDC-047", "SDC-048") for i in r.issues)

    def test_large_design_relations_fast_and_correct(self):
        """Phase 4 perf: ancestor sets are precomputed once, so a design with
        hundreds of clocks analyzes in O(N^2) not O(N^3). Also verifies the
        pair count formula N*(N-1)/2."""
        import time
        from clock_relations import analyze_clock_relations
        n = 150
        lines = [f"create_clock -name c{i} -period 5.0 [get_ports p{i}]" for i in range(n)]
        text = "\n".join(lines)
        t0 = time.perf_counter()
        res = analyze_clock_relations(text)
        elapsed = time.perf_counter() - t0
        assert len(res.clocks) == n
        assert len(res.pairs) == n * (n - 1) // 2
        assert elapsed < 5.0, f"clock relations too slow: {elapsed:.1f}s (O(N^3) regression?)"


# ── G. Packaging smoke tests ───────────────────────────────────────────────────

class TestPackagingSmoke:
    """Guards the pip-install / clean-clone fixes."""

    @staticmethod
    def _pyproject_modules():
        """Parse the py-modules list from pyproject.toml (no tomllib on 3.10)."""
        with open("pyproject.toml", encoding="utf-8") as f:
            text = f.read()
        block = re.search(r"py-modules\s*=\s*\[(.*?)\]", text, re.S).group(1)
        return re.findall(r'"([^"]+)"', block)

    def test_pyproject_uses_valid_build_backend(self):
        with open("pyproject.toml", encoding="utf-8") as f:
            text = f.read()
        assert 'build-backend = "setuptools.build_meta"' in text
        assert "setuptools.backends._legacy" not in text

    def test_requirements_include_pyyaml(self):
        with open("requirements.txt", encoding="utf-8") as f:
            reqs = f.read()
        assert "pyyaml" in reqs.lower()

    def test_all_package_modules_import(self):
        """Every py-module declared in pyproject must import cleanly."""
        for mod in self._pyproject_modules():
            __import__(mod)

    def test_cli_entrypoint_runs_help(self):
        """The documented entry point should parse and print help."""
        proc = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0
        assert "check" in proc.stdout and "web" in proc.stdout

    def test_cli_web_resolves_app_path(self):
        """cmd_web must resolve api_server.py (Phase 17 workspace) relative to
        the repo, not the cwd — a clean install or any-cwd invocation works."""
        import cli
        from types import SimpleNamespace
        # cmd_web spawns a subprocess and opens a browser; monkeypatch both to
        # capture the server command without launching anything. The local
        # `import webbrowser` inside cmd_web is intercepted via sys.modules.
        calls = {}

        def fake_run(cmd, **_):
            calls["cmd"] = cmd
            return SimpleNamespace(returncode=0)

        orig_run = subprocess.run
        orig_wb = sys.modules.get("webbrowser")
        fake_wb = type("WB", (), {"open": staticmethod(lambda url: True)})()
        try:
            import subprocess as sp
            sp.run = fake_run
            sys.modules["webbrowser"] = fake_wb
            cli.cmd_web(SimpleNamespace())
        finally:
            sp.run = orig_run
            if orig_wb is None:
                sys.modules.pop("webbrowser", None)
            else:
                sys.modules["webbrowser"] = orig_wb
        cmd = calls.get("cmd", [])
        # [sys.executable, <abs api_server.py>, <port>]
        assert len(cmd) == 3
        assert cmd[1].endswith("api_server.py")
        assert os.path.isabs(cmd[1])
        assert os.path.exists(cmd[1])
        assert cmd[2] == "8501"


# ── H/I. File input vs text input parity ───────────────────────────────────────

class TestInputParity:
    """Uploading a file vs pasting the same text must give identical results."""

    def test_file_and_text_equivalent(self):
        text = """set sdc_version 2.2
create_clock -name clk -period 2.0 [get_ports clk]
set_input_delay -max 3.0 -clock clk [get_ports din]
"""
        with tempfile.NamedTemporaryFile("w", suffix=".sdc", delete=False,
                                         encoding="utf-8") as f:
            f.write(text)
            path = f.name
        try:
            with open(path, encoding="utf-8") as fh:
                file_text = fh.read()
        finally:
            os.unlink(path)
        # The app decodes uploads with errors="replace"; emulate that.
        encoded = file_text.encode("utf-8").decode("utf-8", errors="replace")
        r_file = check_sdc(encoded)
        r_paste = check_sdc(text)
        assert [i.code for i in r_file.issues] == [i.code for i in r_paste.issues]
        assert len(r_file.info) == len(r_paste.info)
