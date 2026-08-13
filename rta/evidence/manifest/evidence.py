"""Ṛta — canonical evidence record.

Single source of truth for every public evidence number the product states:
test count, golden runners, benchmark suites, rule count, version, release
status, phase count and license.

Values that are code-derivable are computed live here. The pytest *collection*
count can only be known by running the suite, so it is recorded in
``RELEASE_EVIDENCE.json`` and regenerated/verified by
``benchmarks/build_evidence.py``. ``tests/test_evidence.py`` and CI assert that
this module, the manifest and the live computation all agree.

No backend semantics live here — this module only *records* facts about the
product. The validation engine is untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # repository root
EVIDENCE_DIR = PROJECT_ROOT / "rta" / "evidence"
TESTS_DIR = PROJECT_ROOT / "rta" / "tests"
MANIFEST_PATH = EVIDENCE_DIR / "manifest" / "RELEASE_EVIDENCE.json"

# Static product facts (brand surface; technical identifiers stay ASCII).
PRODUCT = "Ṛta"
TAGLINE = "Ṛta brings order to timing intent, transforming constraints into trusted engineering knowledge through deterministic precision."
LICENSE = "MIT"
RELEASE_STATUS = "RC_READY_WITH_KNOWN_LIMITATIONS"
PHASE_COUNT = 15  # 15 phase report files in benchmarks/: PHASE3..PHASE17
# (PHASE7 has a proposal + report pair; no PHASE1/2 report files exist)

# The 9 golden runners — each must exist as benchmarks/<name>.py. Kept as the
# canonical ordered list; the filesystem is the verification source.
GOLDEN_RUNNERS = (
    "run_golden",
    "run_golden_semantic",
    "run_reference_designs",
    "run_netlist_aware",
    "run_design_coverage",
    "run_constraint_interactions",
    "run_readiness",
    "run_readiness_diff",
    "run_production_hardening",
)


def version() -> str:
    """Current product version — imported from the rules registry (single source)."""
    from rules_registry import APP_VERSION
    return APP_VERSION


def rule_count() -> int:
    """Live count of registered SDC rules."""
    from rules_registry import get_all_rules
    return len(get_all_rules())


def golden_runner_files() -> list[str]:
    """The canonical golden runners, validated to exist under benchmarks/.

    ``run_benchmark.py`` (the suite aggregator) is deliberately not part of
    the golden set; only the nine evidence-backed runners count.
    """
    missing = [n for n in GOLDEN_RUNNERS
               if not (EVIDENCE_DIR / f"{n}.py").is_file()]
    if missing:
        raise RuntimeError(f"golden runners missing from benchmarks/: {missing}")
    return list(GOLDEN_RUNNERS)


def benchmark_suite_files() -> list[str]:
    """Benchmark test suites under benchmarks/ (``test_*.py``)."""
    return sorted(p.name for p in EVIDENCE_DIR.glob("test_*.py"))


def test_files() -> list[str]:
    """Unit/regression test modules under tests/."""
    return sorted(p.name for p in TESTS_DIR.glob("test_*.py"))


def phase_report_count() -> int:
    """Number of PHASE*.md benchmark reports."""
    return len(list(EVIDENCE_DIR.glob("PHASE*.md")))


def load_manifest() -> dict:
    """Load RELEASE_EVIDENCE.json (raises if missing or corrupt)."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def verify() -> list[str]:
    """Compare live, code-derived facts against the recorded manifest.

    Returns a list of human-readable mismatches (empty list == consistent).

    The pytest *collection* count is intentionally excluded here — it requires
    a full suite collection, which ``benchmarks/build_evidence.py --check``
    performs. Everything else (version, rule count, runner/suite/file counts,
    release status, license, phases, brand facts) is verified.
    """
    man = load_manifest()
    issues: list[str] = []
    checks = [
        ("product", PRODUCT, man.get("product")),
        ("tagline", TAGLINE, man.get("tagline")),
        ("version", version(), man.get("version")),
        ("release_status", RELEASE_STATUS, man.get("release_status")),
        ("license", LICENSE, man.get("license")),
        ("rule_count", rule_count(), man.get("rule_count")),
        ("benchmark_suites", len(benchmark_suite_files()),
         man.get("benchmark_suites")),
        ("test_files", len(test_files()), man.get("test_files")),
        ("phase_count", phase_report_count(), man.get("phase_count")),
    ]
    try:
        golden = golden_runner_files()
    except RuntimeError as exc:  # missing runner: report, don't traceback
        issues.append(f"golden_runners: {exc}")
    else:
        checks.append(
            ("golden_runner_count", len(golden), man.get("golden_runner_count")))
        checks.append(("golden_runners", golden, man.get("golden_runners")))
    for key, live, recorded in checks:
        if live != recorded:
            issues.append(f"{key}: live={live!r} manifest={recorded!r}")
    return issues
