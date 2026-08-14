# Ṛta — Full SDC Validator Parity Audit

**Status:** AUDIT COMPLETE — no implementation performed
**Scope:** Prove every meaningful capability of the original SDC Validator exists and behaves equivalently in Ṛta.
**Source of truth:** original SDC Validator as of commit `ccc90d8` (v1.3.0, flat pre-migration layout, extracted to `_orig_full`) + the original ZIPs under `D:\freebuff`.
**Corpus:** the complete `rta/evidence/` tree — **200 SDC files** (the original's own corpus plus Ṛta-era additions: valid, golden, invalid, malformed, edge_cases, clock_relations, constraint_interactions, design_coverage, golden_semantic, large_design, netlist_aware, production_hardening, readiness, readiness_diff, reference_designs, regression, timing_exceptions, io_constraints).
**Method:** a paired harness ran the identical deterministic battery (check, coverage, clock_relations, converter, linter) on both implementations over all 200 files, plus diff / generate / corners / custom-rules / MMC / reporter / batch batteries, then compared normalized JSON. Every difference was then investigated to its root cause with per-file evidence. CLI surfaces, exit codes, and rule registries were compared directly.

---

## Executive summary

The migration is **behavior-preserving and additive**. On the deterministic core:

| Metric (200 files) | Exact match | Differences | Notes |
|---|---|---|---|
| `check` | 92 | 108 | every diff = Ṛta-additive finding OR original-parser bug fixed (see §5) |
| `coverage` | 193 | 7 | all 7 = original counting commands/values inside comments or missing continuations |
| `clock_relations` | 168 | 32 | all 32 = original's relationship-inference bugs fixed (generated-clock master chains, declared groups) |
| `converter` | 166 | 34 | all 34 = original comment/continuation/virtual-clock bugs fixed; 1 original crash |
| `linter` | **200** | 0 | exact parity |

- **Rule registry:** all **95 original rule codes** exist in Ṛta with **identical severity** (0 missing, 0 severity changes). Ṛta adds **24 new codes** (SDC-046–049, 055–059, 064–070, 150–157) — all enhancements.
- **CLI:** all **12 original subcommands** exist in Ṛta (superset: +`whats-new`). **Exit codes identical** (0 clean / 1 findings / 2 usage or IO).
- **Batteries:** generate (identical except the "SDC Tools" vs "Ṛta" banner), corners (identical), custom-rules (identical), batch (identical), MMC (identical except the same banner), reporter (same template; Ṛta adds HTML escaping + line-number provenance), diff (Ṛta **more** complete: detects clock-period changes the original misses).
- **Zero regressions (class D) and zero missing capabilities (class E)** were found after investigation. Every apparent "regression" traced to an original parser bug that Ṛta fixes, or to a documented intentional behavior.

The **one hard failure in the original**: it **crashes** (unhandled `ValueError`) on a valid file whose *comment* merely mentions `set_input_delay` — Ṛta handles the same file correctly.

---

## Classification legend

| Code | Meaning | Count of distinct root causes found |
|---|---|---|
| **A** | Exact parity | the baseline (most files/metrics) |
| **B** | Ṛta intentional enhancement | new rules, variable resolution, diff completeness, readiness/interactions/API/netlist/CI, dedup |
| **C** | Original behavior intentionally superseded (original bug fixed) | comment parsing, continuation joining, scientific notation, relationship inference, re-coded findings, crash robustness |
| **D** | Migration regression | **0** |
| **E** | Missing capability | **0** |
| **F** | Unable to verify | **0** after investigation (1 harness artifact, resolved) |

---

## 1. Capability-by-capability audit (the requested 35-item list)

> "A feature is complete only when its actual workflow works." For each row: how the original implements it, how Ṛta implements it, the deterministic input used, expected vs actual output, parity status, test coverage, known limitation, required action.

| # | Feature | Original impl | Ṛta impl | Parity | Test coverage | Known limitation / action |
|---|---|---|---|---|---|---|
| 1 | **SDC checker** | `checker.py::check_sdc` (naive line regex, comments NOT stripped, continuations NOT joined) | `rta/engine/rules/checker.py::check_sdc` + `preprocess_sdc` (comments stripped, continuations joined, bracket-balanced, diagnostics on unclosed group) | **A/B/C** | `test_test_drive_parity.py`, 78 preprocess tests | Original fires false findings from command keywords in comments and misreads multiline commands; Ṛta fixed both (§5.1, §5.2). **Action:** none — keep the parity regression test. |
| 2 | **All checker rules** | 95 codes in `rules_registry.py` (11 error, 6 fatal, 38 warning, 40 info) | same 95 codes, **identical severity**; +24 new codes | **A + B** | `rules_diff` reproduced in this audit; `rta tests` | All original codes preserved. **Action:** none. |
| 3 | **Clock analysis** | `clock_relations.py::parse_clocks_from_sdc` | same logic in `rta/engine/analysis/clock_relations.py` | **A** | 200-file corpus, clock counts equal on every file where both parse | See #6 for the relationship-inference divergence. |
| 4 | **Generated clocks** | parsed via naive `create_generated_clock` regex | same + continuation-joined parsing | **A/C** | converter `generated` count matched on 199/200 files; rd03/s02 verified | Original misses `-source` on continuation lines (false SDC-003) and mis-codes undefined `-master_clock` as SDC-003; Ṛta uses the correct SDC-047 (§5.4). |
| 5 | **Virtual clocks** | naive heuristic — marks any `create_clock` whose first line (truncated by `\`) lacks a port as virtual | correct: joins continuations before classifying | **C** | `rd01`, `multiline_tcl`, `c03`, `c20`, `unterminated_brace` all verified | Original produces false "virtual" clocks on multiline `create_clock`; Ṛta correct. **Action:** none. |
| 6 | **Clock relationships** | `infer_relation` + `_find_mismatches`; cannot trace `-master_clock` chains, cannot see declared groups on continuation lines | same API, fixed inference (master-chain tracing, group-aware) | **C** (32/200 differ — all original bugs) | `generated_clock_chain`, `full_featured`, `three_clocks_mixed` file comments assert "0 mismatches expected" — Ṛta delivers; original reports false SDC-062 | e.g. `full_featured.sdc`: original calls `clk_sys` vs `clk_sys_div2` asynchronous; Ṛta correctly synchronous. **Action:** none. |
| 7 | **Clock groups** | `_parse_existing_groups` — misses groups written across `\` continuations (false SDC-031) | continuation-aware | **A/C** | `multi_clock_sync_groups`, `c15`, `s03`, `malformed/conflicting_constraints` | Original false SDC-031 on valid files; Ṛta correct. |
| 8 | **Input delays** | `set_input_delay` regex; reads values out of comments; no TCL variable resolution | variable-resolved, comment-stripped | **A/B/C** | `HR04` (orig reads "064" from a comment → false SDC-008), `RDIF05` (Ṛta resolves `$PERIOD` and catches a real SDC-008 the original misses) | **Action:** none. |
| 9 | **Output delays** | same naive approach | same fixes | **A/B/C** | `RDIF04`: original misreads scientific notation `1.0e1` as `1.0` (false SDC-009); Ṛta parses `10.0` correctly | **Action:** none. |
| 10 | **False paths** | parsed per line | continuation-joined; covered by SDC-020/150/152/155 | **A/B** | `real_design_full` (5 false paths on both after fixture repair — see TEST_DRIVE_PARITY_INVESTIGATION.md) | **Action:** none. |
| 11 | **Multicycle paths** | per-command check (fires SDC-021 per `-setup` even when the matching `-hold` exists in the next command) | pairs `-setup`/`-hold` across commands (documented intentional) | **A/C** | `CI14` (setup+hold present: original fires SDC-021, Ṛta correctly silent), `multicycle_no_hold` (both fire) | Original false positives. **Action:** none. |
| 12 | **Uncertainty** | SDC-022/023 in both, identical triggers | identical | **A** | `c21`, `rd03` verified | — |
| 13 | **Timing derates** | SDC-032/033/040–043 | identical + SDC-156/157 (AOCV/POCV methodology, new) | **A + B** | corpus matched | — |
| 14 | **Case analysis** | SDC-011 value check; regex reads "on" out of comments | SDC-011 identical + SDC-049 (contradiction, new) + SDC-154 (scan mode, new) | **A/B/C** | `HR06`: original fires SDC-011 with value "on" (from comment text); Ṛta fires SDC-049 with the correct 0-vs-1 contradiction | Original false positive. |
| 15 | **Coverage** | `coverage.py::parse_sdc_coverage` — per-category presence | same API in `rta/engine/analysis/coverage.py` | **A/C** | 193/200 exact; 7 diffs all from original comment/continuation miscounts | e.g. `multiline_continuation_content.sdc`: original under-counts (5 vs Ṛta 7 present); `comment_mentions_commands.sdc`: original over-counts (8 vs 7). |
| 16 | **Readiness** | **does not exist** in the original | `rta/engine/trust/` readiness engine (BLOCKED / REVIEW_REQUIRED / READY, baseline & gate) | **B (new)** | `readiness/`, `readiness_diff/` evidence + tests | Not a parity gap — an original absent capability Ṛta ships. |
| 17 | **Constraint interactions / conflicts** | only what `constraint_diff.py` detects | `rta/engine/analysis/` interactions module (duplicates, overrides, contradictions, need-sta) + SDC-046–049, 064–070 | **B (new)** | `constraint_interactions/CI*` evidence + tests | Not a parity gap. |
| 18 | **SDC generator** | `generator.py::generate_sdc(SDCParams)` | identical code in `rta/tools/generate/generator.py` | **A** | byte-for-byte identical output (1320 chars) except the "generated by SDC Tools" vs "generated by Ṛta" banner | **Action:** none. |
| 19 | **SDC linter** | `linter.py::lint_sdc` | identical code in `rta/tools/lint/linter.py` | **A** | **200/200 exact** | — |
| 20 | **Converter** | `converter.py::parse_sdc` | identical code in `rta/tools/convert/converter.py` (uses `preprocess_sdc`) | **A/C** | 166/200 exact; 34 diffs all original-parser bugs (comments, continuations, virtual heuristic) + 1 original crash | **Action:** none. |
| 21 | **Corner Manager** | `corner_manager.py` presets | identical code in `rta/tools/corners/corner_manager.py` | **A** | preset names + `corner_to_dict` identical | — |
| 22 | **MMC** | `mmc.py` (`generate_corner_sdcs`, `check_sdc_multi`, `create_corner_zip`) | identical code in `rta/tools/corners/mmc.py` | **A** | generated corner SDCs byte-identical modulo banner | — |
| 23 | **Diff** | `constraint_diff.py` | identical code in `rta/engine/diff/constraint_diff.py` | **A/B** | CHG-* rule codes identical; Ṛta additionally detects CHG-CK-006 (clock period change) on `full_featured.sdc` (3 vs 2 changes) | Original misses clock-period changes in some layouts. **Action:** none. |
| 24 | **Reports** | `reporter.py` | identical code in `rta/tools/report/reporter.py` | **A/B** | same `_page/_badge/_table` template; Ṛta adds HTML escaping + `L{line}` provenance | — |
| 25 | **CI** | **does not exist** (original `check` has no baseline/gate flags) | `--save-baseline/--baseline/--gate/--gate-policy/--netlist/--top` + JUnit/JSON outputs | **B (new)** | `readiness_diff/`, `production_hardening/` tests | Not a parity gap. |
| 26 | **Custom rules** | `custom_rules.py` (present/absent/count/value/regex conditions) | identical code in `rta/engine/policy/custom_rules.py` | **A** | same ruleset YAML → identical findings on 6-file subset | — |
| 27 | **Test Drive** | original app Test Drive tab | workspace Test Drive | **A** | see `TEST_DRIVE_PARITY_INVESTIGATION.md` — after fixture repair, every metric matches the original | Original's numbers were only correct by accident of its per-line parsing. |
| 28 | **CLI** | 12 subcommands: check, generate, diff, corners, analyze, rules, web, coverage, report, lint, convert, batch | same 12 + `whats-new` | **A + B** | subcommand surface + exit codes (0/1/2) identical | — |
| 29 | **API** | **does not exist** (Streamlit-only) | `rta/api/api_server.py`: /api/health, /design, /rules, /analyze, /lint, /convert, /generate, /corners, /mmc, /mmc/zip, /feedback | **B (new)** | API tests | Not a parity gap. |
| 30 | **Batch processing** | `batch_runner.py::batch_check/batch_lint/batch_report` | identical code in `rta/tools/batch/batch_runner.py` | **A** | `batch_check(valid/)` → identical summary (4 total / 4 ok / 0 errors) | — |
| 31 | **Export / download** | Streamlit download buttons | workspace webui download buttons (6 added in the download-button parity round) | **A** | manual + browser checks | — |
| 32 | **Error handling** | unhandled exceptions on comment keywords; crashes | diagnostics instead of silent merges; no crashes on the corpus | **B/C** | `s01_io_delay_undefined_clock.sdc`: original **crashes** (`float('.')` from a comment); Ṛta returns SDC-046 + SDC-030 | **Action:** none (original crash is its own bug). |
| 33 | **Malformed SDC handling** | naive per-line behavior | bracket/brace-balance diagnostics, continuation diagnostics | **A/B/C** | `malformed/`, `edge_cases/`, `golden/10_malformed/` | Original miscounts on unterminated/conflicting inputs. |
| 34 | **Netlist handling** | **does not exist** | `design_context.py` + netlist-aware rules (SDC-055/056, 151–155), `--netlist/--top` | **B (new)** | `netlist_aware/` evidence + tests | Not a parity gap. |
| 35 | **Additional original capability discovered** | original README "13 Major Features"; app has 10 tabs (Checker, Generator, MMC Manager, MMC Gen, Analyzer, Clock Relations, Coverage, Linter, Converter, Rules) | all 10 tabs present + Interactions + Readiness; webui SPA with results tools | **A + B** | tab inventory compared | — |

---

## 2. Rule registry comparison (exact numbers)

| | Original | Ṛta |
|---|---|---|
| Total rules | 95 | 119 |
| Unique codes | 95 | 119 |
| Codes only in original | — | **0** |
| Codes only in Ṛta | — | **24**: SDC-046, 047, 048, 049, 055, 056, 057, 058, 059, 064, 065, 066, 067, 068, 069, 070, 150, 151, 152, 153, 154, 155, 156, 157 |
| Severity changes on shared codes | — | **0** |
| Severity distribution | 11 error / 6 fatal / 38 warning / 40 info | 15 error / 6 fatal / 53 warning / 45 info |
| Rule modules | checker 66, constraint_diff 21, mmc 4, clock_relations 4 | checker 78, constraint_diff 21, mmc 4, clock_relations 4, **design_context 5, design_coverage 3, constraint_interactions 4** (new modules) |

---

## 3. CLI surface and exit codes

| Subcommand | Original | Ṛta |
|---|---|---|
| check, generate, diff, corners, analyze, rules, web, coverage, report, lint, convert, batch | ✅ | ✅ |
| whats-new | — | ✅ (new) |
| `check` flags | `--json --junit --output --verbose --custom-rules --format` | all of the above + `--netlist --top --save-baseline --baseline --gate --gate-policy` (new) |
| Exit codes | 0 clean / 1 findings / 2 usage-or-IO | **identical** (verified on clean, invalid, missing-file, bad-subcommand) |

---

## 4. Batteries (non-file-level capabilities)

| Battery | Original | Ṛta | Verdict |
|---|---|---|---|
| `generate_sdc(SDCParams)` | 1320 chars, "generated by SDC Tools" banner | identical, "generated by Ṛta" banner | **A** (banner is branding) |
| `diff` (period 10.0→12.5) | 2 changes (GEN-001/002) — misses the clock-period change | 3 changes (+CHG-CK-006) | **B** (Ṛta more complete) |
| corners presets | 4 presets | identical | **A** |
| custom-rules (10-rule YAML) | identical findings | identical | **A** |
| MMC `generate_corner_sdcs` | byte-identical per-corner SDC | byte-identical | **A** (modulo banner) |
| reporter check HTML | same template | same + escaping + line provenance | **A/B** |
| batch `batch_check(valid/)` | 4 total / 4 ok / 0 err | identical | **A** |

---

## 5. Root-cause analysis of every difference class

All 108 `check`-level differences, 7 coverage, 32 clock-relations, and 34 converter differences reduce to **five original-implementation defects**, each fixed in Ṛta, plus Ṛta's additive rules:

### 5.1 Original does not strip comments (most common)
The original's `_grab`/regexes operate on raw text including comments, so a comment that merely *mentions* a keyword produces findings:
- `comment_mentions_commands.sdc`, `c19`: `create_clock` in a comment → false SDC-002 duplicate-clock, false SDC-008.
- `HR04_unconstrained_io.sdc`: comment text `SDC-064` → original reads delay "064" → false SDC-008 ("064ns ≥ 10ns").
- `HR06_contradictory_case.sdc`: comment `set_case_analysis on the same pin` → original fires SDC-011 invalid value "on".
- `s01_io_delay_undefined_clock.sdc`: comment `set_input_delay references a clock…` → original regex captures the sentence-ending "." → **`float('.')` crash**.
- Converter/coverage over-count on the same files (2 clocks, 2 input delays, 3 case_analysis, 8 coverage items).

Ṛta's `preprocess_sdc` strips comments before all parsing. **Class C** (original bug superseded). **Verdict: Ṛta correct.**

### 5.2 Original does not join Tcl `\` continuations
- `rd03_generated_hierarchy.sdc`: `create_generated_clock -name div2 \` with `-source` on the next line → original fires SDC-003 "missing -source" (false); Ṛta sees the `-source`.
- `multiline_continuation_content.sdc`, `c04`, `c20`: `-min` on a continuation line → original fires SDC-028/029 "no -min" (false).
- `multi_clock_sync_groups.sdc`: `set_clock_groups -asynchronous \` → original fires SDC-031 "missing exclusion type" (false).
- `rd01`, `multiline_tcl`, `c03`, `unterminated_brace`: truncated `create_clock` → original marks the clock **virtual** (false).
- `mcp.sdc`/`HR07`: continuation-joined multicycle counts 2 vs original 4; `conflicting_constraints.sdc`: 1 vs 2 false paths.

**Class C. Verdict: Ṛta correct** (this was also the root cause repaired in `TEST_DRIVE_PARITY_INVESTIGATION.md`).

### 5.3 Original misparses numeric formats and cannot resolve variables
- `RDIF04_cur.sdc`: `-period 1.0e1` → original reads "1.0" (period) and "1.1" (delay) → false SDC-008/009; Ṛta parses 10.0/11.0 → correct SDC-008 only.
- `RDIF05_base.sdc`: `set PERIOD 10.0` + `-period $PERIOD` + delay 11.0 → original sees no numbers → **misses the violation**; Ṛta resolves the variable → SDC-008 (correct).
- `c08_var_period.sdc`, `tcl_variables.sdc`: same pattern — Ṛta catches what the original misses.

**Class B/C. Verdict: Ṛta correct (both directions).**

### 5.4 Original mis-codes findings; Ṛta uses dedicated codes
- Undefined `-master_clock` → original emits SDC-003 ("missing -source" with a message about undefined master); Ṛta emits **SDC-047**.
- Undefined clock in `set_input_delay -clock ghost_clk` → original fires SDC-008 (delay-vs-period against a nonexistent clock); Ṛta emits **SDC-046** (the accurate finding).
- Contradictory `set_case_analysis` → original fires SDC-011 (invalid value); Ṛta emits **SDC-049**.
- Clock on a data port → original fires SDC-024 (no groups, from a comment) or nothing; Ṛta emits **SDC-007**.

**Class C (re-coded, more specific). Verdict: Ṛta correct.**

### 5.5 Original clock-relationship inference is incomplete
- `generated_clock_chain.sdc`: original cannot trace `div2 → div4` master chains and reports `clk/div4` asynchronous (SDC-062 mismatch); Ṛta traces the chain → synchronous, 0 mismatches. File comment: "Expected: all pairs synchronous, 0 mismatches".
- `three_clocks_mixed.sdc`: original reports 2 SDC-062 mismatches despite explicitly declared groups; Ṛta: 0. File comment: "All declared correctly → 0 mismatches expected."
- `full_featured.sdc`: original calls `clk_sys` vs `clk_sys_div2` asynchronous; Ṛta: synchronous.
- `real_design_full.sdc`: 21 vs 18 mismatches (the 3 Ṛta-correct pairs are the generated-clock pairs).
- Per-pair SDC-062 info: original emits one per pair (18 rows); Ṛta dedups to 1 (same code set).

**Class C. Verdict: Ṛta correct.**

### 5.6 Ṛta-additive findings (class B — intentional enhancements)
- New rules: SDC-046–049, 055–059, 064–070 (duplicates, overrides, contradictions, undefined references, max/min conflicts), SDC-150–157 (rationale comments, reset trees, scan mode, AOCV/POCV methodology).
- Whole new capabilities absent from the original: readiness, constraint interactions, netlist/design context, HTTP API, CI baseline/gate, `whats-new`.
- Two new UI tabs (Interactions, Readiness); webui SPA; 6 download buttons added for parity with the original's export behavior.
- Diff detects CHG-CK-006 the original misses; dedup of per-pair infos; reporter HTML escaping + line provenance.

---

## 6. Regression tests protecting this audit

| Test | What it pins |
|---|---|
| `rta/tests/test_test_drive_parity.py` (6 tests) | semantic counts on `real_design_full.sdc`: 7 clocks / 21 pairs / 25 constraints / 5 FP / 2 groups / 82.1% (32/39), checker rule IDs |
| `rta/tests/test_sdc_preprocess.py` (78 tests) | comment stripping, continuation joining, unclosed bracket/brace diagnostics |
| `rta/tests/test_parity_defect_classes.py` (23 tests) | permanent protection for the five original defect classes: comments (no false SDC-002/008/011, no crash), continuations (no false SDC-003/028/029/031 + correct counts), numeric/variable parsing (scientific notation + `$VAR` resolution → correct SDC-008), dedicated classification (SDC-046/047/049/007 never revert to SDC-008/003/011/024), clock-relation inference (zero false SDC-062 on `generated_clock_chain`, `three_clocks_mixed`, `full_featured`; exactly 18 mismatches on `real_design_full`) |
| Full suite | **863 passed** (826 → 840 in the parity sprint → 863 with defect-class regression protection) |
| This audit's harness (`_audit/harness.py` + `compare2.py`) | paired 200-file battery, reproducible on demand; re-run after the hardening sprint is byte-identical to the audit baseline |

---

## 7. Parity score

```
Exact parity (A):         200/200 linter · 193/200 coverage · 168/200 clock_relations
                           166/200 converter · 92/200 check (raw); after classifying the
                           differences: every non-matching file is either an original
                           parser bug now fixed (C) or a Ṛta-additive finding (B).
Intentional differences (B): 24 new rule codes; variable resolution; diff completeness;
                           readiness/interactions/netlist/API/CI; UI tabs; reporter/dedup.
Missing (E):              0 — all 95 original rules, 12 CLI subcommands, 10 UI tabs,
                           all batteries present.
Regressions (D):          0 — no original capability lost or degraded.
Unverified (F):           0 — the single run-1 diff anomaly was traced to a harness
                           path-conversion artifact; direct reruns are deterministic.
```

**Bottom line:** on valid, well-formed input the two implementations are semantically identical; where they differ, Ṛta is provably more correct (original comment/continuation/numeric/relation bugs fixed) or intentionally additive. The original's one hard failure mode (crash on comment keywords) does not exist in Ṛta.

---

## 8. Recommended implementation order for remaining gaps

There are **no functional gaps** to implement — the audit found no missing capability and no regression. The only recommended work, in priority order:

1. **Add the bug-class regression tests** (§6 recommendation) — pin that the original's five defect classes never reappear in Ṛta. Lowest cost, locks in the audit result.
2. **Keep the paired harness** as a CI-adjacent tool (`_audit/harness.py`) — it is the fastest way to re-verify parity after any future engine change; consider moving it into `rta/tools/` or `rta/evidence/` if desired.
3. **Document the five original defects** in the README/engineering docs as "behavioral differences from the legacy validator" so the intentional (C) divergences are visible to users who compare against the old tool.
4. Optional: add the same comment/continuation corpus assertions for the converter and coverage modules (not just the checker), since 5.1/5.2 affect all three.

**Explicitly out of scope (per the sprint constraints):** no UI redesign, no new product features, no refactor of unrelated modules, no modification of the frozen backup (none exists in-repo), and no normalization of numbers to force parity.

---

## 9. Evidence inventory

| Artifact | Path |
|---|---|
| This document | `docs/migration/FULL_SDC_VALIDATOR_PARITY_AUDIT.md` |
| Prior investigation (fixture root cause) | `docs/migration/TEST_DRIVE_PARITY_INVESTIGATION.md` |
| Original implementation sandbox | `D:\freebuff\_orig_full` (from `ccc90d8`, v1.3.0) |
| Original ZIPs | `D:\freebuff\sdc-tools-main` history; original `.zip` archives |
| Paired harness + comparators | `_audit/harness.py`, `_audit/compare2.py`, probes 1–7 |
| Raw paired results | `_audit/orig2.json`, `_audit/rta2.json` |

*Audited 2026-08-14. No implementation performed in this sprint.*
