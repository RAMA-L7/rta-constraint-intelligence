"""
Phase 9 — coverage metamorphic testing.

Coverage results must be invariant under semantically equivalent formatting:
multiline SDC, variables, scientific notation, comments, CRLF, bus expression
variants, Verilog formatting. If the answer changes, that is a bug.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from design_context import parse_verilog
from design_coverage import analyze_coverage, coverage_findings

V = """
module top ( input clk, input rst_n, input [7:0] data_in, output [7:0] data_out );
    wire [7:0] w;
    flop u1 ( .clk(clk), .d(data_in), .q(w) );
    reg_out u2 ( .d(w), .q(data_out) );
endmodule
module flop ( input clk, input [7:0] d, output [7:0] q );
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

BASE = (
    "set sdc_version 2.2\n"
    "create_clock -name clk -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports {data_in[7:4]}]\n"
    "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"
)


def _sig(sdc: str) -> tuple:
    ctx = parse_verilog(V).context
    cov = analyze_coverage(sdc, ctx)
    s = cov.summary()
    fs = sorted((f["code"], f["msg"]) for f in coverage_findings(sdc, ctx))
    return (s["inputs"], s["outputs"], s["clocks"], s["exceptions"], fs)


def main() -> int:
    base = _sig(BASE)
    variants = {
        "multiline": (
            "set sdc_version 2.2\n"
            "create_clock \\\n    -name clk \\\n    -period 5.0 \\\n    [get_ports clk]\n"
            "set_input_delay \\\n    -max 2.0 \\\n    -min 0.5 \\\n    -clock clk \\\n"
            "    [get_ports {data_in[7:4]}]\n"
            "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"),
        "variable_period": (
            "set CLK_PERIOD 5.0\n"
            "create_clock -name clk -period $CLK_PERIOD [get_ports clk]\n"
            "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports {data_in[7:4]}]\n"
            "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"),
        "scientific_notation": BASE.replace("5.0", "5e0"),
        "comments": (
            "# top-level comment\n"
            "set sdc_version 2.2\n"
            "create_clock -name clk -period 5.0 [get_ports clk] # inline\n"
            "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports {data_in[7:4]}]\n"
            "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"),
        "crlf": BASE.replace("\n", "\r\n"),
        "extra_whitespace": "  " + BASE.replace("\n", "\n  "),
        # NOTE: data_in[*] / data_in[7:0] are NOT equivalent to data_in[7:4]
        # (8 vs 4 bits) — that is a genuine semantic difference, not a
        # metamorphic one, so no such variant is included.
        "braced_ports": (
            "set sdc_version 2.2\n"
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -min 0.5 -clock clk "
            "[get_ports {data_in[7] data_in[6] data_in[5] data_in[4]}]\n"
            "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"),
    }
    checks = 0
    fails = 0
    for name, sdc in variants.items():
        checks += 1
        try:
            got = _sig(sdc)
        except Exception as e:
            print(f"  ❌ {name}: raised {e}")
            fails += 1
            continue
        if got != base:
            print(f"  ❌ {name}: signature differs")
            print(f"       base: {base}")
            print(f"       got:  {got}")
            fails += 1
        else:
            print(f"  ✅ {name}")
    print(f"COVERAGE METAMORPHIC: {checks - fails}/{checks} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
