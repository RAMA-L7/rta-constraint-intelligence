"""
Presentation-layer tests for Context-Aware Constraint Analysis.

Proves the machine-readable finding context renders cleanly and
deterministically in the HTML report, WITHOUT changing analysis logic:

  - context present  -> compact "Evidence" block with human labels
  - absent values    -> shown as "not available", never invented
  - booleans         -> yes/no
  - list-of-pairs    -> L<line>→<value> form
  - no context       -> no Evidence block at all
  - same input       -> byte-identical report output
"""

import pytest

from checker import check_sdc
from rta.tools.report import reporter


FIXTURE_SDC = (
    "create_clock -name PLL0 -period 0.8333 [get_ports p]\n"
    "set_input_delay 20.0 -clock PLL0 [get_ports DATA_IN]\n"
)


@pytest.fixture(scope="module")
def result():
    return check_sdc(FIXTURE_SDC)


class TestContextBrief:

    def test_evidence_block_renders_labels(self):
        i = next(i for i in check_sdc(FIXTURE_SDC).errors if i.code == "SDC-008")
        html = reporter._context_brief(i.context)
        assert "Evidence:" in html
        assert "Referenced clock" in html
        assert "PLL0" in html
        assert "Clock period" in html
        assert "Netlist available" in html
        # Availability is stored as an explicit YES/NO state string.
        assert "NO" in html

    def test_none_value_renders_not_available(self):
        ctx = {"referenced_clock": None}
        html = reporter._context_brief(ctx)
        assert "not available" in html
        assert "None" not in html

    def test_boolean_values_render_yes_no(self):
        html = reporter._context_brief({"datapath_only": False,
                                        "hold_fix_found": True})
        assert ">no<" in html.replace("</dd>", "<") or "no" in html
        assert "yes" in html
        assert "False" not in html and "True" not in html

    def test_pair_lists_render_line_form(self):
        html = reporter._context_brief({"values_by_line": [[12, "0.1"],
                                                           [13, "0.2"]]})
        assert "L12→0.1" in html and "L13→0.2" in html

    def test_empty_context_no_block(self):
        assert reporter._context_brief(None) == ""
        assert reporter._context_brief({}) == ""


class TestReportIntegration:

    def test_check_report_contains_evidence(self, result):
        html = reporter.generate_check_report(result, "test.sdc")
        assert "Evidence:" in html
        assert "Referenced clock" in html

    def test_findings_without_context_have_no_evidence(self):
        text = ("create_clock -name dupe -period 5 [get_ports a]\n"
                "create_clock -name dupe -period 10 [get_ports b]\n")
        html = reporter.generate_check_report(check_sdc(text), "dup.sdc")
        # SDC-002 carries no context -> no Evidence blocks anywhere.
        assert "Evidence:" not in html

    def test_report_deterministic_with_context(self, result):
        h1 = reporter.generate_check_report(check_sdc(FIXTURE_SDC), "t.sdc")
        h2 = reporter.generate_check_report(check_sdc(FIXTURE_SDC), "t.sdc")
        assert h1 == h2

    def test_html_escaping_in_values(self):
        html = reporter._context_brief({"affected_object": "<script>x</script>"})
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
