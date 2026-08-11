"""Phase 11 — Readiness metamorphic tests.

Readiness must be stable under semantically-equivalent transformations:
  - single-line vs multiline commands
  - variables resolving to the same value
  - scientific notation
  - whitespace
  - comments
  - CRLF
  - reordered valid options
  - equivalent braced collections
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc  # noqa: E402

PASS = FAIL = 0


def ok(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  ❌ {msg}")


BASE = """set sdc_version 2.2
create_clock -name c -period 10.0 [get_ports clk]
set_propagated_clock [get_clocks c]
set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]
"""


def readiness_sig(text):
    r = check_sdc(text)
    rdy = r.readiness or {}
    return (rdy.get("overall"), rdy.get("mode"),
            tuple(sorted(b["code"] for b in rdy.get("blockers", []))),
            tuple(sorted(b["code"] for b in rdy.get("review_items", []))),
            tuple(sorted(b["code"] for b in rdy.get("advisories", []))))


def main() -> int:
    print("READINESS METAMORPHIC")
    ref = readiness_sig(BASE)

    variants = {
        "multiline": BASE.replace(
            "set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]",
            "set_input_delay -max 2.0 -min 0.5 -clock c \\\n    [get_ports din]"),
        "variable": ("set PER 10.0\n" + BASE.replace("-period 10.0", "-period $PER")),
        "scientific": BASE.replace("-period 10.0", "-period 1.0e1"),
        "whitespace": BASE.replace("  ", "   ").replace("-max 2.0", "  -max   2.0"),
        "comments": "\n".join(f"# note {i}" for i in range(5)) + "\n" + BASE,
        "crlf": BASE.replace("\n", "\r\n"),
        "reordered": BASE.replace(
            "-clock c [get_ports din] set_input_delay",
            "[get_ports din] set_input_delay -clock c"),
        "braced": BASE.replace("[get_ports din]", "[get_ports {din}]"),
    }
    for name, text in variants.items():
        sig = readiness_sig(text)
        ok(sig == ref, f"{name}: readiness differs {ref} vs {sig}")

    print(f"READINESS METAMORPHIC: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
