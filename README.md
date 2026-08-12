# Ṛta

> **Constraint Intelligence for Digital Design — deterministic SDC validation, generation, and pre-STA readiness review, with optional netlist-aware checking.**

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.5.5-blue" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-gray" alt="Platform">
  <img src="https://img.shields.io/badge/Scope-Block--Level-lightgrey" alt="Scope">
  <img src="https://img.shields.io/github/actions/workflow/status/RAMA-L7/rta-constraint-intelligence/ci.yml?branch=main" alt="CI">
  <img src="https://img.shields.io/pypi/v/rta-constraint-intelligence" alt="PyPI version">
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

**Scope:** block-level (single flat RTL or gate-level netlist) today. Hierarchical, full-chip resolution is a planned extension of the same design-context model — see `design_context.py`.

---

## 🚀 Quick Start

### Install from source
```bash
git clone https://github.com/RAMA-L7/rta-constraint-intelligence.git
cd rta-constraint-intelligence
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[web]"
streamlit run legacy/streamlit/app.py   # preserved legacy Streamlit UI
```

### CLI
```bash
python3 cli.py check sample.sdc                       # validate
python3 cli.py generate --design MY_CHIP --clock clk=10.0   # generate
python3 cli.py --help                                 # see all commands
```

### Verify your setup
```bash
python3 smoke_test.py                # fast engine check, no browser needed
pytest rta/tests -q                   # full test suite
```

> 📖 **New to the CLI?** Read the complete [**Ṛta CLI User Guide — Every Feature**](docs/features/README-11-cli-user-guide.md): installation, all 12 commands, exit codes, CI gates, netlist-aware checks, and a tested workflow.

Ṛta ships with **809 pytest tests** across the engine, covering deterministic
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

## 📋 Feature Overview (15 Major Features)

| # | Feature | Module | CLI Command | Description |
|---|---------|--------|-------------|-------------|
| 1 | [**Checker / Validator**](docs/features/README-01-checker.md) | `checker.py` | `rta check` | 100+ semantic checks: errors, warnings, best practices |
| 2 | [**Generator**](docs/features/README-02-generator.md) | `generator.py` | `rta generate` | Generate a complete signoff-ready SDC from a structured spec (11 sections: clocks, I/O, design rules, derate, DFT, exceptions, power, dont-use) |
| 3 | **Netlist-Aware Cross-Checks** *(new)* | `design_context.py`, `design_coverage.py` | `rta check --netlist` | Resolves get_ports/get_pins/get_cells against a real RTL or gate-level Verilog file via structural connectivity — not name-matching |
| 4 | **Constraint Interactions** *(new)* | `constraint_interactions.py` | — | Detects exact duplicates, silent overrides, and contradictory constraints (e.g. max_delay < min_delay) within one SDC |
| 5 | **Constraint Readiness** *(new)* | `constraint_readiness.py` | — | Aggregates Checker evidence into a 7-dimension signoff-readiness verdict with prioritized fix-actions |
| 6 | [**Linter**](docs/features/README-01-checker.md#sdc-linter) | `linter.py` | `rta lint` | Format & reorganize SDC files with section ordering |
| 7 | [**Converter**](#sdc-convert) | `converter.py` | `rta convert` | Parse SDC to structured JSON/YAML for tool integration |
| 8 | [**Batch Processor**](#sdc-batch) | `batch_runner.py` | `rta batch` | Process all SDCs in a directory — check, lint, report |
| 9 | [**Constraint Change Analyzer**](docs/features/README-03-diff.md) | `constraint_diff.py` | `rta diff` | Semantic diff with TCL variable resolution + wildcard drift |
| 10 | [**Clock Relation Analyzer**](docs/features/README-04-clock-relations.md) | `clock_relations.py` | `rta analyze clock-relations` | Infer correct clock relationships and detect mismatches |
| 11 | [**Multi-Corner Manager (MMC)**](docs/features/README-05-mmc.md) | `corner_manager.py` + `mmc.py` | `rta corners` | PVT corner presets, per-corner SDC generation, ZIP packaging |
| 12 | [**Constraint Coverage Gap Analysis**](docs/features/README-06-coverage.md) | `coverage.py` | `rta coverage` | Category gap analysis, plus netlist-aware real-port coverage when a design is supplied |
| 13 | [**Custom Rules Engine**](docs/features/README-07-custom-rules.md) | `custom_rules.py` | `rta check --custom-rules` | YAML-based project-specific validation policies |
| 14 | [**Rules Registry**](docs/features/README-08-rules-registry.md) | `rules_registry.py` | `rta rules` | Centralized documentation of all 111+ rule codes |
| 15 | [**HTML Signoff Reports**](docs/features/README-09-reports.md) | `reporter.py` | `rta report` | Self-contained, zero-dependency HTML reports |

Plus a preserved legacy [**Streamlit Web UI**](docs/features/README-10-web-ui.md) (`legacy/streamlit/app.py`) with all 12 tools as equal-prominence tabs — Checker, Generator, Linter, Converter, Corner Mgr, MMC SDC, Diff, Clock, Coverage, Interactions, Readiness, Rules (retired from the launch path; kept in `legacy/`).

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
#   WARN   [CHG-CK-001]  Clock period decreased from 5ns to 4ns
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
rta rules list                             # all 60+ rules
rta rules list --severity error             # errors only
rta rules list --search derate              # search by keyword
rta rules show SDC-060                      # single rule details
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

---

## 📦 Project Structure

```
rta-constraint-intelligence/    (clone dir)
│
├── core modules ──────────────────────────────
│   ├── checker.py           # SDC validation (40+ checks)
│   ├── generator.py         # SDC generation from params
│   ├── linter.py            # SDC formatter + section reorganization
│   ├── converter.py         # SDC → JSON/YAML parser
│   ├── batch_runner.py      # Directory-wide batch processing
│   ├── constraint_diff.py   # Semantic SDC diff + change rules
│   ├── clock_relations.py   # Clock relation inference + mismatches
│   ├── corner_manager.py    # PVT corner data model + presets
│   ├── mmc.py               # Multi-corner SDC operations
│   ├── coverage.py          # Constraint coverage gap analysis
│   ├── custom_rules.py      # YAML-based custom validation rules
│   ├── rules_registry.py    # Central rule code documentation (60+)
│   ├── reporter.py          # HTML signoff report generator
│   ├── tcl_resolver.py      # TCL $variable resolution
│   └── wildcard_analyzer.py # Wildcard pattern risk analysis
│
├── interfaces ─────────────────────────────────
│   ├── cli.py               # Command-line interface (12 commands)
│   └── legacy/streamlit/    # Preserved legacy Streamlit UI (retired)
│       ├── app.py           # Legacy Streamlit shell
│       └── ui/              # Legacy tab modules (modular UI)
│
├── packaging & deployment ─────────────────────
│   ├── pyproject.toml       # PyPI package configuration
│   ├── Dockerfile           # Container image (Python 3.11-slim)
│   ├── .dockerignore        # Docker build exclusions
│   └── __init__.py          # Package init
│
├── sample files ───────────────────────────────
│   ├── samples/
│   │   ├── example.sdc                 # Full example SDC file
│   │   ├── constraint_diff_v1.sdc      # Diff demo: version 1
│   │   ├── constraint_diff_v2.sdc      # Diff demo: version 2
│   │   └── clock_relations.sdc         # Clock relations demo
│   └── custom_rules_example.yaml       # 10 example custom rules
│
├── git hooks & CI ─────────────────────────────
│   ├── .pre-commit-config.yaml         # Pre-commit framework config
│   ├── .pre-commit-hooks/sdc-check.sh  # Standalone git hook
│   └── rta.cmd                        # Windows CLI wrapper
│
├── documentation ──────────────────────────────
│   ├── README.md                       # This file
│   └── docs/features/                  # Detailed feature docs
│       ├── README-01-checker.md         # SDC Checker / Validator
│       ├── README-02-generator.md       # SDC Generator
│       ├── README-03-diff.md            # Constraint Change Analyzer
│       ├── README-04-clock-relations.md # Clock Relation Analyzer
│       ├── README-05-mmc.md             # Multi-Corner Manager
│       ├── README-06-coverage.md        # Constraint Coverage Gap
│       ├── README-07-custom-rules.md    # Custom Rules Engine
│       ├── README-08-rules-registry.md  # Rules Registry
│       ├── README-09-reports.md         # HTML Signoff Reports
│       ├── README-10-web-ui.md          # Streamlit Web UI
│       └── README-11-cli-user-guide.md  # Engineer-facing CLI guide (every feature)
│
├── MIT License                          # Open-source (MIT)
└── .gitignore                           # Git exclusions
```

---

## 🖥️ CLI Reference

| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `check` | Validate SDC | `--json`, `--junit`, `--custom-rules`, `--verbose`, `--format` |
| `generate` | Generate SDC | `--clock`, `--design`, `--derate`, `--operating-condition` |
| `diff` | Semantic diff | `--linked-v1`, `--linked-v2`, `--json`, `--verbose` |
| `corners` | Manage corners | `list`, `show <name>` |
| `analyze` | Deep analysis | `clock-relations`, `--json` |
| `rules` | Rule lookup | `list`, `show <code>`, `--module`, `--severity`, `--search` |
| `coverage` | Gap analysis | `--json`, `--missing-only` |
| `lint` | Format/reorganize SDC | `--check`, `--fix`, `--output` |
| `convert` | SDC to JSON/YAML | `--format`, `--output` |
| `batch` | Directory-wide processing | `check`, `lint`, `report`, `--fix` |
| `report` | HTML reports | `check`, `diff`, `clock-relations`, `coverage` |
| `web` | Launch browser UI | (opens `http://localhost:8501`) |

---

## 🏗️ Design Principles

1. **Zero external dependencies** for core validation (stdlib only)
2. **Single Python files** — no complex package hierarchies
3. **Fail-fast on errors** — CLI exits with code 1 if any errors found
4. **Graceful optional features** — YAML (PyYAML optional), Web (Streamlit optional)
5. **CI-friendly** — JUnit XML, JSON output, exit codes, pre-commit hooks
6. **Self-contained reports** — HTML with inline CSS, no CDN, no JS

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

Contributions welcome! The project is organized for easy extension:

- **Add a new checker rule:** Edit `checker.py` (add condition) + `rules_registry.py` (add documentation)
- **Add a new custom condition:** Edit `custom_rules.py` (add `@_cond("name")` handler)
- **Add a new coverage item:** Edit `coverage.py` (add to appropriate category)
- **Add a new report section:** Edit `reporter.py` (add generator function)
- **Add a new tab (legacy UI):** Create `legacy/streamlit/ui/tab_<name>.py` and add to `legacy/streamlit/app.py` tab list
- **Add a new Streamlit tab:** Edit `app.py` (add to `st.tabs()` list)

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