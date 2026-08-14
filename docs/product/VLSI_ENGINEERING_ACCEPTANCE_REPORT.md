# Ṛta — VLSI Engineering Acceptance Report

**Status:** ACCEPTANCE EVALUATION COMPLETE — no fixes performed
**Date:** 2026-08-14 · **Product under test:** Ṛta v1.5.8
**Persona:** block-level Physical Design / STA / SDC Constraints engineer
**Method:** every workflow was executed end-to-end against the real product (CLI `python cli.py`, live API `rta/api/api_server.py`, workspace webui served by that API). No mocked data, no UI-only credit. Findings below include exact reproduction steps.

---

## 1. Overall verdict

**A real block-level VLSI engineer CAN use Ṛta end-to-end today.**

- All **14 workflows** execute real input → real backend → real result → real user action.
- All **10 questions** an engineer asks (what's wrong / missing / suspicious / covered / clocks / conflicts / changed / ready / export / CI) are answered by a working surface.
- The product is **honest about its boundaries**: it consistently states it is *pre-STA constraint intelligence*, never signoff or STA replacement, and it explicitly marks what it cannot verify without a netlist.
- **No P0 findings** (nothing prevents real engineering use).
- **7 P1 findings** (significantly reduce usefulness in specific workflows) and **10 P2 findings** (polish / convenience).
- The most serious single defect is in the **generator**: it can emit a malformed SDC line (and its own output fails its own linter) — details in §WF6.

Verdict summary: **ACCEPT WITH P1 FIXES** for the generator defect and the source-location/mismatch-label inconsistencies; everything else is P2 polish.

---

## 2. Workflow matrix (PASS / PARTIAL / FAIL)

| # | Workflow | Verdict | One-line evidence |
|---|---|---|---|
| 1 | SDC Validation | **PASS** ⚠ | deterministic (byte-identical re-runs), correct severities/IDs/counts; line numbers inconsistent across rules |
| 2 | Clock Intelligence | **PASS** ⚠ | inventory + relationships + hierarchy + explanations; CLI "Mismatches:" header contradicts its own section |
| 3 | Coverage | **PASS** ⚠ | score/present/total/categories/actionable; UI says "coverage ≠ correctness"; standalone CLI omits the disclaimer; UI hides SDC-only category score |
| 4 | Constraint Interactions | **PASS** | SDC-067/068/069 with `:9 ↔:8` line pairs, what/why/review |
| 5 | Readiness | **PASS** | BLOCKED/REVIEW_REQUIRED/READY with per-dimension WHY + actions + "not an STA signoff" disclaimer |
| 6 | SDC Generator | **PASS** ⚠ | full SDC generated, re-imports cleanly; **malformed `set_operating_conditions` when OC omitted; output fails its own linter** |
| 7 | Linter | **PASS** | clean/check/fix/format + exit codes, CLI + API |
| 8 | Converter | **PASS** | SDC→JSON/YAML preserves clocks/delays/exceptions/groups; no reverse path (not claimed) |
| 9 | Corner / MMC | **PARTIAL** | corners list/show work; **no CLI for MMC generation/validation or corner editing** (API/UI only) |
| 10 | Diff | **PASS** | period/uncertainty/IO/FP/MCP changes detected with severity + why-it-matters |
| 11 | Netlist | **PASS** | SDC-only vs SDC+netlist delta exactly as advertised; no invented netlist intelligence |
| 12 | CI | **PASS** | baseline/gate/junit/json; PASS exit 0, gate-FAIL exit 1, invalid invocation exit 2 — CI genuinely blocks |
| 13 | Reports / Export | **PASS** | all 4 HTML reports non-empty with real findings; open-hint printed; one cosmetic text duplication |
| 14 | Test Drive | **PASS** | real samples → real `/api/analyze` → real results; results JSON downloadable; no mock data |

---

## 3. Findings with exact reproduction

### P1 — significantly reduces engineering usefulness

**P1-1. Source location (line numbers) is inconsistent across findings.**
An engineer asking "where in my SDC?" gets a line number for some rules and not others.
- `python cli.py check rta/evidence/timing_exceptions/multicycle_no_hold.sdc --json` → SDC-021, SDC-030, and all 19 SDC-1xx info items carry **no `line` field**; SDC-150 does.
- Compare: `check rta/evidence/readiness/HR13_multiple_blockers.sdc --json` → SDC-046 has `"line": 6`.
- Most rules do not populate `Issue.line`; only rule-specific paths do.
- Reproduction: `python cli.py check rta/evidence/timing_exceptions/multicycle_no_hold.sdc --json`.

**P1-2. Clock-relations CLI contradicts itself: "Mismatches: 0" then a "Mismatches:" section listing findings.**
- `python cli.py analyze clock-relations rta/evidence/regression/real_design_full.sdc` prints:
  - `Mismatches: 0` and `Missing Constraints: 18` (from `stats`),
  - then a section titled **`Mismatches:`** listing 18 SDC-062 "No set_clock_groups…" findings (which are the *missing* constraints).
- Root cause: `rta/cli/cli.py` prints `result.stats.get('mismatches')` for the header but iterates `result.mismatches` (which contains missing-constraint objects) under the literal label `"Mismatches:"`. `stats['mismatches']` is 0 while `stats['missing']` = `len(result.mismatches)`.

**P1-3. Generator emits malformed SDC and output that fails its own linter.**
- `python cli.py generate -d MY_SOC -c clk=10.0:sys_clk --derate --output gen.sdc` (no `--operating-condition`)
  → line 39 is literally `set_operating_conditions -max ` — **empty operating-condition value** (invalid SDC) + trailing whitespace.
- `python cli.py lint --check gen.sdc` → `Line 39: Trailing whitespace` → exit 1.
- `python cli.py check gen.sdc` → 0 errors (the empty OC line is not flagged), so a broken constraint can be generated, validated, and shipped silently.
- The generator should either emit a real OC name, omit the line, or require `--operating-condition`.

**P1-4. Standalone `rta coverage` CLI never states "coverage ≠ correctness".**
- `python cli.py coverage rta/evidence/reference_designs/rd01_single_clock/rd01_single_clock.sdc` (and `--json`) contains **no** "not correctness" disclosure; the JSON has no `confidence_is_not_correctness` flag.
- The flag exists in `check --json` and the webui Coverage page shows the callout — the standalone coverage surface is the only one missing it.

**P1-5. Webui Coverage page hides the SDC-only category-gap score the engine computes.**
- `python cli.py coverage <sdc>` (no netlist) returns a real 39-category score (e.g. rd01 = 43.6%, 17/39).
- The webui Coverage page (`/api/analyze` → `coverage`) shows **only** design-aware port coverage; without a netlist it renders an empty state and never surfaces the 39-category score.
- Two coverage definitions exist; the CLI shows both, the UI shows only one.

**P1-6. API `analyze` returns `ok: true` for an empty/missing `sdc` body.**
- `curl -X POST /api/analyze -H 'Content-Type: application/json' -d '{}'` → 200, `ok: true`, `scope.commands_found: 0`, one "SDC-001 no clock" finding — indistinguishable from analyzing a genuinely empty SDC.
- An integration bug (empty body) silently "succeeds" instead of a 400. The UI never sends empty input, so this is API-contract robustness, but it is a trust hazard for CI/API consumers.

**P1-7. API clock-relations response carries contradictory counts.**
- `/api/analyze` on `real_design_full.sdc` returns `clock_relations.stats.mismatches = 0` while `clock_relations.mismatches` has **18 entries** (and `stats.missing = 18`).
- Same root cause as P1-2: `stats` and the `mismatches` list disagree. A consumer reading `stats.mismatches` gets the wrong number.

### P2 — polish / convenience

**P2-1.** `rta corners` CLI is read-only (`list`/`show` only): no corner creation, no MMC generation/validation from the CLI. MMC exists only in API (`/api/mmc`, `/api/mmc/zip`) and webui. CLI-only engineers cannot do multi-corner work.
**P2-2.** `report diff` HTML duplicates the change-rule description ("Constraint removed in V2. Constraint removed in V2.") — cosmetic.
**P2-3.** Gate exit code 2 (`EXIT_INVALID`) collides with argparse's usage-error code 2; the tool prints "gate [STRICT]: FAIL (exit 2)" so it is recoverable, but CI scripts cannot distinguish "invalid invocation" from "gate blocked" by code alone without parsing output.
**P2-4.** `/api/lint` with `fix:false` returns `formatted_text: ""` and `line_count_formatted: 0` even though the CLI linter formats without `--fix`; API consumers must know to pass `fix:true` to get formatted output.
**P2-5.** Checker `stats` and message text disagree in places (e.g. `stats['Clocks']` vs count of parsed clocks is consistent, but the clock-relations stats issue in P1-7 is the pattern to fix globally).
**P2-6.** Test Drive offers 4 small inline samples only; no realistic multi-clock sample with a netlist to demonstrate the design-aware tier.
**P2-7.** Webui "Download results JSON" and report download work, but there is no single "download everything" bundle; several separate downloads.
**P2-8.** `whats-new` is CLI-only; the webui has no release-notes surface.
**P2-9.** CLI `analyze clock-relations` "All Clock Pairs" detail requires `--verbose`; default output shows the mismatch/missing section only.
**P2-10.** README/business site mention 863 tests and surfaces, but the CLI user-guide does not document the exit-code contract (0/1/2/3) or the gate-policy matrix in one place.

---

## 4. Workflow detail (evidence)

### WF1 — SDC Validation — PASS ⚠
Verified on valid / invalid / malformed / warning-heavy / realistic files. Parse, rule execution, severities, IDs, messages, error/warning/info counts all correct; **byte-identical JSON on repeated runs** (deterministic). Exit codes: 0 clean / 1 findings / 2 usage-or-IO. JSON carries `errors/warnings/info/stats/summary/analysis_scope/constraint_coverage/constraint_interactions/constraint_readiness`. Limitation: P1-1 line numbers.

### WF2 — Clock Intelligence — PASS ⚠
`analyze clock-relations` returns inventory (clocks/pairs), relationships (synchronous/asynchronous/physically_exclusive), hierarchy (`-master_clock` chains traced), mismatches, and per-finding explanations with "Specified/Expected" and "Unable to determine a specific relationship — defaulting to asynchronous" (honest uncertainty). No STA-level claims anywhere. Limitation: P1-2 label contradiction.

### WF3 — Coverage — PASS ⚠
Score, present/total/missing, category breakdown with `[Y]/[N]` markers and actionable "Missing — …" text; `--missing-only` works. Webui Coverage page shows the "Coverage is NOT correctness" callout and an honest empty state explaining the netlist requirement. Limitations: P1-4 (CLI disclaimer missing), P1-5 (SDC-only score hidden in UI).

### WF4 — Constraint Interactions — PASS
`check` on `CI20_realistic_mixed.sdc`: `analyzed=14 duplicates=1 overrides=1 conflicts=1`; SDC-067 (`:9 ↔:8` identical delay), SDC-068 (override with line pair + "the earlier constraint is dead"), SDC-069 (max<min "window is impossible"). Answers what/why/review with locations.

### WF5 — Readiness — PASS
`check` on HR fixtures: BLOCKED / REVIEW_REQUIRED / READY with per-dimension status, summary, findings, tier, and action per finding, plus the standing disclaimer "NOT an STA timing signoff — READY does not mean setup/hold passes" and "limited design verification (SDC-only mode)". Readiness explains WHY, never a bare badge.

### WF6 — SDC Generator — PASS ⚠
`generate` produces a complete SDC (clocks, uncertainty, propagated, groups, I/O, derate, scan, reset); re-import `check` → 0 errors, 2 clocks — generated SDC enters the normal validation workflow. Defect: P1-3 (empty `set_operating_conditions` when OC omitted; lint fails on own output).

### WF7 — Linter — PASS
`lint --check` clean → exit 0 ("SDC file is lint-clean"); messy file → formatted output to `--output`; re-check clean. Works in CLI and API.

### WF8 — Converter — PASS
`convert --format json|yaml` preserves `sdc_version`, `units`, `clocks` (with `is_generated`/`is_virtual`), input/output delays, false paths, multicycle paths, clock groups, `constraints_count`, `clocks_count`. No JSON/YAML→SDC reverse path exists (not claimed). Round-trip is one-way by design.

### WF9 — Corner / MMC — PARTIAL
`corners list` (4 presets) and `corners show` (full corner details: process/voltage/temp/op-cond/derates/uncertainty-scale) work. No CLI for corner editing or MMC generation/validation — API (`/api/mmc`, `/api/mmc/zip`) and webui MMC page only (verified working via API).

### WF10 — Diff — PASS
Two realistic versions → detected: clock period decrease (CHG-CK-001 with "50.0MHz frequency increase"), uncertainty (CHG-CK-003), IO delays (CHG-IO-001), false-path removed (CHG-FP-001 FATAL), new false path (CHG-FP-003), new multicycle (CHG-GEN-001), and introduced multicycle-without-hold (CHG-MCP-004 FATAL). Answers what/why/review.

### WF11 — Netlist — PASS
SDC-only: `NETLIST_REQUIRED`, "coverage requires design context", "object existence and coverage unverifiable (SDC-only mode)". SDC+netlist: design context (`top`, 4 ports, 2 instances), `VALIDATED` scope, port-level coverage (`inputs: 3 ports — 1 constrained, 2 exempt`), structural clock resolution, SDC-151 reset-tree finding. The delta is exactly what is advertised; nothing invented.

### WF12 — CI — PASS
`--save-baseline` / `--baseline` / `--gate` verified end-to-end: clean+baseline+STRICT → `gate [STRICT]: PASS (exit 0)`; regression introduced → `gate [STRICT]: FAIL (exit 1)` with the specific trust regressions listed; invalid invocation (STRICT without baseline) → exit 2; JUnit XML valid. CI genuinely blocks a bad change. Disclaimer printed: "CI PASS ≠ timing pass".

### WF13 — Reports / Export — PASS
`report check|coverage|clock-relations|diff` all produce non-empty HTML with real findings (check report has rule codes; diff report lists all 23 changes; coverage report 63 rows). CLI prints `Open with: start <file>`. `analyze all` produces a full E2E HTML (10.9 KB). Exports: JSON (check/coverage/analyze), JUnit, HTML reports, converted JSON/YAML, MMC zip via API.

### WF14 — Test Drive — PASS
The webui Test Drive wires `td-run` → `post("/api/analyze", { sdc })` with real sample SDC text → real backend analysis → results adopted into the session; "Download results JSON" writes `App.state.analysis`. Verified the same `/api/analyze` returns the real 7-clock/21-pair/8-issue result for `real_design_full.sdc`. No mocked or static result data.

---

## 5. Standalone vs session tools

| Tool | A. creates analysis session | B. standalone | C. requires SDC | D. optional netlist | E. other inputs |
|---|---|---|---|---|---|
| **Webui New Analysis** (Findings/Clocks/Coverage/Design/Conflicts/Health/Changes/Report) | ✅ (one session, results-led nav) | — | ✅ | ✅ | top module, baseline JSON, gate policy |
| **Webui Generator / Linter / Converter / Corner Manager / MMC / Rules / CI / Trust** | — | ✅ | depends (gen: none; lint/convert: SDC; corners: none; mmc: template+corners) | ✗ | params / corners |
| **Webui Test Drive** | ✅ (analyzes a sample into the session) | ✅ | ✅ | ✗ | sample selector |
| **CLI `check`** | — | ✅ | ✅ | ✅ (`--netlist/--top`) | `--baseline/--gate/--gate-policy/--custom-rules` |
| **CLI `coverage`** | — | ✅ | ✅ | ✅ (`-n/--top`) | — |
| **CLI `analyze`** | — | ✅ | ✅ | ✅ (`-n/--top`) | — |
| **CLI `lint` / `convert`** | — | ✅ | ✅ | ✗ | — |
| **CLI `diff`** | — | ✅ | ✅ (two SDCs) | ✗ | `--linked-v1/--linked-v2` TCL files |
| **CLI `generate`** | — | ✅ | ✗ | ✗ | clock/params flags |
| **CLI `corners`** | — | ✅ | ✗ | ✗ | preset name (show) |
| **CLI `report`** | — | ✅ | ✅ (check/coverage/clock-relations); two SDCs for diff | ✅ (check/coverage) | — |
| **CLI `batch`** | — | ✅ | ✅ (directory of SDCs) | ✗ | — |
| **API** (11 endpoints) | — | ✅ | per endpoint | analyze: ✅ | params per endpoint |

For every tool the loop is: **give Ṛta** (SDC ± netlist ± options) → **Ṛta returns** (findings / coverage / clocks / readiness / diff / generated SDC / converted JSON / HTML / zip) → **engineer can** (fix, review, export, gate, feed downstream STA).

---

## 6. First-time-user journey

Simulated with no prior knowledge, using the webui landing and CLI help:

1. **What Ṛta does** — landing says "Constraint Intelligence for Digital Design"; the pre-analysis screen is an input surface (paste/load SDC + optional netlist + Analyze). Clear enough.
2. **Where to start** — the product is the input screen; a prominent sample loader ("sample_block.sdc" + netlist) lets a user run something immediately. Good.
3. **Which tool to choose** — after analysis, nav is phrased as questions (Findings, Clocks, Coverage, Design, Conflicts, Health, Changes); "More tools" holds Generator/Linter/Converter/Corner Manager/MMC/Test Drive/Rules/CI/Trust/Documentation. Search (`/`) filters nav. Good.
4. **What input is required** — the input screen separates SDC (required, with file picker) and netlist (separate picker, labeled "no netlist" in the session bar). Reasonably clear.
5. **Netlist optional?** — yes, but the *capability* split (SDC-only vs design-aware) becomes visible only after analysis (`NETLIST_REQUIRED` scope) and on the Coverage empty state. Recorded: the input screen itself does not state what a netlist unlocks. **UX gap (documented, not fixed): state on the input screen that a netlist unlocks design-object verification + coverage.**
6. **What result was produced** — results pages + scope/readiness badges in the session bar; each finding has a message and (some) line numbers (P1-1). Good except locations.
7. **What to do next** — actions per finding (P0/P1/P2 + verb, e.g. `FIX_CLOCKS`), readiness actions, report/export/download buttons. Good.

Recorded UX/product problems (not fixed this sprint):
- Input screen does not pre-state the netlist capability delta (P2).
- Coverage page hides the SDC-only category score (P1-5).
- No release-notes in the UI (P2-8).
- Test Drive samples are tiny; no realistic design-aware sample (P2-6).

---

## 7. Engineering trust test

| Output | What Ṛta KNOWS | What Ṛta INFERS | What Ṛta does NOT know | Needs engineer review | Needs downstream STA |
|---|---|---|---|---|---|
| Checker findings | syntax, duplicates, value sanity, undefined refs, missing categories | data-port naming, suspicious false paths | real delays, cell timing | every REVIEW finding | every unverified path |
| Clock relations | declared clocks, groups, master chains | async/sync/exclusive from structure ("defaulting to asynchronous") | true phase relationship without STA | all pairs w/o declared groups | CDC closure |
| Coverage | which categories/ports are constrained | nothing — counts only | whether constraints are *correct* | "coverage ≠ correctness" (stated) | all timing |
| Readiness | presence/consistency/coverage of constraint set | readiness tier from rules | timing signoff | every REVIEW/BLOCKED dimension | all timing |
| Diff | literal semantic changes | impact framing (CHG-*) | whether the change is bad for timing | every CHG-* | regression runs |
| Netlist | structural connectivity (ports/instances/pins) | reset trees, clock fanout, data-port shapes | parasitic delay, timing | netlist-derived findings | extracted RC timing |
| CI gate | baseline vs current readiness | regression classification | timing correctness ("CI PASS ≠ timing pass" — stated) | gate result | signoff |

Misleading/ambiguous claims found:
- CLI clock-relations "Mismatches: 0" header vs 18-item "Mismatches:" section (P1-2) — reads as a contradiction.
- API `stats.mismatches=0` vs `mismatches[]` length 18 (P1-7).
- Generator's empty `set_operating_conditions -max ` line passes `check` silently (P1-3).
- Standalone coverage CLI omits the "coverage ≠ correctness" disclosure (P1-4).
- API returns `ok:true` on empty input (P1-6).

Trust disclosures that are present and should NOT be weakened: "constraint-readiness review, NOT an STA timing signoff — READY does not mean setup/hold passes"; "coverage is NOT correctness"; "limited design verification (SDC-only mode) — upload a netlist to verify object references"; "CI PASS ≠ timing pass"; engine-failure handling (SDC-140 "a gate can never report PASS on incomplete evidence").

---

## 8. Cross-cutting issues summary

- **CLI issues:** P1-2 (mismatch label), P1-3 (generator), P2-1 (no MMC CLI), P2-3 (exit-2 semantics), P2-9 (verbose-only pair detail).
- **API issues:** P1-6 (empty input ok:true), P1-7 (stats/mismatches conflict), P2-4 (lint fix=false formatted empty).
- **Workspace issues:** P1-5 (SDC-only coverage hidden), P2-6 (tiny test-drive samples), P2-8 (no release notes in UI).
- **Documentation issues:** P2-10 (exit-code contract and gate matrix not documented in one place), plus the CLI user guide does not call out that `corners` is read-only and MMC is UI/API-only.
- **Trust issues:** §7 list — the disclosures that exist are strong; the P1/P2 presentation gaps above are the only places the product reads ambiguously.

---

## 9. Recommended implementation priority

### P0 — prevents real engineering use
**None.** Every workflow functions end-to-end with real processing.

### P1 — significantly reduces engineering usefulness
1. **Generator**: emit a valid operating-condition line (or omit it) when `--operating-condition` is absent; strip the trailing whitespace so generated SDC is lint-clean (WF6 / P1-3).
2. **Source locations**: populate `Issue.line` consistently for all findings in text + JSON (WF1 / P1-1).
3. **Clock-relations presentation**: align the CLI section label with the stats (`Missing Constraints:` for SDC-062 findings) and make `stats['mismatches']` consistent with the `mismatches[]` list in the API (WF2 / P1-2, P1-7).
4. **Coverage disclosures**: add the "coverage ≠ correctness" line to `rta coverage` CLI (text + JSON) and surface the SDC-only category score in the webui Coverage page (WF3 / P1-4, P1-5).
5. **API validation**: return 400 on missing/empty `sdc` for analyze/lint/convert instead of `ok:true` empty analysis (WF14 / P1-6).

### P2 — polish / convenience
1. Add MMC generation/validation + corner editing to the CLI (`corners add/edit`, `mmc generate`) or document read-only status (WF9).
2. Fix the diff-report duplicated rule description (WF10).
3. Document the exit-code contract (0/1/2/3) and gate-policy matrix in one place (WF12).
4. Make `/api/lint` return formatted text with `fix:false` consistent with the CLI (WF8).
5. State the netlist capability delta on the webui input screen (WF1 journey).
6. Larger, realistic Test Drive samples (with netlist) to demonstrate the design-aware tier (WF14).
7. Add release-notes/whats-new to the webui (WF13).
8. Bundle-export option for all results.

---

## 10. Reproduction commands (one-shot)

```bash
# WF1 deterministic + line-number check
python cli.py check rta/evidence/timing_exceptions/multicycle_no_hold.sdc --json   # SDC-021/030/1xx: no line

# WF2 label contradiction
python cli.py analyze clock-relations rta/evidence/regression/real_design_full.sdc  # "Mismatches: 0" + 18-item section

# WF3 disclosures
python cli.py coverage rta/evidence/reference_designs/rd01_single_clock/rd01_single_clock.sdc   # no disclaimer

# WF4 interactions
python cli.py check rta/evidence/constraint_interactions/CI20_realistic_mixed.sdc

# WF5 readiness
python cli.py check rta/evidence/readiness/HR14_realistic_handoff.sdc

# WF6 generator defect
python cli.py generate -d MY_SOC -c clk=10.0:sys_clk --derate --output gen.sdc
python cli.py lint --check gen.sdc          # "Line 39: Trailing whitespace"

# WF10 diff
sed 's/period 5.0/period 4.0/; s/set_clock_uncertainty -setup 0.10/set_clock_uncertainty -setup 0.20/' \
  rta/evidence/reference_designs/rd01_single_clock/rd01_single_clock.sdc > v2.sdc
python cli.py diff rta/evidence/reference_designs/rd01_single_clock/rd01_single_clock.sdc v2.sdc

# WF11 netlist delta
python cli.py check samples/reset_demo/top.sdc                                   # NETLIST_REQUIRED
python cli.py check samples/reset_demo/top.sdc --netlist samples/reset_demo/top.v --top top   # SDC-151 etc.

# WF12 CI
python cli.py check rta/evidence/valid/minimal_valid.sdc --save-baseline base.json
python cli.py check rta/evidence/valid/minimal_valid.sdc --baseline base.json --gate STRICT      # PASS exit 0
python cli.py check v2.sdc --baseline base.json --gate STRICT                                  # FAIL exit 1

# WF13/14 API (start: python rta/api/api_server.py)
curl -X POST http://127.0.0.1:8501/api/analyze -H 'Content-Type: application/json' -d '{"sdc": "<paste>"}'
curl -X POST http://127.0.0.1:8501/api/analyze -H 'Content-Type: application/json' -d '{}'       # ok:true on empty input
```

---

## 11. Scope boundaries honored

- Migration not reopened; no regression, feature, UI, or animation work.
- No changes to correct Ṛta behavior; the five parity-defect classes remain protected by `test_parity_defect_classes.py` (23 tests, green).
- This is an evaluation document only — findings are recorded, not fixed.

*Acceptance evaluated 2026-08-14 on Ṛta v1.5.8. STOP after this report — no fixes performed.*
---

# P1 REMEDIATION SECTION (v1.5.8)

Status of the seven P1 corrections from §4. All verified against the live CLI,
API (port 8501), and webui surfaces on 2026-08-14.

| ID | Finding | Status | Regression test |
|----|---------|--------|-----------------|
| P1-1 | Consistent source locations | **PASS** | `test_p1_corrections.py::test_check_json_carries_line_field`, `test_rule_lines_populated_across_rules`, `test_absence_finding_explicitly_unknown` |
| P1-2 | Clock-relations mismatch vs missing | **PASS** | `test_p1_corrections.py::test_stats_equal_collections`, `test_cli_section_labels_match_semantics`, `test_cli_json_consistent` |
| P1-3 | Generator emits malformed `set_operating_conditions` | **PASS** | `test_p1_corrections.py::test_generate_without_operating_condition`, `test_generate_with_operating_condition_still_emits`, `test_engine_guard_empty_name` |
| P1-4 | Coverage CLI trust disclosure | **PASS** | `test_p1_corrections.py::test_text_disclosure`, `test_json_disclosure` |
| P1-5 | WebUI SDC-only coverage | **PASS** | `test_p1_corrections.py::test_sdc_only_category_coverage_present` |
| P1-6 | API empty-input 400 validation | **PASS** | `test_p1_corrections.py::test_missing_empty_sdc_returns_400`, `test_valid_sdc_still_200` |
| P1-7 | API stats.mismatches contradiction | **PASS** | `test_p1_corrections.py::test_stats_consistent_with_collections` |

## P1-1 — Consistent source locations

**Before:** line numbers appeared only on some rules (SDC-150, SDC-151-157) and
were absent on most checker findings (e.g. SDC-021 had no `:line`); info items
had no line field at all; JSON/API omitted the field for many rules.

**After:** every finding that maps to a concrete SDC command carries `line` in
CLI text (`[SDC-021] :5 ...`), JSON, and API. Absence findings (e.g. SDC-030
"no set_propagated_clock") explicitly remain `line: 0` — they are not fabricated.
Info items (SDC-111/112/119/120/126, count-based) resolve to the first matching
command line. Clock-relations warnings resolve to their `set_clock_groups` line.

**Test:** `test_p1_corrections.py` (SDC-021 line=5, SDC-002 line=1, SDC-030
line=0, SDC-111 resolves to first false-path line, JSON/API line field present).

**Result:** PASS. No rule IDs, severities, or messages changed.

## P1-2 + P1-7 — Clock relations consistency

**Before:** CLI printed `Mismatches: 0` followed by a `Mismatches:` section
listing 18 SDC-062 items; API returned `stats.mismatches: 0` while
`mismatches[]` contained 18 entries.

**After:** the engine result now separates three collections:
`mismatches` (warnings: SDC-060 style), `missing_constraints` (SDC-062
"missing clock-group constraint", labelled **Missing Constraints**), and
`advisories`. `stats.mismatches == len(mismatches)`,
`stats.missing == len(missing_constraints)`, and CLI labels match the
collections. CLI text, `--json`, HTML report, reporter, and webui all render
the split.

**Test:** `test_stats_equal_collections` proves
`stats.mismatches == len(mismatches)` and `stats.missing ==
len(missing_constraints)`; CLI label test proves the text matches semantics.

**Result:** PASS. `real_design_full.sdc`: 0 mismatches, 18 missing constraints
(3 generated pairs correctly synchronous, 21 pairs total unchanged).

## P1-3 — SDC generator must never generate broken SDC

**Before:** `python cli.py generate -d MY_SOC -c clk=10.0:sys_clk --derate
--output gen.sdc` emitted `set_operating_conditions -max` (empty value), which
its own `lint` failed on.

**After:** `generate_sdc` omits the operating-conditions section entirely when
no OC name is present (guard on `oper_cond_name.strip()`), and the CLI parser
now defaults `--operating-condition` to `None` instead of `""`. Generated SDC
contains no malformed commands, no empty values, and passes its own linter and
checker.

**Test:** `test_generate_without_operating_condition` (no OC line, no empty value,
lint-clean) plus `test_engine_guard_empty_name` and a generate -> lint -> check pipeline check.

**Result:** PASS. Verified live:
```
generate -d PIPELINE_SOC -c clk=10.0:sys_clk --derate -o gen.sdc
  -> lint: SDC file is lint-clean ; check: 0 errors
generate -d SOC2 -c clk=10.0:sys_clk -o gen2.sdc (no OC)
  -> set_operating_conditions count: 0
```

## P1-4 — Coverage CLI trust disclosure

**Before:** `rta coverage file.sdc` printed score/present/total with no
"coverage is NOT correctness" disclosure; JSON had no structured trust field.

**After:** CLI text prints the explicit line
`Coverage is NOT correctness - a fully covered design can still have timing
errors.` and JSON exposes
`"trust": {"coverage_is_not_correctness": true, "note": "..."}`.

**Test:** `test_text_disclosure` and `test_json_disclosure` (text + JSON).

**Result:** PASS. Existing disclosures elsewhere unchanged.

## P1-5 — WebUI SDC-only coverage

**Before:** the engine computed the 39-category SDC-only coverage but the API
payload and webui Coverage page hid it when no netlist was supplied.

**After:** `/api/analyze` payload includes `sdc_only_coverage`
(score/present/total/checked/missing) when no netlist is provided, and the
webui Coverage page renders it with the explicit "Coverage is NOT
correctness" callout, distinguishing SDC constraint coverage from
design-aware/netlist coverage and preserving the NETLIST_REQUIRED disclosure.

**Test:** `test_sdc_only_category_coverage_present`.

**Result:** PASS.

## P1-6 — API empty-input validation

**Before:** `POST /api/analyze` with `{}` returned `200 ok:true` with an empty
analysis; same for missing/whitespace SDC.

**After:** `_require_sdc()` rejects missing / empty / whitespace-only SDC with
`400` and a deterministic structured error `{"ok": false, "error":
{"code": "...", "message": "...", "hint": "..."}}` for `/api/analyze`,
`/api/lint`, and `/api/convert`. Optional fields (netlist, top, options)
remain legitimate empty.

**Test:** `test_missing_empty_sdc_returns_400` (parametrized over missing /
empty / whitespace-only SDC for analyze, lint, convert) plus
`test_valid_sdc_still_200`.

**Result:** PASS. Valid requests behave exactly as before.

---

## Post-remediation verification

- Full pytest suite: **886 passed** (863 baseline + 23 new P1 tests), 0 failures.
- Focused P1 + parity + preprocess: 52 passed.
- Smoke: 19/19 (test_release_smoke).
- Comprehensive: cleanroom 17/17, CLI audit 16/16, packaging probe OK.
- Parity harness re-run: 200/200 files identical to audit baseline except the
  additive `missing` count in clock_relations (the P1-2 fix); corners parity
  unchanged (pre-existing branding-class difference).
- Test Drive on `real_design_full.sdc`: 7 clocks / 21 pairs / 25 constraints /
  4+4 I/O / 5 FP / 5 MCP / 2 groups / 82.1% (32/39) / 0 errors — contract intact.
- Generator -> lint -> check pipeline: PASS.

*Sprint constraint honored: no UI redesign, no colors, no animations, no AI,
no new features, no architecture change, migration not reopened, frozen backup
untouched, existing trust disclosures intact.*
