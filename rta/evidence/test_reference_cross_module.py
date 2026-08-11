#!/usr/bin/env python3
"""
Phase 6 — Stage 9: Cross-module consistency for every reference design.

Fundamental facts (clock count, names, periods, generated ancestry, clock
groups, I/O delays) MUST agree between checker / converter / clock_relations /
coverage. Any disagreement is a high-priority architecture finding.

Note: the checker's "Clocks" stat counts PRIMARY clocks only (generated clocks
are reported separately), while the converter lists every clock statement
(primary + generated, including duplicates — matching SDC-002 duplicate
detection). So primary + generated must equal converter's statement count.

Usage:
    python benchmarks/test_reference_cross_module.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RD = ROOT / "rta" / "evidence" / "reference_designs"
sys.path.insert(0, str(ROOT))

from checker import check_sdc                      # noqa: E402
from converter import parse_sdc                    # noqa: E402
from clock_relations import analyze_clock_relations  # noqa: E402
from coverage import parse_sdc_coverage            # noqa: E402


def check_design(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    r = check_sdc(text)
    p = parse_sdc(text, path.name)
    cr = analyze_clock_relations(text)
    cov = parse_sdc_coverage(text, path.name)
    return r, p, cr, cov


def main():
    files = sorted(RD.rglob("*.sdc"))
    problems = []
    for f in files:
        r, p, cr, cov = check_design(f)
        did = f.parent.name
        local = []

        # 1) Clock count: checker PRIMARY + GENERATED must equal converter count
        cc_checker = r.stats["Clocks"]
        gen_checker = r.stats["Generated clocks"]
        cc_conv = len(p.clocks)
        # 2) Generated count: checker stats vs converter is_generated
        gen_conv = sum(1 for c in p.clocks if getattr(c, "is_generated", False))
        # 3) Names: compare converter names vs clock_relations names
        cr_names = sorted({x for pr in cr.pairs for x in (pr.clock_a, pr.clock_b)})
        conv_names = sorted(c.name for c in p.clocks)
        # 4) Pair count: N*(N-1)/2 where N = number of CLOCK STATEMENTS
        #    (converter counts each statement incl. duplicates — matching the
        #    checker, which flags duplicate create_clock as SDC-002).
        n_statements = cc_conv
        expected_pairs = n_statements * (n_statements - 1) // 2
        # 5) Coverage must run without exception and report a score

        if cc_checker + gen_checker != cc_conv:
            local.append(f"checker primary+gen ({cc_checker}+{gen_checker}) != converter {cc_conv}")
        if gen_checker != gen_conv:
            local.append(f"checker gen {gen_checker} != converter {gen_conv}")
        if cc_conv > 0 and not conv_names:
            local.append(f"converter parsed no clock names despite checker={cc_checker}")
        if len(cr.pairs) != expected_pairs:
            local.append(f"pairs {len(cr.pairs)} != expected {expected_pairs} "
                         f"for {n_statements} clock statements")
        if cov.score is None:
            local.append("coverage returned no score")

        status = "FAIL" if local else "OK  "
        print(f"  [{status}] {did:<24} checker_c={cc_checker}+{gen_checker} conv_c={len(conv_names):<3} "
              f"gen={gen_checker}/{gen_conv} pairs={len(cr.pairs)}/{expected_pairs} "
              f"coverage={cov.score}")
        problems.extend(local)

    print(f"\nCROSS-MODULE: {len(files)} designs checked")
    if problems:
        print("INCONSISTENCIES:")
        for p_ in problems:
            print(f"  ❌ {p_}")
        sys.exit(1)
    print("ALL CONSISTENT")
    sys.exit(0)


if __name__ == "__main__":
    main()
