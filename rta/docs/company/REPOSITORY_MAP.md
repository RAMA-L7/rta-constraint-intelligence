# Repository Map

> **Document kind:** architectural reference — where every major component lives, who owns it, and where future work belongs.
> **Purpose:** prevent architectural drift. If you are unsure where code or documentation belongs, this document tells you.
> **Last updated:** 2026-08-07

---

## Repository Structure

```
sdc-tools/
│
├── CORE ENGINE (deterministic analysis pipeline)
│   ├── sdc_preprocess.py          # SDC text normalization
│   ├── tcl_resolver.py            # Bounded Tcl variable resolution
│   ├── checker.py                 # Deterministic rule engine (111 rules)
│   ├── rules_registry.py          # Rule catalog (single source of truth)
│   ├── support_boundary.py        # Trust scope disclosure
│   ├── clock_relations.py         # Clock inventory, ancestry, relations
│   ├── wildcard_analyzer.py       # Wildcard pattern risk scoring
│   ├── design_context.py          # Verilog netlist parsing + object resolution
│   ├── design_coverage.py         # Per-port, per-bus coverage
│   ├── coverage.py                # Category-level coverage (39 items)
│   ├── constraint_interactions.py # Duplicates, overrides, contradictions, overlaps
│   ├── constraint_readiness.py    # Seven-dimension readiness aggregation
│   ├── readiness_diff.py          # Semantic baseline comparison
│   ├── finding_identity.py        # Structured finding comparison
│   ├── policy_engine.py           # Declarative CI gate policies
│   ├── constraint_diff.py         # Semantic SDC diff (CHG rules)
│   └── custom_rules.py            # YAML custom rules engine
│
├── CLI
│   └── cli.py                     # Entry point (rta / sdc-tools)
│
├── WORKSPACE (premium)
│   ├── api_server.py              # Stdlib HTTP API server
│   └── webui/                     # Vanilla JS SPA
│       ├── index.html
│       └── assets/
│           ├── css/app.css
│           └── js/
│               ├── app.js         # Bootstrap + routing
│               ├── pages.js       # Page definitions + state
│               ├── components.js  # Reusable UI components
│               ├── theme.js       # Design tokens + status metadata
│               └── viz.js         # Background canvas
│
├── LEGACY WORKSPACE (Streamlit)
│   ├── app.py                     # Streamlit app (retired from launch path)
│   └── ui/                        # Streamlit page modules
│       ├── workspace.py           # Navigation
│       ├── theme.py               # Design tokens (source of truth for API)
│       ├── components.py          # HTML helpers
│       ├── validator.py           # Checker page
│       ├── overview.py            # Overview page
│       ├── clocks.py              # Clock intelligence page
│       ├── context.py             # Design context page
│       ├── coverage.py            # Coverage page
│       ├── interactions.py        # Interactions page
│       ├── readiness.py           # Readiness page
│       ├── diff.py                # Diff page
│       ├── ci.py                  # CI / policies page
│       ├── reports.py             # Reports page
│       ├── tab_generator.py       # SDC generator tool
│       ├── tab_linter.py          # Linter tool
│       ├── tab_converter.py       # Converter tool
│       ├── tab_corners.py         # Corner manager tool
│       ├── tab_mmc.py             # MMC SDC tool
│       ├── tab_rules.py           # Rules reference
│       ├── tab_test_drive.py      # Test drive (sample SDC)
│       ├── feedback.py            # Feedback dashboard
│       └── state.py               # Session state management
│
├── MARKETING WEBSITE
│   └── site/                      # Static HTML/CSS/JS
│       ├── index.html             # Home
│       ├── platform.html          # Architecture pipeline
│       ├── capabilities.html      # Capabilities hub
│       ├── capabilities/          # Per-capability pages (8 files)
│       ├── benchmarks.html        # Benchmark evidence
│       ├── trust.html             # Trust center
│       ├── docs.html              # Documentation entry
│       ├── release.html           # Release page
│       └── assets/
│           ├── css/site.css       # Website design tokens
│           └── js/site.js         # Header, footer, reveals, canvas
│
├── TOOLS
│   ├── generator.py               # SDC scaffold generation
│   ├── linter.py                  # SDC formatting
│   ├── converter.py               # SDC → JSON/YAML
│   ├── corner_manager.py          # PVT corner presets
│   ├── mmc.py                     # Multi-corner SDC generation
│   ├── batch_runner.py            # Directory-scale processing
│   └── reporter.py                # HTML report generation
│
├── TESTS
│   ├── tests/                     # pytest suite (780+ tests)
│   │   ├── test_checker.py        # Rule engine tests
│   │   ├── test_clock_relations.py
│   │   ├── test_constraint_diff.py
│   │   ├── test_constraint_interactions.py
│   │   ├── test_coverage.py
│   │   ├── test_custom_rules.py
│   │   ├── test_design_context.py
│   │   ├── test_design_coverage.py
│   │   ├── test_readiness_diff.py
│   │   ├── test_rules_registry.py
│   │   ├── test_support_boundary.py
│   │   ├── test_branding.py       # Brand integrity checks
│   │   ├── test_ui_design.py      # Theme/contract tests
│   │   └── ... (28+ test files)
│   │
│   └── benchmarks/                # Benchmark suites (28+ suites)
│       ├── golden/                # Golden parser suite
│       ├── golden_semantic/       # Golden semantic suite
│       ├── reference_designs/     # Reference design suite
│       ├── netlist_aware/         # Netlist-aware suite
│       ├── design_coverage/       # Coverage suite
│       ├── constraint_interactions/ # Interaction suite
│       ├── readiness/             # Readiness suite
│       ├── readiness_diff/        # Diff suite
│       ├── production_hardening/  # Production hardening suite
│       ├── run_golden.py          # Golden runner
│       ├── run_golden_semantic.py
│       ├── run_netlist_aware.py
│       ├── run_design_coverage.py
│       ├── run_constraint_interactions.py
│       ├── run_readiness.py
│       ├── run_readiness_diff.py
│       ├── run_production_hardening.py
│       ├── run_reference_designs.py
│       ├── run_benchmark.py       # Module-level benchmark runner
│       ├── test_release_smoke.py  # Release smoke
│       ├── release_cli_audit.py   # CLI contract audit
│       ├── release_cleanroom.py   # Clean-room wheel journey
│       └── test_*_adversarial.py, test_*_metamorphic.py, test_*_perf.py, ...
│
├── SAMPLES
│   ├── samples/                   # Example SDC files
│   ├── policy_examples/           # Example policy files
│   └── data/                      # Feedback data
│
├── DOCUMENTATION
│   ├── README.md                  # External-facing product description
│   ├── CHANGELOG.md               # Version history
│   ├── CONTRIBUTING.md            # Contributor guide
│   ├── CLAUDE.md                  # AI model project instructions
│   ├── docs/
│   │   ├── rta/                   # Ṛta foundation documents
│   │   ├── product/               # Product design specs
│   │   ├── features/              # Per-module reference docs
│   │   └── company/               # Operating system + onboarding
│   └── site/                      # Website (also in MARKETING WEBSITE)
│
├── PACKAGING
│   ├── pyproject.toml             # Package metadata + entry points
│   ├── requirements.txt           # Runtime dependencies
│   ├── Dockerfile                 # Container build
│   ├── sdc-tools.cmd              # Windows shim (alias)
│   ├── rta.cmd                    # Windows shim (primary)
│   └── .pre-commit-config.yaml    # Pre-commit hooks
│
└── CI/CD
    ├── .github/workflows/ci.yml   # GitHub Actions CI
    └── .pre-commit-hooks/         # Pre-commit hook scripts
```

---

## Ownership Model

| Component | Owner | Reviewer |
|---|---|---|
| Core engine (§1) | Engineering lead | Architecture review (Operating System §9) |
| CLI (`cli.py`) | Engineering lead | Engineering checklist |
| Workspace (`api_server.py` + `webui/`) | Product lead | Product review checklist |
| Website (`site/`) | Product lead | Product review checklist |
| Legacy Streamlit (`app.py` + `ui/`) | Product lead | Product review checklist |
| Tests (`tests/`) | Engineering lead | Engineering checklist |
| Benchmarks (`benchmarks/`) | Engineering lead | Benchmark review (Operating System §12) |
| Documentation (`docs/`) | Product lead | Product review checklist |
| Packaging (`pyproject.toml`) | Engineering lead | Architecture review |
| CI/CD (`.github/`) | Engineering lead | Engineering checklist |
| Company docs (`docs/company/`) | Founding team | Charter alignment |

---

## Module Responsibilities

### Core Engine

| Module | Responsibility | Trust boundary |
|---|---|---|
| `sdc_preprocess.py` | Normalize SDC text, handle comments/multiline/variables | VALIDATED for supported constructs |
| `tcl_resolver.py` | Resolve bounded Tcl scalar variables | PARTIALLY_VALIDATED — execution constructs excluded |
| `checker.py` | Run 111 deterministic rules | VALIDATED per command |
| `rules_registry.py` | Single source of truth for all rules | Reference data — no trust boundary |
| `support_boundary.py` | Report analysis scope (what was checked/skipped) | Self-describing — the trust mechanism |
| `clock_relations.py` | Clock inventory, ancestry, pairwise relations | PARTIALLY_VALIDATED — inferred from text |
| `wildcard_analyzer.py` | Risk-score wildcard patterns | Heuristic — secondary evidence |
| `design_context.py` | Parse Verilog, resolve SDC object references | NETLIST_REQUIRED → VALIDATED when netlist supplied |
| `design_coverage.py` | Per-port/bus/bit coverage | NETLIST_REQUIRED — runs only with design context |
| `coverage.py` | Category-level coverage (39 items) | PARTIALLY_VALIDATED — heuristic score |
| `constraint_interactions.py` | Duplicates, overrides, conflicts, overlaps | PARTIALLY_VALIDATED — overlaps need STA review |
| `constraint_readiness.py` | Seven-dimension readiness aggregation | READY ≠ signoff (mandatory disclaimer) |
| `readiness_diff.py` | Semantic baseline comparison | Identity-based — not line comparison |
| `finding_identity.py` | Structured finding comparison | STRUCTURED or LEGACY_NORMALIZED |
| `policy_engine.py` | Declarative CI gate policies | Engine failure never passes (exit 3) |
| `constraint_diff.py` | Semantic SDC diff (CHG rules) | Semantic-ish — for human review |
| `custom_rules.py` | YAML custom rules | Team-scoped — not official rules |

### Surfaces

| Component | Responsibility |
|---|---|
| `cli.py` | CLI entry point. Dispatches commands. Enforces exit-code contract. |
| `api_server.py` | Stdlib HTTP server. Serves workspace. Exposes backend as JSON. |
| `webui/` | Vanilla JS SPA. Hash router, inspector, status rail. |
| `site/` | Static marketing website. 15 pages, canvas background, evidence cards. |
| `reporter.py` | Self-contained HTML report generation. |
| `app.py` + `ui/` | Legacy Streamlit workspace. Retired from launch path. |

---

## Data Flow

```
User provides: SDC [ + Verilog netlist ]
        ↓
cli.py (parse args, dispatch)
        ↓
sdc_preprocess.py (normalize text)
        ↓
tcl_resolver.py (resolve Tcl variables)
        ↓
checker.py + rules_registry.py (111 rules → issues)
        ↓
clock_relations.py (clock inventory + relations)
        ↓
[optional] design_context.py (resolve SDC references against netlist)
        ↓
[optional] design_coverage.py (per-port/bus/bit coverage)
        ↓
constraint_interactions.py (duplicates, overrides, conflicts)
        ↓
constraint_readiness.py (seven-dimension verdict)
        ↓
support_boundary.py (scope disclosure)
        ↓
readiness_diff.py (if baseline provided: semantic comparison)
        ↓
policy_engine.py (if gate requested: evaluate policy)
        ↓
Output: CLI text / JSON / JUnit XML / HTML report / workspace JSON
```

---

## Where Future Work Belongs

### New analysis capability

If it is part of the deterministic analysis pipeline, it belongs at the repo root as a new Python module. It must:
- Be added to `py-modules` in `pyproject.toml`.
- Have a test file in `tests/`.
- Have an entry in `rules_registry.py` (if it produces findings).
- Have a trust boundary in `support_boundary.py`.
- Be reviewed by architecture review (Operating System §9).

### New CLI command

Add to `cli.py` following the existing dispatch pattern. The command must:
- Follow the exit-code contract (0/1/2/3).
- Produce machine-clean JSON on `--json`.
- Be documented in README and CHANGELOG.

### New workspace page

Add to `webui/pages.js` following the existing page pattern. The page must:
- Fetch data from `api_server.py` endpoints.
- Display trust disclosures.
- Not display unimplemented capabilities.
- Be reviewed by product review (Operating System §10).

### New website page

Add to `site/` as a static HTML file. The page must:
- Follow the site's design tokens (site.css).
- Use the canonical product name and positioning.
- Carry evidence numbers that are current.
- Be reviewed by product review.

### New benchmark suite

Add to `benchmarks/` as a `test_*.py` or `run_*.py` file. The suite must:
- Be deterministic.
- Have verifiable expected outcomes.
- Be added to the CI pipeline (or documented as manual).
- Link to the evidence it proves.

### New documentation

Add to the appropriate `docs/` subdirectory:
- `docs/rta/` — Ṛta foundation documents.
- `docs/product/` — Product design specs.
- `docs/features/` — Per-module reference docs.
- `docs/company/` — Operating system, onboarding, templates.

---

## Anti-Patterns

Do not:

1. **Put analysis logic in `cli.py`.** The CLI dispatches; the engine analyzes.
2. **Put UI logic in the engine.** The engine produces data; surfaces render it.
3. **Put mocks or fixtures in the engine.** Tests live in `tests/` and `benchmarks/`.
4. **Put trust disclosures only in some surfaces.** Every surface that presents analysis results carries its trust disclosure.
5. **Hardcode evidence numbers.** Numbers come from artifacts, not from strings in source code.
6. **Add external dependencies without an ADR.** Dependencies affect the offline-capable, clean-room, and single-wheel guarantees.
7. **Rename SDC standard vocabulary.** The standard's language is not ours to change.
8. **Put product design specs in `docs/rta/`.** `docs/rta/` is for foundational identity and architecture documents. Product design specs belong in `docs/product/`.
9. **Put company process documents in `docs/rta/`.** Operating system, onboarding, and templates belong in `docs/company/`.
10. **Leave stale files in the repository root.** Zip files, build directories, and temporary artifacts should be cleaned up.

---

*This map is a living document. Update it when new modules, surfaces, or directories are added. The map exists to prevent architectural drift — if the map is wrong, the architecture will follow.*
