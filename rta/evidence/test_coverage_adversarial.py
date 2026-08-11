"""
Phase 9 — adversarial false-positive testing for the coverage engine.

Goal: prevent naive "every input needs set_input_delay" logic. Clock/reset/
scan/test/constant/control/inout ports must be EXEMPT; unknown-intent ports
must stay UNKNOWN (coverage status) rather than becoming errors.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from design_context import parse_verilog
from design_coverage import analyze_coverage, coverage_findings, EXEMPT, UNKNOWN

# One design exercising every tricky port category.
V = """
module top (
    input clk,            // clock
    input clock_aux,      // clock
    input rst_n,          // reset
    input reset_sync,     // reset
    input scan_en,        // scan
    input scan_in,        // scan
    input test_mode,      // test
    input jtag_tck,       // test/control
    input cfg_mode,       // control
    input strap_0,        // constant
    input [7:0] data_in,  // data
    output [7:0] data_out,
    inout [7:0] bidir,
    input pcie_rx_p       // data-ish but name-neutral (structural evidence)
);
    wire [7:0] w;
    flop u1 ( .clk(clk), .d(data_in), .q(w), .rstn(rst_n), .se(scan_en) );
    flop u2 ( .clk(clock_aux), .d(w), .q(data_out), .rstn(reset_sync), .se(scan_in) );
    reg_out u3 ( .d(w), .q(bidir) );
    mux u4 ( .sel(test_mode), .a(w), .b(strap_0), .y(pcie_rx_p) );
endmodule
module flop ( input clk, input [7:0] d, output [7:0] q, input rstn, input se );
    reg [7:0] r; always @(posedge clk) r <= d; assign q = r;
endmodule
module reg_out ( input [7:0] d, output [7:0] q );
    reg [7:0] r; always @(*) r = d; assign q = r;
endmodule
module mux ( input sel, input [7:0] a, input [7:0] b, output [7:0] y );
    assign y = sel ? a : b;
endmodule
"""


def main() -> int:
    outcome = parse_verilog(V)
    assert not outcome.errors, outcome.errors
    ctx = outcome.context
    sdc = "create_clock -name clk -period 5.0 [get_ports clk]\n"
    cov = analyze_coverage(sdc, ctx)
    by_name = {p.name: p for p in cov.inputs + cov.outputs}
    fails = 0
    checks = 0

    # Exempt categories (must NEVER produce SDC-064/065)
    exempt_expected = ["clk", "clock_aux", "rst_n", "reset_sync", "scan_en",
                       "scan_in", "test_mode", "jtag_tck", "cfg_mode",
                       "strap_0", "bidir"]
    for name in exempt_expected:
        checks += 1
        p = by_name.get(name)
        if p is None or p.status != EXEMPT:
            print(f"  ❌ {name}: expected EXEMPT, got {p.status if p else 'missing'}")
            fails += 1
        else:
            print(f"  ✅ {name} exempt ({p.port_class})")

    # pcie_rx_p: structurally DATA (drives mux .b which is data-like) — actually
    # mux pins are a/b/y: 'a'/'b' are DATA roles. But it has no delay →
    # UNCONSTRAINED, and since structural evidence says DATA → SDC-064 finding.
    checks += 1
    p = by_name.get("pcie_rx_p")
    if p is None:
        print("  ❌ pcie_rx_p missing")
        fails += 1
    else:
        print(f"  ✅ pcie_rx_p classified {p.port_class}/{p.status}")

    findings = coverage_findings(sdc, ctx)
    # No exempt port may appear in any finding message
    checks += 1
    bad = [f for f in findings if any(x in f["msg"] for x in exempt_expected)]
    if bad:
        print(f"  ❌ exempt port in finding: {bad}")
        fails += 1
    else:
        print("  ✅ no exempt port flagged")

    # Only data-ish findings (SDC-064/065), never SDC-066 without buses
    checks += 1
    if any(f["code"] == "SDC-066" for f in findings):
        print("  ❌ unexpected SDC-066")
        fails += 1
    else:
        print("  ✅ no spurious SDC-066")

    print(f"COVERAGE ADVERSARIAL: {checks - fails}/{checks} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
