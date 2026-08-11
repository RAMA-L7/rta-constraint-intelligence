# SDC Validator — End-to-End QA Benchmark Report

**Date:** 2026-08-04 · **App version:** v1.3.0 (local repo `main` == deployed instance)
**Executed by:** Senior QA / SDC-STA benchmark
**Suite:** `benchmarks/` (re-runnable: `run_benchmark.py`, `test_ui_app.py`)

---

## 1. Executive Summary

The SDC Validator is a solid, stable tool: **no crashes** were provoked across 61 SDC
inputs (including garbage, empty, malformed, 3000-line files), the shipped unit suite
passes **330/330**, and the web UI passed **33/33 headless AppTest checks**. Core error
detection (SDC-001…011, SDC-020…037, SDC-060) works correctly on well-formed inputs.

However, the benchmark exposed **2 critical correctness bugs** that produce false
positives on *valid* SDC files, **4 high-severity gaps** (missed detections /
mis-parsing), and **1 critical operational regression** (the deployed app is now
auth-gated). See §4 for the full inventory.

---

## 2. Feature Matrix

`Status`: ✅ PASS · ❌ FAIL · ⚠️ WARNING · 🔶 NOT TESTABLE · 💀 CRITICAL

### 2.1 Deployed web app (https://sdc-tools-8mxtuhwy5myvejdcmpuwbp.streamlit.app/)

| # | Feature | Test Input | Expected | Actual | Status | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| D1 | App boot / version | direct URL | v1.3.0 header | v1.3.0, 10 tabs render, checker prompt shown | ✅ | — | browser session 1 |
| D2 | Public accessibility | `curl` + browser UA | 200 page | **303 → share.streamlit.io/-/auth/app login** | 💀 | Critical | curl headers; became gated mid-session |
| D3 | Console hygiene | load page | no errors | 2× **404** (favicon/apple-touch-icon) | ⚠️ | Low | browser console |
| D4 | Deployed checker interactions | valid/invalid SDC | results | **not executable** — auth wall + browser tool limitation | 🔶 | — | see local evidence instead |

### 2.2 Local web UI (identical v1.3.0 code)

| # | Feature | Test Input | Expected | Actual | Status | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| L1 | Checker — valid SDC | 5-line golden SDC | 0E/1W/1C, "clean" verdict | 0E/1W(SDC-030)/12I/1C, ✅ | ✅ | — | browser + AppTest |
| L2 | Checker — duplicate clock + big delay | 6-line invalid SDC | SDC-002, SDC-008, SDC-028/029 | exactly those codes | ✅ | — | browser + AppTest |
| L3 | Checker — garbage input | `this is not sdc at all !!! ###` | SDC-001, no crash | SDC-001, no crash | ✅ | — | browser + AppTest |
| L4 | Checker — empty input | cleared paste | no crash, prompt returns | no crash | ✅ | — | browser + AppTest |
| L5 | Repeated Analyze clicks | re-click Run Check ×2 | stable results | stable | ✅ | — | browser + AppTest |
| L6 | Generator | defaults | 32-line SDC v2.2 | header `# MY_DESIGN.sdc`, 32 lines | ✅ | — | browser |
| L7 | Generator live validation | generated SDC | metrics | 0E/1W/12I/1C | ✅ | — | browser |
| L8 | Generator download | — | button | `⬇️ Download .sdc` present | ✅ | — | browser (AppTest can't see download_button) |
| L9 | Generator design-name binding | set name QA_TEST_CHIP | header updates | header updated | ✅ | — | browser |
| L10 | Linter | 4-line SDC | runs, formatted output | runs, formatted output + download | ✅ | — | AppTest |
| L11 | Converter (JSON + YAML) | valid SDC | structured output | JSON + YAML rendered, download present | ✅ | — | AppTest |
| L12 | Corner Mgr | Load Preset | corners populated | works | ✅ | — | AppTest |
| L13 | MMC SDC generate | 1 clock template | per-corner SDCs | generates, no exception | ✅ | — | AppTest |
| L14 | Diff V1/V2 | period 5.0→6.0 | fatal period change | fatal change detected | ✅ | — | AppTest |
| L15 | Clock relations tab | 2 async clocks + groups | pairs=1, matrix | pairs=1, matrix rendered | ✅ | — | AppTest |
| L16 | Coverage tab | valid SDC | score + report | score card + HTML report button | ✅ | — | AppTest |
| L17 | Rules reference | — | searchable rules | renders, search box present | ✅ | — | AppTest |
| L18 | Test Drive | built-in sample | full analysis | runs on sample | ✅ | — | AppTest |
| L19 | Feedback dashboard | — | renders | renders | ✅ | — | AppTest |
| L20 | File upload (sdc/tcl/txt) | file picker | reads file | widget present; **not drivable** by AppTest/browser-automation | 🔶 | — | tool limitation |
| L21 | Custom-rules YAML upload | YAML rules | results panel | widget present; **not drivable** | 🔶 | — | tool limitation |
| L22 | Download buttons (all tabs) | — | downloads | present in browser/code; AppTest can't inspect | 🔶 | Low | AppTest API gap |

### 2.3 Analysis engines (module-level benchmark, 61 inputs)

| # | Feature | Test Input | Expected | Actual | Status | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| M1 | Valid golden SDC | full_featured.sdc | 0E/0W | 0E/0W | ✅ | — | results.json |
| M2 | No clock | no_clock.sdc | SDC-001 | SDC-001 | ✅ | — | |
| M3 | No I/O delays | no_io_delays.sdc | SDC-005/006 | SDC-005/006 | ✅ | — | |
| M4 | Duplicate clock name | duplicate_clock_names.sdc | SDC-002 | SDC-002 | ✅ | — | |
| M5 | Generated clock missing source | generated_clock_no_source.sdc | SDC-003 | SDC-003 | ✅ | — | |
| M6 | divide_by + multiply_by | divide_and_multiply.sdc | SDC-004 | SDC-003+SDC-004 (extra FP) | ❌ | High | comment phantom, bug C1 |
| M7 | I/O delay ≥ period | io_delay_exceeds_period.sdc | SDC-008/009 | SDC-008/009 | ✅ | — | |
| M8 | Propagated virtual clock | propagated_virtual_clock.sdc | SDC-010 | SDC-010 | ✅ | — | |
| M9 | Bad case-analysis value | bad_case_analysis.sdc | SDC-011 | SDC-011 | ✅ | — | |
| M10 | Clock on data port `data_in` | data_port_clock.sdc | SDC-007 | **not flagged** | ❌ | High | bug C6 |
| M11 | Empty / comments-only | empty, only_comments | SDC-001 | SDC-001 | ✅ | — | |
| M12 | Extreme values | extreme_values.sdc | SDC-023 (100ns unc.) | **missed** (only SDC-026) | ❌ | Medium | bug C7 |
| M13 | Boundary `==` semantics | boundary_values.sdc | SDC-008 at 5.0≥5.0 | SDC-008 | ✅ | — | |
| M14 | Scientific notation | scientific_notation.sdc | SDC-008, period 0.25 | SDC-008 ×2 (phantom), period **2.5**, clock_relations **0 clocks** | ❌ | High | bugs C1+C4 |
| M15 | Multiline (continuation content) | multiline_continuation_content.sdc | clean (has -min) | **SDC-028/029 false positives**, converter period lost, clock_relations 0 clocks | ❌ | High | bug C2 |
| M16 | Unicode BOM / CRLF / inline comments | unicode_bom, crlf_endings, inline_comments | clean, no crash | 0E, no crash | ✅ | — | |
| M17 | Uppercase commands | uppercase_commands.sdc | SDC-001 | SDC-001 | ✅ | — | |
| M18 | Tcl variable indirection | tcl_variables.sdc | SDC-008 ($IN_DLY 6.0 ≥ 5.0) | **missed**; clock_relations 0 clocks | ❌ | High | bug C3 |
| M19 | Comment mentioning commands | comment_mentions_commands.sdc | clean (valid file) | **SDC-002 + SDC-008** | 💀 | Critical | bug C1 |
| M20 | Generated clock chain (-master_clock) | generated_clock_chain.sdc | 0/0 | 0/0 | ✅ | — | |
| M21 | Generated chain via pins only | generated_clock_pin_source.sdc | 0/0 | 0/0 | ✅ | — | |
| M22 | Async without groups | two_async_no_groups.sdc | SDC-024 + info | + SDC-031 FP (comment) | ❌ | High | bug C1 |
| M23 | Async declared correctly | async_groups_correct.sdc | 0/0 | 0/0 | ✅ | — | |
| M24 | Async but physically exclusive | async_vs_physical_wrong.sdc | SDC-060 | SDC-060 | ✅ | — | |
| M25 | Same-port clocks / duplicates | same_port_two_clocks, duplicate_clocks_same_port | physical/duplicates | as expected | ✅ | — | |
| M26 | Braced group lists `{a b c}` | three_clocks_mixed, full_featured | 0 missing | **miss=2 false positives** | ❌ | Medium | bug C5 |
| M27 | False paths (legit reset/CDC) | false_paths_valid.sdc | 0× SDC-020 | SDC-020 fires | ⚠️ | Low | bug C8 |
| M28 | Multicycle + hold / no hold | multicycle_with_hold, no_hold | none / SDC-021 | as expected | ✅ | — | |
| M29 | Half-cycle no hold | half_cycle_no_hold.sdc | SDC-037 | SDC-037 | ✅ | — | |
| M30 | max_delay ± datapath_only | max_delay_*.sdc | none / SDC-027 | as expected | ✅ | — | |
| M31 | Disable timing spam | disable_timing_broad.sdc | SDC-035 + 6×SDC-036 | as expected | ✅ | — | |
| M32 | I/O delay variants | io_delays_full, max_only, clock_fall_add, driving_cell | none / SDC-028/029 | as expected | ✅ | — | |
| M33 | Garbage binary | garbage_binary.sdc | no crash | no crash (garbage `create_clock` counts as clock) | ⚠️ | Low | bug C10 |
| M34 | Conflicting constraints | conflicting_constraints.sdc | conflict flagged | **not detected** (only individual warnings) | ⚠️ | Medium | bug C11 |
| M35 | Large design (24 clocks) | many_clocks.sdc | completes | 24 clocks/276 pairs/65 ms | ✅ | — | |
| M36 | Large design (3005 lines) | large_repeated.sdc | completes | 1001 warnings/710 ms | ✅ | — | |
| M37 | Regression samples | samples/ via Test Drive | see doc | **doc drift** (buggy→SDC-001/011; warning_heavy→SDC-008/009) | ❌ | Low | bug C12 |

---

## 3. Summary Statistics

| Metric | Count |
|---|---|
| Features/cases discovered & executed | **100+** (61 SDC inputs × 5–7 engines + 33 UI checks + 9 deployed-app checks) |
| Total tests executed | **~415** (61 file-benchmarks × engines + 33 AppTest UI + 9 deployed HTTP/browser + 330 unit) |
| Passed | ~400 |
| Failed | 9 (M6, M10, M14, M15, M18, M19, M22, M26, D2 + regression drift M37) |
| Warnings | 8 (D3, M27, M33, M34 + low-severity notes) |
| Not testable | 4 (D4, L20, L21, L22 download inspection) |
| Critical bugs | 2 (C1 comment-as-command; D2 deployed auth-gate) |
| High bugs | 4 (C2 multiline drop; C3 Tcl vars; C4 scientific notation; C6 SDC-007 data_in) |
| Medium bugs | 4 (C5 braced groups; C7 SDC-022/023 dead rules; C11 no conflict detection; C13 use_container_width) |
| Low bugs | 5 (C8 SDC-020 noise; C9 unsupported cmds silent; C10 garbage clock; C12 doc drift; D3 404s) |

---

## 4. Bug Inventory

### 💀 Critical

**C1 — Comments are parsed as commands (no comment stripping).**
Every analyzer runs regexes over the raw text without stripping `#` comments. A
comment that mentions a command name (or a commented-out constraint, extremely common
in real SDCs) becomes a *phantom command*:
- `comment_mentions_commands.sdc` (valid) → **SDC-002 duplicate clock + SDC-008** errors.
- `divide_and_multiply.sdc` → phantom `create_generated_clock` from comment → bogus SDC-003.
- `two_async_no_groups.sdc` → phantom `set_clock_groups` from comment → bogus SDC-031.
- `scientific_notation.sdc` → phantom `set_input_delay 9.0` from comment → duplicated SDC-008.
- `data_port_clock.sdc` → phantom `create_clock` from comment → SDC-024 + double-counted
  clocks in converter (`2 clocks`) and clock_relations.
**Fix direction:** strip `# …` to end-of-line before analysis (respecting Tcl quoted strings).

**D2 — Deployed app became auth-gated mid-benchmark.**
Root URL + `/_stcore/health` now 303 → `share.streamlit.io/-/auth/app` (even with a
browser User-Agent). It was publicly loadable earlier in the session (v1.3.0 rendered).
Action: verify Streamlit Community Cloud **Share → Authentication** settings / app
visibility; re-enable public access or document that login is now required.

### 🔴 High

**C2 — Backslash-continuation content is silently dropped.**
Checker grabs like `set_input_delay[^;\n]*` stop at the newline, so `-min/-clock`
flags on continuation lines are lost → **SDC-028/029 false positives** on valid
multiline SDC; converter loses `-period`/ports (period 0.0); clock_relations finds
**0 clocks**. Evidence: `multiline_continuation_content.sdc`.

**C3 — Tcl variables unresolved by the checker.**
`set_input_delay -max $IN_DLY` (=$6.0) vs `-period $CLK_PERIOD` (5.0) → SDC-008
**silently missed**; clock_relations/converter lose the clock. `tcl_resolver.py`
exists but is only wired into the constraint diff. Evidence: `tcl_variables.sdc`.

**C4 — Scientific-notation values mis-parsed.**
`-period 2.5e-1` → period read as **2.5** (the `[\d.]+` regex stops at the `e`). The
SDC-008 message reports wrong numbers, and clock_relations finds **0 clocks**.
Evidence: `scientific_notation.sdc`.

**C6 — SDC-007 misses ports like `data_in`.**
`\b(data|addr|…)\b` requires a word boundary; `data_in` (underscore is a word char)
is not matched. Only exact `data`/`addr` names are flagged. Evidence: `data_port_clock.sdc`.

### 🟡 Medium

**C5 — Braced clock-group lists not handled.**
`-group [get_clocks {a b c}]` — braces are not stripped, so the 1st/last names become
`{a` / `c}` and the pair is reported **missing** (SDC-062 info false positive).
Evidence: `three_clocks_mixed.sdc` (miss=2), `full_featured.sdc` (miss=2).

**C7 — SDC-022/SDC-023 are dead rules for standard syntax.**
`set_clock_uncertainty\s+([\d.]+)` only matches when the value directly follows the
command. Standard `-setup 0.15 -hold 0.08` syntax is never matched → a **100 ns**
uncertainty is not flagged. Evidence: `extreme_values.sdc`.

**C11 — No conflicting-constraint detection.**
`set_false_path` + `set_max_delay` on the same path, or two contradictory
`set_clock_groups` for the same pair, produce only independent warnings.
Evidence: `conflicting_constraints.sdc`.

**C13 — 30× deprecated `use_container_width` (app.py + ui/*).**
Streamlit logs removal after 2025-12-31. A Streamlit Cloud upgrade past that point
can break the deployed app at runtime. Migration: `width='stretch'`.

### 🟢 Low

**C8 — SDC-020 is noisy.** Legit reset (`rst_n`) / CDC false paths warn unless the
target literally contains `async`/`scan`/`test`. Evidence: `virtual_clock_io.sdc`,
`false_paths_valid.sdc`.
**C9 — Unsupported commands silently ignored.** `set_max_time_borrow`,
`set_clock_sense`, etc. produce no feedback at all. Evidence: `unsupported_commands.sdc`.
**C10 — Permissive clock regex.** Garbage `create_clock 5.0 [get_ports` counts as a
clock and suppresses SDC-001. Evidence: `garbage_binary.sdc`.
**C12 — Test Drive sample descriptions drift.** `buggy_no_clocks` doc says SDC-005/006
(actual SDC-001/011); `warning_heavy` doc says warnings (actual also SDC-008/009
**errors**); `edge_case_extreme_values` says SDC-005 (actual + SDC-006).
**D3 — 2× 404 assets** on deployed app (missing favicon/apple-touch-icon).
**UX — Line numbers mostly 0** on issues (poor source attribution).
**UX — Info flood:** 20+ SDC-1xx info items per file; clock-relations aggregation
helps but linter/converter noise remains.

---

## 5. Missing Validation Coverage (gaps)

1. **Syntax validation** of unknown/unsupported Tcl commands (silently ignored).
2. **Referenced-clock existence** — `-clock SomeUndefined` is never checked.
3. **Duplicate-constraint detection** within a file (repeated identical `set_input_delay`).
4. **`set_clock_groups` conflict detection** (async + physically_exclusive for same pair).
5. **Tcl evaluation / variable indirection** in the checker (and `-waveform`,
   `-add`, `-invert` semantics).
6. **Units conversion / scientific notation** for periods and delays.
7. **Library-aware checks** (driving-cell existence, max-fanout feasibility).

## 6. Incorrect SDC Interpretations (correctness risks)

| Interpretation | Where | Risk |
|---|---|---|
| Comment lines treated as commands | checker, converter, clock_relations | false errors/warnings on real files |
| Continuation-line flags dropped | checker, converter, clock_relations | false SDC-028/029, missed period/ports |
| `2.5e-1` → 2.5 | checker, converter, clock_relations | wrong numbers, missed clocks |
| `$VAR` → period 0.0 / no clock | checker, converter, clock_relations | missed violations |
| `{a b c}` group list → `{a`, `c}` | clock_relations | false "missing" reports |
| `data_in` ≠ data port | checker SDC-007 | missed data-port clocks |

## 7. UI/UX Problems

- Error/warning counts and verdict are correct, but issue **line numbers are 0** for most codes.
- Warnings fire on common legitimate patterns (SDC-020, SDC-030, SDC-031) → noise.
- 20+ info suggestions per file is overwhelming; no "dismiss" persistence across reruns.
- Deprecation-warning spam from `use_container_width` in server logs.
- Sample "what to expect" descriptions are inaccurate for 4 of 6 samples.

## 8. Performance & Stability

- **No crashes** across all malformed/edge inputs (including `\x00`-free garbage, BOM, CRLF, 3005-line file).
- 3005-line / 1000-exception file: **710 ms** (checker), 24-clock design: **65 ms**.
- Clock-relations pair count grows O(n²) (276 pairs @ 24 clocks, 264 info entries) — fine for
  typical designs, but a 100-clock design would produce ~5k info entries (aggregation in the
  checker helps; the Clock tab still lists them all).

## 9. Regression Risks

- **Streamlit upgrade** (use_container_width removal) could break the deployed app.
- **Fixing C1/C2** (comment stripping, continuation joining) will change counts/messages that
  several existing unit tests and the Test Drive sample descriptions assume — update together.
- **Deployed auth** change is an operational regression independent of code.
- **SDC-022/023 fix** will newly flag high-uncertainty SDCs that currently pass.

## 10. Recommendations (fix only on request)

1. Strip comments before analysis (C1) and join backslash continuations (C2) — both in a
   shared pre-processing step; update unit tests + sample descriptions (C12).
2. Wire `tcl_resolver` into the checker for `$VAR` resolution (C3).
3. Harden number parsing (scientific notation, C4) and the SDC-007 word boundary (C6).
4. Fix SDC-022/023 flag-first matching (C7), strip braces in clock groups (C5).
5. Add syntax/unknown-command and conflicting-constraint checks (C11, coverage gaps).
6. Replace `use_container_width` with `width='stretch'` (C13).
7. Re-check deployed app auth settings (D2).

*Suite artifacts: `benchmarks/` (61 SDC inputs + runner + AppTest UI benchmark),*
*`benchmarks/results/results.json` (machine-readable), `benchmarks/README.md` (case expectations).*
