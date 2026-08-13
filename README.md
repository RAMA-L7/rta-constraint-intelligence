# Ṛta

> **Ṛta brings order to timing intent, transforming constraints into trusted engineering knowledge through deterministic precision.**

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.5.8-blue" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-gray" alt="Platform">
  <img src="https://img.shields.io/badge/Scope-Block--Level-lightgrey" alt="Scope">
  <img src="https://img.shields.io/github/actions/workflow/status/RAMA-L7/rta-constraint-intelligence/ci.yml?branch=main" alt="CI">
  <img src="https://img.shields.io/pypi/v/rta-constraint-intelligence" alt="PyPI version">
</p>

<p align="center">
  <a href="https://RAMA-L7.github.io/rta-constraint-intelligence/">🌐 Business Site</a> ·
  <a href="https://pypi.org/project/rta-constraint-intelligence/">📦 PyPI</a> ·
  <a href="docs/features/README-11-cli-user-guide.md">📖 CLI User Guide</a> ·
  <a href="rta/evidence/manifest/RELEASE_EVIDENCE.json">🧾 Release Evidence</a>
</p>

---

## What is Ṛta?

**SDC (Synopsys Design Constraints)** files are the standard way to define timing, power, and design rule constraints for digital synthesis. A single mistake in an SDC file — a missing clock, an incorrect derate, an overly broad wildcard, a constraint pointing at a port that doesn't exist — can cause silicon failure or thousands of false timing violations.

Ṛta is a **deterministic constraint-quality layer that runs before STA** — not an STA engine, not a timing signoff tool, and not "AI-powered" (no LLMs anywhere in the analysis path). It covers the full SDC lifecycle:

```
  Write ──▶ Validate ──▶ Generate ──▶ Review ──▶ Readiness ──▶ Signoff
   │            │             │            │            │            │
   ▼            ▼             ▼            ▼            ▼            ▼
  Rules      Checker      Generator    Diff/Matrix  Interactions   STA
  Engine    (+ netlist)                + Coverage    + Readiness  (external)
```

**READY ≠ STA signoff. Coverage ≠ correctness. CI pass ≠ timing closure.** Ṛta is honest about what it does and doesn't prove.

**Scope:** block-level (single flat RTL or gate-level netlist) today. Hierarchical, full-chip resolution is a planned extension of the same design-context model — see `rta/engine/context/design_context.py`.

---

## 🆕 What's New

### v1.5.7 (latest)

**Engine fixes (found by real-usage verification):**
- **`rst_n` reset trees now detected by SDC-151/152/153.** The pin classifier previously recognized `rst`/`reset`/`rstn` but not `rst_n` — the most common reset naming in real designs — so the reset-tree checks silently never fired for most blocks. `_pin_role` now also matches `rst_n`, `reset_n`, `arst_n`.
- **Semantic diff reports the highest-signal changes.** A clock period *increase* (e.g. 10 → 12 ns) previously produced no finding — only decreases fired. New **`CHG-CK-006`** flags it. IO delay *value* changes were misreported as remove+add pairs; they now match on endpoint+mode and report as **`CHG-IO-001`** modifications.

**New surfaces:**
- 🌐 **Business site** (`rta/business-site/`) — premium marketing pages for every feature, with install commands, a searchable **Rules catalog** (all rules, filters, per-rule detail), and the brand North Star. Live at **https://RAMA-L7.github.io/rta-constraint-intelligence/** (also reachable from the tool header nav).
- 🧪 **Engineer test kit** (`engineer_test_kit/`) — self-contained per-feature fixture sets (SDC + matching netlists) with a README and machine-readable manifest, so you can validate every promised feature exactly as an engineer would. The commands in the [Test Kit](#-engineer-test-kit) section below are copy-paste ready.

### Earlier in v1.5.x — the "advanced rules" batch

| Code | Severity | What it catches |
|---|---|---|
| `SDC-150` | warning | Timing exception (`set_false_path` / `set_multicycle_path` / `set_case_analysis`) with no explanatory comment nearby — an undocumented exception can hide a real violation |
| `SDC-151` | warning | Unconstrained reset tree — a net driving ≥2 flip-flop reset pins with no timing exception |
| `SDC-152` | warning | Blanket wildcard false path covering a reset tree — hides the sync-input vs deassertion distinction |
| `SDC-153` | warning | Reset synchronizer shape — a reset tree that also drives data inputs needs distinct sync-input vs deassertion exceptions |
| `SDC-154` | warning | Scan enable referenced with no `set_case_analysis` mode assignment — STA would blend shift and capture paths |
| `SDC-155` | warning | Fully-blanket false path in a DFT design — cannot distinguish scan-present from non-scan flops |
| `SDC-156` | info | Flat single-number derates on an advanced (≤16nm) flow — consider AOCV/POCV |
| `SDC-157` | info | Flat and sigma/table derates mixed in one file — pick one methodology per corner |

Full details: `rta rules show SDC-150` … `rta rules show SDC-157`.

---

## 🚀 Quick Start

### Install from PyPI (recommended)
```bash
pip install rta-constraint-intelligence
rta --version        # Ṛta v1.5.7
```

### Install from source
```bash
git clone https://github.com/RAMA-L7/rta-constraint-intelligence.git
cd rta-constraint-intelligence
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[web]"
streamlit run legacy/streamlit/app.py   # preserved legacy Streamlit UI
```

### CLI (from source, use `python cli.py`; after pip install, use `rta`)
```bash
rta check sample.sdc                       # validate
rta generate --design MY_CHIP --clock clk=10.0   # generate
rta --help                                 # see all commands
```

### Verify your setup
```bash
python3 smoke_test.py                # fast engine check, no browser needed
pytest rta/tests -q                   # full test suite
```

### See what changed in each release

```bash
rta whats-new          # release notes for the latest versions
rta whats-new --all    # full changelog from the terminal
```

Works offline after install (the notes ship inside the wheel). If your
installed version is behind, it tells you the exact upgrade command.

> 📖 **New to the CLI?** Read the complete [**Ṛta CLI User Guide — Every Feature**](docs/features/README-11-cli-user-guide.md): installation, all 12 commands, exit codes, CI gates, netlist-aware checks, and a tested workflow.

Ṛta ships with **826 pytest tests** across the engine, covering deterministic
checks, netlist resolution, interactions, and readiness scoring — backed by
**9 golden runners** and **42 benchmark suites**. All counts are recorded in
`RELEASE_EVIDENCE.json` and regenerated via `python rta/evidence/build_evidence.py`.

### Docker
```bash
docker build -t rta .
docker run -it rta check sample.sdc                # CLI
docker run -p 8501:8501 rta web                     # Web UI
```

---

## 📋 Feature Overview (119 Rules · 15 Major Features)

| # | Feature | Module | CLI Command | Description |
|---|---------|--------|-------------|-------------|
| 1 | [**Checker / Validator**](docs/features/README-01-checker.md) | `rta/engine/rules/checker.py` | `rta check` | 119 semantic checks: errors, warnings, best practices |
| 2 | [**Generator**](docs/features/README-02-generator.md) | `rta/engine/generate/generator.py` | `rta generate` | Generate a complete signoff-ready SDC from a structured spec |
| 3 | **Netlist-Aware Cross-Checks** | `rta/engine/context/design_context.py`, `design_coverage.py` | `rta check --netlist` | Resolves get_ports/get_pins/get_cells against a real RTL or gate-level Verilog file via structural connectivity — not name-matching |
| 4 | **Constraint Interactions** | `rta/engine/analysis/constraint_interactions.py` | — | Detects exact duplicates, silent overrides, and contradictory constraints |
| 5 | **Constraint Readiness** | `rta/engine/analysis/constraint_readiness.py` | — | Aggregates Checker evidence into a 7-dimension signoff-readiness verdict |
| 6 | [**Linter**](docs/features/README-01-checker.md#sdc-linter) | `rta/engine/lint/linter.py` | `rta lint` | Format & reorganize SDC files with section ordering |
| 7 | [**Converter**](#sdc-convert) | `rta/engine/convert/converter.py` | `rta convert` | Parse SDC to structured JSON/YAML for tool integration |
| 8 | [**Batch Processor**](#sdc-batch) | `rta/engine/batch/batch_runner.py` | `rta batch` | Process all SDCs in a directory — check, lint, report |
| 9 | [**Constraint Change Analyzer**](docs/features/README-03-diff.md) | `rta/engine/diff/constraint_diff.py` | `rta diff` | Semantic diff with TCL variable resolution + wildcard drift |
| 10 | [**Clock Relation Analyzer**](docs/features/README-04-clock-relations.md) | `rta/engine/analysis/clock_relations.py` | `rta analyze clock-relations` | Infer correct clock relationships and detect mismatches |
| 11 | [**Multi-Corner Manager (MMC)**](docs/features/README-05-mmc.md) | `rta/engine/corners/corner_manager.py` + `mmc.py` | `rta corners` | PVT corner presets, per-corner SDC generation, ZIP packaging |
| 12 | [**Constraint Coverage Gap Analysis**](docs/features/README-06-coverage.md) | `rta/engine/analysis/design_coverage.py` | `rta coverage` | Category gap analysis, plus netlist-aware real-port coverage |
| 13 | [**Custom Rules Engine**](docs/features/README-07-custom-rules.md) | `rta/engine/rules/custom_rules.py` | `rta check --custom-rules` | YAML-based project-specific validation policies |
| 14 | [**Rules Registry**](docs/features/README-08-rules-registry.md) | `rta/engine/rules/rules_registry.py` | `rta rules` | Centralized documentation of all 119 rule codes |
| 15 | [**HTML Signoff Reports**](docs/features/README-09-reports.md) | `rta/engine/report/reporter.py` | `rta report` | Self-contained, zero-dependency HTML reports |

Plus:
- **Advanced constraint-intelligence rules (SDC-150…157)** — rationale linting, reset/CDC structural completeness, DFT/scan-mode coverage, and AOCV/POCV derate methodology (see [What's New](#-whats-new)).
- A preserved legacy [**Streamlit Web UI**](docs/features/README-10-web-ui.md) (`legacy/streamlit/app.py`) with all 12 tools as equal-prominence tabs — Checker, Generator, Linter, Converter, Corner Mgr, MMC SDC, Diff, Clock, Coverage, Interactions, Readiness, Rules (kept in `legacy/` by design).
- A **static workspace UI** with a stdlib API server (`rta/workspace/`) — the active web surface, also deployed to **Hugging Face Spaces**.

---

## 🔍 Check Your SDC

```bash
rta check design.sdc
# Output:
#   Errors:   3    (SDC-001, SDC-005, SDC-006)
#   Warnings: 8    (SDC-024, SDC-030, ...)
#   Info:    12    (best practice suggestions)
#
#   [SDC-001] No create_clock defined — all paths unconstrained.
#   [SDC-024] 4 clocks but no set_clock_groups — CDC un-flagged.
```

### Design-aware checking (SDC + netlist)

Give Ṛta the RTL/gate-level netlist and it resolves every `get_ports` / `get_pins` / `get_cells` structurally — typo'd ports, empty wildcards, and bad hierarchy are caught with proof, and the reset/CDC/scan/coverage rules have real fanout to work with:

```bash
rta check design.sdc --netlist design.v --top top
#   Design context: top (12 ports, 34 instances)
#   ...
#   [SDC-151] Reset tree 'rst_n' drives 2 flip-flop reset pin(s) but has no
#             timing exception — async reset deassertion and CDC paths are unconstrained.
```

With JSON output for CI integration:
```bash
rta check design.sdc --json
rta check design.sdc --junit --output results.xml
```

With custom rules:
```bash
rta check design.sdc --custom-rules my_policy.yaml --custom-rules team_rules.yaml
```

With CSV output (for CI/CD):
```bash
rta check design.sdc --format csv > results.csv
rta check design.sdc --format markdown > report.md
```

## 📝 Lint & Format SDC

```bash
rta lint design.sdc                    # preview formatted output
rta lint design.sdc --fix              # fix in-place
rta lint design.sdc --check            # exit 1 if not clean
rta lint design.sdc --output clean.sdc # write to file
```

## 🔄 Convert SDC

```bash
rta convert design.sdc --format json
rta convert design.sdc --format yaml --output constraints.yaml
```

## 📦 Batch Process

```bash
rta batch check ./sdc_files/           # check all SDCs in directory
rta batch lint ./sdc_files/ --fix      # lint all files in-place
rta batch report coverage ./sdc_files/ -o ./reports/
```

## ⚙️ Generate SDC

```bash
rta generate \
  --design MY_CHIP \
  --clock clk_core=5.0:sys_clk \
  --clock clk_slow=20.0:slow_clk \
  --uncertainty 0.15 \
  --operating-condition WORST \
  --derate \
  --propagated \
  --output my_chip.sdc
```

## 🔍 Compare SDC Versions

```bash
rta diff old.sdc new.sdc \
  --linked-v1 params_v1.tcl \
  --linked-v2 params_v2.tcl \
  --verbose
# Output:
#   FATAL  [CHG-FP-001]  False path removed — timing now checked on this path
#   INFO   [CHG-CK-001]  Clock period decreased from 5ns to 4ns
#   INFO   [CHG-CK-006]  Clock period increased from 10.0ns to 12.0ns — verify intentional
#   INFO   [CHG-IO-001]  Input delay on data[0] changed 2.0ns -> 2.5ns
#   INFO   [CHG-GEN-001] New constraint added
```

## 🕐 Clock Relation Analysis

```bash
rta analyze clock-relations design.sdc
# Output:
#   Clocks: 4    Pairs: 6    Mismatches: 2
#   [SDC-060] WARNING  CLKA vs CLKB
#     Specified: -asynchronous
#     Expected:  -physically_exclusive
```

## 🔲 Multi-Corner SDC Generation

```bash
rta corners list                            # see presets
rta corners show "Classic 3-corner"        # view details
```

```bash
# Generate per-corner SDCs via the Web UI
rta web
# → MMC Corner Manager tab → load preset → generate
```

## 📊 Constraint Coverage

```bash
rta coverage design.sdc
# Output:
#   Overall Coverage: 56.4% (22/39 items)
#
#   🕐 Clocks: 78%       [#####.....] (7/9)
#   🔌 I/O: 67%          [####......] (4/6)
#   ⚠️ Exceptions: 71%   [#####.....] (5/7)
#   📏 Design Rules: 83% [######....] (5/6)
#   📊 AOCV/Derate: 0%   [..........] (0/5) ← critical gap
#   ⚡ Power/DFT: 33%    [###.......] (2/6)

rta coverage design.sdc --missing-only    # compact view
rta coverage design.sdc --json            # for automation
```

## 📋 Rules Lookup

```bash
rta rules list                             # all 119 rules
rta rules list --severity error             # errors only
rta rules list --search derate              # search by keyword
rta rules show SDC-151                      # single rule details
```

## 📋 Custom Rules YAML

```yaml
# my_policy.yaml
name: My Team Policies
version: "1.0"
rules:
  - id: MY-001
    name: "Clock period ≤ 10ns"
    severity: warning
    command: create_clock
    condition: value_above
    field: period
    threshold: 10.0
    message: "Clock period {value}ns exceeds 10ns limit"

  - id: MY-002
    name: "Propagated clock required"
    severity: error
    command: set_propagated_clock
    condition: present
    message: "No set_propagated_clock — required by policy"
```

## 📋 HTML Signoff Reports

```bash
rta report check design.sdc -o quality_report.html
rta report diff old.sdc new.sdc -o diff_report.html
rta report clock-relations design.sdc -o clock_report.html
rta report coverage design.sdc -o coverage_report.html
```

The CLI prints how to open the report right after writing it:

```
Written to quality_report.html
Open with: start quality_report.html      # Windows
Open with: open quality_report.html       # macOS / Linux
```

On Windows, `start quality_report.html` opens it in your default browser. The `rta analyze all ... -o report.html` full-analysis report prints the same hint.

---

## 🧪 Engineer Test Kit

The repo ships a self-contained **`engineer_test_kit/`** — per-feature fixture sets (SDC + matching netlists) with a `README.md` and machine-readable `manifest.json`, so you (or an engineer on your team) can validate every promised feature on realistic inputs:

| Kit | Feature | What it exercises |
|---|---|---|
| `01_block_full` | Reference good block | A clean APB+UART block (0 errors) — the baseline every other set is compared against |
| `02_check_variants` | Checker edge cases | No I/O delays, I/O exceeding period, missing generated-clock source, duplicate clocks, empty file |
| `03_clock_relations` | Clock relation analysis | Async-vs-exclusive mismatch, missing clock groups, generated-clock chains |
| `04_coverage` | Coverage (netlist-aware) | Partially constrained bus → partial-coverage finding |
| `05_design_context` | Design context | Typo'd port, wildcard with no match, bad hierarchy → SDC-055/056/057 |
| `06_scan_dft` | DFT/scan mode | Unconstrained scan_en → SDC-154; blanket scan cut → SDC-155 |
| `07_reset_cdc` | Reset / CDC | Unconstrained `rst_n` → SDC-151; blanket → SDC-152; sync-stage → SDC-153; covered → clean |
| `08_derate_ocv` | Derate methodology | Flat derate on 16nm corner → SDC-156; mixed flat+sigma → SDC-157 |
| `09_rationale` | Exception comments | No-comment false path → SDC-150; commented → clean |
| `10_generate` – `17_report` | Tool features | generate, lint, convert, diff (incl. TCL), baseline + gate, corners, batch, HTML reports |

Quick tour (from the repo root):

```bash
# Reference block — expect 0 errors
python cli.py check engineer_test_kit/01_block_full/apb_uart.sdc \
  --netlist engineer_test_kit/01_block_full/apb_uart_netlist.v --top apb_uart_top

# Unconstrained reset tree — expect SDC-151
python cli.py check engineer_test_kit/07_reset_cdc/reset_unconstrained.sdc \
  --netlist engineer_test_kit/07_reset_cdc/apb_uart_netlist.v --top apb_uart_top

# Covered reset — expect SDC-151/152/153 absent
python cli.py check engineer_test_kit/07_reset_cdc/reset_covered.sdc \
  --netlist engineer_test_kit/07_reset_cdc/apb_uart_netlist.v --top apb_uart_top

# Flat derate on a 16nm corner — expect SDC-156 (--verbose shows info-level findings)
python cli.py check --verbose engineer_test_kit/08_derate_ocv/flat_on_16nm.sdc

# Full E2E: analyze all → HTML report
python cli.py analyze all engineer_test_kit/01_block_full/apb_uart.sdc \
  --netlist engineer_test_kit/01_block_full/apb_uart_netlist.v --top apb_uart_top -o report.html
```

Every set's expected findings are documented in `engineer_test_kit/README.md` and `engineer_test_kit/manifest.json`.

---

## 📦 Project Structure

```
rta-constraint-intelligence/    (clone dir)
│
├── rta/ ────────────────────────────────── the package (pip-installable)
│   ├── engine/                 # deterministic analysis core
│   │   ├── rules/              # checker, rules_registry (119 codes), custom_rules
│   │   ├── context/            # design_context (netlist resolution)
│   │   ├── analysis/           # interactions, readiness, clock_relations,
│   │   │                       #   design_coverage, async_reset_check,
│   │   │                       #   dft_scan_check, derate_methodology
│   │   ├── diff/               # constraint_diff (semantic diff)
│   │   ├── generate/ lint/ convert/ batch/ corners/ report/
│   ├── cli/cli.py              # command-line interface (12 commands)
│   ├── api/                    # HTTP API server (workspace backend)
│   ├── workspace/              # static web UI (active web surface)
│   ├── branding/               # product identity
│   ├── evidence/               # release evidence, golden runners, benchmarks,
│   │                           #   RELEASE_EVIDENCE.json
│   ├── tools/                  # deploy_hf_space.py, report/, corners/, ...
│   ├── tests/                  # 826 pytest tests
│   ├── examples/ docs/ knowledge/
│   └── business-site/          # 🌐 marketing site (GitHub Pages)
│
├── engineer_test_kit/          # 🧪 per-feature SDC+netlist fixture sets
├── legacy/streamlit/           # preserved legacy Streamlit UI (retired)
├── cli.py                      # root shim: `python cli.py ...` (== `rta`)
├── pyproject.toml              # PyPI package (rta-constraint-intelligence)
├── Dockerfile                  # container image
├── samples/                    # demo SDC files
├── docs/features/              # detailed per-feature documentation
└── CONTRIBUTING.md / CHANGELOG.md / LICENSE
```

---

## 🖥️ CLI Reference

| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `check` | Validate SDC | `--json`, `--junit`, `--custom-rules`, `--netlist`, `--top`, `--verbose`, `--format`, `--baseline`, `--gate` |
| `generate` | Generate SDC | `--clock`, `--design`, `--derate`, `--operating-condition` |
| `diff` | Semantic diff | `--linked-v1`, `--linked-v2`, `--json`, `--verbose` |
| `corners` | Manage corners | `list`, `show <name>` |
| `analyze` | Deep analysis | `clock-relations`, `all`, `--netlist`, `--top`, `--json` |
| `rules` | Rule lookup | `list`, `show <code>`, `--module`, `--severity`, `--search` |
| `coverage` | Gap analysis | `--json`, `--missing-only`, `--netlist`, `--top` |
| `lint` | Format/reorganize SDC | `--check`, `--fix`, `--output` |
| `convert` | SDC to JSON/YAML | `--format`, `--output` |
| `batch` | Directory-wide processing | `check`, `lint`, `report`, `--fix` |
| `report` | HTML reports | `check`, `diff`, `clock-relations`, `coverage` |
| `whats-new` | Release notes | `--all` (full changelog) |
| `web` | Launch browser UI | (opens `http://localhost:8501`) |

---

## 🏗️ Design Principles

1. **Deterministic, no LLMs** — the analysis path is pure, provable, and reproducible
2. **Provable findings only** — anything the resolver can't verify stays un-assumed (never silent correctness)
3. **Zero external dependencies** for core validation (stdlib only)
4. **Fail-fast on errors** — CLI exits with code 1 if any errors found
5. **Graceful optional features** — YAML (PyYAML optional), Web (Streamlit optional)
6. **CI-friendly** — JUnit XML, JSON output, exit codes, pre-commit hooks
7. **Self-contained reports** — HTML with inline CSS, no CDN, no JS

---

## 📚 Documentation

**Detailed feature documentation** — each feature has its own README with:
- Why it's needed (problem statement)
- How it was implemented (technical architecture)
- Use cases (when/why to use it)
- Structural view (ASCII diagrams)
- Flow diagrams (step-by-step)
- CLI usage examples
- Python API examples
- Configuration reference

→ **[Feature Documentation Index](docs/features/)**

---

## 🧪 Test Samples

```bash
# Run all available samples through the checker
rta check samples/example.sdc --verbose
rta coverage samples/example.sdc
rta analyze clock-relations samples/clock_relations.sdc
rta diff samples/constraint_diff_v1.sdc samples/constraint_diff_v2.sdc

# New samples with intentional bugs
rta check samples/buggy_no_clocks.sdc
rta check samples/warning_heavy.sdc

# Lint & convert
rta lint samples/example.sdc
rta convert samples/example.sdc --format json

# Run the full test suite
python -m pytest rta/tests/ -q
```

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide, including the rule-authoring guide for custom rules and the evidence/benchmark discipline. At a glance:

- **Add a new checker rule:** Edit `rta/engine/rules/checker.py` + register it in `rta/engine/rules/rules_registry.py`
- **Add a new custom condition:** Edit `rta/engine/rules/custom_rules.py`
- **Add a new coverage item:** Edit `rta/engine/analysis/design_coverage.py`
- **Add a new report section:** Edit `rta/engine/report/reporter.py`
- **Run the evidence gate:** `python rta/evidence/build_evidence.py` then `pytest rta/tests/test_evidence.py`

---

## 📜 License

**MIT License** — free for commercial and non-commercial use.

---

## 🙏 Acknowledgments

Built with deep respect for:
- [Ausdia](https://www.ausdia.com/) — TimeVision constraint analysis tool and their excellent blog posts on SDC pitfalls
- [Synopsys](https://www.synopsys.com/glossary/what-is-sdc.html) — SDC standard and tool documentation
- [OpenCores](https://opencores.org/) — open-source digital design community

---

*Ṛta is an open-source project by RAMA-L7 — an MIT-licensed constraint-intelligence toolkit for digital design.*
