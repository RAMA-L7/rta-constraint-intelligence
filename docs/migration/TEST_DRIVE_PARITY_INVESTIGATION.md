# Test Drive Parity Investigation — `real_design_full.sdc`

**Status:** Investigation only — no implementation changed
**Date:** 2026-08-14
**Scope:** Functional parity between the Original SDC Validator Test Drive and the Ṛta Test Drive on the same input file.

---

## 0. Executive summary

**The two implementations disagree on every count EXCEPT coverage and linter.** Investigation proves the cause is **not** a semantic regression in Ṛta's analysis rules — it is **one malformed line in the input fixture** plus the *different Tcl-line-handling philosophy* of the two parsers:

| Metric | Original | Ṛta | Delta |
|---|---|---|---|
| checker errors | 0 | 0 | — |
| checker warnings | 5 | 7 | +2 |
| coverage score | 82.1 | 82.1 | — |
| coverage present/total | 32/39 | 32/39 | — |
| clock_relations clocks | 7 | 6 | **−1** |
| clock_relations pairs | 21 | 15 | **−6** |
| linter warnings | 0 | 0 | — |
| converter clocks | 7 | 6 | **−1** |
| converter constraints | 25 | 17 | **−8** |
| converter input delays | 4 | 4 | — |
| converter output delays | 4 | 4 | — |
| converter false paths | 5 | 1 | **−4** |
| converter clock groups | 2 | 1 | **−1** |

**Verdict: the Original counts are the intended semantics; Ṛta's lower counts are a parse artifact of a malformed input line — NOT a loss of analysis capability.** When the fixture's corrupt line is fixed, Ṛta produces **exactly** the original's numbers (7 clocks / 21 pairs / 25 constraints / 5 false paths / 2 clock groups — verified empirically, §5).

Two real findings fall out of this investigation:

1. **`samples/real_design_full.sdc` (and its 2 identical copies) is corrupted**: line 58 has an unclosed `[` bracket that, under Ṛta's (correct, Tcl-faithful) preprocessor, swallows the remainder of the file into one logical command — hiding 4 false paths, 3 multicycle paths, 3 case analyses, 3 derates, 1 clock group. The Original parser ignores line structure, so it never noticed.
2. **Ṛta has no diagnostic when a bracket is left unclosed** — `preprocess_sdc` silently merges to EOF instead of reporting the malformed construct. A robustness gap worth a follow-up (see §7, Recommendation 2).

---

## 1. How the two implementations were compared

- **Original SDC Validator** = the pre-migration implementation of `checker.py`, `clock_relations.py`, `converter.py`, `coverage.py`, `linter.py` at commit `ccc90d8` of the sdc-tools lineage (last commit before the modules became migration shims). Reconstructed into a sandbox and executed directly.
- **Ṛta** = the current repo: root modules are shims into `rta/engine/rules/checker.py`, `rta/engine/analysis/clock_relations.py`, `rta/engine/analysis/coverage.py`, `rta/tools/convert/converter.py`, `rta/tools/lint/linter.py`, all fed by the shared `rta/engine/preprocess/sdc_preprocess.py::preprocess_sdc`.
- **Input**: `samples/real_design_full.sdc` (md5 `cb8a1c5…`). The copies at `rta/evidence/regression/real_design_full.sdc` and `rta/examples/samples/real_design_full.sdc` are byte-identical modulo CRLF/LF line endings.

Both sides reproduced the reported numbers exactly.

---

## 2. Difference-by-difference analysis

### 2.1 Clocks: 7 vs 6 — missing `clk_core_div4` (Classification: **A→E, root cause = input corruption**)

| | Original | Ṛta |
|---|---|---|
| clocks | `clk_axi, clk_core, clk_core_div2, clk_core_div4, clk_mem, vclk_axi, vclk_core` | `clk_axi, clk_core, clk_core_div2, clk_mem, vclk_axi, vclk_core` |

**Exact missing clock: `clk_core_div4`** (the second `create_generated_clock`).

**Root cause — lines 29–30 of the fixture:**
```
create_generated_clock -name clk_core_div2 -source [get_ports clk_core] \
create_generated_clock -name clk_core_div4 -source [get_ports clk_core] \
```
These two lines carry trailing `\` Tcl continuation markers. The file was clearly produced by a "reorganization" tool that split long lines and left `\` artifacts (see the file's own header: *"SDC Lint — Reorganized Constraint File"*).

- **Original** parses line-by-line (no continuation resolution) → sees two commands → 7 clocks.
- **Ṛta** applies Tcl rule 9/10 (`preprocess_sdc`: *"a backslash-newline is replaced by a single space"*) → joins the two lines into ONE logical command containing two `create_generated_clock` statements. The converter's regex `create_generated_clock[^;\n]*` matches the merged line once, and `-name\s+(\S+)` keeps the **first** name (`clk_core_div2`) — `clk_core_div4` is silently dropped.

**Correct behavior:** a real Tcl interpreter treats `\`-newline as continuation, so the merged single command is actually **malformed Tcl** (two command words in one line). The file's *intent* is two generated clocks. Neither parser handles this gracefully: the Original silently counts the lines; Ṛta silently drops the second clock.

### 2.2 Clock relations: 21 vs 15 pairs (Classification: **E — pure arithmetic consequence of §2.1**)

Pairs = nC2 of the clock set: 7 clocks → 21 pairs; 6 clocks → 15 pairs. **The pair-count delta is exactly the missing clock** — not a changed inference. All 15 Ṛta pairs are also present in the original's 21 (verified: `clk_core_div2` pairs missing in Ṛta are the ones involving `clk_core_div4`).

### 2.3 Converter: 25 vs 17 constraints — the 8 missing (Classification: **A→E, root cause = §2.4 bracket swallow**)

Original converter breakdown: 7 clocks + 4 input + 4 output + 5 false paths + 5 multicycle (4 real + 1 max_delay appended) = 25.
Ṛta breakdown: 6 clocks + 4 input + 4 output + 1 false path + 2 multicycle (1 merged + 1 max_delay) = 17.

The 8 missing = **1 clock** (`clk_core_div4`, §2.1) + **4 false paths** (§2.5) + **3 multicycle paths** (§2.4 swallow).

### 2.4 The core mechanism: unclosed bracket on line 58 swallows lines 58–117 (Classification: **A — Ṛta robustness gap; root cause = input corruption**)

```
58  set_driving_cell -lib_cell BUF_X4 -pin Z [remove_from_collection [all_inputs] \
59  set_load 0.05 [all_outputs]
```

Line 58 has **two** defects: a trailing `\` continuation **and** an unclosed bracket — `[remove_from_collection [all_inputs]` opens 2 brackets and closes only 1, leaving `in_bracket = 1` for the rest of the file.

`preprocess_sdc` (sdc_preprocess.py) tracks brace/bracket depth and only ends a logical command when `in_brace == 0 and in_bracket == 0`. Because the bracket never closes, the command starting at line 58 accumulates **every subsequent line through EOF (line 117)** into ONE logical command:

```
set_driving_cell ... set_load 0.05 [all_outputs] # ── False Paths ── set_false_path ... set_multicycle_path ...
set_case_analysis ... set_timing_derate ... set_max_area ... set_dont_use ...
```

Empirically confirmed: `preprocess_sdc` yields a single logical command `start=58 end=117` containing `set_false_path`, `set_multicycle_path`, `set_case_analysis`, `set_timing_derate`, `set_max_delay`, `set_operating_conditions`, `set_dont_use`, `set_max_area` — **the entire remainder of the file**.

The Original's converter regexes `set_false_path[^;\n]*` run line-by-line, so they find all 5; Ṛta's run over the merged blob, so each `_grab` finds only the **first** match to end-of-line.

### 2.5 False paths: 5 vs 1 (Classification: **A — lost findings, root cause = §2.4 swallow**)

Original: 5 separate `ParsedException` objects (rst_n, test_mode, clk_core→clk_axi, clk_axi→clk_core, through *bist*).
Ṛta: **1** `ParsedException` with `from_='[get_ports', to='[get_clocks', through=['[get_pins']` — a **garbage merge** of three different commands (from line 63, 65, 67), produced because the regex `set_false_path[^;\n]*` on the swallowed blob captures from the first `set_false_path` to end-of-line and `_parse_exception` then takes the first `-from`, first `-to`, all `-through`.

This is a **real regression symptom**: 4 false paths that the Original found are invisible to Ṛta on this file. On a well-formed file they are found (§5).

### 2.6 Clock groups: 2 vs 1 (Classification: **C — count artifact; semantic content preserved**)

Lines 45–46:
```
set_clock_groups -asynchronous \ -group [get_clocks {clk_core clk_core_div2 clk_core_div4}] \
set_clock_groups -asynchronous \ -group [get_clocks clk_core] \
```
Continuation join merges them into ONE command. The merged Ṛta object contains **both** groups: `groups: [['clk_core','clk_core_div2','clk_core_div4'], ['clk_core']]` — semantically the same CDC intent, counted as 1 command instead of 2. This is a counting-format difference, not lost information. (Note both parses are crude: Original stores `groups=['[get_clocks']` — truncated — so neither parses the collections fully.)

### 2.7 Checker warnings: 5 vs 7 (Classification: **C (legitimate) + A (regression symptom)**)

| # | Original | Ṛta |
|---|---|---|
| 1 | SDC-020 false_path between clk_core/clk_axi | SDC-048 clock group refs undefined `clk_core_div4` |
| 2 | SDC-020 false_path between clk_axi/clk_core | SDC-027 max_delay no -datapath_only |
| 3 | SDC-021 multicycle setup 3 no hold | SDC-150 set_false_path no comment |
| 4 | SDC-021 multicycle setup 4 no hold | SDC-150 set_false_path no comment |
| 5 | SDC-027 max_delay no -datapath_only | SDC-150 set_false_path no comment |
| 6 | | SDC-150 set_multicycle_path no comment |
| 7 | | SDC-150 set_multicycle_path no comment |

- **SDC-150 ×5** = the new F1 rationale-comment linting rule (v1.5.2). **Intentional Ṛta enhancement** — would fire on the Original's input too if the Original had the rule. Legitimate.
- **SDC-048** (clock group references undefined `clk_core_div4`) = **false positive caused by §2.1**: the clock IS defined in the file; Ṛta just lost it to the continuation merge. Regression symptom, not a real finding.
- **Lost SDC-020 ×2 and SDC-021 ×2**: the false-path and multicycle commands were swallowed by §2.4, so the checker's exception-analysis rules never saw them. **Real findings silently dropped** — the same regression class as §2.5.

Net: +5 (SDC-150, legit) −4 (SDC-020/021 swallowed) +1 (SDC-048 spurious) = +2. The "2 extra warnings" are therefore **not** two clean enhancements: 5 are legitimate, 4 real warnings went missing, 1 is spurious.

### 2.8 Coverage 82.1 and linter 0: unchanged (Classification: **no difference**)

Coverage uses the same `preprocess_sdc`, but it counts *category presence* (≥1 match per keyword), and the swallowed blob still contains every keyword → same 32/39. Linter doesn't use the preprocessor at all. No action needed.

---

## 3. Classification summary (per the finding's A–E scheme)

| Difference | Class | One-line justification |
|---|---|---|
| Clock 7→6 (missing `clk_core_div4`) | **E→A** | Input has corrupt `\` continuation; Ṛta merges and drops the 2nd clock; Original counts lines. Ṛta side: silent data loss = regression symptom. |
| Pairs 21→15 | **E** | Pure nC2 arithmetic of §2.1. |
| Constraints 25→17 (−8) | **A** | 1 clock (§2.1) + 4 false paths + 3 multicycle (§2.4 swallow). |
| False paths 5→1 | **A** | Swallowed by unclosed bracket; findings lost. |
| Clock groups 2→1 | **C** | Continuation merge; both groups preserved inside 1 object. |
| Checker warnings 5→7 | **C + A** | +5 SDC-150 legit enhancement; −4 SDC-020/021 swallowed; +1 SDC-048 spurious. |
| Coverage / linter | — | Identical. |

**Bottom line:** No Ṛta analysis rule is wrong. One corrupted fixture line (58) plus trailing-`\` artifacts on lines 29/30/45/46 produce every discrepancy. The Original's counts happen to match the file's intent only because its line-based parser ignores Tcl continuation semantics entirely.

---

## 4. Which side is "correct"?

- **If the question is "what does the file say semantically":** the **Original counts are correct** — the file *intends* 7 clocks, 5 false paths, 2 clock groups, 25 constraints. That is the value an engineer reading the file sees.
- **If the question is "which parser is more correct Tcl":** Ṛta's `preprocess_sdc` implements Tcl rules 9/10 faithfully; the *file* is what violates Tcl (unclosed bracket = syntax error in any real Tcl interpreter). The Original parser is simpler and wrong about continuations, but robust to them by accident.
- **Neither is acceptable behavior on malformed input**: the Original silently miscounts; Ṛta silently swallows 60 lines. Both should flag the malformed construct (Recommendation 2).

---

## 5. Proof: with a well-formed copy, Ṛta == Original

A corrected copy (trailing `\` stripped, `\ -group` → ` -group`, line 58 bracket closed as `[remove_from_collection [all_inputs] [all_outputs]]`) run through current Ṛta:

```
converter clocks/constraints/io/fp/cg/mc/derate/ca: 7 25 4 4 5 2 5 4 3
clock_relations clocks/pairs: 7 21
checker: 0 errors, 8 warnings  → SDC-020 ×2 + SDC-027 + SDC-150 ×5
```

→ **7 clocks, 21 pairs, 25 constraints, 5 false paths, 2 clock groups — exactly the Original.** (Checker is 8 vs Original's 5 because of the legit SDC-150 rule + the SDC-021 cross-command hold-pairing improvement; see §6.)

---

## 6. Rule-level behavior differences that are legitimate

- **SDC-150 rationale-comment lint** (new, v1.5.2): fires on undocumented false/multicycle/case_analysis lines. Enhancement. ✔
- **SDC-021 (multicycle without hold fix)**: Ṛta matches setup/hold across separate commands on identical endpoints (checker.py lines 457–478); the Original flagged setup/hold pairs even when the hold fix exists on the next line. Ṛta's is the intended behavior. ✔
- **SDC-048 (undefined clock ref)**: new rule; correct rule, but its firing here is a false positive caused by the §2.1 parse loss — fix the fixture and it won't fire.

---

## 7. Recommendations (not yet implemented — this sprint is investigation only)

### Recommendation 1 (fixture fix, primary)
Repair `real_design_full.sdc` in **all three locations** (`samples/`, `rta/evidence/regression/`, `rta/examples/samples/`):
- Remove trailing `\` continuations on lines 29, 30, 45, 46, 58 (or restore the true multi-line command bodies they reference — e.g. `-divide_by 2 -pins [get_pins …]` for the generated clocks).
- Close the bracket on line 58: `set_driving_cell -lib_cell BUF_X4 -pin Z [remove_from_collection [all_inputs] [get_ports inst_addr*]]`.
- Normalize `\ -group` → ` -group`.

After the fix, re-run and assert parity: 7 clocks / 21 pairs / 25 constraints / 5 false paths / 2 clock groups / 82.1 coverage.

**Regression test:** `rta/tests/test_evidence.py` (or a new `test_test_drive_parity.py`) asserting the fixed fixture yields the exact counts above, plus a test that `preprocess_sdc` raises/annotates on an unclosed bracket (Recommendation 2).

### Recommendation 2 (engine hardening, follow-up)
`preprocess_sdc` should not silently merge to EOF when `in_bracket > 0` at end of file — emit a parse diagnostic (e.g. `SCOPE-UNSUPPORTED`-style warning: "unclosed bracket starting line N") so the malformed construct is visible instead of silently hiding 60 lines of findings. This protects every consumer (checker, converter, clock relations, coverage).

### Recommendation 3 (parity harness)
Add a `docs/migration/` regression script that runs Original-vs-Ṛta on a small corpus of well-formed SDC files and diffs the five Test Drive numbers, so parity regressions are caught by pytest rather than manual runs.

---

## 8. Files & functions responsible

| Concern | File | Function |
|---|---|---|
| Continuation join + bracket tracking | `rta/engine/preprocess/sdc_preprocess.py` | `preprocess_sdc` (rules 9/10; silent EOF merge) |
| Clock loss (first-`-name` only) | `rta/tools/convert/converter.py` | `parse_sdc` (`create_generated_clock` loop) |
| False-path merge artifact | `rta/tools/convert/converter.py` | `_grab` + `_parse_exception` over swallowed blob |
| Checker SDC-048 false positive | `rta/engine/rules/checker.py` | clock-group cross-reference rule |
| Original (reference) line-based parse | sdc-tools `ccc90d8` `converter.py`/`checker.py` | per-line regex |

---

## 9. What was NOT done (scope guard)

- ❌ No implementation changes made anywhere.
- ❌ No rule semantics changed.
- ❌ No numbers normalized to force parity — every delta above is explained by parse behavior, and parity is proven achievable by fixing the fixture alone.
- ❌ No UI changes, no new features, no unrelated refactors.
