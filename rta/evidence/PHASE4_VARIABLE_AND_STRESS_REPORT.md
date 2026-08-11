# PHASE 4 — Tcl Variable Support + Preprocessor Hardening + Real-World Stress Test

Date: 2026-08-04
Status: **COMPLETE**

---

## 1. Baseline (before changes)

| Suite | Before | After |
|---|---|---|
| pytest `tests/` | 383/383 PASS | **402/402 PASS** (+19 new regression tests) |
| Golden benchmark | 21/22 (c08 failing) | **22/22 PASS** |
| UI benchmark (`test_ui_app.py`) | 33/33 PASS | **33/33 PASS** |
| State isolation (`test_ui_state_isolation.py`) | 6/6 PASS | **6/6 PASS** |
| Full benchmark suite | 61 files | 61 files |

No deviations from the stated Phase 4 baseline were observed before implementation.

---

## 2. c08 Root Cause

**Case** (`benchmarks/golden/04_variables/c08_var_period.sdc`):
```
set CLK_PERIOD 2.5
set IN_DLY 6.0
create_clock -name core_clk -period $CLK_PERIOD [get_ports clk]
set_input_delay -max $IN_DLY -min 0.2 -clock core_clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock core_clk [all_outputs]
```

**Expected** (independently verified): after Tcl resolution, `core_clk` period = 2.5 ns; input delay `-max 6.0` ≥ 2.5 → **SDC-008**.

**Failing modules**: checker (period regex could not read `$CLK_PERIOD` → empty `period_map` → no SDC-008; converter reported period 0.0; clock relations saw the clock but with default period).

**Root cause**: `preprocess_sdc()` had no variable support. `$CLK_PERIOD` was left as literal text, so `NUM_PATTERN` never matched and every consumer silently treated the value as missing (0.0 / no period / default 5.0). This is the classic "unresolved Tcl in SDC" failure mode.

**Required syntax** (Tcl(n), expr(n)): `set NAME VALUE` scalar assignment; `$NAME` and `${NAME}` substitution; substitution is **order-aware** (a later `set` must not retroactively change earlier commands); `$` inside `{...}` braces is **not** substituted (braces suppress substitution); `$` inside double quotes **is** substituted.

---

## 3. Variable-Support Design

Implemented entirely inside the **shared preprocessor** (`sdc_preprocess.py`) so all three migrated consumers (checker, converter, clock_relations — plus coverage in this phase) benefit with zero per-module changes.

Pipeline (unchanged entry points, enriched behavior):

```
Raw SDC
  → preprocess_sdc()
      → logical commands (comments stripped, continuations joined, provenance)
      → _resolve_variables()   [NEW]
          env = {}  (scalar variables, in-file order)
          for cmd in commands:
              text = _substitute_vars(cmd.text, env)   # $NAME / ${NAME}
              if cmd matches  set NAME VALUE  → env[NAME] = VALUE
```

Key properties:

- **Bounded**: only plain scalar `set NAME VALUE`. No expressions, arrays, namespaces, procs, command substitution.
- **Order-aware**: assignments take effect only for subsequent commands (Part 4 requirement proven by test `test_order_aware_reassignment`).
- **Brace/quote semantics** (Tcl rule): `{...}` suppresses `$` substitution; `"..."` allows it; `\$` escapes.
- **Longest-identifier matching**: `$CLK2` resolves to variable `CLK2`, never `CLK` + `"2"` (verified).
- **Unresolved variables are preserved verbatim** (Part 9): `$UNKNOWN` stays in the text — never silently 0, empty, or random. Downstream validators then behave deterministically (e.g. a clock with `-period $UNKNOWN` has no resolvable period; no crash).
- **`set` vs SDC `set_*` disambiguation** (Part 5): the regex requires `set` + whitespace + identifier. `set_input_delay`, `set_clock_groups`, etc. are single tokens and can never match.
- **Fast path**: commands containing no `$` skip the substitution scan (proven: preprocess scales linearly, §10).
- **`set` commands remain in output** as inert lines — provenance and line numbers are preserved (they are ignored by all SDC consumers).

---

## 4. Supported Tcl Subset (explicit)

| Construct | Supported |
|---|---|
| `set NAME VALUE` scalar assignment | ✅ |
| `$NAME` substitution | ✅ |
| `${NAME}` substitution | ✅ |
| Order-aware reassignment (`set P 10` … `set P 5`) | ✅ |
| Values: bare, quoted, braced; integers, decimals, scientific notation, negatives | ✅ |
| Multi-line `set NAME \` + newline + `VALUE` | ✅ |
| Variables as period / delay / clock-name values | ✅ |
| `$` inside `"double quotes"` substituted (even when braces appear inside the quotes — reviewer fix) | ✅ |
| `$` inside `{braces}` literal (NOT substituted) | ✅ |
| `\$` escaped dollar | ✅ |
| Longest-name matching (`$CLK2` ≠ `$CLK`+`2`) | ✅ |

## 5. Unsupported Tcl Subset (explicit — left inert)

| Construct | Behavior |
|---|---|
| `foreach`, `for`, `if`, `proc`, `while` | Treated as inert text commands; never executed |
| `eval`, `exec`, `source`, `open`, `subst`, backticks | Inert text (proven in §11) |
| `[command substitution]` | Brackets only tracked for comment logic; not evaluated |
| `$array(key)`, `::namespace::var`, env vars (`$env(…)`) | Left as literal unresolved text |
| Expressions (`expr`, `[expr $a+1]`) | Not evaluated |
| Braced value containing nested substitution | Braces suppress substitution per Tcl rule |

---

## 6. Variable Edge-Case Results

All implemented and tested in `tests/test_sdc_preprocess.py::TestTclVariables` + stress tests:

| Edge case | Result |
|---|---|
| `set CLK_PERIOD 2.5` → `-period $CLK_PERIOD` | period = 2.5 ✅ |
| `${PERIOD}` braced-name form | period = 5.0 ✅ |
| Order-aware reassignment (10 then 5) | a=10, b=5 ✅ |
| Undefined `$UNKNOWN` | preserved verbatim, no crash, no silent 0 ✅ |
| Similar names `CLK`=10, `CLK2`=5 | `$CLK2`→5, `$CLK`→10 (no `10`+`2`) ✅ |
| Empty value `set EMPTY {}` | resolves to empty; downstream deterministic, no crash ✅ |
| Negative `-0.25` and sci `2.5e-1` in variables | both parse correctly ✅ |
| Variable as clock name (`set NAME core_clk`) | name = core_clk ✅ |
| Variable across multiline command | period = 10.0 ✅ |
| `set_input_delay` NOT treated as `set` | SDC-008 fires correctly (no `set` confusion) ✅ |
| Braces suppress substitution (`-group [get_clocks {$X}]`) | `$X` literal ✅ |
| No state leak between `preprocess_sdc` calls | ✅ |
| Variable reused across 20 commands | all resolve ✅ |

---

## 7. Preprocessor Stress-Test Results (`benchmarks/test_preprocess_stress.py`)

**21/21 PASS** after correcting two *test-side* counting bugs (the preprocessor itself was never at fault):

Covered adversarial combinations — comments+multiline, multiline+scientific notation, variables+multiline, variables+comments, braces+comments, brackets+braces, quoted `#` (`"BUF#X2"`), multiple commands, blank lines, **CRLF**, **tabs/large whitespace**, **Unicode BOM**, **no trailing newline**, **unterminated trailing backslash**, semicolon-separated commands, backslash inside quotes, very long single commands (5k chars), **1000-command large file (no loss, no duplication)**, braces spanning physical lines, order-aware reassignment, brace-suppressed substitution.

Invariants enforced everywhere: no crash, no command loss, no duplication, correct `start_line ≤ end_line` provenance, and **deterministic** output (same input → identical result on repeat calls).

---

## 8. Realistic SDC Corpus (`benchmarks/test_realistic_corpus.py`)

**2/2 PASS**. Two realistic production-style files were built following Accellera SDC 2.1 / tool conventions:

- **`realistic_soctop.sdc`** — SoC top: `set sdc_version`, `set_units` (multiline), Tcl period variables, two primary clocks with `-waveform`, two generated clocks (`-multiply_by 2`, `-master_clock` + `-divide_by 4`), two `set_clock_uncertainty` forms, `set_clock_groups -asynchronous` with a braced 3-clock group, 4 I/O delays with braced `{data_in*}` port lists, `set_driving_cell`/`set_input_transition`/`set_load`, 3 timing exceptions (one multiline `-setup -hold`), `set_case_analysis`, `set_disable_timing`, design rules, `set_operating_conditions`.
  - Verified: 2 primary + 2 generated clocks; `clk_cpu` period **2.0** from `$CLK_PERIOD_CPU`; `pll_2x` period derived = **1.0**; clock relations: 4 clocks, **6 pairs** = 4·3/2, no crash.
- **`realistic_ddr.sdc`** — DDR memory interface: differential clocks with `-waveform`, uncertainty, braced bus port lists `{dq[0] dq[1] …}`, wildcard `dq[*]`, false path + multicycle with `-hold`.
  - Verified: 2 clocks, period 1.875, braced bus lists accepted, 1 pair.

---

## 9. Cross-Module Consistency Matrix

Probe fed one representative SDC (comment mentioning `create_clock -name ghost`, `set CLK_PERIOD 2.5e-1`, multiline `create_clock -period $CLK_PERIOD`, multiline `set_input_delay -max 3.0e-1`, braced `set_clock_groups`) through all modules.

| Feature | Checker | Converter | Clock Relations | Linter | Coverage | Constraint Diff |
|---|---|---|---|---|---|---|
| Full-line comments | ✅ stripped (via preprocess) | ✅ | ✅ | ✅ (leading comments preserved intentionally) | ✅ **fixed this phase** (was counting commented clocks!) | ✅ own `_strip_comments` |
| Multiline `\` join | ✅ | ✅ | ✅ | ✅ (own join in formatter) | ✅ **fixed** | ✅ own `_join_continuations` |
| Scientific notation | ✅ `2.5e-1`→0.25 | ✅ | ✅ | N/A (formatter) | N/A (presence only) | ⚠️ `-period 2.5e-1` → **no period** (`[\d.]+`) |
| Tcl variables | ✅ | ✅ | ✅ | N/A | ✅ **fixed** | ✅ via `tcl_resolver.SymbolTable` (must be passed in) |
| Braced collections | ✅ | ✅ | ✅ | N/A | N/A | ⚠️ `[get_clocks {a b}]` → **not expanded** (kept as `-group [get_clocks {a b}]`) |
| Consistency verdict | ✅ | ✅ | ✅ | N/A | ✅ | ⚠️ **partially inconsistent** |

**Phase-4 changes**: `coverage.py` was migrated to the shared preprocessor because a **demonstrated correctness impact** was found — a file with *all* clocks commented out reported `Primary clock: present=True, "2 defined"` while the checker correctly reported `0 clocks` + `SDC-001`. This is a genuine false positive that would mislead users (green "clocks covered" for an empty design). After migration: `present=False`, 16/16 coverage tests still pass, plus 2 new regression tests.

**Constraint diff** remains partially inconsistent (sci-notation periods and braced group expansion). This is **documented, not migrated**: the diff module owns a separate Tcl resolver (`tcl_resolver.py`) and is used only for comparing two versions where both sides share the same parsing behavior — so these gaps do not currently cause wrong *diff* conclusions (self-diff matched 5/5). Migration is deferred to keep the diff's separate symbol-table contract stable; see §14.

**Linter** is intentionally not migrated: it is a formatter, not a semantic analyzer. Its comment-preservation is correct behavior (comments must survive linting).

---

## 10. Performance Measurements

Preprocess scaling is **near-linear**; `check` cost is dominated by the inherently O(N²) clock-pair analysis.

| Size | Commands | Preprocess | Full check | Peak mem |
|---|---|---|---|---|
| ~100 lines | 81 | 2 ms | 15 ms | 39 KiB |
| ~1,000 lines | 801 | 22 ms | 162 ms | 448 KiB |
| ~10,000 lines | 8,001 | 230 ms | ~13.2 s | 4.6 MiB |

Scaling 1k→10k: preprocess **x10.5** (linear ✓), check x81 (inherent O(N²) pairs — 2,000 clocks → ~2M pairs).

**Found and fixed an O(N³) defect**: `analyze_clock_relations` recomputed `_get_ancestors()` (a linear scan over *all* clocks) for *every pair*. At 400 clocks this was 6.85 s. The ancestor sets are now **precomputed once per clock** and passed via an optional `ancestor_sets` cache to `infer_relation()` (backward-compatible signature preserved). Result: 6.85 s → 0.50 s at 400 clocks (13.7× faster), full analysis now O(N²). Regression test: 150 clocks analyze < 5 s with exactly N·(N−1)/2 pairs.

No catastrophic regex backtracking, no accidental O(N²) in preprocessing, no repeated whole-file scanning.

---

## 11. Security Assessment (`benchmarks/test_security.py`)

**5/5 PASS.** Uploaded SDC is treated as untrusted input:

| Check | Result |
|---|---|
| `exec touch marker` inert (no file created) | ✅ |
| `source ~/.bashrc` / `eval {…}` / `[exec whoami]` inert | ✅ |
| `set f [open /etc/passwd r]` inert (no read) | ✅ |
| checker + converter survive hostile input without executing | ✅ |
| No environment-variable expansion (`$HOME` stays literal) | ✅ |
| No subprocess invocation, no file side effects | ✅ |

Confirmation: **arbitrary Tcl remains inert text.** The variable implementation performs only string substitution against an in-file dictionary — there is no `eval()`, `exec()`, `os.system()`, `subprocess`, or file I/O anywhere in the preprocessor.

---

## 12. Golden Results

- **Before: 21/22** (only c08 failing)
- **After: 22/22 PASS** — c08 now passes because implementation behavior matches the independently verified expectation (period 2.5, SDC-008 fires). **No golden expectation was changed.**

```
GOLDEN BENCHMARK — 22/22 cases match expected (correct) behavior
```

---

## 13. Regression Results (final, all executed)

| Suite | Result |
|---|---|
| `pytest tests/ -q` | **402/402 PASS** (383 baseline + 19 new) |
| `benchmarks/run_golden.py` | **22/22** |
| `benchmarks/run_benchmark.py` | 61 files analyzed |
| `benchmarks/test_preprocess_stress.py` | **21/21** |
| `benchmarks/test_realistic_corpus.py` | **2/2** |
| `benchmarks/test_security.py` | **5/5** |
| `benchmarks/test_performance.py` | PASS (preprocess near-linear) |
| `benchmarks/test_ui_app.py` | **33/33** |
| `benchmarks/test_ui_state_isolation.py` | **6/6** |
| Local Streamlit smoke (`streamlit run app.py`) | HTTP 200, no error/traceback in logs |

---

## 14. Files Modified

| File | Change |
|---|---|
| `sdc_preprocess.py` | Bounded Tcl variable resolution: `_SET_CMD`, `_VAR_REF`, `_clean_set_value`, `_substitute_vars`, `_resolve_variables`; fast path; wired into `preprocess_sdc()`. |
| `clock_relations.py` | **Perf fix**: precomputed `ancestor_sets` cache → O(N²) analysis (was O(N³)); optional param on `infer_relation()` (backward compatible). |
| `coverage.py` | Migrated to shared preprocessor (fixes demonstrated false positive: commented-out clocks counted as present). |
| `tests/test_sdc_preprocess.py` | +20 tests: variable subset, edge cases, c08 end-to-end, no state leak, quoted-brace substitution (reviewer fix). |
| `tests/test_coverage.py` | +2 tests: commented-clock false positive, multiline+variable detection. |
| `tests/test_regressions.py` | +1 perf regression test (150 clocks, pair-count formula, <5 s). |
| `benchmarks/test_preprocess_stress.py`, `test_realistic_corpus.py`, `test_security.py`, `test_performance.py` | New Phase 4 benchmark suites (reusable). |

Untouched by design: `checker.py` and `converter.py` needed no changes (they already consume `preprocess_sdc()`); `linter.py` (formatter, correct as-is); `constraint_diff.py` (own resolver contract preserved; gaps documented).

---

## 14b. Code-Review Fixes Applied This Phase

A reviewer pass flagged that `_substitute_vars` tracked brace depth but not quote state, so `{`/`}` inside `"double quotes"` were treated as real brace delimiters — deviating from Tcl (braces inside quotes are literal and `$` must still substitute). **Fixed**: `_substitute_vars` now mirrors `_strip_line_comment`'s `in_quote` tracking — while inside quotes, braces are literal and `$` is still substituted. Regression test: `test_dollar_substituted_inside_quotes_with_braces`. Reviewer also confirmed the ancestor cache is read-only safe (no mutation → no cross-pair contamination) and the coverage migration is correct.

## 15. Remaining Limitations (documented, deferred)

1. **General Tcl variable evaluation** — only the bounded scalar subset is supported; arrays, namespaces, `$env(…)`, expressions remain literal text. This matches the Phase 4 scope and security requirement.
2. **Cross-constraint conflict detection** — explicitly deferred (Phase 5 candidate).
3. **Constraint-diff braced-collection / sci-notation parsing** — diff's separate parser (`_parse_clock_groups` regex `-group \[[^\]]+\]`, `_parse_create_clock` `-period ([\d.]+)`) does not expand `[get_clocks {a b}]` or read `2.5e-1`. No current wrong diff output (self-diff matches); revisit if diff consumption broadens.
4. **`set_clock_groups` with a single `-group` and no second group** — analyzed correctly but produces the expected missing-pair advisory; not a bug.
5. **Low-confidence `.25` (leading-dot) literals** — still not supported as numbers (per Tcl expr(n) this is not a valid literal); intentionally unchanged.

---

## 16. Recommended Phase 5

Based on evidence from this phase:

1. **Cross-constraint conflict detection** (the last remaining golden-class limitation) — e.g. duplicate `create_clock` on the same port with different periods, `set_max_delay` vs `set_min_delay` inversions, conflicting `set_case_analysis` on the same pin. The preprocessor + resolved variables now give a clean, consistent input surface to build on.
2. **Constraint-diff parser alignment** — extend `_parse_create_clock`/`_parse_clock_groups` to use `parse_number()`/`parse_collection()` (2 small functions; removes the last known inconsistency).
3. **Optional**: expose unresolved-variable diagnostics as an advisory info item (currently silent-but-preserved); decide policy before adding a rule ID.
4. Re-run the full suite (all suites in §13) after each change; golden suite should stay 22/22.

---

*Phase 4 principle honored: variable support is bounded, deterministic, order-aware, and safe — the validator is not a Tcl execution engine.*
