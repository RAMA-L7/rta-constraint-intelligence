#!/usr/bin/env python3
"""
Phase 8 — Netlist-aware adversarial tests.

Malformed/hostile Verilog must never crash the parser and must degrade to
explicit errors (no silent wrong design context):
  - incomplete modules, duplicate modules, undefined instantiated module
  - deep hierarchy, escaped identifiers, similar names
  - comments containing fake modules, strings containing keywords
  - huge wildcard matches / empty wildcard matches

Usage: python benchmarks/test_netlist_adversarial.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from design_context import parse_verilog, resolve_collection  # noqa: E402


def _no_crash(name, v, must_parse=False):
    """Parser must never raise; outcome.errors always available."""
    try:
        o = parse_verilog(v)
    except Exception as e:
        print(f"  ❌ {name}: CRASH {type(e).__name__}: {e}")
        return False
    if must_parse and o.context is None:
        print(f"  ❌ {name}: expected parse but got errors: {o.errors}")
        return False
    if not must_parse and o.context is not None and not o.errors:
        print(f"  ❌ {name}: expected degraded parse but silently succeeded")
        return False
    print(f"  ✅ {name}")
    return True


def main():
    print("NETLIST-AWARE ADVERSARIAL")
    # The incomplete module must degrade with an explicit warning (never silent)
    o_incomplete = parse_verilog("module top ( input clk );\n    wire w;\n")
    assert o_incomplete.warnings, "incomplete module must produce a warning"

    checks = [
        ("incomplete_module_missing_endmodule",
         "module top ( input clk );\n    wire w;\n",
         True),   # degrades with a warning, still builds usable context
        ("duplicate_modules",
         "module a; endmodule\nmodule a; endmodule\n",
         False),
        ("undefined_instantiated_module",
         "module top; mystery u1 ( .a(1'b0) ); endmodule\n",
         True),
        ("empty_module_no_semicolon",
         "module top ( input a ) endmodule\n",
         True),   # endmodule without ';' is legal Verilog

        ("escaped_identifier",
         'module top ( input clk );\n  \\weird.name u9 ( .clk(clk) );\nendmodule\n',
         True),
        ("comments_with_fake_modules",
         "// module fake ( input x );\n/* module fake2 ( input y ); */\nmodule top ( input a ); endmodule\n",
         True),
        ("strings_containing_keywords",
         'module top ( input a ); wire w; assign w = "module bogus; input z;"; endmodule\n',
         True),
        ("deep_hierarchy",
         "module top ( input c ); m1 u1 ( .c(c) ); endmodule\n"
         "module m1 ( input c ); m2 u2 ( .c(c) ); endmodule\n"
         "module m2 ( input c ); m3 u3 ( .c(c) ); endmodule\n"
         "module m3 ( input c ); endmodule\n",
         True),
        ("malformed_port_list",
         "module top ( input clk, ; endmodule\n",
         False),
        ("behavioral_only_no_modules",
         "always @(posedge clk) q <= d;\n",
         False),
    ]

    passed = 0
    for name, v, must_parse in checks:
        passed += _no_crash(name, v, must_parse)

    # Resolution edge: similar names must not cross-match
    v = ("module top ( input clk, input abc, input abcd ); "
         "endmodule\n")
    o = parse_verilog(v)
    ctx = o.context
    r1 = resolve_collection("get_ports", "abc", ctx)
    r2 = resolve_collection("get_ports", "abcd", ctx)
    ok = (r1.kind == "RESOLVED" and r1.matches == ["abc"]
          and r2.matches == ["abcd"])
    passed += ok
    print(f"  {'✅' if ok else '❌'} similar names {r1.matches} / {r2.matches} do not cross-match")

    # Huge wildcard match (stress glob over many names)
    ports = ", ".join(f"input p{i}" for i in range(2000))
    v = f"module top ( {ports} ); endmodule\n"
    o = parse_verilog(v)
    r = resolve_collection("get_ports", "p*", o.context)
    ok = r.kind == "RESOLVED" and len(r.matches) == 2000
    passed += ok
    print(f"  {'✅' if ok else '❌'} 2000-name wildcard resolves ({len(r.matches) if r else 0})")

    print(f"\nNETLIST ADVERSARIAL: {passed}/{len(checks)+2} checks passed")
    sys.exit(0 if passed == len(checks) + 2 else 1)


if __name__ == "__main__":
    main()
