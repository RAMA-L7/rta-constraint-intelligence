"""Release notes for the ``rta whats-new`` command.

This module ships inside the wheel, so ``rta whats-new`` works offline in
any environment — it does not need the git repo or a network connection.
Keep in sync with CHANGELOG.md: append the new version here on every
release (newest first).
"""

#: version -> list of bullet lines describing what changed in that release.
RELEASE_NOTES: dict[str, list[str]] = {
    "1.5.8": [
        "After writing any HTML report the CLI now prints how to open it: "
        "'start report.html' on Windows, 'open report.html' on macOS/Linux.",
        "README documents the report-open hint and links the live surfaces.",
        "P1 corrections from the VLSI Engineering Acceptance report: consistent "
        "source line numbers on all checker findings (CLI/JSON/API), clock-relations "
        "output now separates mismatches from missing constraints with consistent "
        "stats, the SDC generator never emits a malformed set_operating_conditions "
        "line, coverage CLI discloses 'coverage is NOT correctness', the webui shows "
        "SDC-only category coverage, and the API rejects empty/missing SDC with "
        "HTTP 400 for analyze/lint/convert.",
    ],
    "1.5.7": [
        "rst_n (and reset_n / arst_n) reset trees are now detected by "
        "SDC-151/152/153 — previously the most common reset naming was "
        "silently invisible.",
        "Semantic diff now reports clock period increases (CHG-CK-006) and "
        "matches IO delay value changes as modifications (CHG-IO-001).",
        "New surfaces: business site (GitHub Pages), engineer test kit "
        "(engineer_test_kit/), workspace header nav to the business site.",
    ],
    "1.5.6": [
        "AOCV/POCV derate methodology rules: SDC-156 (flat derate on an "
        "advanced-node flow, info) and SDC-157 (flat + sigma derates mixed, info).",
    ],
    "1.5.5": [
        "DFT / scan-mode completeness: SDC-154 (scan enable without mode "
        "coverage) and SDC-155 (scan false path too broad).",
    ],
    "1.5.4": [
        "Async reset & CDC structural completeness: SDC-151 (unconstrained "
        "reset tree), SDC-152 (suspect blanket false path), SDC-153 (reset "
        "synchronizer input).",
    ],
    "1.5.3": [
        "Packaging fix: rationale lint shipped in the wheel (SDC-150).",
    ],
    "1.5.2": [
        "Rationale-comment linting (SDC-150): timing exceptions without an "
        "explanatory comment are flagged.",
    ],
    "1.5.1": [
        "One-shot 'rta analyze all' + netlist CLI parity, published to PyPI.",
    ],
}


def latest_version() -> str:
    """Return the newest version present in the notes (keys are newest-first)."""
    return next(iter(RELEASE_NOTES))


def notes_for(version: str) -> list[str]:
    """Return the bullet list for a version, or [] if unknown."""
    return RELEASE_NOTES.get(version, [])
