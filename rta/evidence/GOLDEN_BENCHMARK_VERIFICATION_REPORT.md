# GOLDEN BENCHMARK VERIFICATION REPORT

**SDC Tools (v1.3.0)** · Phase 2 of QA: VERIFY → REPRODUCE → CLASSIFY → ROOT-CAUSE → GOLDEN TESTS
Date: 2026-08-04 · Scope: diagnostic only — **no production code was modified.**

---

## 1. BASELINE

| Suite | Executed | Passed | Failed | Notes |
|---|---|---|---|---|
| `pytest tests/` (unit) | 330 | 330 | 0 | clean |
| `benchmarks/run_benchmark.py` (61 SDC inputs) | 61 | — | — | produces `benchmarks/results/results.json` |
| `benchmarks/test_ui_app.py` (AppTest UI) | 33 | 33 | 0 | all 10 tabs + Test Drive + Feedback |
| `benchmarks/test_ui_state_isolation.py` | 6 | 6 | 0 | no state leakage between inputs/views |
| `benchmarks/run_golden.py` (golden suite) | 22 | 10 | 12 | **failures are the confirmed-bug backlog** |

Deployed app health: `https://sdc-tools-8mxtuhwy5myvejdcmpuwbp.streamlit.app/` is **auth-gated**
(303 → `share.streamlit.io/-/auth/app`). It was public earlier in the session but now requires
login — **check Streamlit Cloud Share → Authentication**. UI tests were therefore executed
against the identical local v1.3.0 code via Streamlit `AppTest`.

---

## 2. VERIFIED FINDINGS (F01–F14)

Each prior benchmark finding was reduced to a minimal reproducer, run independently, and
compared against behavior established from authoritative references:
[Tcl(n) man pages](https://www.tcl-lang.org/man/tcl8.6/TclCmd/Tcl.htm) (comments = Rule 10,
continuation = Rule 9, number syntax), Accellera SDC 2.1 command syntax, and Synopsys
command references (uncertainty/clock-group/input-delay option grammar).

### Classification legend
- **CONFIRMED BUG** — demonstrable incorrect result on valid input
- **CONFIRMED VALIDATOR LIMITATION** — correct-by-design behavior gap, not a crash
- **FALSE POSITIVE IN BENCHMARK** — earlier benchmark conclusion was wrong
- **EXPECTED BEHAVIOR** — tool is correct
- **AMBIGUOUS** — needs human review

| # | Finding | Minimal reproducer | Expected | Actual | Classification | Sev | Confidence | Affected modules | Likely root cause |
|---|---|---|---|---|---|---|---|---|---|
| F01 | Full-line comment parsed as command | `# create_clock -name fake_clk -period 1.0 [get_ports fake_clk]` + real clock | 1 clock, no errors | **2 clocks** (`fake_clk` phantom); SDC-024 + SDC-062 noise | **CONFIRMED BUG** | **P0** | high | checker, converter, clock_relations | No comment stripping in any parser |
| F02 | Inline trailing comment | `create_clock … # master clock` | parse OK | correct (1 clock, 0 errors) | **EXPECTED BEHAVIOR** | — | high | — | inline comments after commands are already handled |
| F03 | Multiline `create_clock \` continuation | `create_clock \` newline `-name sys_clk \` newline `-period 10.0 \` newline `[get_ports clk]` | period 10.0, port clk | converter `clocks=[('', 0.0, '')]`; checker loses name/period | **CONFIRMED BUG** | **P0** | high | checker, converter | Continuation lines dropped (no line-joining in checker/converter) |
| F04 | Multiline `set_input_delay \` | `set_input_delay \` … `-min 0.3 \` … | no SDC-028 | **false SDC-028** "No -min" | **CONFIRMED BUG** | P1 | high | checker | `-min` on continuation line invisible to regex |
| F05 | Scientific notation | `-period 2.5e-1`, delays `3.0e-1` | period 0.25; 0.3 ≥ 0.25 → SDC-008 | period parsed as **2.5**; SDC-008 fires on wrong numbers | **CONFIRMED BUG** | **P0** | high | checker, converter, clock_relations | `[\d.]+` regex truncates `2.5e-1` → `2.5` |
| F06 | Integer vs float period | `-period 10` / `-period 10.0` | both 10.0 | both 10.0 ✓ | **EXPECTED BEHAVIOR** | — | high | — | — |
| F07 | Leading-dot literal `.25` | `-period .25`, `-max .1` | (`.25` is **invalid Tcl** — needs `0.25`) | period `.25`→0.25 OK, but delay `.1`→**1.0** | AMBIGUOUS (LOW) | P3 | medium | checker | invalid-Tcl input; delay regex `[^0-9]*` swallows the dot |
| F08 | Negative `-min` delay | `-min -0.25` | legal, no errors | no errors ✓ | **EXPECTED BEHAVIOR** | — | high | — | — |
| F09 | Tcl variables | `set CLK_PERIOD 2.5` / `set IN_DLY 6.0` / `-period $CLK_PERIOD` | period 2.5; 6.0 ≥ 2.5 → SDC-008 | converter period **0.0**; **SDC-008 missed** | **CONFIRMED VALIDATOR LIMITATION** | P1 | high | checker, converter, clock_relations | `tcl_resolver.py` exists but is only wired into `constraint_diff` |
| F10 | SDC-007 misses `data_in` | `create_clock … [get_ports data_in]` | SDC-007 | **missed** (no error) | **CONFIRMED BUG** | P1 | high | checker | `\b(data|addr|…)\b` word boundary fails on `data_in` (underscore is a word char) |
| F11 | Braced group list `{clk_a clk_b}` | `-group [get_clocks {clk_a clk_b}] -group [get_clocks clk_c]` | 1 pair genuinely undeclared | **3 pairs** reported missing | **CONFIRMED BUG** | P1 | high | clock_relations | `split()` on `{clk_a clk_b}` yields `['{clk_a', 'clk_b}']` — names never match |
| F12 | Uncertainty flag-first | `set_clock_uncertainty -setup 100.0 -hold 50.0 [get_clocks c]` | SDC-023 (100 ns) | **missed**; only flagless `0.01` triggers SDC-022 | **CONFIRMED BUG** | P1 | high | checker | regex requires value immediately after `set_clock_uncertainty` |
| F13 | Conflicting `set_false_path` + `set_max_delay` same path | `set_false_path -from U_A/Q -to U_B/D` + `set_max_delay 1.0 -from U_A/Q -to U_B/D` | conflict flagged | only SDC-020/SDC-027 heuristic notes; **no cross-constraint conflict detection** | **CONFIRMED VALIDATOR LIMITATION** | P2 | high | checker | no pairwise exception analysis |
| F14 | False path on reset (noise?) | `set_false_path -from [get_ports rst_n] -to U1/D` | — | SDC-020 advisory fires on a standard reset pattern | **EXPECTED BEHAVIOR** (rule is advisory; noisy by design) | P3 | high | checker | SDC-020 is a best-practice heuristic, not a syntax error |

### Golden-suite cross-checks that refined the above
- **c11/c12 (generated clock chains):** Checker's `Clocks` metric counts **primary clocks only**
  (`Generated clocks` is a separate metric) — the earlier "3 clocks expected" assumption was
  wrong for that metric. The genuine defect is the **converter returning period 0.0** for
  generated clocks (no master-period derivation). Clock-relations chain resolution
  (`-master_clock` and pin-linked `-source`) is **correct**: 3 pairs, all synchronous, 0 missing.
  Note `-divide_by 2` **doubles** the period (5.0 → 10.0), which the module does correctly.
- **SDC-006** fires correctly for a design with no `set_output_delay` (verified in UI and backend).

---

## 3. FALSE POSITIVES IN PREVIOUS BENCHMARK

Important — these were **not** validator bugs:

| Earlier claim | Corrected verdict | Evidence |
|---|---|---|
| "Inline comments corrupt parsing" | **FALSE POSITIVE** — only **full-line** comment-only lines create phantoms; trailing comments after commands parse fine | F02 passes (1 clock, 0 errors) |
| "Generated clocks not parsed at all / 3 clocks expected" | **FALSE POSITIVE (partially)** — checker counts primary+generated in separate metrics by design; clock-relations resolves chains correctly. Real defect is **converter period=0.0** only | c11/c12 now fail *only* on converter periods |
| "UI state leaks between inputs" (ISO-04 initially failed) | **FALSE POSITIVE** — SDC-006 legitimately fires on the second input; the app was right, my test expectation was wrong | after correction: 6/6 pass |
| "`.25` leading-dot is a parser failure" | **AMBIGUOUS/LOW** — `.25` is invalid Tcl anyway; period parse is correct; only the delay regex has a minor quirk | F07 |

---

## 4. PARSER ARCHITECTURE FINDINGS (duplicated parsing)

```
Raw SDC
   ├─ checker.py            ── line/command regexes (no comment strip, no line-join)
   ├─ converter.py          ── independent regex parse (no comment strip, no line-join)
   ├─ linter.py             ── independent regex parse
   ├─ clock_relations.py    ── own parse + line-join for groups ONLY
   ├─ constraint_diff.py    ── own parse + line-join + tcl_resolver (the only consumer)
   ├─ coverage.py           ── independent regex parse
   └─ mmc.py / reporter.py / custom_rules.py / wildcard_analyzer.py — more regex
```

**There is no shared preprocessing or parsing layer.** Six+ modules independently regex the raw
text. Consequences proven by this phase:

1. **Line continuation is handled by `clock_relations._parse_existing_groups` and
   `constraint_diff` only** — checker and converter drop continuation content (F03/F04).
2. **Comment stripping exists nowhere** (F01).
3. **Tcl variable resolution exists only in `constraint_diff`** (F09).
4. **Number regexes `[\d.]+` are duplicated verbatim** in checker, converter, clock_relations —
   identical sci-notation bug in all three (F05).
5. **Inconsistent interpretation across modules for the same syntax** is *proven*:
   - `2.5e-1`: checker and converter both read 2.5; clock_relations drops the clock entirely
     (clocks=[]) — three different behaviors from one input.
   - Multiline `create_clock`: checker finds a clock (broken), converter `('', 0.0, '')`,
     clock_relations finds nothing — three different results.
   - Generated-clock periods: clock_relations derives them (correct), converter returns 0.0.

**Conclusion:** the duplicated-parsing architecture is directly causing correctness divergence.
A shared preprocessing layer (comment strip → line-join → variable resolution → shared
command-parsing primitives) would fix F01/F03/F04/F05/F09 and eliminate cross-module drift.
This is *proven* by the F05/F03 three-module divergence above, not assumed.

---

## 5. CONFIRMED BUG BACKLOG (priority order)

| Priority | ID(s) | Bug | Modules | Fix size |
|---|---|---|---|---|
| **P0** | F01/c01/c19 | Comments parsed as commands → phantom constraints, wrong clock counts | checker, converter, clock_relations | S (shared preprocessor) |
| **P0** | F03/c03 | Multiline `\` commands lose name/period/port | checker, converter | S (line-join prepass) |
| **P0** | F05/c06 | Scientific notation truncated (`2.5e-1` → `2.5`) | checker, converter, clock_relations | S (number regex) |
| **P1** | F04/c20 | Continuation-line `-min` missed → false SDC-028 | checker | S (same prepass) |
| **P1** | F09/c08 | Tcl variables unresolved (except diff) | checker, converter, clock_relations | M (wire tcl_resolver) |
| **P1** | F10/c22 | SDC-007 misses `data_in` (word-boundary) | checker | XS (regex fix) |
| **P1** | F11/c15 | Braced clock-group lists misparsed → 3 phantom "missing" | clock_relations | XS (strip braces) |
| **P1** | F12/c21 | Flag-first `set_clock_uncertainty` value missed (SDC-023 dead) | checker | XS (option-order regex) |
| **P2** | F13 | No conflict detection (false_path vs max_delay etc.) | checker | L (new rule family) |
| **P3** | F07/F14 | Leading-dot delay quirk; SDC-020 noise on standard reset FPs | checker | XS/S |
| **P3** | — | 30× deprecated `use_container_width` (removal after 2025-12-31) | app.py, ui/* | S (mechanical) |

P0 = correctness/data corruption · P1 = major semantic errors · P2 = incomplete validation ·
P3 = UX/noise/maintenance.

---

## 6. RULE-PURPOSE CLASSIFICATION (requested item 6)

| Rule | Purpose | Current behavior | Correct classification |
|---|---|---|---|
| SDC-007 Clock on Data Port | heuristic warning (D) | regex misses snake_case ports | heuristic — not a syntax error |
| SDC-008/009 I/O delay ≥ period | semantic correctness (B) | correct for plain decimals; wrong for sci-notation | semantic rule — number parsing is the bug |
| SDC-020 Suspicious False Path | heuristic advisory (D) | noisy on standard reset FPs | heuristic, not parser failure |
| SDC-021/022/023 multicycle/uncertainty | semantic/heuristic (B/C) | SDC-023 unreachable for flag-first syntax | rule fine; regex order bug |
| SDC-024/062 clock groups | best-practice (C) + advisory (E) | counts phantom pairs when braces misparsed | misparse is the bug |
| SDC-028/029 I/O -min missing | completeness heuristic (C) | false positive on multiline | parsing bug, not rule bug |
| SDC-030 propagated clock | best-practice (C) | consistent | expected |

Heuristic/advisory rules firing "noisily" on valid input should not be labeled parser failures —
but the F01/F03/F05 family **are** parser failures because they corrupt the underlying parse.

---

## 7. GOLDEN BENCHMARK SUMMARY

- **Total golden cases: 22** (`benchmarks/golden/`)
  - Parser cases: 8 (01_comments×2, 02_multiline×2, 03_numeric_formats×3, 04_variables×1)
  - Clock cases: 6 (05_primary_clocks×2, 06_generated_clocks×2, 07_clock_groups×3)
  - I/O cases: 1 (08_io_delays×1)
  - Exception cases: 1 (09_timing_exceptions×1)
  - Malformed cases: 1 (10_malformed×1)
  - Regression cases: 4 (12_regressions×4) + 1 state-isolation file
- **Machine-readable manifest:** `benchmarks/golden/manifest.json` — each case has
  `id / input / purpose / expected / classification / confidence / reference`
  (expected = correct SDC behavior, *not* current tool output).
- **Deterministic runner:** `benchmarks/run_golden.py` → `benchmarks/golden/results.json`.
- **Current status: 10/22 match correct behavior; the 12 failures are the verified bug backlog
  and will flip to pass as production is fixed.**
- Every confirmed-bug case is a permanent regression test.

---

## 8. NEXT IMPLEMENTATION PLAN (safe order)

1. **Shared SDC/Tcl preprocessing module** (highest ROI — fixes F01, F03, F04, F05 root causes
   in one place): comment stripping (respecting Tcl rule 10: `#` starts a comment only at start
   of command), backslash-newline joining (rule 9), and a shared `parse_number()` accepting
   `10 / 10.0 / 0.25 / 2.5e-1 / 1E+2 / -0.25`. Wire it into checker, converter, clock_relations,
   coverage first; constraint_diff already has its own.
2. **Adopt `tcl_resolver` in checker/converter** for `$VAR` substitution before the new
   preprocessor runs (F09).
3. **Regex fixes:** SDC-007 port-name detection (match `data`/`addr` as substrings of
   `data_in`), uncertainty flag-order tolerance, brace-stripping in group parsing (F10, F11, F12).
4. **Re-run golden suite** — each of the 12 failing cases is the acceptance test.
5. **Deploy check:** re-enable public access on Streamlit Cloud (auth wall) and re-run the
   browser-level UI pass against the deployed instance.

**Do NOT** build a full Tcl interpreter — the architecture only needs the subset above, and the
project's own `tcl_resolver` already covers variable binding.

---

## 9. SUCCESS CRITERIA — ANSWERS

- **Genuinely correct findings:** F01, F03, F04, F05, F10, F11, F12 (7 confirmed bugs); F09, F13
  (2 confirmed limitations). All have minimal reproducers in `benchmarks/verify_findings.py`
  and golden cases.
- **False positives:** inline comments, "generated clocks not parsed", "UI state leakage",
  leading-dot period.
- **Limitations vs bugs:** documented in §2 and §6.
- **Cross-module impact:** F01/F03/F05 affect checker + converter + clock_relations (proven
  divergence); F09 affects all but diff.
- **Semantics-backed expectations:** all golden expectations cite Tcl(n)/SDC command grammar;
  `-divide_by 2` period-doubling verified.
- **Trustworthy regression set:** the 12 failing golden cases + 22 total.
- **Safest fix order:** shared preprocessor first (§8), with golden cases as acceptance tests.
