# Ṛta — Feature Mapping

> **Document kind:** product architecture reference · **Status:** current (revised)
> **Source of truth:** `docs/product/PRODUCT_CAPABILITY_CATALOG.md` — the permanent
> home of the feature inventory (was `reference-features-for-startup.md`; the
> working copy is archived to `legacy/working-copies/` once the catalog is canonical,
> per `REPOSITORY_BLUEPRINT.md` §7 and founder Correction 5).
> **Date:** 2026-08-07
> No feature may disappear. This table is the contract between the capability
> catalog and the Ṛta target architecture.
> **Target-page column** follows `WORKSPACE_INFORMATION_ARCHITECTURE.md` (session
> tools unlock after analysis; standalone tools are always visible; nothing is
> ever hidden under "More tools").

---

## 1. FEATURE → BACKEND → UI → STATUS → TARGET PAGE

| # | Feature | Backend module(s) | Current UI (webui) | Status | Target page (rta/workspace) |
|---|---|---|---|---|---|
| 1 | Validate / Check | `checker.py`, `rules_registry.py`, `sdc_preprocess.py`, `tcl_resolver.py` | `#/validator` (Findings) | ✅ working | Workspace → ANALYZE → Validation (session tool) |
| 2 | Generate SDC | `generator.py` | `#/generator` (Generator) | ✅ working | Workspace → TOOLS → Generator (standalone, always visible) |
| 3 | Lint / Format | `linter.py` | `#/linter` (Linter) | ✅ working | Workspace → TOOLS → Linter (standalone) |
| 4 | Convert SDC→JSON/YAML | `converter.py` | `#/converter` (Converter) | ✅ working | Workspace → TOOLS → Converter (standalone) |
| 5 | Batch check/report/lint | `batch_runner.py` | CLI only | ✅ CLI | CLI (unchanged) |
| 6 | Semantic diff | `constraint_diff.py`, `readiness_diff.py`, `finding_identity.py`, `tcl_resolver.py`, `wildcard_analyzer.py` | `#/diff` (Changes) | ✅ working | Workspace → DECIDE → Change Intelligence (session tool; needs baseline) |
| 7 | Clock relations | `clock_relations.py` | `#/clocks` (Clocks) | ✅ working | Workspace → ANALYZE → Clock Intelligence (session tool) |
| 8 | Multi-corner manager | `corner_manager.py`, `mmc.py` | `#/corners`, `#/mmc` | ✅ working | Workspace → TOOLS → Corner Manager / MMC (standalone) |
| 9 | Constraint coverage | `coverage.py`, `design_coverage.py` | `#/coverage` (Coverage) | ✅ working | Workspace → ANALYZE → Coverage Intelligence (session tool) |
| 10 | Design context (netlist) | `design_context.py` | `#/context` (Design) | ✅ working | Workspace → ANALYZE → Design Intelligence (session tool) |
| 11 | Constraint interactions | `constraint_interactions.py` | `#/interactions` (Conflicts) | ✅ working | Workspace → ANALYZE → Constraint Conflicts (session tool) |
| 12 | Readiness | `constraint_readiness.py` | `#/readiness` (Health) | ✅ working | Workspace → DECIDE → Readiness (session tool) |
| 13 | Readiness diff / CI gate | `readiness_diff.py`, `policy_engine.py` | `#/ci`, `#/diff` | ✅ working | Workspace → DECIDE → CI (needs policy) + Change Intelligence (needs baseline) |
| 14 | Custom rules (YAML) | `custom_rules.py` | input on `#/new_analysis` + `#/validator` (Sprint 3D) | ✅ working | Workspace → ANALYZE → Validation → Custom Rules input (session context) |
| 15 | Rule registry | `rules_registry.py` | `#/rules` (Rules) | ✅ working | Workspace → KNOWLEDGE → Rules (always visible) |
| 16 | Trust model / scope disclosure | `support_boundary.py` | `#/trust` (Trust) | ✅ working | Workspace → KNOWLEDGE → Trust (always visible) |
| 17 | HTML reports | `reporter.py` | `#/reports` (Report) | ✅ working | Workspace → OUTPUT → Reports (session tool) |
| 18 | Export (JSON/baseline) | `evidence.py`, API | `#/export` (Export) | ✅ working | Workspace → OUTPUT → Export (session tool) |
| 19 | Test drive (run-all) | all modules | `#/test_drive` | ✅ working | Workspace → TOOLS → Test Drive (standalone) |
| 20 | Feedback | `api_server.py` `/api/feedback` → `data/feedback.json` | `#/feedback` | ✅ working | Workspace → TOOLS → Feedback (always visible) |
| 21 | Documentation | `docs/features/*`, site docs | `#/documentation` | ✅ working | Workspace → KNOWLEDGE → Documentation (always visible) |
| 22 | CLI (12 commands) | `cli.py` | terminal | ✅ working | CLI (unchanged) |
| 23 | Web UI server | `api_server.py` | root `/` | ✅ working | rta/api/ (HTTP surface) |
| 24 | Business website | `site/` | static site | ✅ working | rta/website/ (business site — separate from workspace) |
| 25 | Legacy Streamlit UI | `app.py` + `ui/` | retired | 🔶 legacy (kept) | legacy/streamlit/ (preserved, never imported) |

**Status legend:** ✅ working · 🔶 legacy/kept · ⏳ planned (none currently).

## 2. Tool-first naming (per blueprint §6 + workspace IA §4)

Every first-class tool owns exactly one workspace route and one engine entry.
Session tools unlock after analysis; standalone tools are always visible:

| Tool | Engine entry | Workspace route | Class |
|---|---|---|---|
| Ṛta Validate | `check_sdc()` | ANALYZE → Validation | session |
| Ṛta Generate | `generate_sdc()` | TOOLS → Generator | standalone |
| Ṛta Linter | `lint_sdc()` | TOOLS → Linter | standalone |
| Ṛta Converter | `parse_sdc()` / `sdc_to_json/yaml()` | TOOLS → Converter | standalone |
| Ṛta Corner Manager | `Corner`, `CORNER_PRESETS` | TOOLS → Corner Manager | standalone |
| Ṛta MMC | `generate_corner_sdcs()`, `check_sdc_multi()` | TOOLS → MMC | standalone |
| Ṛta Clock Intelligence | `analyze_clock_relations()` | ANALYZE → Clocks | session |
| Ṛta Coverage | `parse_sdc_coverage()`, `design_coverage` | ANALYZE → Coverage | session |
| Ṛta Design Context | `design_context` | ANALYZE → Design | session |
| Ṛta Conflicts | `constraint_interactions` | ANALYZE → Interactions | session |
| Ṛta Readiness | `constraint_readiness` | DECIDE → Health | session |
| Ṛta Diff | `readiness_diff`, `constraint_diff` | DECIDE → Changes | session (needs baseline) |
| Ṛta CI | `policy_engine` | DECIDE → CI | session (needs policy) |
| Ṛta Rules | `rules_registry` | KNOWLEDGE → Rules | always visible |
| Ṛta Trust | `support_boundary` | KNOWLEDGE → Trust | always visible |
| Ṛta Test Drive | all | TOOLS → Test Drive | standalone |
| Ṛta Feedback | feedback store | TOOLS → Feedback | always visible |

## 3. Coverage check

- **24/24** reference features mapped (25 rows incl. legacy UI which the catalog
  documents as superseded).
- **0 features missing.** Sprint 3D closed the last gap (custom-rules input).
- **0 features lost in the restructure** — the blueprint moves surfaces, never
  drops capabilities.
- New features may be added in future sprints; existing ones are never removed.
- **Permanent inventory:** the feature list itself now lives at
  `docs/product/PRODUCT_CAPABILITY_CATALOG.md`; this mapping table is the
  architecture contract on top of it.

---

*Mapping complete (revised for product-first blueprint). Cross-referenced with
`docs/product/SPRINT3D_FEATURE_AUDIT.md` (verification matrices),
`WORKSPACE_INFORMATION_ARCHITECTURE.md` (availability classes) and
`REPOSITORY_BLUEPRINT.md` (target locations).*
