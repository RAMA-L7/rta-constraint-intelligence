#!/usr/bin/env python3
"""
Phase 6 — Stages 4 + 8: Feature coverage matrix + severity accuracy review.

Feature coverage matrix: for every registered rule, which reference design
exercises it (and how — CLI/backend/UI/report).

Severity accuracy review: flag rules whose severity may be misclassified
(e.g. a heuristic recommended as error, or an info masquerading as guaranteed
failure). Recommendations only — no production change.

Usage:
    python benchmarks/reference_coverage_matrix.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RD = ROOT / "rta" / "evidence" / "reference_designs"
sys.path.insert(0, str(ROOT))

from checker import check_sdc              # noqa: E402
from rules_registry import get_all_rules   # noqa: E402


def main():
    designs = sorted(RD.rglob("*.sdc"))
    design_ids = [d.parent.name for d in designs]
    fired = {}  # code -> set(design)
    for d in designs:
        text = d.read_text(encoding="utf-8", errors="replace")
        r = check_sdc(text)
        for i in r.issues:
            fired.setdefault(i.code, set()).add(d.parent.name)
        for it in r.info:
            fired.setdefault(it.code, set()).add(d.parent.name)

    rules = get_all_rules()
    print("=" * 100)
    print("FEATURE COVERAGE MATRIX — which registered rule fires in which reference design")
    print("=" * 100)
    print(f"{'code':<10} {'sev':<8} {'module':<16} {'fired-in':<55} {'uncovered'}")
    uncovered = []
    for rule in rules:
        f = fired.get(rule.code, set())
        if f:
            shown = ",".join(sorted(f))
            unc = ""
        else:
            uncovered.append(rule.code)
            shown = "-"
            unc = "⚠ NOT EXERCISED by any reference design"
        print(f"{rule.code:<10} {rule.severity:<8} {rule.module:<16} {shown:<55} {unc}")

    print(f"\nTotal registered rules: {len(rules)}")
    print(f"Exercised by reference designs: {len(set(fired))}")
    print(f"NOT exercised (unit-test-only or unused): {len(uncovered)} -> {sorted(uncovered)}")

    # ── Stage 8: severity accuracy review ──────────────────────────────────
    print("\n" + "=" * 100)
    print("SEVERITY ACCURACY REVIEW (recommendations only, no changes)")
    print("=" * 100)
    # Heuristic best-practice checks that are severity=warning but effectively
    # policy advice (they fire on legal SDC) — the Phase 6 report argues they
    # should not be interpreted as correctness failures.
    heuristic_warning = {"SDC-020", "SDC-021", "SDC-022", "SDC-023", "SDC-024",
                         "SDC-025", "SDC-026", "SDC-027", "SDC-028", "SDC-029",
                         "SDC-030", "SDC-031", "SDC-032", "SDC-033", "SDC-034",
                         "SDC-035", "SDC-036", "SDC-037", "SDC-040", "SDC-041",
                         "SDC-042", "SDC-043", "SDC-044", "SDC-045"}
    # Semantic/verifiable rules — higher confidence, severity is defensible.
    semantic_error = {"SDC-001", "SDC-002", "SDC-003", "SDC-004", "SDC-005",
                      "SDC-006", "SDC-007", "SDC-008", "SDC-009", "SDC-010",
                      "SDC-011", "SDC-046"}
    semantic_warning = {"SDC-047", "SDC-048", "SDC-049"}
    for code in sorted(heuristic_warning | semantic_error | semantic_warning):
        rule = next((r for r in rules if r.code == code), None)
        if not rule:
            continue
        kind = ("heuristic policy advisory" if code in heuristic_warning
                else "verifiable semantic" if code in semantic_error | semantic_warning
                else "?")
        note = ""
        if code in heuristic_warning and rule.severity == "warning":
            note = "→ OK as warning; must NOT be treated as correctness failure"
        elif code in semantic_error and rule.severity == "error":
            note = "→ OK as error"
        elif code in semantic_warning and rule.severity == "warning":
            note = "→ OK as warning"
        else:
            note = "→ REVIEW: severity may be misclassified"
        print(f"  {code:<8} {rule.severity:<8} [{kind:<28}] {note}")

    print("\nSeverity review complete (no production change made).")
    sys.exit(0)


if __name__ == "__main__":
    main()
