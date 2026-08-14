# Ṛta — Feature Traceability

> Maps the authoritative feature requirement source to the Ṛta implementation.
>
> **Source of truth:** the original startup feature reference
> (`reference-features-for-startup.md`) was archived as provenance per
> founder correction C5; its canonical successor is
> `rta/docs/product/PRODUCT_CAPABILITY_CATALOG.md` (the exhaustive v1.3.0
> feature reference, cross-checked against the current codebase in this
> document). Every feature in that reference must be represented in the new
> architecture — **nothing is silently dropped.**
>
> Engine behavior is frozen (`docs/product/FUNCTIONAL_BASELINE.md`). Reuse
> working deterministic functionality; do not rebuild it.

---

## 1. Traceability table

Reference sections below are from `PRODUCT_CAPABILITY_CATALOG.md` (canonical
feature inventory). "Entry point" = the surface the rebuild exposes.

| # | Reference feature (§) | Ṛta capability | Entry point (rebuild) | Required input | Output | Backend implementation | Test coverage |
|---|------------------------|----------------|----------------------|----------------|--------|------------------------|---------------|
| 1 | SDC Checker / validation (§3) | SDC Validator | Validator card / Findings page | SDC (netlist optional, top, custom-rules) | findings (code/sev/msg/line), stats, scope | `checker.py` + `sdc_preprocess.py` + `tcl_resolver.py` + `clock_relations.py` + `constraint_interactions.py` + `constraint_readiness.py` | `test_checker.py` (96), `test_sdc_preprocess.py` (78), `test_tcl_resolver.py` (30), `test_p1_corrections.py` (23), `test_parity_defect_classes.py` (23) |
| 2 | SDC Generator (§4) | SDC Generator | Generator card / tool | generation parameters (design, clocks, OC, derate, scan…) | self-consistent SDC text | `generator.py` (`generate_sdc`, `SDCParams`) | `test_generator.py` (31), `test_p1_corrections.py` (gen tests) |
| 3 | SDC Linter (§5) | SDC Linter | Linter card / tool | SDC | issues + formatted text (22-section canonical order) | `linter.py` | `test_linter.py` (17) |
| 4 | SDC Converter (§6) | SDC Converter | Converter card / tool | SDC + json/yaml | structured JSON/YAML doc | `converter.py` (`parse_sdc`, `sdc_to_json/yaml`) | `test_converter.py` (14) |
| 5 | Batch Runner (§7) | Batch processing | CLI only (`batch`) — kept CLI-only per reference | directory of SDCs | per-file status + `BatchSummary` | `batch_runner.py` | `test_batch_runner.py` (7), `test_evidence.py` (21) |
| 6 | Semantic Diff (§8) | SDC Diff | Diff card / Changes page | V1 + V2 SDC (+ linked TCL) | CHG-* changes (21 rules), stats, impact text | `constraint_diff.py` + `tcl_resolver.py` + `wildcard_analyzer.py` | `test_constraint_diff.py` (13), `test_wildcard_analyzer.py` (26), `test_readiness_diff.py` (37) |
| 7 | Clock Relations (§10) | Clock Intelligence | Clocks card / page | SDC | inventory, N×N matrix, mismatches + missing constraints | `clock_relations.py` (5 inference rules, SDC-060..063) | `test_clock_relations.py` (15), `test_p1_corrections.py` (stats), `test_parity_defect_classes.py` (inference) |
| 8 | Multi-Corner Manager (§11) | Corner Manager + MMC | Corners + MMC cards / tools | presets or corner JSON; template or params | corner lists, per-corner SDCs, cross-corner findings, ZIP | `corner_manager.py` (4 presets, validation) + `mmc.py` (SDC-050/051/053) | MMC evidence suites; `test_reporter.py` (26) covers corner report; acceptance WF9 |
| 9 | Constraint Coverage (§12) | Coverage | Coverage card / page | SDC (netlist optional) | score 0–100, 39 items / 6 categories, missing list | `coverage.py` (+ `design_coverage.py` for netlist) | `test_coverage.py` (18), `test_design_coverage.py` (29), `test_design_context.py` (41) |
| 10 | Custom Rules Engine (§13) | Custom rules (in Validator) | Validator card (advanced input) | SDC + YAML ruleset | CUST-*/FND-* findings folded into check | `custom_rules.py` (9 condition handlers, `integrate_with_check`) | `test_custom_rules.py` (29) |
| 11 | Rules Registry (§14) | Rules | Rules card / tool | none (browse) / SDC (execute) | searchable rule catalog (119 rules) | `rules_registry.py` | `test_rules_registry.py` (20) |
| 12 | HTML Reports (§15) | Reports | Report card / page | check/diff/clock/coverage results | 5 self-contained HTML report types | `reporter.py` | `test_reporter.py` (26) |
| 13 | TCL Resolver (§9) | TCL variable resolution | Diff / Validator (linked files, CLI flags) | SDC + `set VAR` assignments / linked TCL | resolved symbols, correct parsing | `rta/engine/preprocess/tcl_resolver.py` | `test_tcl_resolver.py` (30) |
| 14 | Wildcard Analyzer (§9) | Wildcard risk | Diff (CHG-WC rules) | wildcard patterns in SDC | pattern parse, risk score 0–10, comparisons | `wildcard_analyzer.py` | `test_wildcard_analyzer.py` (26) |
| 15 | CI gates / policy | CI | CI card / tool | SDC + baseline + gate policy | PASS/FAIL verdict + exit code | `policy_engine.py` + readiness/readiness_diff | `test_policy_engine.py` (34), acceptance WF12 |
| 16 | Export / download | Export (session) | Report / Export page | analysis results | JSON snapshot, baseline download, HTML | `reporter.py` + session store | `test_ui_state_isolation.py`, acceptance WF13 |
| 17 | Test Drive (run-all) | Test Drive | Test Drive card / tool | sample or uploaded SDC | unified dashboard from real backend | all engine modules via `/api/analyze` | `test_test_drive_parity.py` (6), acceptance WF14 |
| 18 | Feedback dashboard | Feedback | Feedback (support) | thumbs + comment | persisted entries + dashboard | `feedback.py` → `rta/workspace/data/feedback.json` | `test_ui_state_isolation.py` evidence |
| 19 | Web UI | Workspace | the workspace itself | per feature | per feature (real backend) | `api_server.py` + `rta/workspace/webui/` | webui evidence suites (35/35 state etc.), acceptance WF13/14 |
| 20 | CLI (12 commands) | CLI (13 subcommands incl. `whats-new`) | CLI | per command | text/JSON/JUnit/CSV/MD/HTML + exit codes | `cli.py` | `test_cli.py` (56), `release_cli_audit.py` (16/16) |
| 21 | Packaging / Docker / CI workflows | Packaging | repo surfaces | source | wheel/sdist, Docker image, pre-commit hook, GitHub Actions | `pyproject.toml`, `Dockerfile`, `.pre-commit-hooks/sdc-check.sh`, `.github/workflows/ci.yml` | `release_cleanroom.py` (17/17), `release_packaging_probe.py` |

**Plus Ṛta-only capabilities (intentional enhancements, present since v1.3+):**

| Capability | Backend | Notes |
|---|---|---|
| Design Context / netlist-aware rules (SDC-055..066) | `rta/engine/context/design_context.py`, `rta/engine/analysis/design_coverage.py` | netlist optional input |
| Async reset / CDC completeness (SDC-151..153) | `async_reset_check.py` | v1.5.4 |
| DFT / scan completeness (SDC-154..155) | `dft_scan_check.py` | v1.5.5 |
| AOCV/POCV derate methodology (SDC-156..157) | `derate_methodology.py` | v1.5.6 |
| Rationale-comment linting (SDC-150) | `rationale_lint.py` | v1.5.2 |
| Readiness (tiers + dimensions) | `constraint_readiness.py` | enhanced v1.3+ |
| Constraint interactions (SDC-067..070) | `constraint_interactions.py` | enhanced |
| `rta whats-new` | `rta/engine/meta/release_notes.py` | v1.5.8 |

---

## 2. Reference §20 known limitations — status (frozen, documented)

Recorded in the canonical catalog; unchanged (backend frozen). None blocks a
feature entry point:

- `CHG-WC-002` defined but never emitted → broadening reported under `CHG-WC-001`.
- `CHG-FP-002` "same wildcard" branch unreachable.
- `wildcard_comparisons` declared, never populated.
- `Constraint.line_number` always 0 from `parse_sdc_constraints` (diff-side; the
  checker's `Issue.line` is populated per P1-1).
- `SDC-054` derate-monotonicity is a no-op in `check_sdc_multi`.
- Converter value-extraction quirks (`-max 1.2` form), `waveform` never
  populated, max/min delay appended to multicycle list.
- Linter dead code (`_parse_lines`, `_MULTI_LINE_COMMANDS`); multi-line without
  `\` dropped on collapse.
- Generator `-master_clock {port}` + CLI/library scan-port default mismatch.
- TCL resolver is string-replacement (not a tokenizer); circular refs bounded
  by 5 passes.
- Custom-rules templating supports `{count}`/`{value}` only.
- `batch lint --fix` overwrites in place (by design).

---

## 3. Coverage claims by workflow (no feature declared complete by presence alone)

Per the engineering acceptance rule: a feature is complete only when
**INPUT → real backend → real processing → real result → real user action**
works end-to-end. Verified status:

| Feature | End-to-end verified | Evidence |
|---|---|---|
| Validator / Generator / Linter / Converter | ✅ | acceptance WF1, WF6, WF7, WF8 |
| Clock Intelligence | ✅ | acceptance WF2 |
| Coverage | ✅ | acceptance WF3 |
| Interactions | ✅ | acceptance WF4 |
| Readiness | ✅ | acceptance WF5 |
| Diff | ✅ | acceptance WF10 |
| Netlist / Design Context | ✅ | acceptance WF11 |
| CI | ✅ | acceptance WF12 (PASS 0 / FAIL 1 live) |
| Reports / Export | ✅ | acceptance WF13 |
| Test Drive | ✅ | acceptance WF14 (real backend, no mocks) |
| Corner / MMC | ⚠️ PARTIAL | acceptance WF9 — corners CLI read-only, MMC API/UI-only |

---

## 4. Traceability conclusion

- **All 21 reference features present** and reachable in the current product;
  the rebuild keeps all of them (none dropped).
- 5 new capability areas added since the reference (design-aware, reset/CDC,
  DFT, derate methodology, rationale lint) — all additive, none replacing.
- Rebuild reuses the frozen backend for every row; only entry points,
  navigation, and presentation change.
- Remaining gaps are the acceptance-report P2 items (out of scope for this
  sprint) and the two PARTIAL surfaces (Corners CLI read-only, MMC CLI
  absence) — tracked in `PRODUCT_REBUILD_PLAN.md`.
