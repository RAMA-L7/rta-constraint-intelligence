# Changelog

All notable changes to Ṛta (formerly SDC Tools) are documented here.

## [1.5.4] — 2026-08-12

### Added

- **Async reset & CDC structural completeness (Feature F2)** — new module
  `rta/engine/analysis/async_reset_check.py` with three design-aware rules:
  - `SDC-151` (warning) Unconstrained reset tree — a net structurally driving
    ≥2 flip-flop reset pins with no timing exception touching it.
  - `SDC-152` (warning) Suspect blanket false path — a wildcard
    `set_false_path` (`-from [all_inputs]` / `*`) covers a reset tree while no
    targeted exception exists, hiding the sync-input vs deassertion distinction.
  - `SDC-153` (warning) Reset synchronizer input unconstrained — a reset tree
    whose net also drives data input(s), the async-reset synchronizer shape.
  - Provable-only: all three rules run ONLY when a netlist is supplied
    (`--netlist` / design context); SDC-only mode stays completely silent.
    Fixed ≥2 reset-pin threshold (documented), zero noise on the existing
    `netlist_aware` fixture corpus.

## [1.5.3] — 2026-08-12

### Fixed

- **Packaging: root shim `rationale_lint.py` added to `py-modules`.** The
  v1.5.2 wheel shipped without it, so the installed package's checker
  silently skipped the rationale-lint import (guarded try/except) and
  SDC-150 never fired from an installed `rta` — despite working in the repo.
  New regression test `test_all_root_shims_in_py_modules` fails the suite if
  any root shim is missing from `py-modules`, so this class of bug is caught
  by pytest, not by a manual release check.

## [1.5.2] — 2026-08-12

### Added

- **Rationale-comment linting (`SDC-150`)** — Feature F1. Flags
  `set_false_path` / `set_multicycle_path` / `set_case_analysis` lines that
  lack a substantive explanatory comment (within 3 lines above or inline,
  incl. multiline continuation lines). Enforces the advice SDC-020 already
  gives, turning an advisory fix suggestion into an enforceable check. Pure
  text / line-proximity — runs in SDC-only and design-aware modes, no netlist
  needed. 781 pytest tests, 112 rules.

## [1.5.1] — 2026-08-12

### Added

- **`rta analyze all` — one-shot full-block E2E run.** Runs check + coverage + clock relations + constraint interactions + readiness over the same SDC (+ optional netlist) and emits one combined result in three modes: text summary, `--json`, or a single self-contained HTML report (`-o report.html`). Exit code matches `rta check` (0 = no errors, 1 = errors), so it doubles as a CI gate. Verified design-aware with `--netlist design.v --top top`.
- **CLI netlist parity.** `rta coverage --netlist`, `rta analyze clock-relations --netlist`, and `rta report check --netlist` now expose the design-aware analysis that was previously UI-only — same deterministic engine, no engine changes.
- **CI + PyPI badges** in the README (live GitHub Actions status and PyPI version).
- CLI user guide documents the new one-shot workflow (`docs/features/README-11-cli-user-guide.md`).

### Fixed

- Evidence manifest and public docs re-synced to the current test count (767 pytest tests) after new CLI tests landed.

## [1.5.0] — 2026-08-11

### ✨ New Features

- **Netlist-Aware Cross-Checks** — `design_context.py` / `design_coverage.py` resolve `get_ports`/`get_pins`/`get_cells` against a real RTL or gate-level Verilog file via structural pin/net connectivity (not name-matching). Available in Checker, Coverage, and Clock Relations tabs; block-level scope, full-chip planned.
- **Constraint Interactions** (`constraint_interactions.py`) — new tab detecting exact duplicates, silent overrides, and contradictory constraints (e.g. `set_max_delay` < `set_min_delay` on the same endpoints) within a single SDC.
- **Constraint Readiness** (`constraint_readiness.py`) — new tab aggregating Checker evidence into a 7-dimension signoff-readiness verdict (Clocks, I/O, Exceptions, Coverage, Consistency, Analysis Trust, Design Context) with prioritized fix-actions. Explicitly not an STA signoff tool.
- **`smoke_test.py`** — standalone engine regression test (no browser/Streamlit required); run after any change for fast pass/fail feedback.
- Rebranded project to **Ṛta**; engine reorganized under `rta/` as a proper package (top-level modules are now thin migration shims for backward compatibility).
- Premium visual redesign of the web UI (light, flat, single-accent theme) — navigation kept as the original flat tab bar by design; new tabs added alongside existing ones rather than restructuring around them.

### 🐛 Bug Fixes

- **Packaging / `pip install`** — raised the `pyproject.toml` build-system floor to `setuptools>=77.0.1`. The PEP 639 SPDX license expression (`license = "MIT"` + `license-files`) cannot be parsed by older setuptools (verified: 68.1.2 fails with a `project.license` configuration error; 77.0.1 builds — 77.0.0 was yanked from PyPI). `release_cleanroom.py` now builds the wheel itself from a fresh venv pinned to the declared floor, so this class of regression is caught by the gate instead of slipping past a pre-built wheel.

### 🚀 First PyPI Release under the Ṛta name

- **`rta-constraint-intelligence` v1.5.0 published to PyPI** — `pip install rta-constraint-intelligence` now installs the package and the `rta` command (wheel + sdist, `License-Expression: MIT`, Python ≥ 3.10). The short name `rta` was already taken on PyPI, so the distribution keeps the full name; the `rta` console script is unaffected.
- CLI help/usage text now consistently says `rta` (the legacy `sdc-tools` name was dropped in the rebrand and is no longer installed as a command).
- New [`docs/features/README-11-cli-user-guide.md`](docs/features/README-11-cli-user-guide.md) — engineer-facing guide covering all 12 CLI commands, exit codes, CI gates, netlist-aware checks, and a tested workflow.

### 🔧 Notes

- All 95 pre-existing rule codes retained with identical severity/behavior — verified via direct functional comparison, not just static diff.
- 16 new rule codes added (`SDC-046`–`SDC-070` range) covering undefined-clock references and the interactions/design-context checks above.

## [1.3.0] — 2026-07-25

### ✨ New Features

- **SDC Linter** (`rta lint`) — Format & reorganize SDC files with consistent section ordering, spacing, and formatting
- **SDC Converter** (`rta convert`) — Parse SDC files to structured JSON/YAML for tool integration
- **Batch Processor** (`rta batch`) — Process all SDC files in a directory (check, lint, report)
- **CSV/Markdown output** (`rta check --format csv/markdown`) — Machine-readable output for CI/CD
- **Line numbers in checker** — Error/warning messages now show source line numbers
- **Dark mode support** — Full dark theme with `prefers-color-scheme` and Streamlit dark mode toggle
- **10-tab Web UI** — Added Linter, Converter, and Rules Reference tabs to Streamlit app
- **GitHub Actions CI** — Automated test pipeline on Python 3.10/3.11/3.12 across Linux, Windows, macOS

### 🐛 Bug Fixes

- **SDC-008/009 regex** — Fixed checker regex to handle flags between command and value (e.g., `set_input_delay -max 6.0`)
- **pyproject.toml** — Fixed unquoted wildcard key that caused TOML parse error

### 📝 Documentation

- **CHANGELOG.md** — New file documenting all version history
- **CONTRIBUTING.md** — New file with testing guidelines and development setup
- **README.md** — Updated to 13 features, added lint/convert/batch sections
- **10 feature docs** — Complete feature documentation in `docs/features/`
- **3 new sample SDCs** — `buggy_no_clocks.sdc`, `warning_heavy.sdc`, `multi_corner_template.sdc`

### 🧪 Testing

- **311 tests** — Comprehensive test suite covering all 15+ modules
- **Code review** — Fixed 10 issues from cross-module code review
- **Test files**: `test_linter.py`, `test_converter.py`, `test_batch_runner.py` (new)

### 🏗️ Infrastructure

- **Dockerfile** — Updated to include new modules (linter, converter, batch_runner, ui/)
- **.gitignore** — Added `graphify-out/`, `.pytest_cache`, IDE files, log files
- **Version bump** — Updated to v1.3.0 across all files

---

## [1.2.0] — 2026-07-24

### ✨ New Features

- **Clock Relation Analyzer** (`sdc-tools analyze clock-relations`) — Detect incorrect `set_clock_groups` constraints (SDC-060..063)
- **Rules Reference tab** — Searchable table of all SDC rule codes with engineering context
- **MMC integration in SDC Generator** — Live validation + multi-corner generation + baseline comparison
- **HTML Clock Relations Report** — Visual clock matrix with mismatch highlighting

### 🐛 Bug Fixes

- **Virtual clock detection** — Improved virtual clock identification in checker
- **Derate value extraction** — Fixed regex for extracting derate values

### 📝 Documentation

- **Clock Relations feature doc** (`docs/features/README-04-clock-relations.md`)
- **Rules Registry feature doc** (`docs/features/README-08-rules-registry.md`)
- **Updated feature docs** for Checker and Coverage modules

---

## [1.1.0] — 2026-07-23

### ✨ New Features

- **Constraint Change Analyzer** (`sdc-tools diff`) — Semantic SDC diff with 20 change detection rules (CHG-*)
- **TCL Variable Resolution** (`tcl_resolver.py`) — Resolve `$VARNAME` references in linked TCL files
- **Wildcard Pattern Analyzer** (`wildcard_analyzer.py`) — Risk-score wildcard patterns in SDC object specs
- **MMC SDC Generator** — Generate per-corner SDC files with cross-corner checks
- **MMC Corner Manager** — PVT corner presets (3-corner, 5-corner, 8-corner, custom)
- **Coverage Gap Analysis** (`sdc-tools coverage`) — 39-item analysis across 6 constraint categories
- **Custom Rules Engine** (`sdc-tools check --custom-rules`) — YAML-based project-specific validation policies
- **Rules Registry** — Centralized documentation for all 60+ rule codes

### 📦 Packaging

- **PyPI package** — `pip install sdc-tools`
- **Docker image** — `ramal7/sdc-tools`
- **Pre-commit hooks** — `.pre-commit-config.yaml` for SDC validation

### 📝 Documentation

- **8 feature docs** in `docs/features/`
- **Master README** with project structure, CLI reference, quick-start examples

---

## [1.0.0] — 2026-07-22

### ✨ Initial Release

- **SDC Checker** (`sdc-tools check`) — 40+ semantic checks for SDC files
  - 11 error rules (SDC-001..011)
  - 18 warning rules (SDC-020..037)
  - 17 best-practice info rules (SDC-100..126)
- **SDC Generator** (`sdc-tools generate`) — Generate complete SDC from CLI parameters
  - Clock definitions (primary, generated, virtual)
  - I/O constraints with timing
  - Design rules, derate, power constraints
- **JSON output** (`--json`) — Machine-readable output
- **JUnit XML output** (`--junit`) — CI/CD integration
- **HTML Reports** (`sdc-tools report`) — Self-contained signoff reports
- **Streamlit Web UI** (`sdc-tools web`) — Interactive browser interface
