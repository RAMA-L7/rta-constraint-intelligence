# PHASE 5 — Semantic SDC Correctness, Conflict Analysis & Undefined-Reference Validation

Date: 2026-08-04
Status: **COMPLETE**

---

## 1. Multi-Agent Execution Summary

Phase 5 was run as a supervised multi-agent effort. Agent conclusions were not merged blindly — every proposed rule required independent evidence + a minimal reproducer before implementation.

| Subagent | Responsibility | Findings | Disagreements & resolution |
|---|---|---|---|
| **A — SDC/STA Semantics Researcher** (researcher-docs) | Authoritative behavior for 14 SDC commands: undefined refs, `-add_delay`, duplicates, overrides | `-clock` to a nonexistent clock → tool error/warning (statically detectable); repeated `set_input_delay` without `-add_delay` **replaces**; duplicate `create_clock` name → duplicate; `set_case_analysis 0` then `1` = override (statically detectable); false_path+max_delay and multicycle repeats = **netlist-dependent** | (web researcher returned no usable citations; docs agent's evidence was accepted and cross-checked against the Accellera/standard behavior) |
| **B — Code/Architecture Investigator** (code-searcher) | Trace parsing → semantic flow, rule infra, safe insertion points | Checker already has `period_map`, `defined_clock_names` needs building; rule numbering free at **SDC-046..049**; `Issue` dataclass is keyword-constructed everywhere (safe to extend); UI renders `i.line` in Test Drive | None — confirmed the P0 fallback bug live in `checker.py` |
| **C — Adversarial QA / Benchmark Engineer** (this report's suites) | Minimal reproducers, false-conflict hunting, negative tests | Confirmed 5 gaps (see §4-8); 13 adversarial break-attempts; caught 1 test-expectation error (`[get_clocks {a b c}]` IS resolvable) | My own adversarial test claimed `{a b c}` was netlist-dependent — **corrected**: clock NAMES are always statically resolvable; only ports/pins/all_clocks/wildcards are netlist-dependent |
| **D — Implementation** (supervisor) | Implement only supervisor-approved confirmed rules | Implemented SDC-046..049, `line2` provenance, `_clock_ref()` classifier | — |
| **E — Independent Reviewer** (code-reviewer) | Challenge the diffs | Found a **real false positive**: `-clock [get_clocks *]` parsed to `['*']` → SDC-046 fired on a wildcard (netlist-dependent). Also flagged dead code in SDC-048 block | **Accepted and fixed**: wildcard guard added to the `get_clocks` bracket path in `_clock_ref()`; SDC-048 dead branch removed; new adversarial + production tests lock it in |

---

## 2. Baseline (before changes)

| Suite | Result |
|---|---|
| pytest `tests/` | 403/403 PASS |
| Golden parser benchmark | 22/22 |
| UI benchmark | 33/33 |
| State isolation | 6/6 |
| Full benchmark corpus | 61 files |
| Local Streamlit | HTTP 200 |

---

## 3. Authoritative Semantic Table

Established from SDC/Tcl semantics research (used to classify every proposed rule):

| Command | Referenced objects | Repeated commands | Genuine conflict? | Statically detectable? |
|---|---|---|---|---|
| `create_clock` | source port/pin | same name → redefinition/duplicate | same name, different period | **YES** (duplicate name) |
| `create_generated_clock` | `-source`, `-master_clock` | independent per name | `-master_clock` undefined | **YES** (undefined master) |
| `set_input_delay`/`set_output_delay` | ports, `-clock` | replaces unless `-add_delay`; `-max`/`-min`/`-rise`/`-fall` are distinct | `-clock` undefined | **YES** (undefined clock) |
| `set_clock_uncertainty` | `[get_clocks ...]` | `-setup`/`-hold` distinct | undefined clock ref | **YES** |
| `set_clock_groups` | `[get_clocks ...]` lists | multiple groups legal | undefined clock in group | **YES** |
| `set_false_path` / `set_max_delay` | `-from/-to/-through` | legal coexistence | same path both — **requires netlist** | **NO** |
| `set_multicycle_path` | paths, `-setup`/`-hold` | setup/hold independent | path overlap — **requires netlist** | **NO** |
| `set_case_analysis` | pins/ports | later value overrides | 0 then 1 on same pin | **YES** |
| `set_load`/`set_input_transition`/`set_driving_cell` | ports | independent, accumulate | — | N/A |

**Classification scheme adopted**: `DEFINITELY UNDEFINED` (clock names never declared — statically provable) vs `POTENTIALLY NETLIST-DEPENDENT` (`get_ports`, `get_pins`, `all_*`, wildcards) vs `VALID` vs `UNRESOLVABLE BY STATIC SDC-ONLY ANALYSIS` (path-overlap conflicts).

---

## 4. Undefined-Reference Results (highest priority)

**P0 confirmed + fixed.** Reproducer:
```
create_clock -name clk_a -period 10.0 [get_ports clk]
set_input_delay -max 12.0 -min 0.5 -clock nonexistent_clk [get_ports data_in]
```
Before: SDC-008 fired against **clk_a** (silent wrong analysis — the Phase-3-identified risk). After: **SDC-046** fires, **no SDC-008 fallback**.

Covered references:
- `set_input_delay`/`set_output_delay -clock` → **SDC-046 (error)** — no silent fallback
- `create_generated_clock -master_clock` → **SDC-047 (warning)**
- `set_clock_groups` clock names → **SDC-048 (warning)** — only bare names; wildcards/skips handled

The reference classifier (`_clock_ref`) distinguishes resolvable clock names from netlist-dependent tokens:
- `-clock nonexistent_clk` → resolvable, undefined → flag
- `-clock [get_clocks clk_a]` / `{a b}` → resolvable names → check each
- `-clock [get_ports clk]`, `[get_pins ...]`, `[all_clocks]`, `*`, `{clk* sync*}` → **netlist-dependent → never flagged**

---

## 5. Duplicate-Constraint Results

Per the semantic table, **repeated `set_input_delay` without `-add_delay` replaces (override) — NOT a conflict**. `-max` vs `-min`, `-rise` vs `-fall`, different clocks, and `-add_delay` accumulation are all **distinct legal constraints**. No duplicate rules were implemented — the analyzer deliberately does NOT flag them (false-positive risk is higher than the value). Existing SDC-002 still covers duplicate `create_clock` names.

---

## 6. Conflict/Override Results

Only **one** high-confidence conflict was implemented:

**SDC-049 — Contradictory `set_case_analysis`** on the same object with two different values (e.g. `0` then `1`). Warning with **both source lines** (`line` = current, `line2` = earlier conflicting constraint). Backed by evidence: a pin cannot be both 0 and 1 in one mode; the later value silently overrides the earlier.

Deliberately NOT flagged (documented, not errors): `set_max_delay` + `set_false_path` on overlapping paths (netlist-dependent), multicycle setup/hold overlaps (netlist-dependent), I/O delay value differences (override semantics).

---

## 7. Timing-Exception Results

No timing-exception conflict rules were implemented — per evidence, resolving `-from/-to/-through` overlap requires a netlist. Classified as `NETLIST-DEPENDENT` / `UNRESOLVABLE BY STATIC ANALYSIS` and documented as out of scope for this phase.

---

## 8. False Positives Discovered During Development (mandatory section)

| # | False positive | Discovery | Resolution |
|---|---|---|---|
| 1 | My adversarial test claimed `[get_clocks {a b c}]` is netlist-dependent | QA re-derivation | **Test error**: clock NAMES are always statically resolvable; corrected the test to assert SDC-048 fires for `a`,`b` and NOT for declared `c` |
| 2 | **SDC-046/047 fired on `-clock [get_clocks *]` / `-master_clock [get_clocks *]`** | Independent reviewer | **Real production bug**: `parse_collection` yielded `['*']` and the wildcard guard only existed on the bare-ref path. Fixed in `_clock_ref()`; locked in with adversarial + production tests |
| 3 | SDC-048 dead `net_dep` branch (unreachable `continue`) | Independent reviewer | Removed |
| 4 | `SDC-046: line 23` comment vs actual line 27 in realistic file | Self-check | Comment corrected |

---

## 9. Architecture

No large refactor. Semantic analysis lives in `checker.py` and reuses the Phase-3/4 shared preprocessor output (already normalized: comments stripped, continuations joined, variables resolved, provenance attached). Two small additions:

1. **`_clock_ref(stmt, flag)`** — a single reference classifier (names + netlist-dependent flag) reused by SDC-046/047/048 and the SDC-008/009 comparison.
2. **`Issue.line2`** — optional second source line for conflict findings, rendered by `reporter.py` (`L{a} ↔ L{b}`) and the Test Drive UI (`(conflicts with line N)`).

No O(N²) cross-comparison: SDC-049 uses a dict keyed by object; the undefined-ref checks are per-command lookups against a set.

---

## 10. Rules Added

| Rule | Severity | Purpose | Evidence |
|---|---|---|---|
| **SDC-046** | error | `-clock` in `set_input_delay`/`set_output_delay` references an undefined clock (replaces silent tightest-clock fallback) | Tools error/warn on broken clock refs; static clock names are provably undefined |
| **SDC-047** | warning | `create_generated_clock -master_clock` undefined | Generated clock period/phase undefined without a resolvable master |
| **SDC-048** | warning | `set_clock_groups` names an undefined clock | Grouping a nonexistent clock silently excludes nothing |
| **SDC-049** | warning | Contradictory `set_case_analysis` on one object (dual-line provenance) | A pin cannot be both 0 and 1 in one mode |

All registered in `rules_registry.py` (module `checker`, version `1.4.0`) so the Rules UI/reports document them.

---

## 11. Golden Semantic Benchmark

`benchmarks/golden_semantic/` — 9 deterministic cases, machine-readable `manifest.json`, runner `run_golden_semantic.py` → `results.json`.

| Group | Cases | Expected |
|---|---|---|
| undefined_references | s01 (io delay), s02 (master), s03 (group) | SDC-046 / 047 / 048 |
| case_analysis | s04 | SDC-049 with dual line |
| valid_multiple_constraints | s05 (max/min), s06 (netlist refs), s07 (add_delay+modes) | **no** findings |
| realistic | s10 (one defect), s11 (three defects) | exact intended findings only |

**Result: 9/9 PASS.**

---

## 12. Full Regression (all executed)

| Suite | Result |
|---|---|
| `pytest tests/ -q` | **409/409 PASS** (403 baseline + 6 new semantic tests) |
| Parser golden `run_golden.py` | **22/22** (unchanged — no regression) |
| Semantic golden `run_golden_semantic.py` | **9/9** |
| Adversarial semantic QA | **13/13** |
| Full benchmark corpus | 61 files |
| Preprocessor stress | 21/21 |
| Realistic corpus | 2/2 |
| Realistic defect verification | PASS |
| Security | 5/5 |
| UI benchmark | **33/33** |
| State isolation | **6/6** |
| Local Streamlit smoke | HTTP 200, no errors |

---

## 13. Performance

Semantic checks use set/dict indexing (no N² comparisons).

| Size | check_sdc time | scaling |
|---|---|---|
| ~100 constraints | 17 ms | — |
| ~1,000 constraints | 66 ms | x3.8 |
| ~10,000 constraints | 1,106 ms | x16.8 (dominated by inherent clock-pair analysis; semantic checks near-linear) |

**SEMANTIC PERF PASS.** No quadratic blowup introduced by Phase 5.

---

## 14. Security / Stability

Unchanged from Phase 4 (security 5/5): the new rules operate only on already-preprocessed, already-resolved text — no new execution surface, no file I/O, no subprocesses. Undefined `$VARIABLE` tokens are preserved (never evaluated). All new code is pure string/set analysis.

---

## 15. Files Modified

| File | Change |
|---|---|
| `checker.py` | `_clock_ref()` classifier; SDC-046 (fixes P0 fallback), SDC-047, SDC-048, SDC-049; `defined_clock_names` set; `Issue.line2`; SDC-008/009 now compare only against a *defined* referenced clock |
| `rules_registry.py` | Registered SDC-046..049 |
| `reporter.py` | Renders `line2` dual-provenance (`L{a} ↔ L{b}`) |
| `ui/tab_test_drive.py` | Shows `(conflicts with line N)` |
| `tests/test_regressions.py` | +6 semantic regression tests (incl. wildcard-ref no-false-positive) |
| `benchmarks/golden_semantic/` | 9 cases + manifest + runner + realistic verification |
| `benchmarks/test_semantic_adversarial.py`, `test_semantic_perf.py` | New Phase 5 suites |

---

## 16. Remaining Ambiguities (documented, NOT flagged)

1. **Timing-exception path conflicts** (false_path vs max_delay, multicycle overlaps) — require a netlist; classified `NETLIST-DEPENDENT`.
2. **I/O delay value differences** without `-add_delay` — override semantics, not conflicts.
3. **`set_case_analysis` spelling variants** (`rising` vs `rise`) — currently treated as distinct values; semantically near-equivalent, acceptable.
4. **Clocks defined in linked/included files** — a single-file checker cannot see them; SDC-046/047/048 may fire on references intended for other files (multi-file flows). Severity choice (error vs warning) partially accounts for this.
5. **`-clock [get_clocks {a b}]` multi-clock refs on `set_input_delay`** — unusual (that option takes one clock); if all names are defined, no finding.
6. **Defined-but-periodless generated clocks** — SDC-008/009 comparison is now skipped (was: tightest fallback); more correct, but a documented behavior change on valid input.

---

## 17. Next Phase Recommendation

1. **Multi-file / linked-constraint resolution** — let `set_clock_groups`/I/O delays resolve clock names across linked files (the checker already has a single-file view; extending it would remove the biggest remaining SDC-046/047/048 false-positive source).
2. **Duplicate `create_clock` on the same port with `-add`** — high-confidence duplicate detection refinement (same port, different names, no `-add`).
3. **Rise/fall spelling normalization** for `set_case_analysis` comparisons.
4. Re-run all suites (above) after each change; parser golden must stay 22/22 and semantic golden 9/9.

---

*Phase 5 principle honored: false positives were treated as more dangerous than missing uncertain warnings. Only 4 high-confidence, evidence-backed semantic rules were implemented — each with independent golden benchmarks.*
