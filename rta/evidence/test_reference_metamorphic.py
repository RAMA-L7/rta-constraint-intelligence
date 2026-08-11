#!/usr/bin/env python3
"""
Phase 6 — Stage 10: Metamorphic testing.

Semantically equivalent variants of the same SDC MUST produce identical
validator results. The validator must not change its answer merely because
formatting changed.

Variants per base SDC:
  - single-line vs multiline (\\ continuation)
  - literal period 0.25 vs scientific 2.5e-1
  - literal period vs Tcl variable ($PERIOD)
  - $PERIOD vs ${PERIOD}
  - different whitespace / indentation
  - LF vs CRLF line endings
  - braced collections {a b} vs repeated -group / separate statements
  - reordered valid options
  - added comments

Usage:
    python benchmarks/test_reference_metamorphic.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from checker import check_sdc  # noqa: E402


def _group_membership(text):
    """Extract per-`-group` clock-name membership from set_clock_groups.

    Returns a sorted list of frozensets (one per -group across all
    set_clock_groups commands). Content-based, so a braced-collection
    misparse (e.g. '{clk_a clk_b}' treated as one literal token) is caught.
    """
    import re
    from sdc_preprocess import preprocess_sdc, parse_collection
    members = []
    for cmd in preprocess_sdc(text):
        if not cmd.text.strip().startswith("set_clock_groups"):
            continue
        for gm in re.split(r"-group\b", cmd.text)[1:]:
            # Capture the full collection expression [get_clocks {...}] or a
            # bare name that follows -group, whichever appears first.
            ref_m = re.search(r"\[[^\]]*\]|\S+", gm)
            if not ref_m:
                continue
            names = parse_collection(ref_m.group(0))
            if names:
                members.append(frozenset(names))
    return sorted(members, key=lambda s: sorted(s))


def facts(text):
    """Semantic facts that MUST be invariant across formatting variants."""
    r = check_sdc(text)
    return {
        "errors": sorted({i.code for i in r.issues if i.sev == "error"}),
        "warnings": sorted({i.code for i in r.issues if i.sev == "warning"}),
        "clocks": r.stats["Clocks"],
        "gen": r.stats["Generated clocks"],
        "groups": r.stats["Clock groups"],
        "group_members": _group_membership(text),
        "in_delay": r.stats["Input delays"],
        "out_delay": r.stats["Output delays"],
    }


BASE = """set sdc_version 2.2
# comment line
create_clock -name clk_a -period 0.25 [get_ports clk_a]
create_clock -name clk_b -period 10.0 [get_ports clk_b]
set_clock_groups -asynchronous -group [get_clocks {clk_a clk_b}]
set_input_delay -max 2.0 -min 0.5 -clock clk_a [get_ports data_in]
set_input_delay -max 3.0 -clock clk_b [get_ports data_out]
"""


def variants(base=BASE):
    yield ("baseline", base)
    yield ("multiline", (
        "set sdc_version 2.2\n"
        "# comment line\n"
        "create_clock \\\n"
        "    -name clk_a -period 0.25 [get_ports clk_a]\n"
        "create_clock \\\n"
        "    -name clk_b \\\n"
        "    -period 10.0 \\\n"
        "    [get_ports clk_b]\n"
        "set_clock_groups -asynchronous \\\n"
        "    -group [get_clocks {clk_a clk_b}]\n"
        "set_input_delay \\\n"
        "    -max 2.0 -min 0.5 \\\n"
        "    -clock clk_a [get_ports data_in]\n"
        "set_input_delay -max 3.0 -clock clk_b [get_ports data_out]\n"
    ))
    yield ("scientific_notation", base.replace("0.25", "2.5e-1"))
    yield ("tcl_variable", (
        "set sdc_version 2.2\n"
        "set PERIOD 0.25\n"
        "# comment line\n"
        "create_clock -name clk_a -period $PERIOD [get_ports clk_a]\n"
        "create_clock -name clk_b -period 10.0 [get_ports clk_b]\n"
        "set_clock_groups -asynchronous -group [get_clocks {clk_a clk_b}]\n"
        "set_input_delay -max 2.0 -min 0.5 -clock clk_a [get_ports data_in]\n"
        "set_input_delay -max 3.0 -clock clk_b [get_ports data_out]\n"
    ))
    yield ("tcl_braced_variable", base.replace("-period 0.25", "-period ${PERIOD}")
           .replace("set sdc_version 2.2\n", "set sdc_version 2.2\nset PERIOD 0.25\n"))
    yield ("crlf", base.replace("\n", "\r\n"))
    yield ("extra_whitespace", "\n\n" + "  \n".join(line for line in base.splitlines()) + "\n")
    # Tcl brace-quoted list vs unbraced list — IDENTICAL object list in Tcl.
    # (NOT `-group A -group B`, which would change async semantics: one group
    # {A B} keeps A/B related; two groups make them async to each other.)
    yield ("braced_vs_unbraced_list", base.replace(
        "[get_clocks {clk_a clk_b}]",
        "[get_clocks clk_a clk_b]"
    ))
    yield ("options_reordered", (
        "set sdc_version 2.2\n"
        "create_clock -period 0.25 -name clk_a [get_ports clk_a]\n"
        "create_clock [get_ports clk_b] -period 10.0 -name clk_b\n"
        "set_clock_groups -group [get_clocks {clk_a clk_b}] -asynchronous\n"
        "set_input_delay -clock clk_a -max 2.0 -min 0.5 [get_ports data_in]\n"
        "set_input_delay -clock clk_b -max 3.0 [get_ports data_out]\n"
    ))
    yield ("comments_added", (
        "set sdc_version 2.2\n"
        "# leading comment\n"
        "create_clock -name clk_a -period 0.25 [get_ports clk_a]  # inline\n"
        "# another comment\n"
        "create_clock -name clk_b -period 10.0 [get_ports clk_b]\n"
        "set_clock_groups -asynchronous -group [get_clocks {clk_a clk_b}]\n"
        "set_input_delay -max 2.0 -min 0.5 -clock clk_a [get_ports data_in]\n"
        "set_input_delay -max 3.0 -clock clk_b [get_ports data_out]\n"
    ))


def main():
    base_facts = facts(BASE)
    print("METAMORPHIC TEST — base facts:", base_facts)
    failures = []
    checked = 0
    for name, text in variants():
        checked += 1
        f = facts(text)
        same = f == base_facts
        # Multiline / CRLF / whitespace variants are pure formatting;
        # variable variants are semantic equivalents.
        print(f"  {'✅' if same else '❌'} {name:<24} {f}")
        if not same:
            failures.append((name, f))
    print(f"\nMETAMORPHIC: {checked} variants, {len(failures)} mismatches")
    for name, f in failures:
        print(f"  ❌ {name}: {f} != base {base_facts}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
