#!/usr/bin/env python3
"""
Phase 8 — Netlist-aware metamorphic tests.

Equivalent formatting must produce identical design-context facts and
identical design-aware validation results:
  - whitespace / line breaks / comments in Verilog
  - ANSI vs non-ANSI port lists
  - named vs positional connections (when module port order is known)
  - equivalent SDC formatting (multiline, CRLF, comments)

Usage: python benchmarks/test_netlist_metamorphic.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc                                   # noqa: E402
from design_context import parse_verilog, validate_design_references  # noqa: E402

V_BASE = """
module top ( input clk, input [7:0] data_in, output [7:0] data_out );
    wire [7:0] w;
    flop u1 ( .clk(clk), .d(data_in), .q(w) );
    flop u2 ( .clk(clk), .d(w), .q(data_out) );
endmodule
module flop ( input clk, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule
"""

# Same design: different whitespace, comments, line breaks
V_VARIANT = """
// comment line
module top
(
    input clk,          // clock
    input  [7:0] data_in ,
    output [7:0] data_out
) ;
    wire [7:0] w ;
    flop u1 ( .clk( clk ) , .d( data_in ) , .q( w ) ) ;
    /* block
       comment */
    flop u2 ( .clk(clk), .d(w), .q(data_out) ) ;
endmodule

module flop ( input clk , input [7:0] d , output [7:0] q ) ;
    reg [7:0] r ;
    always @( posedge clk ) r <= d ;
    assign q = r ;
endmodule
"""

SDC_BASE = (
    "set sdc_version 2.2\n"
    "create_clock -name clk -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]\n"
    "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"
)

SDC_VARIANT = (
    "set sdc_version 2.2\n"
    "create_clock -name clk -period 5.0 \\\n"
    "    [get_ports clk]\n"          # multiline continuation
    "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]\n"
    "set_output_delay -max 2.0 \\\n"
    "    -min 0.5 -clock clk [get_ports data_out]\n"
)


def _facts(v, sdc):
    o = parse_verilog(v)
    assert o.context is not None, o.errors
    ctx = o.context
    r = check_sdc(sdc, context=ctx)
    findings = validate_design_references(sdc, ctx)
    return (
        ctx.top_module,
        sorted(ctx.ports),
        sorted(ctx.instances),
        sorted(ctx.pins),
        r.scope.get("status"),
        [(f.code, f.msg) for f in findings],
    )


# ANSI header vs non-ANSI body-declared ports must yield identical facts
V_ANSI = V_BASE
V_NONANSI = """
module top ( clk, data_in, data_out );
    input clk;
    input [7:0] data_in;
    output [7:0] data_out;
    wire [7:0] w;
    flop u1 ( .clk(clk), .d(data_in), .q(w) );
    flop u2 ( .clk(clk), .d(w), .q(data_out) );
endmodule
module flop ( clk, d, q );
    input clk;
    input [7:0] d;
    output [7:0] q;
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule
"""

# Named connections vs positional connections (module port order known)
V_POSITIONAL = """
module top ( input clk, input [7:0] data_in, output [7:0] data_out );
    wire [7:0] w;
    flop u1 ( clk, data_in, w );
    flop u2 ( clk, w, data_out );
endmodule
module flop ( input clk, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule
"""


def main():
    print("NETLIST-AWARE METAMORPHIC")
    f1 = _facts(V_BASE, SDC_BASE)
    f2 = _facts(V_VARIANT, SDC_VARIANT)
    ok = f1 == f2
    print(f"  {'✅' if ok else '❌'} formatting variants produce identical results")
    if not ok:
        print("   base:", f1)
        print("   variant:", f2)

    # CRLF variant of the same SDC
    sdc_crlf = SDC_BASE.replace("\n", "\r\n")
    f3 = _facts(V_BASE, sdc_crlf)
    ok2 = f1 == f3
    print(f"  {'✅' if ok2 else '❌'} CRLF SDC identical results")

    # ANSI vs non-ANSI port lists → same port set + directions
    f4 = _facts(V_ANSI, SDC_BASE)
    f5 = _facts(V_NONANSI, SDC_BASE)
    ok3 = f4[1] == f5[1] and f4[2] == f5[2] and f4[5] == f5[5]
    print(f"  {'✅' if ok3 else '❌'} ANSI vs non-ANSI port declarations identical"
          + (f" (ansi={f4[1]} nonansi={f5[1]})" if not ok3 else ""))

    # named vs positional connections → same pins (positional resolved via
    # module port order: clk, d, q → pins clk/d/q on each instance)
    f6 = _facts(V_BASE, SDC_BASE)
    f7 = _facts(V_POSITIONAL, SDC_BASE)
    ok4 = f6[3] == f7[3]
    print(f"  {'✅' if ok4 else '❌'} named vs positional connections identical pins"
          + (f" (named={sorted(f6[3])} pos={sorted(f7[3])})" if not ok4 else ""))

    total, passed = 4, (ok + ok2 + ok3 + ok4)
    print(f"\nNETLIST METAMORPHIC: {passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
