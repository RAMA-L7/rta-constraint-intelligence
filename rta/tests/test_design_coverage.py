"""
Phase 9 — design_coverage.py unit tests (design-aware constraint coverage).

Covers the structural port classifier, bus-aware coverage, timing-exception
endpoint status, clock structural coverage, SDC-064/065/066 findings, and the
COVERAGE != CORRECTNESS separation. SDC-only behavior is untouched (covered
elsewhere).
"""

import pytest

from design_context import parse_verilog
from design_coverage import (
    analyze_coverage, coverage_findings, classify_port_structure,
    CONSTRAINED, UNCONSTRAINED, PARTIALLY_CONSTRAINED, EXEMPT, UNKNOWN,
    NOT_APPLICABLE,
)

V_FULL = """
module top (
    input clk,
    input rst_n,
    input [7:0] data_in,
    input scan_en,
    output [7:0] data_out,
    output [3:0] status
);
    wire [7:0] w;
    flop u1 ( .clk(clk), .d(data_in), .q(w), .rstn(rst_n), .se(scan_en) );
    reg_out u2 ( .d(w), .q(data_out) );
    assign status = w[3:0];
endmodule

module flop ( input clk, input [7:0] d, output [7:0] q, input rstn, input se );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule

module reg_out ( input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(*) r = d;
    assign q = r;
endmodule
"""

SDC_FULL = (
    "set sdc_version 2.2\n"
    "create_clock -name clk -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]\n"
    "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"
    "set_false_path -from [get_ports scan_en] -to [get_ports data_out]\n"
)


@pytest.fixture(scope="module")
def ctx():
    o = parse_verilog(V_FULL)
    assert not o.errors, o.errors
    return o.context


class TestStructuralClassification:
    def test_clock_port_structural(self, ctx):
        cls, ev = classify_port_structure("clk", ctx)
        assert cls == "CLOCK"
        assert "pin" in ev

    def test_data_input_structural(self, ctx):
        cls, ev = classify_port_structure("data_in", ctx)
        assert cls == "DATA"
        assert "pin" in ev

    def test_data_output_structural(self, ctx):
        cls, ev = classify_port_structure("data_out", ctx)
        assert cls == "DATA"

    def test_reset_structural(self, ctx):
        cls, ev = classify_port_structure("rst_n", ctx)
        assert cls == "RESET"

    def test_scan_structural(self, ctx):
        cls, ev = classify_port_structure("scan_en", ctx)
        assert cls in ("SCAN", "CONTROL")

    def test_unknown_without_connections(self):
        o = parse_verilog("module top ( input aaa_zzz ); endmodule\n")
        cls, ev = classify_port_structure("aaa_zzz", o.context)
        assert cls == "UNKNOWN"


class TestPortCoverage:
    def test_full_coverage(self, ctx):
        cov = analyze_coverage(SDC_FULL, ctx)
        by_name = {p.name: p for p in cov.inputs + cov.outputs}
        assert by_name["data_in"].status == CONSTRAINED
        assert by_name["data_out"].status == CONSTRAINED
        assert by_name["clk"].status == EXEMPT
        assert by_name["rst_n"].status == EXEMPT
        assert by_name["scan_en"].status == EXEMPT

    def test_unconstrained_input(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_output_delay -max 2.0 -clock clk [get_ports data_out]\n"
            # data_in never constrained
        )
        cov = analyze_coverage(sdc, ctx)
        di = next(p for p in cov.inputs if p.name == "data_in")
        assert di.status == UNCONSTRAINED

    def test_unconstrained_output(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports data_in]\n"
            # data_out never constrained
        )
        cov = analyze_coverage(sdc, ctx)
        do = next(p for p in cov.outputs if p.name == "data_out")
        assert do.status == UNCONSTRAINED

    def test_partial_bus_coverage(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports {data_in[3:0]}]\n"
        )
        cov = analyze_coverage(sdc, ctx)
        di = next(p for p in cov.inputs if p.name == "data_in")
        assert di.status == PARTIALLY_CONSTRAINED

    def test_whole_bus_wildcard_bit(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports data_in[*]]\n"
        )
        cov = analyze_coverage(sdc, ctx)
        di = next(p for p in cov.inputs if p.name == "data_in")
        assert di.status == CONSTRAINED

    def test_inout_conservative(self):
        o = parse_verilog("module top ( inout [7:0] bidir, input clk ); endmodule\n")
        cov = analyze_coverage("create_clock -name clk -period 5 [get_ports clk]\n", o.context)
        bi = next(p for p in cov.inputs if p.name == "bidir")
        # inout ports are classified INOUT and treated as EXEMPT (conservative:
        # no I/O delay expected by convention; never reported unconstrained)
        assert bi.status == EXEMPT
        assert bi.port_class == "INOUT"


class TestClockCoverage:
    def test_clock_structural_resolution(self, ctx):
        cov = analyze_coverage(SDC_FULL, ctx)
        c = next(c for c in cov.clocks if c.name == "clk")
        assert c.structurally_resolved
        assert c.fanout == 1  # drives u1/clk
        assert c.status in ("RESOLVED", "NO_STRUCTURAL_FANOUT")

    def test_virtual_clock(self, ctx):
        sdc = "create_clock -name vclk -period 10.0\n"
        cov = analyze_coverage(sdc, ctx)
        c = next(c for c in cov.clocks if c.name == "vclk")
        assert c.is_virtual
        assert not c.structurally_resolved

    def test_generated_clock_source_resolved(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "create_generated_clock -name div2 -source [get_ports clk] "
            "-divide_by 2 [get_pins u1/q]\n"
        )
        cov = analyze_coverage(sdc, ctx)
        gc = next(c for c in cov.clocks if c.name == "div2")
        assert gc.structurally_resolved


class TestExceptionCoverage:
    def test_exception_endpoints_resolved(self, ctx):
        cov = analyze_coverage(SDC_FULL, ctx)
        fp = next(e for e in cov.exceptions if e.command == "set_false_path")
        assert fp.status == "OBJECTS_RESOLVED"

    def test_exception_empty_collection(self, ctx):
        sdc = SDC_FULL + "set_false_path -from [get_ports debug_*] -to [get_ports data_out]\n"
        cov = analyze_coverage(sdc, ctx)
        empties = [e for e in cov.exceptions if e.status == "EMPTY_COLLECTION"]
        assert empties

    def test_exception_missing_explicit_object(self, ctx):
        sdc = SDC_FULL + "set_false_path -from [get_ports bogus] -to [get_ports data_out]\n"
        cov = analyze_coverage(sdc, ctx)
        assert any(e.status == "PARTIALLY_RESOLVED" for e in cov.exceptions)


class TestFindings:
    def test_sdc_064_unconstrained_input(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_output_delay -max 2.0 -clock clk [get_ports data_out]\n"
        )
        f = coverage_findings(sdc, ctx)
        assert any(x["code"] == "SDC-064" for x in f)
        assert not any(x["code"] == "SDC-065" for x in f)  # data_out IS constrained

    def test_sdc_065_unconstrained_output(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports data_in]\n"
        )
        f = coverage_findings(sdc, ctx)
        assert any(x["code"] == "SDC-065" for x in f)
        assert not any(x["code"] == "SDC-064" for x in f)

    def test_sdc_066_partial_bus(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports {data_in[3:0]}]\n"
        )
        f = coverage_findings(sdc, ctx)
        assert any(x["code"] == "SDC-066" for x in f)

    def test_no_findings_when_fully_constrained(self, ctx):
        assert coverage_findings(SDC_FULL, ctx) == []

    def test_exempt_ports_never_findings(self, ctx):
        sdc = "create_clock -name clk -period 5.0 [get_ports clk]\n"
        f = coverage_findings(sdc, ctx)
        # clk/rst_n/scan_en are exempt; data ports are unconstrained → SDC-064/065
        assert all(x["code"] in ("SDC-064", "SDC-065") for x in f)
        assert not any("clk" in x["msg"] for x in f)

    def test_finding_line_provenance(self, ctx):
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports data_in]\n"
        )
        f = coverage_findings(sdc, ctx)
        sdc65 = [x for x in f if x["code"] == "SDC-065"]
        assert sdc65 and sdc65[0]["line"] == 0  # no covering delay → no line ref


class TestCoverageSummary:
    def test_summary_counts(self, ctx):
        cov = analyze_coverage(SDC_FULL, ctx)
        s = cov.summary()
        assert s["inputs"]["total"] == 4          # clk, rst_n, data_in, scan_en
        assert s["inputs"]["exempt"] == 3
        assert s["inputs"]["constrained"] == 1    # data_in
        assert s["outputs"]["total"] == 2
        assert s["outputs"]["constrained"] == 1   # data_out
        assert s["clocks"]["defined"] == 1
        assert s["exceptions"]["total"] == 1
        assert s["coverage_is_not_correctness"] is True

    def test_summary_machine_readable(self, ctx):
        cov = analyze_coverage(SDC_FULL, ctx)
        d = cov.to_dict()
        assert "summary" in d and "inputs" in d and "clocks" in d


class TestCheckerIntegration:
    V = """
    module top ( input clk, input [7:0] data_in, output [7:0] data_out );
        wire [7:0] w;
        flop u1 ( .clk(clk), .d(data_in), .q(w) );
        assign data_out = w;
    endmodule
    module flop ( input clk, input [7:0] d, output [7:0] q );
        reg [7:0] r;
        always @(posedge clk) r <= d;
        assign q = r;
    endmodule
    """

    SDC = (
        "set sdc_version 2.2\n"
        "create_clock -name clk -period 5.0 [get_ports clk]\n"
        "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]\n"
        "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"
    )

    def test_coverage_attached_only_with_context(self):
        from checker import check_sdc
        ctx = parse_verilog(self.V).context
        r = check_sdc(self.SDC, context=ctx)
        assert r.coverage["summary"]["inputs"]["total"] == 2
        assert r.coverage["summary"]["outputs"]["total"] == 1
        r2 = check_sdc(self.SDC)
        assert r2.coverage == {}

    def test_sdc_only_never_emits_coverage_rules(self):
        from checker import check_sdc
        r = check_sdc(self.SDC)
        assert not any(i.code in ("SDC-064", "SDC-065", "SDC-066") for i in r.issues)

    def test_design_aware_can_emit_coverage_rules(self):
        from checker import check_sdc
        ctx = parse_verilog(self.V).context
        sdc = self.SDC.replace("set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]",
                               "")
        r = check_sdc(sdc, context=ctx)
        assert any(i.code == "SDC-064" for i in r.issues)
