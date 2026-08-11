"""
Phase 9 — coverage analysis performance.

Measure parse + coverage on synthetic designs with growing object counts and
constraint counts. Watch for accidental O(N²) behavior in connectivity or
per-port SDC rescans.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from design_context import parse_verilog
from design_coverage import analyze_coverage


def _build(n_ports: int, n_inst: int) -> str:
    """Deterministic synthetic design: n_ports data inputs + outputs, n_inst flops."""
    ins = []
    ports = []
    for i in range(n_ports):
        ports.append(f"input [7:0] data_in_{i}")
        ports.append(f"output [7:0] data_out_{i}")
    for i in range(n_inst):
        ports.append(f"input clk_{i % 8}")
    portlist = ", ".join(ports)
    body = []
    for i in range(n_inst):
        body.append(f"flop u{i} ( .clk(clk_{i % 8}), .d(data_in_{i % n_ports}), "
                    f".q(data_out_{i % n_ports}) );")
    return (
        f"module top ( {portlist} );\n"
        + "\n".join(body) + "\n"
        + "endmodule\n"
        + "module flop ( input clk, input [7:0] d, output [7:0] q );\n"
        + "reg [7:0] r; always @(posedge clk) r <= d; assign q = r;\n"
        + "endmodule\n"
    )


def _sdc(n_ports: int) -> str:
    lines = ["set sdc_version 2.2"]
    for i in range(min(n_ports, 8)):
        lines.append(f"create_clock -name clk_{i} -period 5.0 [get_ports clk_{i}]")
    for i in range(n_ports):
        lines.append(f"set_input_delay -max 2.0 -min 0.5 -clock clk_{i % 8} "
                     f"[get_ports data_in_{i}]")
        lines.append(f"set_output_delay -max 2.0 -min 0.5 -clock clk_{i % 8} "
                     f"[get_ports data_out_{i}]")
    return "\n".join(lines)


def main() -> int:
    print("DESIGN COVERAGE PERFORMANCE")
    ok = True
    for n_ports, n_inst in ((5, 10), (25, 50), (50, 100), (100, 500)):
        v = _build(n_ports, n_inst)
        sdc = _sdc(n_ports)
        t0 = time.perf_counter()
        ctx = parse_verilog(v).context
        t1 = time.perf_counter()
        cov = analyze_coverage(sdc, ctx)
        t2 = time.perf_counter()
        s = cov.summary()
        ok &= bool(ctx) and s["inputs"]["constrained"] == n_ports
        print(f"  {'✅' if ok else '❌'} {n_ports} ports / {n_inst} inst: "
              f"parse={t1-t0:.3f}s coverage={t2-t1:.3f}s "
              f"(inputs={s['inputs']['total']})")
    print(f"COVERAGE PERF: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
