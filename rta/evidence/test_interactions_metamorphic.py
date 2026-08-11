"""
Phase 10 — Metamorphic suite for the constraint-interaction analyzer.

Semantically equivalent formatting must produce identical interaction
findings. The base design contains: one max<min conflict, one fp/mcp
possible conflict, one exact duplicate. Every variant must yield the same
(category, code) multiset and the same finding count.

Variants: multiline, scientific notation, Tcl variables, extra whitespace,
added comments, CRLF, option reordering, equivalent braced collections.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from constraint_interactions import analyze_interactions

BASE = (
    "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
    "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
    "set_false_path -from [get_ports a] -to [get_ports b]\n"
    "set_multicycle_path 2 -from [get_ports a] -to [get_ports b]\n"
    "set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
    "set_min_delay 10 -from [get_ports a] -to [get_ports b]\n"
)

VARIANTS = {
    "multiline": (
        "set_input_delay \\\n"
        "    -max 2.0 -clock clk_a [get_ports din]\n"
        "set_input_delay \\\n"
        "    -max 2.0 -clock clk_a [get_ports din]\n"
        "set_false_path \\\n"
        "    -from [get_ports a] -to [get_ports b]\n"
        "set_multicycle_path \\\n"
        "    2 -from [get_ports a] -to [get_ports b]\n"
        "set_max_delay 5 \\\n"
        "    -from [get_ports a] -to [get_ports b]\n"
        "set_min_delay 10 \\\n"
        "    -from [get_ports a] -to [get_ports b]\n"
    ),
    "scientific_notation": (
        "set_input_delay -max 2e0 -clock clk_a [get_ports din]\n"
        "set_input_delay -max 2.0e0 -clock clk_a [get_ports din]\n"
        "set_false_path -from [get_ports a] -to [get_ports b]\n"
        "set_multicycle_path 2.0 -from [get_ports a] -to [get_ports b]\n"
        "set_max_delay 5e0 -from [get_ports a] -to [get_ports b]\n"
        "set_min_delay 1e1 -from [get_ports a] -to [get_ports b]\n"
    ),
    "variables": (
        "set D 2.0\n"
        "set M 5\n"
        "set N 10\n"
        "set_input_delay -max $D -clock clk_a [get_ports din]\n"
        "set_input_delay -max ${D} -clock clk_a [get_ports din]\n"
        "set_false_path -from [get_ports a] -to [get_ports b]\n"
        "set_multicycle_path 2 -from [get_ports a] -to [get_ports b]\n"
        "set_max_delay $M -from [get_ports a] -to [get_ports b]\n"
        "set_min_delay $N -from [get_ports a] -to [get_ports b]\n"
    ),
    "whitespace": (
        "set_input_delay   -max   2.0   -clock   clk_a   [get_ports din]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]   \n"
        "set_false_path    -from [get_ports a]  -to [get_ports b]\n"
        "set_multicycle_path    2   -from [get_ports a] -to [get_ports b]\n"
        "set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
        "set_min_delay 10 -from [get_ports a] -to [get_ports b]\n"
    ),
    "comments": (
        "# comment at top\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din] # trailing\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
        "# another comment\n"
        "set_false_path -from [get_ports a] -to [get_ports b]\n"
        "set_multicycle_path 2 -from [get_ports a] -to [get_ports b]\n"
        "set_max_delay 5 -from [get_ports a] -to [get_ports b]\n"
        "set_min_delay 10 -from [get_ports a] -to [get_ports b]\n"
    ),
    "crlf": BASE.replace("\n", "\r\n"),
    "option_reorder": (
        "set_input_delay [get_ports din] -clock clk_a -max 2.0\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
        "set_false_path -to [get_ports b] -from [get_ports a]\n"
        "set_multicycle_path -to [get_ports b] -from [get_ports a] 2\n"
        "set_max_delay -to [get_ports b] -from [get_ports a] 5\n"
        "set_min_delay -to [get_ports b] -from [get_ports a] 10\n"
    ),
    "braced_collections": (
        "set_input_delay -max 2.0 -clock clk_a [get_ports {din}]\n"
        "set_input_delay -max 2.0 -clock clk_a [get_ports din]\n"
        "set_false_path -from [get_ports a] -to [get_ports {b}]\n"
        "set_multicycle_path 2 -from [get_ports {a}] -to [get_ports b]\n"
        "set_max_delay 5 -from [get_ports a] -to [get_ports {b}]\n"
        "set_min_delay 10 -from [get_ports {a}] -to [get_ports b]\n"
    ),
}


def signature(ia) -> tuple:
    """(category, code) multiset — the semantic fingerprint of the findings."""
    return tuple(sorted((f["category"], f["code"]) for f in ia.findings))


def main() -> int:
    print("INTERACTION METAMORPHIC")
    base_ia = analyze_interactions(BASE)
    base_sig = signature(base_ia)
    base_n = len(base_ia.findings)
    print(f"  base: {base_n} findings {base_sig}")
    failures = 0
    for name, sdc in VARIANTS.items():
        ia = analyze_interactions(sdc)
        sig = signature(ia)
        ok = sig == base_sig and len(ia.findings) == base_n
        if ok:
            print(f"  ✅ {name}")
        else:
            failures += 1
            print(f"  ❌ {name}: got {len(ia.findings)} findings {sig}")
    total = len(VARIANTS)
    print(f"INTERACTION METAMORPHIC: {total - failures}/{total} variants equivalent")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
