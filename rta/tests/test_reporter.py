"""
Tests for the HTML Report Generator module.
"""

import pytest
from reporter import (
    generate_check_report, generate_diff_report,
    generate_clock_report, generate_coverage_report,
    generate_rules_report,
)

from checker import check_sdc
from coverage import parse_sdc_coverage
from clock_relations import analyze_clock_relations
from constraint_diff import analyze_constraint_changes
from rules_registry import get_all_rules


class TestGenerateCheckReport:
    """Tests for the SDC quality check report."""

    def test_generates_html(self, minimal_sdc):
        result = check_sdc(minimal_sdc)
        html = generate_check_report(result, "test.sdc")
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")
        assert html.strip().endswith("</html>")

    def test_contains_title(self, minimal_sdc):
        result = check_sdc(minimal_sdc)
        html = generate_check_report(result, "test.sdc")
        assert "SDC Quality Report" in html
        assert "test.sdc" in html

    def test_contains_version(self, minimal_sdc):
        result = check_sdc(minimal_sdc)
        html = generate_check_report(result, "test.sdc")
        assert "Ṛta" in html

    def test_contains_metrics(self, minimal_sdc):
        result = check_sdc(minimal_sdc)
        html = generate_check_report(result, "test.sdc")
        # Should have some metric numbers
        assert "issues" in html.lower() or "error" in html.lower() or "warn" in html.lower()

    def test_verbose_includes_info(self, minimal_sdc):
        result = check_sdc(minimal_sdc)
        html = generate_check_report(result, "test.sdc", verbose=True)
        assert html is not None

    def test_inline_css_present(self, minimal_sdc):
        """Reports should have inline CSS, no external references."""
        result = check_sdc(minimal_sdc)
        html = generate_check_report(result, "test.sdc")
        assert "<style>" in html
        assert '.metrics' in html or '.badge' in html


class TestGenerateDiffReport:
    """Tests for the change impact report."""

    def test_generates_html(self):
        v1 = "create_clock -name clk -period 5.0 [get_ports clk]"
        v2 = "create_clock -name clk -period 10.0 [get_ports clk]"
        result = analyze_constraint_changes(v1, v2)
        html = generate_diff_report(result, "v1.sdc", "v2.sdc")
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_contains_version(self):
        v1 = ""
        v2 = "create_clock -name clk -period 5.0"
        result = analyze_constraint_changes(v1, v2)
        html = generate_diff_report(result, "old.sdc", "new.sdc")
        assert "Ṛta" in html

    def test_contains_file_names(self):
        v1 = ""
        v2 = "create_clock -name clk -period 5.0"
        result = analyze_constraint_changes(v1, v2)
        html = generate_diff_report(result, "old.sdc", "new.sdc")
        assert "old.sdc" in html
        assert "new.sdc" in html

    def test_inline_css_present(self):
        v1 = ""
        v2 = "create_clock -name clk -period 5.0"
        result = analyze_constraint_changes(v1, v2)
        html = generate_diff_report(result, "old.sdc", "new.sdc")
        assert "<style>" in html


class TestGenerateClockReport:
    """Tests for the clock relations report."""

    def test_generates_html(self, full_sdc):
        result = analyze_clock_relations(full_sdc)
        html = generate_clock_report(result, "full.sdc")
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_contains_version(self, full_sdc):
        result = analyze_clock_relations(full_sdc)
        html = generate_clock_report(result, "full.sdc")
        assert "Ṛta" in html

    def test_empty_result(self):
        result = analyze_clock_relations("")
        html = generate_clock_report(result, "empty.sdc")
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_inline_css_present(self, full_sdc):
        result = analyze_clock_relations(full_sdc)
        html = generate_clock_report(result, "full.sdc")
        assert "<style>" in html


class TestGenerateCoverageReport:
    """Tests for the coverage report."""

    def test_generates_html(self, full_sdc):
        result = parse_sdc_coverage(full_sdc, "full.sdc")
        html = generate_coverage_report(result, "full.sdc")
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_contains_score(self, full_sdc):
        result = parse_sdc_coverage(full_sdc, "full.sdc")
        html = generate_coverage_report(result, "full.sdc")
        assert "Score" in html or "Coverage" in html

    def test_empty_result(self):
        result = parse_sdc_coverage("")
        html = generate_coverage_report(result, "empty.sdc")
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_inline_css_present(self, full_sdc):
        result = parse_sdc_coverage(full_sdc, "full.sdc")
        html = generate_coverage_report(result, "full.sdc")
        assert "<style>" in html


class TestGenerateRulesReport:
    """Tests for the rules registry report."""

    def test_generates_html(self):
        rules = get_all_rules()
        html = generate_rules_report(rules, "All Rules")
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_contains_version(self):
        html = generate_rules_report([], "Empty")
        assert "Ṛta" in html

    def test_contains_rule_codes(self):
        rules = get_all_rules()
        html = generate_rules_report(rules[:5], "Test")
        assert "SDC" in html or "CHG" in html


class TestReportProperties:
    """Properties that all reports should share."""

    @pytest.fixture(params=["check", "clock", "coverage"])
    def report_type(self, request):
        return request.param

    def test_all_reports_have_doctype(self, full_sdc):
        """Every report generator should produce valid HTML."""
        results = {}

        # Check report
        from checker import check_sdc
        check_result = check_sdc(full_sdc)
        results["check"] = generate_check_report(check_result, "full.sdc")

        # Clock report
        from clock_relations import analyze_clock_relations
        cr_result = analyze_clock_relations(full_sdc)
        results["clock"] = generate_clock_report(cr_result, "full.sdc")

        # Coverage report
        from coverage import parse_sdc_coverage
        cov_result = parse_sdc_coverage(full_sdc, "full.sdc")
        results["coverage"] = generate_coverage_report(cov_result, "full.sdc")

        for name, html in results.items():
            assert html.strip().startswith("<!DOCTYPE html>"), f"{name} report missing doctype"
            assert html.strip().endswith("</html>"), f"{name} report missing html close"
            assert "<style>" in html, f"{name} report missing CSS"

    def test_no_external_dependencies(self, full_sdc):
        """All reports must be self-contained (no CDN, no external URLs)."""
        from checker import check_sdc
        result = check_sdc(full_sdc)
        html = generate_check_report(result, "full.sdc")

        forbidden = ["http://", "https://", "src=", "@import"]
        # Exceptions: the generated date line mentioning a URL, or Ṛta reference URLs
        # Only check that there's no <script> or <link> to external resources
        assert "<script" not in html, "Report contains external JavaScript"
        assert '<link rel="stylesheet"' not in html, "Report uses external stylesheet"

    def test_issue_messages_html_escaped(self):
        """User-controlled text in findings must render as data, never markup.

        Phase 14 security audit: SDC content such as a clock name containing
        '<script>' flows into issue messages. If a report is opened in a browser
        with that markup unescaped, the SDC becomes a stored-XSS vector. The
        reporter must HTML-escape everything it interpolates.
        """
        text = (
            "set sdc_version 2.2\n"
            "create_clock -name clk_good -period 10.0 [get_ports clk_core]\n"
            "set_input_delay -max 2.0 -clock <script>alert(1)</script> [get_ports din]\n"
        )
        result = check_sdc(text)
        assert any(i.code == "SDC-046" for i in result.issues), \
            "expected an undefined-clock-reference finding"
        html = generate_check_report(result, "evil.sdc")
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        assert "<script>alert(1)</script>" not in html

    def test_object_names_html_escaped(self, full_sdc):
        """Design-aware coverage table must escape port/object names."""
        from design_context import parse_verilog
        netlist = (
            "module top (input clk_core, input <b>din</b>, output dout);\n"
            "  assign dout = din;\nendmodule\n"
        )
        ctx = parse_verilog(netlist).context
        sdc = (
            "set sdc_version 2.2\n"
            "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n"
            "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
            "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n"
        )
        result = check_sdc(sdc, context=ctx)
        html = generate_check_report(result, "evil.sdc")
        assert "&lt;b&gt;din&lt;/b&gt;" in html
        assert "<b>din</b>" not in html
