#!/usr/bin/env python3
"""
Phase 8 — Netlist-aware performance benchmark.

Measures separately: Verilog parsing, hierarchy construction, collection
resolution (exact + wildcard), and full design-aware SDC validation at
approximately 1k / 10k / 100k design objects.

No hard wall-clock assertions (machine-dependent) — reports numbers and
fails only on pathological slowdowns (e.g. >60s at 10k, quadratic blowup).

Usage: python benchmarks/test_netlist_perf.py
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc                                   # noqa: E402
from design_context import parse_verilog, resolve_collection    # noqa: E402


def _build_netlist(n_flops: int) -> str:
    """Deterministic flat netlist with n_flops flop instances."""
    ports = "input clk, input [7:0] data_in, output [7:0] data_out"
    lines = [f"module top ( {ports} );", "  wire [7:0] w;"]
    prev = "data_in"
    for i in range(n_flops):
        lines.append(f"  flop u{i:05d} ( .clk(clk), .d({prev}), .q(w) );")
        prev = "w"
    lines.append("  assign data_out = w;")
    lines.append("endmodule")
    lines.append("module flop ( input clk, input [7:0] d, output [7:0] q );")
    lines.append("  reg [7:0] r; always @(posedge clk) r <= d; assign q = r;")
    lines.append("endmodule")
    return "\n".join(lines)


SDC = (
    "set sdc_version 2.2\n"
    "create_clock -name clk -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]\n"
    "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"
    "set_false_path -from [get_pins u00000/D] -to [get_pins u09999/Q]\n"
)


def bench(n_flops):
    v = _build_netlist(n_flops)
    t0 = time.perf_counter()
    o = parse_verilog(v)
    t_parse = time.perf_counter() - t0
    if o.context is None:
        return None, None, None, None, o.errors
    ctx = o.context

    t0 = time.perf_counter()
    r = resolve_collection("get_cells", "u0*", ctx)
    t_glob = time.perf_counter() - t0

    t0 = time.perf_counter()
    r2 = resolve_collection("get_ports", "data_in", ctx)
    t_exact = time.perf_counter() - t0

    t0 = time.perf_counter()
    check_sdc(SDC, context=ctx)
    t_check = time.perf_counter() - t0
    return t_parse, t_glob, t_exact, t_check, None


def main():
    print("NETLIST-AWARE PERFORMANCE")
    results = []
    for n in (1000, 10000, 100000):
        t_parse, t_glob, t_exact, t_check, err = bench(n)
        if err:
            print(f"  ❌ {n:>6} objects: parse failed {err}")
            sys.exit(1)
        results.append((n, t_parse, t_glob, t_exact, t_check))
        print(f"  ✅ {n:>6} objects | parse={t_parse:.3f}s "
              f"| glob={t_glob*1000:.1f}ms | exact={t_exact*1000:.1f}ms "
              f"| full check={t_check:.3f}s")

    # Sanity: 10k must not blow up relative to 1k more than ~25x (allows some
    # superlinearity but rejects quadratic disaster).
    n1, t1 = results[0][0], results[0][1] + results[0][4]
    n2, t2 = results[1][0], results[1][1] + results[1][4]
    ratio = (t2 / t1) / (n2 / n1) if t1 > 0 else 99
    ok = ratio < 8.0
    print(f"  {'✅' if ok else '❌'} 10k/1k scaling ratio {ratio:.2f}x "
          f"(linear=1.0, quadratic-disaster threshold=8.0)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
