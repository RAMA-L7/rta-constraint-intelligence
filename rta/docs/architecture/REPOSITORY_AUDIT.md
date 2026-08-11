# Ṛta — Repository Audit

> **Document kind:** architectural reference (living) · **Status:** baseline for the
> Ṛta Version 1 repository restructure · **Audit date:** 2026-08-07
> **Scope:** every file and folder in the repository, classified. Nothing may be
> deleted; everything must remain recoverable. This audit is the input to
> `REPOSITORY_BLUEPRINT.md` and `MIGRATION_PLAN.md`.

---

## 1. Audit summary

| Metric | Value |
|---|---|
| Total files (excl. `.git`, `__pycache__`) | ~610 |
| Tracked in git (`git ls-files`) | 93 |
| Untracked (Ṛta-era work, never committed) | most of `webui/`, `site/`, `benchmarks/`, `docs/company`, `docs/product`, `docs/rta`, many engine modules |
| Top-level directories | 21 (excl. `.git`) |
| Root-level Python modules | 29 (incl. `__init__.py`) |
| Distinct product surfaces | 4 (engine + CLI · premium workspace · legacy Streamlit · marketing website) |

**Grouping rule:** the audit enumerates every file row-by-row where that is
meaningful (source, surfaces, docs, samples, packaging). Bulk artifact/evidence
folders (`benchmarks/` ≈ 366 files, `ui/__pycache__/`, `build/`, `dist/`, `svg/`,
`graphify-out/`) are classified **by class** with a complete inventory of their
constituent groups — every file still belongs to exactly one classification.

**Classification legend**

| Column | Meaning |
|---|---|
| Used? | Referenced by code, docs, tests, packaging, or CI today |
| Duplicate? | Functionality exists elsewhere (superseded/mirrored) |
| Legacy? | Superseded by a newer implementation |
| Required? | Needed for the product, release, or evidence chain |
| Should move? | Proposed target in the Ṛta blueprint |
| Risk if removed | What breaks today if deleted (deletion is NOT proposed — information only) |

**Duplicate / legacy hotspots**

| # | Hotspot | Nature |
|---|---|---|
| D1 | `app.py` + `ui/` (Streamlit) vs `api_server.py` + `webui/` (SPA) | **Legacy UI superseded by premium workspace.** Kept (do not delete) for reference and token source of truth (`ui/theme.py` is consumed by `api_server.py`). |
| D2 | `site/` (marketing) vs `webui/` (product) | **Not duplicates — two distinct surfaces** (business website vs engineering application). Both current. |
| D3 | `svg/` (40 × `gemini-svg (N).svg`) | **Unreferenced generated assets** — no HTML/JS/CSS references them. Legacy experiment dump. |
| D4 | `build/`, `dist/`, `sdc_tools.egg-info/` | Build artifacts, gitignored, regenerable from `pyproject.toml`. |
| D5 | `graphify-out/` | Gitignored tool output (knowledge-graph experiment). |
| D6 | `__pycache__/` (root + packages) | Gitignored bytecode. |
| D7 | `.streamlit/config.toml` | Stale: still says "SDC Validator" + old dark palette for the retired Streamlit UI. |
| D8 | `docs/company/REPOSITORY_MAP.md` vs new `docs/architecture/` | The new `docs/architecture/` series supersedes/extends the map; map stays as the company-level index. Note: `REPOSITORY_MAP.md` still cites "780+ tests" — the verified count is 800 (see `RELEASE_EVIDENCE.json`); pre-existing staleness recorded here for the restructure. |

---

## 2. Root — deterministic engine (frozen)

Every module below participates in the analysis pipeline. **Frozen per Product
Charter §2 / AI Contributor Guide §5 — do not modify without approval.**

| File | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `sdc_preprocess.py` | SDC text normalization | ✅ | | | ✅ | `rta/engine/preprocess/` | Analysis correctness |
| `tcl_resolver.py` | Bounded Tcl variable resolution | ✅ | | | ✅ | `rta/engine/preprocess/` | Variable resolution |
| `checker.py` | Deterministic rule engine (111 rules) | ✅ | | | ✅ | `rta/engine/rules/` | Entire product |
| `rules_registry.py` | Rule catalog (single source of truth) | ✅ | | | ✅ | `rta/engine/rules/` | Rule docs, reports |
| `support_boundary.py` | Trust scope disclosure | ✅ | | | ✅ | `rta/engine/trust/` | Trust contract |
| `clock_relations.py` | Clock inventory, ancestry, relations | ✅ | | | ✅ | `rta/engine/analysis/` | Clock Intelligence |
| `wildcard_analyzer.py` | Wildcard risk scoring | ✅ | | | ✅ | `rta/engine/analysis/` | Diff/risk text |
| `design_context.py` | Verilog netlist parsing + object resolution | ✅ | | | ✅ | `rta/engine/context/` | Design-aware mode |
| `design_coverage.py` | Per-port/per-bus coverage | ✅ | | | ✅ | `rta/engine/analysis/` | Coverage evidence |
| `coverage.py` | 39-item category coverage | ✅ | | | ✅ | `rta/engine/analysis/` | Coverage page |
| `constraint_interactions.py` | Duplicates/overrides/contradictions/overlaps | ✅ | | | ✅ | `rta/engine/analysis/` | Conflicts page |
| `constraint_readiness.py` | Seven-dimension readiness | ✅ | | | ✅ | `rta/engine/analysis/` | Readiness page |
| `readiness_diff.py` | Semantic baseline comparison | ✅ | | | ✅ | `rta/engine/diff/` | Changes/CI |
| `finding_identity.py` | Structured finding comparison | ✅ | | | ✅ | `rta/engine/diff/` | Diff identity |
| `policy_engine.py` | Declarative CI gate policies | ✅ | | | ✅ | `rta/engine/policy/` | CI gate |
| `constraint_diff.py` | Semantic SDC diff (CHG rules) | ✅ | | | ✅ | `rta/engine/diff/` | CLI diff |
| `custom_rules.py` | YAML custom rules engine | ✅ | | | ✅ | `rta/engine/policy/` | Custom rules |
| `evidence.py` | Evidence manifest (counts/version) | ✅ | | | ✅ | `rta/evidence/manifest/` | Release evidence |

## 3. Root — surfaces & interfaces

| File | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `cli.py` | CLI entry (`rta` / `sdc-tools`) | ✅ | | | ✅ | `rta/cli/` | Every CLI workflow |
| `api_server.py` | Stdlib HTTP API + static server for `webui/` | ✅ | | | ✅ | `rta/api/` | `rta web` |
| `app.py` | **Legacy Streamlit shell** | 🔶 (not in launch path) | D1 | ✅ | 🔶 kept | `legacy/streamlit/app.py` | Nothing (superseded by webui) |
| `__init__.py` | Root package marker | ✅ | | | ✅ | `rta/__init__.py` | Imports |
| `rta.cmd` | Windows shim (primary CLI) | ✅ | | | ✅ | keep at repo root | `rta` on Windows |
| `sdc-tools.cmd` | Windows shim (alias) | ✅ | | | ✅ | keep at repo root | alias |

## 4. Root — tools (generators/formatters/reporters)

| File | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `generator.py` | SDC scaffold generation | ✅ | | | ✅ | `rta/tools/generate/` | Generator tool |
| `linter.py` | SDC formatting | ✅ | | | ✅ | `rta/tools/lint/` | Linter tool |
| `converter.py` | SDC → JSON/YAML | ✅ | | | ✅ | `rta/tools/convert/` | Converter tool |
| `corner_manager.py` | PVT corner presets | ✅ | | | ✅ | `rta/tools/corners/` | Corner Manager |
| `mmc.py` | Multi-corner SDC generation | ✅ | | | ✅ | `rta/tools/corners/` | MMC tool |
| `batch_runner.py` | Directory-scale processing | ✅ | | | ✅ | `rta/tools/batch/` | `rta batch` |
| `reporter.py` | HTML report generation | ✅ | | | ✅ | `rta/tools/report/` | Reports |

## 5. Root — packaging, config, CI

| File | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `pyproject.toml` | Package metadata + entry points | ✅ | | | ✅ | `rta/../pyproject.toml` (repo root, keep) | Packaging |
| `requirements.txt` | Runtime deps (pyyaml + streamlit extra) | ✅ | | | ✅ | keep | installs |
| `Dockerfile` | Container build | ✅ | | | ✅ | keep | docker |
| `.dockerignore` | Docker context filter | ✅ | | | ✅ | keep | docker |
| `.gitignore` | Repo ignore rules | ✅ | | | ✅ | keep | hygiene |
| `.pre-commit-config.yaml` | Pre-commit hooks | ✅ | | | ✅ | keep | hooks |
| `.pre-commit-hooks/sdc-check.sh` | SDC check hook | ✅ | | | ✅ | `rta/infrastructure/scripts/` | hook |
| `.github/workflows/ci.yml` | CI pipeline | ✅ | | | ✅ | keep | CI |
| `.github/workflows/sdc-readiness.yml.example` | Readiness CI example | 🔶 | | | ✅ | keep | docs/example |
| `.streamlit/config.toml` | **Stale Streamlit theme** ("SDC Validator", old dark palette) | 🔶 | D7 | ✅ | 🔶 kept | `legacy/streamlit/config/` | Nothing (retired UI) |

## 6. Root — docs & metadata

| File | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `README.md` | External product description | ✅ | | | ✅ | keep (root) | first contact |
| `CHANGELOG.md` | Version history | ✅ | | | ✅ | keep | release |
| `CONTRIBUTING.md` | Contributor guide | ✅ | | | ✅ | keep | community |
| `CLAUDE.md` | AI contributor entry | ✅ | | | ✅ | keep | AI workflow |
| `LICENSE` | MIT license | ✅ | | | ✅ | keep | legal |
| `reference-features-for-startup.md` | **Feature inventory** — superseded by canonical `docs/product/PRODUCT_CAPABILITY_CATALOG.md` (correction C5) | ✅ | | | ✅ | canonical → catalog; working copy → `legacy/working-copies/` | sprint audits |
| `RELEASE_EVIDENCE.json` | Release evidence artifact (800 tests, 111 rules, 42 suites, v1.3.0) | ✅ | | | ✅ | `rta/evidence/manifest/` | evidence chain |
| `custom_rules_example.yaml` | Example ruleset | ✅ | | | ✅ | `rta/examples/` | custom rules demo |

## 7. Directories

### 7.1 `webui/` — premium workspace SPA (current product UI)

| Path | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `webui/index.html` | SPA shell | ✅ | | | ✅ | `rta/workspace/webui/` | `rta web` |
| `webui/__init__.py` | Package marker | ✅ | | | ✅ | same | imports |
| `webui/assets/css/app.css` | Workspace design system (Arcade-light) | ✅ | | | ✅ | same | entire look |
| `webui/assets/js/app.js` | Bootstrap + routing + session state | ✅ | | | ✅ | same | navigation |
| `webui/assets/js/pages.js` | Page definitions (results-led nav) | ✅ | | | ✅ | same | all pages |
| `webui/assets/js/components.js` | Reusable UI components | ✅ | | | ✅ | same | components |
| `webui/assets/js/theme.js` | Design tokens fallback + status metadata | ✅ | | | ✅ | `rta/branding/tokens/` (pairs with `ui/theme.py`) | status badges |
| `webui/assets/js/viz.js` | Background topology canvas | ✅ | | | ✅ | same | background |

### 7.2 `ui/` — legacy Streamlit workspace

All `.py` files: `workspace.py, theme.py, components.py, validator.py, overview.py,
clocks.py, context.py, coverage.py, interactions.py, readiness.py, diff.py, ci.py,
reports.py, tab_generator.py, tab_linter.py, tab_converter.py, tab_corners.py,
tab_mmc.py, tab_rules.py, tab_test_drive.py, feedback.py, state.py` +
`__init__.py` + `__pycache__/`.

**Classification:** Legacy (superseded by `webui/`), 🔶 used today only for
`ui/theme.py` → `api_server.py` design tokens. **Should move:** `legacy/streamlit/`
(token authority → `rta/branding/tokens/`).
**Risk if removed:** design-token source of truth + historical reference. **Do not
remove** — Sprint 3D migrated the palette in `ui/theme.py`; the file remains the
token authority.

### 7.3 `site/` — business website (current)

| Path | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `site/index.html` | Home | ✅ | | | ✅ | `rta/website/` | marketing |
| `site/platform.html` | Architecture pipeline | ✅ | | | ✅ | same | marketing |
| `site/capabilities.html` | Capabilities hub | ✅ | | | ✅ | same | marketing |
| `site/capabilities/*.html` (8) | Per-capability pages (ci, clocks, context, coverage, interactions, readiness, regression, validation) | ✅ | | | ✅ | same | marketing |
| `site/benchmarks.html` | Benchmark evidence | ✅ | | | ✅ | same | evidence |
| `site/trust.html` | Trust center | ✅ | | | ✅ | same | trust |
| `site/docs.html` | Documentation entry | ✅ | | | ✅ | same | docs |
| `site/release.html` | Release page | ✅ | | | ✅ | same | release |
| `site/assets/css/site.css` | Website tokens | ✅ | | | ✅ | same | look |
| `site/assets/js/site.js` | Website interactions/canvas | ✅ | | | ✅ | same | motion |

### 7.4 `tests/` — pytest suite (current, 27 files + conftest + runner)

| File | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `conftest.py`, `__init__.py` | Fixtures | ✅ | | | ✅ | `rta/tests/` | fixtures |
| `test_checker.py` … `test_wildcard_analyzer.py` (24 files) | Engine tests | ✅ | | | ✅ | `rta/tests/` | evidence |
| `test_branding.py`, `test_evidence.py`, `test_ui_design.py` | Integrity contracts | ✅ | | | ✅ | `rta/tests/` | integrity |
| `run_comprehensive_checks.py` | Subprocess end-to-end smoke | ✅ | | | ✅ | `rta/tests/` | smoke |

### 7.5 `benchmarks/` — evidence suites (current, 366 files incl. data)

| Group | Examples | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| Runners | `run_golden.py`, `run_golden_semantic.py`, `run_reference_designs.py`, `run_netlist_aware.py`, `run_design_coverage.py`, `run_constraint_interactions.py`, `run_readiness.py`, `run_readiness_diff.py`, `run_production_hardening.py`, `run_benchmark.py` | ✅ | | | ✅ | `rta/evidence/runners/` | evidence chain |
| Suites | `test_*_adversarial/metamorphic/perf/security/realistic/confidence/ci_gate`.py (28+) | ✅ | | | ✅ | same | evidence |
| Release | `test_release_smoke.py`, `release_cli_audit.py`, `release_cleanroom.py`, `release_packaging_probe.py`, `build_evidence.py`, `generate_support_matrix.py`, `verify_findings.py`, `reference_coverage_matrix.py` | ✅ | | | ✅ | same | release |
| Data dirs | `golden/`, `golden_semantic/`, `reference_designs/`, `netlist_aware/`, `design_coverage/`, `constraint_interactions/`, `readiness/`, `readiness_diff/`, `production_hardening/`, `regression/`, `edge_cases/`, `malformed/`, `invalid/`, `valid/`, `large_design/`, `clock_relations/`, `io_constraints/`, `timing_exceptions/` | ✅ | | | ✅ | same | expected data |
| Results | `results/results.json` | ✅ | | | ✅ | same | evidence |
| Reports | `PHASE*.md`, `SPRINT*.md`, `QA_REPORT.md`, `GOLDEN_BENCHMARK_VERIFICATION_REPORT.md`, `RTA_FOUNDATION_REPORT.md`, `RELEASE_MANIFEST.md`, `support_matrix.md`, `README.md` | ✅ | | | ✅ | `rta/evidence/reports/` | history |

### 7.6 `docs/` — documentation

| Subdir | Purpose | Files | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|---|
| `docs/company/` | Operating system, charter, guides, templates, repo map | 11 | ✅ | | | ✅ | `rta/docs/company/` | process |
| `docs/rta/` | Foundation (brand, taxonomy, capability map, trust, roadmap, open-core, architecture) | 10 | ✅ | | | ✅ | `rta/docs/foundation/` | strategy |
| `docs/product/` | PDS, HFPS, experience architecture, design system, phase audits | 10 | ✅ | | | ✅ | `rta/docs/product/` | product |
| `docs/features/` | Per-module reference READMEs | 10 | ✅ | | | ✅ | `rta/docs/features/` | reference |
| `docs/architecture/` | **This series (new, product-first revision)** | 9 | — | | | ✅ | `rta/docs/architecture/` | restructure |

### 7.7 Samples, data, policy

| Path | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|
| `samples/` (19 files) | Example SDC corpus | ✅ | | | ✅ | `rta/examples/samples/` | demos/tests |
| `data/feedback.json` | Feedback store | ✅ | | | ✅ | `rta/workspace/data/` | feedback |
| `policy_examples/` (3 yaml) | Example policies | ✅ | | | ✅ | `rta/examples/policies/` | policy docs |

### 7.8 Artifacts & experiments (gitignored or unreferenced)

| Path | Count | Purpose | Used | Dup | Legacy | Req | Should move | Risk if removed |
|---|---|---|---|---|---|---|---|---|
| `svg/` | 40 | **Unreferenced generated icons** (`gemini-svg (N).svg`) | ❌ | D3 | ✅ | ❌ | `legacy/assets/` | none |
| `build/` | 59 | Build output (incl. `build/lib/*.py` copies) | 🔶 | D4 | ✅ | ❌ | regenerate | none (gitignored) |
| `dist/` | 1 | Built wheel | 🔶 | D4 | ✅ | ❌ | regenerate | none (gitignored) |
| `sdc_tools.egg-info/` | 6 | Package metadata | 🔶 | D4 | ✅ | ❌ | regenerate | none (gitignored) |
| `graphify-out/` | 54 | Knowledge-graph experiment output | ❌ | D5 | ✅ | ❌ | `legacy/experiments/` | none (gitignored) |
| `__pycache__/` (root + dirs) | 29+ | Bytecode | ❌ | D6 | ✅ | ❌ | — | none |
| `.benchmarks/` | cache | Benchmark cache | 🔶 | | ✅ | ❌ | keep gitignored | none |
| `.pytest_cache/` | — | Pytest cache | ❌ | | ✅ | ❌ | — | none |

## 8. Business website vs product (separation check)

| Concern | Business website (`site/`) | Product workspace (`webui/`) |
|---|---|---|
| Purpose | Marketing, company, evidence, trust, docs, release | Engineering application: analysis, sessions, reports, tools |
| Audience | Prospective users/investors | Engineers using the product |
| Tech | Static HTML/CSS/JS | SPA + `api_server.py` |
| Ownership | Product lead | Product lead (workspace) |
| **Current state** | Separate and clean ✅ | Separate and clean ✅ |
| **Blueprint change** | → `rta/website/` | → `rta/workspace/` |

The two surfaces are already correctly separated. The restructure formalizes this
into the folder names.

## 9. Tool-first check (reference-features §21 → tools)

Every capability in the reference feature inventory is a **first-class tool**, not
a hidden "More tools" item. See `FEATURE_MAPPING.md` for the full table.

---

## 10. Notes & open items

1. `ui/theme.py` is the design-token **source of truth** consumed by the API —
   the legacy folder cannot be fully archived until that dependency is moved into
   `rta/branding/tokens/`.
2. Only 93 files are git-tracked; the majority of Ṛta-era work is uncommitted.
   **Recommend a full initial commit (or branch) before restructuring.**
3. `.streamlit/config.toml` carries stale "SDC Validator" branding — flag for the
   brand sweep during migration.
4. `build/lib/` duplicates root modules (D4) — do not edit; it is build output.
5. Nothing is proposed for deletion. Every legacy/artifact item maps to
   `legacy/` or regeneration.

*This audit classifies 100% of the repository. No file is left unclassified.*
