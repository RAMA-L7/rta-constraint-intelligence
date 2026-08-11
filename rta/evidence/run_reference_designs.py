#!/usr/bin/env python3
"""
Phase 6 — Reference design evaluation + accuracy scorecard.

Runs every reference design (RD01..RD08) through checker / converter /
clock_relations / coverage and compares against the INDEPENDENTLY derived
manifest (benchmarks/reference_designs/manifest.json). Expected values were
derived from SDC/Tcl semantics — not from validator output.

Computes, per deterministic design:
  - false positives (unexpected errors/warnings on CLEAN designs)
  - false negatives (injected defects NOT detected on RD07)
  - precision / recall per category
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RD = ROOT / "rta" / "evidence" / "reference_designs"
sys.path.insert(0, str(ROOT))

from checker import check_sdc                     # noqa: E402
from converter import parse_sdc                   # noqa: E402
from clock_relations import analyze_clock_relations  # noqa: E402
from coverage import parse_sdc_coverage           # noqa: E402

# ── Results collection for the scorecard ──────────────────────────────────────

# Per-category true/false positive/negative counting (semantic rules only
# where ground truth is known; heuristic warnings classified separately).
STATS = {}

# Heuristic / best-practice advisories (SDC-020..045). These fire by design on
# legal SDC ("confirm this false path", "add -hold fix", "0.05ns is tight",
# "consider set_propagated_clock", "add clock groups") and are NOT correctness
# false positives — they are policy recommendations. Phase 6 scores them in a
# separate advisory bucket so precision/recall measure semantic accuracy only.
HEURISTIC_WARNINGS = frozenset(
    f"SDC-{n:03d}" for n in list(range(20, 38)) + list(range(40, 46))
)

# Semantic rules with independently verified ground truth (Phase 5): undefined
# references, duplicates, and contradictions. These are the rules the scorecard
# measures precision/recall on.
SEMANTIC_RULES = frozenset(["SDC-002", "SDC-008", "SDC-009", "SDC-046",
                            "SDC-047", "SDC-048", "SDC-049"])

ADVISORY_STATS = []  # (design, rule, note) for the advisory report


def add_stat(cat, tp=0, fp=0, fn=0):
    s = STATS.setdefault(cat, {"tp": 0, "fp": 0, "fn": 0})
    s["tp"] += tp
    s["fp"] += fp
    s["fn"] += fn


def evaluate(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    r = check_sdc(text)
    p = parse_sdc(text, path.name)
    cr = analyze_clock_relations(text)
    cov = parse_sdc_coverage(text, path.name)
    return {
        "errors": sorted({i.code for i in r.issues if i.sev == "error"}),
        "warnings": sorted({i.code for i in r.issues if i.sev == "warning"}),
        "info": sorted({i.code for i in r.info}),
        "clock_count": r.stats["Clocks"],
        "generated_count": r.stats["Generated clocks"],
        "periods": {c.name: c.period for c in p.clocks},
        "conv_clocks": len(p.clocks),
        "pairs": len(cr.pairs),
        "missing": cr.stats.get("missing", 0),
        "groups_declared": r.stats.get("Clock groups", 0) > 0,
        "relations": {frozenset((x.clock_a, x.clock_b)): x.inferred_relation for x in cr.pairs},
        "coverage_score": cov.score,
        "all_issues": r.issues,
    }


def main():
    manifest = json.loads((RD / "manifest.json").read_text(encoding="utf-8"))
    print("=" * 78)
    print("PHASE 6 — REFERENCE DESIGN EVALUATION")
    print("=" * 78)

    summary = []
    for design in manifest["designs"]:
        dpath = RD / design["file"]
        exp = design["expected"]
        injected_defects = design.get("injected_defects", [])
        act = evaluate(dpath)
        did = design["id"]
        issues = []

        # Clock counts
        if act["clock_count"] != exp.get("clock_count"):
            issues.append(f"clock_count: expected {exp.get('clock_count')} got {act['clock_count']}")
        if exp.get("generated_count") is not None and act["generated_count"] != exp.get("generated_count"):
            issues.append(f"generated: expected {exp.get('generated_count')} got {act['generated_count']}")
        if exp.get("conv_clock_count") and act["conv_clocks"] != exp.get("conv_clock_count"):
            issues.append(f"conv_clocks: expected {exp.get('conv_clock_count')} got {act['conv_clocks']}")
        if exp.get("pair_count") is not None and act["pairs"] != exp.get("pair_count"):
            issues.append(f"pairs: expected {exp.get('pair_count')} got {act['pairs']}")

        # Periods
        for name, val in exp.get("periods", {}).items():
            got = act["periods"].get(name)
            if got is None or abs(got - val) > 1e-9:
                issues.append(f"period {name}: expected {val} got {got}")

        # Semantic / errors
        if "errors" in exp:
            unexpected = set(act["errors"]) - set(exp["errors"])
            missing = set(exp["errors"]) - set(act["errors"])
            if unexpected:
                issues.append(f"unexpected errors: {sorted(unexpected)}")
            if missing:
                issues.append(f"missing errors: {sorted(missing)}")
        if "errors_include" in exp:
            for e in exp["errors_include"]:
                if e not in act["errors"]:
                    issues.append(f"missing error {e}")
        if "semantic_errors" in exp:
            unexpected = set(act["errors"]) - set(exp["semantic_errors"])
            if unexpected:
                issues.append(f"unexpected semantic errors: {sorted(unexpected)}")
        if "warnings_include" in exp:
            for w in exp["warnings_include"]:
                if w not in act["warnings"]:
                    issues.append(f"missing warning {w}")
        if "warnings_exclude" in exp:
            for w in exp["warnings_exclude"]:
                if w in act["warnings"]:
                    issues.append(f"unexpected warning {w}")
        if exp.get("groups_declared") and not act["groups_declared"]:
            issues.append("clock groups not detected")

        ok = not issues
        summary.append({"id": did, "ok": ok, "issues": issues, "actual": act, "expected": exp,
                        "classification": design["classification"],
                        "injected_defects": injected_defects})
        print(f"{'✅' if ok else '❌'} {did} [{design['classification']:<18}] {design['file']}")
        for i in issues:
            print(f"      ⚠ {i}")

    # ── Per-design detail + scorecard accumulation ───────────────────────────
    print("\n" + "=" * 78)
    print("FALSE POSITIVE / FALSE NEGATIVE ANALYSIS (deterministic designs)")
    print("=" * 78)

    for s in summary:
        did = s["id"]
        exp, act = s["expected"], s["actual"]
        known = set(exp.get("known_warnings", []))
        if s["classification"] == "clean":
            # Semantic FPs: unexpected errors or non-heuristic warnings.
            fp_errs = set(act["errors"]) - set(exp.get("errors", []))
            fp_warns = set(act["warnings"]) - known - HEURISTIC_WARNINGS
            for e in sorted(fp_errs):
                print(f"  FP-CANDIDATE {did}: unexpected ERROR {e}")
            for w in sorted(fp_warns):
                print(f"  FP-CANDIDATE {did}: unexpected WARNING {w}")
            add_stat(did, tp=0, fp=len(fp_errs) + len(fp_warns), fn=0)
            # Heuristic advisories: declared in manifest OR fire-by-design rules.
            for w in sorted(set(act["warnings"]) & HEURISTIC_WARNINGS):
                tag = "declared" if w in known else "undeclared"
                ADVISORY_STATS.append((did, w, tag))
                print(f"  ADVISORY  {did}: heuristic {w} ({tag})")
        elif s["classification"] == "broken":
            injected = [d["rule"] for d in s["injected_defects"]]
            detected_err = set(act["errors"])
            detected_warn = set(act["warnings"])
            for rule in injected:
                if rule in detected_err or rule in detected_warn:
                    print(f"  DETECTED  {did}: injected {rule}")
                else:
                    print(f"  MISSED    {did}: injected {rule} — FALSE NEGATIVE")
            tp = sum(1 for rule in injected if rule in detected_err or rule in detected_warn)
            add_stat(did, tp=tp, fp=0, fn=len(injected) - tp)
            # Unexpected findings beyond injected: exclude declared advisories
            # and heuristic-by-design rules (SDC-020/030 fire on legal content).
            unexpected = ((set(act["errors"]) | set(act["warnings"]))
                          - set(injected) - known - HEURISTIC_WARNINGS)
            for u in sorted(unexpected):
                print(f"  FP-CANDIDATE {did}: unexpected finding {u}")
            add_stat(did, tp=0, fp=len(unexpected), fn=0)
            for w in sorted(set(act["warnings"]) & HEURISTIC_WARNINGS):
                ADVISORY_STATS.append((did, w, "declared" if w in known else "undeclared"))
                print(f"  ADVISORY  {did}: heuristic {w}")

    undeclared = [a for a in ADVISORY_STATS if a[2] == "undeclared"]
    print(f"\n  Heuristic advisories observed: {len(ADVISORY_STATS)} "
          f"({len(undeclared)} undeclared in manifest)")
    for did, w, tag in undeclared:
        print(f"    undeclared advisory: {did} → {w}")

    # ── Scorecard ────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("SCORECARD (precision / recall by deterministic category)")
    print("=" * 78)
    totals = {"tp": 0, "fp": 0, "fn": 0}
    for cat, s in sorted(STATS.items()):
        for k in totals:
            totals[k] += s[k]
        prec = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) else 1.0
        rec = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) else 1.0
        print(f"  {cat:<14} TP={s['tp']:<3} FP={s['fp']:<3} FN={s['fn']:<3} "
              f"precision={prec:.2f} recall={rec:.2f}")
    tprec = totals["tp"] / (totals["tp"] + totals["fp"]) if (totals["tp"] + totals["fp"]) else 1.0
    trec = totals["tp"] / (totals["tp"] + totals["fn"]) if (totals["tp"] + totals["fn"]) else 1.0
    print(f"  {'TOTAL':<14} TP={totals['tp']:<3} FP={totals['fp']:<3} FN={totals['fn']:<3} "
          f"precision={tprec:.2f} recall={trec:.2f}")

    passed = sum(1 for s in summary if s["ok"])
    print(f"\nREFERENCE DESIGNS: {passed}/{len(summary)} fully match expected facts")
    result = {"designs": [{ "id": s["id"], "ok": s["ok"], "issues": s["issues"]} for s in summary],
              "scorecard": STATS}
    (RD / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    sys.exit(0 if passed == len(summary) else 1)


if __name__ == "__main__":
    main()
