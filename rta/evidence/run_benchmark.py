#!/usr/bin/env python3
"""
Ṛta — Reusable QA Benchmark Runner.

Runs every analysis engine (checker, linter, converter, coverage,
clock_relations, wildcard_analyzer, constraint_diff) over every *.sdc file in
the evidence tree (rta/evidence/) and writes machine-readable results to
rta/evidence/results/results.json so the same suite can be rerun after changes.

Usage:
    python rta/evidence/run_benchmark.py            # run everything
    python rta/evidence/run_benchmark.py -q        # quiet summary only
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent   # rta/evidence/ — benchmark data tree
sys.path.insert(0, str(ROOT.parent.parent))  # repository root (root shims)

from checker import check_sdc                        # noqa: E402
from linter import lint_sdc                          # noqa: E402
from converter import parse_sdc, sdc_to_json, sdc_to_yaml  # noqa: E402
from coverage import parse_sdc_coverage              # noqa: E402
from clock_relations import analyze_clock_relations  # noqa: E402
from wildcard_analyzer import parse_wildcard         # noqa: E402
from constraint_diff import analyze_constraint_changes  # noqa: E402

GROUPS = [
    "valid", "invalid", "edge_cases", "clock_relations",
    "timing_exceptions", "io_constraints", "malformed",
    "large_design", "regression",
]


def _safe(fn, *args, **kwargs):
    """Run fn; return (ok, value_or_error)."""
    try:
        return True, fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — benchmark must not die on bad input
        return False, f"{type(exc).__name__}: {exc}"


def analyze_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    rec = {"file": str(path.relative_to(ROOT)), "size_bytes": len(text.encode("utf-8")),
           "lines": text.count("\n") + 1}
    t0 = time.time()

    # ── Checker ──
    ok, r = _safe(check_sdc, text)
    if ok:
        rec["checker"] = {
            "errors": len(r.errors), "warnings": len(r.warnings), "info": len(r.info),
            "error_codes": sorted({i.code for i in r.issues if i.sev == "error"}),
            "warning_codes": sorted({i.code for i in r.issues if i.sev == "warning"}),
            "info_codes": sorted({i.code for i in r.info}),
            "issues": [{"sev": i.sev, "code": i.code, "line": i.line, "msg": i.msg} for i in r.issues],
            "stats": r.stats,
        }
    else:
        rec["checker"] = {"crash": r}

    # ── Linter ──
    ok, r = _safe(lint_sdc, text, fix=False)
    rec["linter"] = {"warnings": r.warnings, "issues": r.issues[:20]} if ok else {"crash": r}

    # ── Converter ──
    ok, r = _safe(parse_sdc, text, path.name)
    if ok:
        rec["converter"] = {
            "clocks_count": r.clocks_count, "constraints_count": r.constraints_count,
            "input_delays": len(r.input_delays), "output_delays": len(r.output_delays),
            "false_paths": len(r.false_paths), "clock_groups": len(r.clock_groups),
            "clocks": [{"name": c.name, "period": c.period, "port": c.port,
                        "generated": c.is_generated, "virtual": c.is_virtual} for c in r.clocks],
        }
    else:
        rec["converter"] = {"crash": r}

    # ── Coverage ──
    ok, r = _safe(parse_sdc_coverage, text, path.name)
    rec["coverage"] = {"score": round(r.score, 1), "present": r.total_present,
                       "total": r.total_items} if ok else {"crash": r}

    # ── Clock relations ──
    ok, r = _safe(analyze_clock_relations, text)
    if ok:
        rec["clock_relations"] = {
            "clocks": len(r.clocks), "pairs": len(r.pairs), "stats": r.stats,
            "clock_names": [c.name for c in r.clocks],
            "mismatches": [{"code": m.code, "severity": m.severity, "clock_a": m.clock_a,
                            "clock_b": m.clock_b, "specified": m.specified, "expected": m.expected}
                           for m in r.mismatches],
        }
    else:
        rec["clock_relations"] = {"crash": r}

    # ── Wildcard analyzer (first 30 patterns) ──
    wild = []
    for m in re.finditer(r'\[(get_[a-z_]+)\s+([^\]]+)\]', text):
        try:
            p = parse_wildcard(f"[{m.group(1)} {m.group(2)}]")
            wild.append({"raw": p.raw, "risk": p.risk_score, "specificity": p.specificity})
        except Exception:
            pass
        if len(wild) >= 30:
            break
    rec["wildcards"] = wild

    # ── Constraint diff (pair with the same file vs itself → 0 changes) ──
    ok, r = _safe(analyze_constraint_changes, text, text)
    rec["self_diff"] = {"total": r.stats.get("total_changes", 0)} if ok else {"crash": r}

    rec["runtime_ms"] = int((time.time() - t0) * 1000)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    results = []
    for group in GROUPS:
        gdir = ROOT / group
        if not gdir.exists():
            continue
        for path in sorted(gdir.glob("*.sdc")):
            results.append(analyze_file(path))

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with open(out / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if args.quiet:
        print(f"{len(results)} benchmark files analyzed → rta/evidence/results/results.json")
        return

    for rec in results:
        chk = rec.get("checker", {})
        if "crash" in chk:
            status = "💥 CRASH"
        elif chk.get("errors", 0) or chk.get("warnings", 0):
            status = f"⚠ {chk.get('errors',0)}E/{chk.get('warnings',0)}W"
        else:
            status = "✅ clean"
        cr = rec.get("clock_relations", {})
        crs = cr.get("stats", {}) if isinstance(cr, dict) else {}
        print(f"[{status:>9}] {rec['file']:<60} lines={rec['lines']:>5} "
              f"clk={crs.get('clocks', '?')} pairs={crs.get('pairs', '?')} "
              f"mism={crs.get('mismatches', '?')} miss={crs.get('missing', '?')} "
              f"conv={rec.get('converter', {}).get('clocks_count', '?')} "
              f"cov={rec.get('coverage', {}).get('score', '?')}% "
              f"{rec.get('runtime_ms', 0)}ms")


if __name__ == "__main__":
    main()
