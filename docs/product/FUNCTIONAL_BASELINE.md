# Ṛta — Functional Baseline (Frozen Contract)

> **Purpose:** the verified functional contract of Ṛta at the close of the P1
> Engineering Correction Sprint. This document is the reference the product
> rebuild must preserve. From this point forward the deterministic SDC engine
> is **frozen**: rule semantics, rule IDs, severities, parser behavior,
> coverage/clock/readiness calculations, diff semantics, generator semantics,
> and converter semantics change only if a genuine correctness regression is
> discovered. UI/API *presentation* may adapt to the new architecture, but the
> underlying engineering results must remain identical.
>
> Baseline: **Ṛta v1.5.8** · verified 2026-08-14.

---

## 0. Verified baseline summary

| Dimension | Value |
|---|---|
| pytest (full suite incl. evidence) | **1,227 passed, 0 failures** |
| pytest (`rta/tests/` manifest) | 886 tests / 29 files |
| P1 regression tests (`test_p1_corrections.py`) | 23 (all green) |
| Parity-defect regression tests (`test_parity_defect_classes.py`) | 23 (all green) |
| Test Drive parity (`test_test_drive_parity.py`) | 6 (all green) |
| Engineering workflows (acceptance) | 14/14 accepted |
| Acceptance findings | 0 P0 · 0 P1 (all 7 corrected) · 10 P2 (open, out of scope) |
| Paired parity harness | 200-file corpus, intact (identical to audit baseline) |
| Rules catalog | **119 rules** in `rules_registry` (SDC-001..157 + CHG-*); analysis-scope code `SCOPE-UNSUPPORTED` emitted by readiness/diff/policy (not a registry rule) |
| Coverage model | 39 items across 6 categories (SDC-only) + design-aware (netlist) |
| Engine module map | analysis: `clock_relations`, `coverage`, `design_coverage`, `constraint_interactions`, `constraint_readiness`, `async_reset_check`, `dft_scan_check`, `derate_methodology`, `rationale_lint` · context: `design_context` · preprocess: `sdc_preprocess`, `tcl_resolver` · diff: `readiness_diff` · policy: `policy_engine` · tools: `generate`, `lint`, `report`, `convert`, `corners`, `batch` |
| CLI commands | check · generate · diff · corners · analyze · rules · whats-new · web · coverage · report · lint · convert · batch |
| CLI exit-code contract | 0 pass · 1 gate/analysis fail · 2 invalid invocation · 3 engine failure |
| API endpoints | health · design · rules · analyze · lint · convert · generate · corners · mmc · mmc/zip · diff · report/html · feedback |
| `real_design_full.sdc` contract | 7 clocks · 21 clock pairs · 25 constraints · 5 false paths · 4 multicycles · 2 clock groups · 82.1% coverage (32/39) · 0 errors |
| Runtime | Python ≥ 3.10, stdlib-only core; no required runtime deps |

### Non-negotiables (trust disclosures — must never be weakened)

- "Constraint-readiness review, **NOT an STA timing signoff** — READY does not mean setup/hold passes."
- "**Coverage is NOT correctness** — a fully covered design can still have timing errors."
- "**Limited design verification (SDC-only mode)** — upload a netlist to verify object references."
- "**CI PASS ≠ timing pass**."
- Engine failure never fakes a PASS (SDC-140 / gate cannot report PASS on incomplete evidence).

---

## 1. Capability contract (per capability)

For every capability: **INPUT · PROCESSING · OUTPUT · DEPENDENCIES ·
STANDALONE/SESSION · SDC REQUIRED? · NETLIST REQUIRED? · LIMITATIONS ·
VERIFIED TESTS.**

---

### 1.1 SDC Validator (checker)

- **INPUT:** SDC text or file. Optional: netlist (Verilog), `--top`, custom-rules YAML (`--custom-rules`, repeatable).
- **PROCESSING:** preprocess (strip comments, join `\` continuations, resolve `$VAR`s, detect unclosed brackets) → per-command rule engine → clock-relations folding → constraint-interactions folding → readiness aggregation.
- **OUTPUT:** `CheckResult` — errors / warnings / info with `code`, `severity`, `message`, `line` (source location; absence findings stay `line: 0`), plus `stats` (per-command counts). CLI: text, `--json`, `--junit`, `--format csv|markdown`, `--output`; exit 1 on any error.
- **DEPENDENCIES:** `sdc_preprocess`, `tcl_resolver`, `checker` (+ `clock_relations`, `constraint_interactions`, `constraint_readiness`, `rules_registry`).
- **STANDALONE/SESSION:** both — standalone `rta check`; session entry via webui Validator/Findings.
- **SDC REQUIRED?** yes. **NETLIST REQUIRED?** no (unlocks design-aware rules SDC-055..066, 151..155 and coverage).
- **LIMITATIONS:** object resolution requires a netlist; SDC-only mode explicitly scoped `NETLIST_REQUIRED`; no STA timing; deterministic — same input → same findings.
- **VERIFIED TESTS:** `test_checker.py` (96), `test_p1_corrections.py` (23), `test_parity_defect_classes.py` (23), `test_test_drive_parity.py` (6), `test_sdc_preprocess.py` (78), `test_tcl_resolver.py` (30), `test_custom_rules.py` (29), `test_policy_engine.py` (34).

### 1.2 SDC Generator

- **INPUT:** generation parameters (design name, clocks `NAME=PERIOD[:PORT]` repeatable, uncertainty, sdc-version, operating-condition, derate, ideal-reset, reset-port, propagated, scan, scan-port) via CLI flags or `SDCParams` dataclass / API `POST /api/generate`.
- **PROCESSING:** `generate_sdc(p)` emits a 22-section canonical SDC (version → units → clocks → attributes → CDC groups → I/O → design rules → OC → derate → ideal → scan → min-pulse → case → disable arcs → path groups → wire load → false paths → multicycle → half-cycle → power → dont-use).
- **OUTPUT:** SDC text (stdout / `--output` file / API response). Must be **self-consistent**: passes its own linter and checker, no malformed commands, no empty values (P1-3: OC section omitted when no OC name), no trailing whitespace beyond pre-existing CRLF style.
- **DEPENDENCIES:** `generator.py` only (self-contained).
- **STANDALONE/SESSION:** both — standalone `rta generate`; session webui Generator (copy / download / open in Validator).
- **SDC REQUIRED?** no — generation starts from parameters.
- **LIMITATIONS:** library `--scan-port` default differs from CLI default (`scan_en` vs `scan_mode`); generated `-master_clock` references a port name.
- **VERIFIED TESTS:** `test_generator.py` (31), `test_p1_corrections.py` generator tests, `test_evidence.py` (21).

### 1.3 SDC Linter

- **INPUT:** SDC file; flags `--check`, `--fix`, `--output`.
- **PROCESSING:** `lint_sdc(text, fix)` → checks trailing whitespace, tabs, lines > 120 chars; fix mode reorders into canonical 22-section order, inserts banners, collapses `\`-continuations, preserves header comments.
- **OUTPUT:** `LintResult` (original/formatted text, issues, line counts, warnings, fixed). `--check` exits 1 if not clean.
- **DEPENDENCIES:** `linter.py` (self-contained).
- **STANDALONE/SESSION:** both — standalone CLI; webui Linter tool.
- **SDC REQUIRED?** yes.
- **LIMITATIONS:** multi-line commands not ending in `\` are dropped when collapsing continuations; `_parse_lines`/`_MULTI_LINE_COMMANDS` dead code.
- **VERIFIED TESTS:** `test_linter.py` (17), `test_evidence.py`.

### 1.4 SDC Converter

- **INPUT:** SDC file; `--format json|yaml`; `--output`.
- **PROCESSING:** `parse_sdc(text)` → structured `ParsedSDC` (filename, sdc_version, units, clocks[], input/output_delays[], false_paths[], multicycle_paths[], clock_groups[], timing_derate[], case_analysis[], constraints_count, clocks_count).
- **OUTPUT:** JSON or YAML document (file or stdout). Round-trip preserves data; conversion is one-way (no JSON→SDC claim).
- **DEPENDENCIES:** `converter.py` (+ `pyyaml` for YAML — optional).
- **STANDALONE/SESSION:** both — standalone CLI; webui Converter.
- **SDC REQUIRED?** yes.
- **LIMITATIONS:** I/O-delay `value` extraction quirk with `-max 1.2` flag form; `waveform` never populated; `set_max_delay`/`set_min_delay` appended to `multicycle_paths` list.
- **VERIFIED TESTS:** `test_converter.py` (14).

### 1.5 Clock Intelligence

- **INPUT:** SDC file; `--json`; webui Clocks page.
- **PROCESSING:** `analyze_clock_relations(text)` — clock inventory (primary/generated/virtual), pair inference (5 priority rules: same-port-diff-period → physically exclusive; ancestor/descendant → synchronous; shared ancestor → synchronous; different source → asynchronous; default async), mismatch detection.
- **OUTPUT:** clocks[], pairs[] (relation per pair), existing_groups[], and three finding collections: `mismatches` (SDC-060/061 warnings), `missing_constraints` (SDC-062 — labelled **Missing Constraints**, not "Mismatches"), `advisories` (SDC-063). `stats` consistent: `mismatches == len(mismatches)`, `missing == len(missing_constraints)` (P1-2/P1-7). Full N×N matrix with hover reason in webui.
- **DEPENDENCIES:** `clock_relations.py`; folded into checker.
- **STANDALONE/SESSION:** both — `rta analyze clock-relations`; webui Clocks.
- **SDC REQUIRED?** yes. **NETLIST REQUIRED?** no.
- **LIMITATIONS:** not STA-level clock analysis; synchronous pairs marked `-asynchronous` accepted (conservative); inference is structural, not simulation-backed.
- **VERIFIED TESTS:** `test_clock_relations.py` (15), `test_p1_corrections.py` (stats-consistency), `test_parity_defect_classes.py` (inference), `test_test_drive_parity.py`.

### 1.6 Coverage

- **INPUT:** SDC file; optional netlist + `--top`; `--json`, `--missing-only`.
- **PROCESSING:** SDC-only: 39-item category gap analysis across 6 categories (Clocks 9, I/O 6, Timing Exceptions 7, Design Rules 6, AOCV/Derate 5, Power/DFT 6). With netlist: design-aware port-level coverage (inputs/outputs/clocks/exceptions) in addition.
- **OUTPUT:** `CoverageResult` — score 0–100, present/total (39), missing list, per-category breakdown with status (good ≥80 / warn ≥50 / bad). CLI prints "**Coverage is NOT correctness**" and JSON exposes `trust.coverage_is_not_correctness` (P1-4). API `analyze` payload includes `sdc_only_coverage` when no netlist (P1-5).
- **DEPENDENCIES:** `coverage.py`, `design_coverage.py` (netlist), `design_context.py`.
- **STANDALONE/SESSION:** both — `rta coverage`; webui Coverage.
- **SDC REQUIRED?** yes. **NETLIST REQUIRED?** no (design-aware mode optional).
- **LIMITATIONS:** coverage ≠ correctness; SDC-only coverage cannot verify design objects; netlist-aware items only with netlist.
- **VERIFIED TESTS:** `test_coverage.py` (18), `test_design_coverage.py` (29), `test_design_context.py` (41), `test_p1_corrections.py` (disclosure + SDC-only payload).

### 1.7 Design Context / Netlist

- **INPUT:** SDC + optional Verilog netlist + optional `--top`.
- **PROCESSING:** `design_context.py` parses netlist (ports, instances, pin_nets/net_pins, module directions); `design_coverage.py` classifies port coverage; netlist-aware rules resolve object references, detect reset trees (SDC-151/152/153), scan shapes (SDC-154/155).
- **OUTPUT:** design context summary (`top`, ports, instances, clocks structurally resolved), port-level coverage, netlist-backed findings (SDC-055..066, SDC-151..155).
- **DEPENDENCIES:** `design_context.py`, `design_coverage.py`, `checker.py`.
- **STANDALONE/SESSION:** SDC-only is standalone; design-aware requires netlist supplied alongside.
- **SDC REQUIRED?** yes. **NETLIST REQUIRED?** for design-aware mode only.
- **LIMITATIONS:** netlist parsing is structural (module/port connectivity), not gate-level timing; no invented netlist intelligence beyond what is computed.
- **VERIFIED TESTS:** `test_design_context.py` (41), `test_design_coverage.py` (29), `test_netlist_*` evidence suites.

### 1.8 Constraint Interactions (Conflicts)

- **INPUT:** SDC (folds into check / API analyze).
- **PROCESSING:** `constraint_interactions.py` — duplicate detection (SDC-067/068), overrides, contradictions (SDC-069), overlapping exceptions, legal-multiple detection.
- **OUTPUT:** analyzed/duplicates/overrides/conflicts/need-sta/legal-multiples counts; line-paired conflict findings (`:9 ↔ :8`) with what/why/review.
- **DEPENDENCIES:** `constraint_interactions.py`, checker.
- **STANDALONE/SESSION:** folds into validator (both surfaces).
- **SDC REQUIRED?** yes.
- **LIMITATIONS:** flags need-STA items for review — does not resolve them.
- **VERIFIED TESTS:** `test_constraint_interactions.py` (44), `test_finding_identity.py` (30).

### 1.9 Readiness

- **INPUT:** SDC (+ netlist optional, + baseline for diff mode).
- **PROCESSING:** `constraint_readiness.py` aggregates per-dimension status from rule tiers.
- **OUTPUT:** tier (BLOCKED / REVIEW_REQUIRED / READY) + per-dimension status (analysis trust, clocks, consistency, coverage, design context, exceptions, I/O) each with **WHY** (findings + actions, e.g. `P2 REVIEW_CLOCK_MODEL`), plus standing "not an STA signoff" disclaimer.
- **DEPENDENCIES:** `constraint_readiness.py`, checker, coverage, design context.
- **STANDALONE/SESSION:** both — folded into `rta check`; webui Health.
- **SDC REQUIRED?** yes.
- **LIMITATIONS:** readiness is pre-STA constraint intelligence, never a signoff claim.
- **VERIFIED TESTS:** `test_readiness_*` evidence suites, `test_policy_engine.py` (34), acceptance WF5.

### 1.10 Diff

- **INPUT:** V1 SDC + V2 SDC (+ optional `--linked-v1`/`--linked-v2` TCL files, `--v1-name`, `--v2-name`).
- **PROCESSING:** `constraint_diff.py` + `tcl_resolver.py` + `wildcard_analyzer.py` — join continuations, strip comments, resolve variables, parse 34 command types, match constraints, classify against 21 CHG-* rules.
- **OUTPUT:** `ChangeAnalysisResult` — changes (fatal/warning/info) with stats (v1/v2/matched/added/removed/modified/fatal/warnings/info/total), change descriptions with impact + review guidance. HTML report via `report diff`.
- **DEPENDENCIES:** `constraint_diff.py`, `tcl_resolver.py`, `wildcard_analyzer.py`.
- **STANDALONE/SESSION:** standalone `rta diff`; webui Changes (readiness-diff authority).
- **SDC REQUIRED?** yes — two of them.
- **LIMITATIONS:** CHG-WC-002 never emitted; CHG-FP-002 "same wildcard" branch unreachable; `wildcard_comparisons` declared but never populated.
- **VERIFIED TESTS:** `test_constraint_diff.py` (13), `test_wildcard_analyzer.py` (26), `test_tcl_resolver.py` (30), `test_readiness_diff.py` (37).

### 1.11 Corner Manager

- **INPUT:** none required (presets) — `rta corners list`, `rta corners show "<preset>"`; webui Corner Manager (create/edit/delete corners, JSON import/export).
- **PROCESSING:** `corner_manager.py` — Corner data model with validation ranges (voltage 0.3–1.5 V, temp −55..175 °C, process set, derates 0.5–1.5, uncertainty 0.5–2.0); 4 presets (Classic 3, Industrial 5, Full 8, Custom); JSON serialization.
- **OUTPUT:** corner lists, per-corner display grid, JSON.
- **DEPENDENCIES:** `corner_manager.py` (standalone).
- **STANDALONE/SESSION:** standalone CLI (read-only) / session webui (editable).
- **SDC REQUIRED?** no. **NETLIST REQUIRED?** no.
- **LIMITATIONS:** CLI corners is read-only; editing is webui/API-only.
- **VERIFIED TESTS:** evidence corner suites, acceptance WF9 (PARTIAL — read-only CLI).

### 1.12 MMC (Multi-Corner)

- **INPUT:** base SDC template or generation parameters + corner set.
- **PROCESSING:** `mmc.py` — `generate_corner_sdcs` (clone per corner, apply OC/derates/uncertainty scale), `diff_corners` (section-aware line diff), `check_sdc_multi` (per-corner checks + cross-corner rules SDC-050/051/053), `create_corner_zip`.
- **OUTPUT:** per-corner SDCs, ZIP download, cross-corner consistency findings, corner diff.
- **DEPENDENCIES:** `mmc.py` → generator, checker, corner_manager.
- **STANDALONE/SESSION:** API/UI-only (`/api/mmc`, `/api/mmc/zip`, webui MMC) — no CLI subcommand.
- **SDC REQUIRED?** template or params. **NETLIST REQUIRED?** no.
- **LIMITATIONS:** SDC-054 (derate monotonicity) is a declared no-op.
- **VERIFIED TESTS:** evidence MMC suites, acceptance WF9.

### 1.13 Test Drive

- **INPUT:** sample SDC picker or uploaded SDC.
- **PROCESSING:** runs the full battery — checker, coverage, clock relations, linter, converter — through the real backend (`/api/analyze`-equivalent), no mocked results.
- **OUTPUT:** unified dashboard (metrics + findings + coverage + clocks + lint + conversion), JSON download, feedback prompt.
- **DEPENDENCIES:** all engine modules.
- **STANDALONE/SESSION:** session tool (webui).
- **SDC REQUIRED?** yes.
- **LIMITATIONS:** sample set is small.
- **VERIFIED TESTS:** `test_test_drive_parity.py` (6), acceptance WF14.

### 1.14 Rules (Registry)

- **INPUT:** none for browsing; SDC for execution.
- **PROCESSING:** `rules_registry.py` — central documentation of all 119 rules (`Rule{code, severity, short_name, description, why_matters, fix, reference_url, module, added_version}`).
- **OUTPUT:** `rta rules list [--module|--severity|--search|--json]`, `rta rules show <code>`; webui Rules page (searchable/filterable); JSON/Markdown downloads.
- **DEPENDENCIES:** `rules_registry.py`.
- **STANDALONE/SESSION:** standalone CLI; session webui.
- **SDC REQUIRED?** no for browsing; yes for execution.
- **LIMITATIONS:** none significant.
- **VERIFIED TESTS:** `test_rules_registry.py` (20).

### 1.15 CI

- **INPUT:** SDC + baseline JSON (`--save-baseline` / `--baseline`) + gate policy (`--gate {BLOCKERS_ONLY,NO_READINESS_REGRESSION,STRICT,CUSTOM}` + `--gate-policy`).
- **PROCESSING:** policy engine evaluates gate tiers against findings + readiness regression vs baseline.
- **OUTPUT:** PASS/FAIL verdict with exit code (0 pass / 1 gate-fail / 2 invalid / 3 engine-failure), regression details; JSON/JUnit consumable.
- **DEPENDENCIES:** `policy_engine.py`, checker, readiness, readiness_diff.
- **STANDALONE/SESSION:** standalone CLI; webui CI tool.
- **SDC REQUIRED?** yes (+ baseline for gates).
- **LIMITATIONS:** exit 2 collides with argparse usage-error code (documented P2); CI PASS ≠ timing pass.
- **VERIFIED TESTS:** `test_policy_engine.py` (34), acceptance WF12 (PASS 0 / FAIL 1 verified).

### 1.16 Trust

- **INPUT:** none (presentational).
- **PROCESSING:** trust disclosures surfaced on readiness, coverage, CI, and scope states.
- **OUTPUT:** standing disclaimers (see §0) — never weakened.
- **DEPENDENCIES:** presentation layer.
- **STANDALONE/SESSION:** both surfaces.
- **SDC REQUIRED?** no.
- **LIMITATIONS:** none.
- **VERIFIED TESTS:** acceptance trust test; `test_trust_transparency.py` evidence.

### 1.17 Reports

- **INPUT:** results of check / diff / clock-relations / coverage (+ `--output` path).
- **PROCESSING:** `reporter.py` — 5 self-contained HTML report types (check, diff, clock-relations, rules, coverage), inline CSS, no external assets; footer with version + date.
- **OUTPUT:** self-contained HTML files; CLI prints open hint (`start file.html` / `open file.html`).
- **DEPENDENCIES:** `reporter.py`.
- **STANDALONE/SESSION:** standalone CLI (`rta report ...`); webui Report page (HTML/JSON download).
- **SDC REQUIRED?** yes (per report type).
- **LIMITATIONS:** cosmetic description duplication in diff report (P2).
- **VERIFIED TESTS:** `test_reporter.py` (26), acceptance WF13.

### 1.18 Documentation

- **INPUT:** none.
- **PROCESSING:** README, CONTRIBUTING, docs/features (13 per-feature guides), docs/architecture, docs/migration, docs/product, in-CLI help, `rta whats-new`.
- **OUTPUT:** user + contributor + product documentation surfaces.
- **DEPENDENCIES:** repo docs.
- **STANDALONE/SESSION:** n/a.
- **SDC REQUIRED?** no.
- **LIMITATIONS:** exit-code contract and gate-policy matrix not in one place (P2-10).
- **VERIFIED TESTS:** evidence docs-consistency checks.

### 1.19 Feedback

- **INPUT:** thumbs up/down + optional comment after results.
- **PROCESSING:** `feedback.py` — persisted to `rta/workspace/data/feedback.json`; aggregates totals, satisfaction, entries.
- **OUTPUT:** feedback dashboard (webui Feedback page); persisted entries.
- **DEPENDENCIES:** `feedback.py`, webui.
- **STANDALONE/SESSION:** session (webui).
- **SDC REQUIRED?** no.
- **LIMITATIONS:** simple 1/0/−1 model.
- **VERIFIED TESTS:** `test_ui_state_isolation.py` evidence, acceptance.

### 1.20 CLI

- **INPUT:** commands + flags (13 subcommands; see §0).
- **PROCESSING:** argparse over the frozen engine; deterministic; CI-friendly.
- **OUTPUT:** text / JSON / JUnit / CSV / Markdown / HTML; exit codes 0/1/2/3.
- **DEPENDENCIES:** all engine modules.
- **STANDALONE/SESSION:** standalone.
- **SDC REQUIRED?** per command.
- **LIMITATIONS:** `rta web` launches the workspace; corners read-only.
- **VERIFIED TESTS:** `test_cli.py` (56), `release_cli_audit.py` (16/16).

### 1.21 API

- **INPUT:** JSON bodies (sdc, netlist, top, baseline, gate, custom_rules, format, params…).
- **PROCESSING:** `api_server.py` (stdlib http.server) wraps the frozen engine; validates required SDC (HTTP 400 structured error for missing/empty/whitespace — P1-6); `ok`/`error` envelope.
- **OUTPUT:** JSON (analysis, lint, convert, generate, corners, mmc, diff, report/html, rules, design, health, feedback).
- **DEPENDENCIES:** engine modules, `api_server.py`.
- **STANDALONE/SESSION:** powers the webui session.
- **SDC REQUIRED?** for analyze/lint/convert/diff (400 otherwise).
- **LIMITATIONS:** stats must stay consistent with collections (P1-7 fixed; regression-guarded).
- **VERIFIED TESTS:** `test_p1_corrections.py` API tests; acceptance WF13/14.

### 1.22 Batch processing

- **INPUT:** directory path; `batch check|report|lint [--fix] [--verbose]`.
- **PROCESSING:** `batch_runner.py` recursively discovers `**/*.sdc`, applies one operation per file, aggregates `BatchSummary`.
- **OUTPUT:** per-file status lines + summary (total/ok/errors/skipped); HTML reports per file (report mode); exit 1 if any file errored.
- **DEPENDENCIES:** checker, reporter, linter.
- **STANDALONE/SESSION:** standalone CLI only.
- **SDC REQUIRED?** yes (per file).
- **LIMITATIONS:** `batch lint --fix` overwrites files in place (by design); no web surface (per reference).
- **VERIFIED TESTS:** `test_batch_runner.py` (7), `test_evidence.py` (21).

---

## 2. Freeze scope

The following are **frozen** (no behavior change without a documented
correctness regression):

- Rule semantics, IDs, severities, messages (SDC-*, CHG-*; `SCOPE-UNSUPPORTED` scope handling)
- Parser behavior (preprocess, TCL resolution, bracket diagnostics)
- Coverage calculations (39-category model, scoring)
- Clock calculations (inference rules, pair classification, stats)
- Readiness calculations (dimensions, tiers, actions)
- Diff semantics (CHG-* classification)
- Generator semantics (22-section output)
- Converter semantics (ParsedSDC schema)
- Trust disclosures (never weakened)

**Presentation may change** (webui/API shape, navigation, feature entry
points, visual design) as long as the engineering results remain identical.
The API may add fields (e.g. `sdc_only_coverage`) but must not contradict
engine collections (`stats` consistency is regression-guarded).

---

## 3. Session vs standalone model (current)

| Pattern | Works today | Entry |
|---|---|---|
| Standalone CLI | yes | `rta <command>` |
| Standalone web tool | yes (tools exist pre-analysis) | webui Generator/Linter/Converter/Corners/MMC/Diff/Rules/CI/Test Drive |
| Analysis session (upload → findings → clocks → coverage → readiness) | yes | webui New Analysis → Results group |
| Cross-links | Generator → Open in Validator; Validator → Clocks/Coverage/Health; Test Drive → all | webui |

The rebuild (PRODUCT_WORKSPACE_ARCHITECTURE_V2.md) must preserve both
patterns while making every capability independently reachable.

*Baseline verified 2026-08-14 on Ṛta v1.5.8. Any future change to engine
behavior must update this document and re-run the verification chain
(pytest, smoke, comprehensive, parity harness, Test Drive).*
