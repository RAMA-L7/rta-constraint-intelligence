"""tests/test_evidence.py — Evidence consistency and product-integrity tests.

Guards the single-source-of-truth contract: the code-derived facts, the
recorded RELEASE_EVIDENCE.json manifest and the public surfaces (README,
website, CONTRIBUTING, LICENSE) must all agree. Any drift fails here.

The manifest is loaded lazily (fixture) so that pytest *collection* never
depends on the file existing — if it is missing, these tests fail with a
clear message instead of erroring during collection.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import evidence

ROOT = evidence.PROJECT_ROOT


@pytest.fixture(scope="module")
def manifest():
    return evidence.load_manifest()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# ── Manifest ↔ live computation ────────────────────────────────────────────


def test_manifest_has_required_keys(manifest):
    for key in ("product", "tagline", "version", "release_status", "license",
                "test_count", "test_files", "rule_count", "golden_runner_count",
                "benchmark_suites", "phase_count", "golden_runners",
                "test_files_detail"):
        assert key in manifest, key


def test_live_facts_match_manifest(manifest):
    mismatches = evidence.verify()
    assert mismatches == [], mismatches


def test_rule_count_matches_registry(manifest):
    from rules_registry import get_all_rules
    assert len(get_all_rules()) == manifest["rule_count"]
    assert evidence.rule_count() == manifest["rule_count"]


def test_version_consistency_across_sources(manifest):
    from rules_registry import APP_VERSION
    assert APP_VERSION == manifest["version"]
    pyproject = _read("pyproject.toml")
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    assert m and m.group(1) == manifest["version"], "pyproject version drift"


def test_golden_runners_exist_on_disk(manifest):
    for name in manifest["golden_runners"]:
        assert (evidence.EVIDENCE_DIR / f"{name}.py").is_file(), name
    assert len(manifest["golden_runners"]) == manifest["golden_runner_count"]
    assert manifest["golden_runner_count"] == len(evidence.GOLDEN_RUNNERS)


def test_benchmark_suite_count_matches_disk(manifest):
    on_disk = sorted(p.name for p in evidence.EVIDENCE_DIR.glob("test_*.py"))
    assert len(on_disk) == manifest["benchmark_suites"]


def test_test_file_count_matches_disk(manifest):
    on_disk = sorted(p.name for p in evidence.TESTS_DIR.glob("test_*.py"))
    assert len(on_disk) == manifest["test_files"]
    assert set(on_disk) == set(manifest["test_files_detail"])


def test_phase_count_matches_disk(manifest):
    on_disk = len(list(evidence.EVIDENCE_DIR.glob("PHASE*.md")))
    assert on_disk == manifest["phase_count"]
    assert on_disk == evidence.PHASE_COUNT


def test_manifest_is_valid_json_and_utf8(manifest):
    raw = evidence.MANIFEST_PATH.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert parsed == manifest
    assert "Ṛta" in raw  # Unicode brand must survive the manifest


def test_collection_count_matches_manifest(manifest):
    """Full pytest collection must equal the recorded test_count.

    This is the drift guard: adding a test without regenerating the manifest
    fails here (and in CI via ``python benchmarks/build_evidence.py --check``).
    """
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "rta/tests/", "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    out = proc.stdout + proc.stderr
    m = re.search(r"(\d+)\s+test(?:s)? collected", out)
    assert m, f"could not parse collection output:\n{out[-2000:]}"
    assert proc.returncode == 0, out[-2000:]
    assert int(m.group(1)) == manifest["test_count"]


# ── License ─────────────────────────────────────────────────────────────────


def test_license_file_exists_and_is_mit():
    lic = _read("LICENSE")
    assert "MIT License" in lic
    assert "Permission is hereby granted" in lic
    pyproject = _read("pyproject.toml")
    assert "MIT" in pyproject


def test_wheel_metadata_declares_mit():
    pyproject = _read("pyproject.toml")
    assert 'license = "MIT"' in pyproject  # PEP 639 SPDX expression
    assert "license-files" in pyproject
    # PEP 639 license string + license-files need setuptools >= 77 to build;
    # an older floor fails with a `project.license` configuration error
    # (regression guard — 68.1.2 fails, 77.0.1 builds; 77.0.0 was yanked).
    # Regex-parse the [build-system] floor (robust to reformatting/extra
    # build requirements; anchored so comments can't satisfy the check).
    m = re.search(r'\[build-system\].*?requires\s*=\s*\["setuptools>=(\d+)',
                  pyproject, re.S)
    assert m, "build-system floor for setuptools missing in pyproject.toml"
    assert int(m.group(1)) >= 77, (
        f"setuptools floor {m.group(1)} < 77 — PEP 639 license string "
        "requires setuptools >= 77 (68.x fails with a project.license error)")


# ── Public surfaces consume the manifest ────────────────────────────────────


def test_readme_quotes_manifest_counts(manifest):
    readme = _read("README.md")
    assert f"{manifest['test_count']} pytest tests" in readme
    assert f"{manifest['golden_runner_count']} golden" in readme
    assert f"{manifest['benchmark_suites']} benchmark suites" in readme
    assert "RELEASE_EVIDENCE.json" in readme


def test_site_pages_quote_manifest_counts(manifest):
    for page in ("index.html", "benchmarks.html", "release.html", "trust.html"):
        text = _strip_html(_read(f"rta/website/{page}"))
        assert f"{manifest['test_count']}/{manifest['test_count']}" in text, page


def test_site_release_status_matches_manifest(manifest):
    assert manifest["release_status"] in _read("rta/website/release.html")


def test_contributing_counts_updated(manifest):
    contrib = _read("CONTRIBUTING.md")
    assert f"{manifest['test_count']} pytest tests" in contrib
    assert f"{manifest['test_files']} test" in contrib


def test_no_stale_numbers_on_live_surfaces():
    stale = ("710/710", "691 pytest", "**311 tests**", "311 tests across 14")
    for path in ("README.md", "rta/website/index.html", "rta/website/benchmarks.html",
                 "rta/website/release.html", "rta/website/trust.html", "CONTRIBUTING.md",
                 "rta/docs/product/HIGH_FIDELITY_PRODUCT_SPEC.md",
                 "rta/docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md",
                 "rta/docs/product/PRODUCT_WEBSITE_DESIGN_DNA.md",
                 "rta/docs/rta/BENCHMARK_EVIDENCE_MAP.md"):
        text = _read(path)
        for phrase in stale:
            assert phrase not in text, f"{path} contains stale '{phrase}'"


def test_product_docs_and_map_quote_manifest_counts(manifest):
    spec = _read("rta/docs/product/HIGH_FIDELITY_PRODUCT_SPEC.md")
    arch = _read("rta/docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md")
    dna = _read("rta/docs/product/PRODUCT_WEBSITE_DESIGN_DNA.md")
    evmap = _read("rta/docs/rta/BENCHMARK_EVIDENCE_MAP.md")
    n = str(manifest["test_count"])
    s = str(manifest["benchmark_suites"])
    assert f"{n} pytest" in spec
    assert f"{s}/{s}" in spec
    assert f"**{n}/{n}**" in arch
    assert f"{n} pytest tests" in arch
    assert f"{n} / 9 / {s}" in dna
    assert f"{n} passed" in evmap
    assert f"{s}/{s}" in evmap


def test_tagline_consistent(manifest):
    # The site header/footer is injected by site.js on every page; the home
    # page <title> also carries the canonical tagline statically.
    for path in ("README.md", "rta/website/index.html", "rta/website/assets/js/site.js"):
        text = _read(path)
        assert manifest["tagline"] in text, path


def test_cli_version_matches_manifest(manifest):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "cli.py", "--version"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, out
    assert manifest["version"] in out