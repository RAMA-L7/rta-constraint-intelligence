# Phase 7 — Support Boundary, Netlist-Dependent Analysis & Trust Transparency

## 1. Multi-Agent Summary

| Agent | Responsibility | Outcome |
|---|---|---|
| **A — SDC Coverage Researcher** | Inventory SDC commands/options from authoritative refs (Accellera SDC 2.1 / Synopsys-style) | Produced the option sets in `support_boundary.py` STANDARD_OPTIONS (48 commands) |
| **B — Netlist/STA Semantics Engineer** | Determine which checks fundamentally need design context | Defined NETLIST_COLLECTION_FNS (get_ports/get_pins/get_cells/get_nets/get_clocks/all_*/filter_collection/…) and NETLIST_QUERY_COMMANDS (current_design/current_instance) |
| **C — Code Capability Auditor** | Map actual implementation against claimed support | Traced checker.py/_grab inventory, linter.py COMMAND_CATEGORY (40+ commands), coverage.py items, converter.py parsing → RECOGNIZED_COMMANDS = union of what modules actually parse |
| **D — Adversarial QA** | Build cases where unsupported/netlist syntax could look "clean" | `benchmarks/test_trust_transparency.py` (8/8) + `benchmarks/test_no_false_confidence.py` (6/6) |
| **E — UX/Trust Engineer** | Least-noisy way to expose limitations | One collapsible "Analysis Coverage" expander in Checker tab + CLI scope lines + report section — no issue-list flooding |
| **F — Independent Reviewer** | Challenge classifications + wording | Found 3 classification fixes (see §5) and the `-waveform` / `set_units` data-table corrections; all applied |

**Disagreement resolution:** the reviewer claimed `-waveform` on `create_clock`
was "ignored"; evidence (constraint_diff.py parses `-waveform` for change
detection) showed it is credited → classification updated, and the two unit
tests + one benchmark case that encoded the old classification were corrected.

## 2. Baseline (before changes)

- pytest: 409/409 · parser golden: 22/22 · semantic golden: 9/9 · reference designs: 8/8
- UI: 33/33 · state isolation: 6/6 · security: 5/5 · stress: 21/21 · corpus: 61 files

## 3. SDC Command Support Matrix

Full matrix generated at `benchmarks/support_matrix.md` (44 commands; `support_boundary.py` is the source of truth). Summary:

| Level | Command count | Meaning |
|---|---|---|
| **FULL** | e.g. `set_sdc_version`, `set_units`, `set_case_analysis` (presence-only semantics) | validator's rules cover the whole documented option surface it claims |
| **PARTIAL** | e.g. `create_clock` (-add/-comment ignored), `set_input_delay` (-rise/-fall/-add_delay ignored), `set_clock_uncertainty` (-clock/-source/-from/-to ignored for value analysis) | recognized, core options value-analyzed, some options silently ignored |
| **NETLIST_REQUIRED** | `current_design`, `current_instance`, and every command with `[get_*]`/`all_*` refs | object resolution needs design context |
| **UNSUPPORTED** | `set_clock_sense`, `set_ideal_latency`, `set_ideal_transition`, `set_min_transition` (standard SDC, no module parses) | recognized as standard but not analyzed — never silently "clean" |

## 4. Tcl Support Matrix

| Construct | Level | Notes |
|---|---|---|
| `set NAME VALUE` scalar assignment | FULL | bounded subset since Phase 4, order-aware, `${NAME}` supported |
| `$VAR` / `${VAR}` substitution | FULL | deterministic, unresolved tokens preserved (never 0/empty) |
| `if`/`foreach`/`for`/`while`/`proc`/`source`/`exec`/`eval`/`expr`/`list`/`concat`/… | TCL_EXECUTION_REQUIRED | never executed; surfaced in scope |
| `[expr …]`/`[exec …]`/`[source …]` inline | TCL_EXECUTION_REQUIRED | `_INLINE_TCL_RE`; inert text to the validator |
| `set sdc_version` | FULL | normalized to `set_sdc_version` |

## 5. Silent-Ignore Findings (highest-priority audit)

| Construct | Silent-ignore today | Classification | Action |
|---|---|---|---|
| `create_clock -waveform` | **no longer ignored** — constraint_diff.py parses it | FULL-credited | credited in INTERPRETED_OPTIONS |
| `create_clock -add/-comment` | ignored | PARTIAL (honest) | surfaced via scope.ignored_options |
| `set_input_delay -rise/-fall/-add_delay` | ignored | PARTIAL | surfaced |
| `set_clock_uncertainty -clock/-source/-from/-to` | ignored for value analysis | PARTIAL | surfaced |
| `set_clock_latency/transition` (all options) | presence-only | PARTIAL | surfaced |
| `set_clock_sense` | not parsed by any module | **UNSUPPORTED** — must not look clean | surfaced (reviewer-confirmed) |

**Principle applied:** an ignored option that "materially changes semantics" is
never presented as fully understood; every such command contributes to
PARTIALLY_VALIDATED with the option names listed.

## 6. Netlist-Dependent Boundary

Cannot be proven from SDC alone (documented in scope, never faked):
- whether `[get_ports foo]` / `[get_pins a/b/D]` actually resolve
- whether wildcard collections are empty
- whether a timing path actually exists / exceptions overlap
- whether clocks reach sequential elements
- whether generated-clock `-source` objects exist
- unconstrained-port truth
- electrical-vs-library matching

→ Architecture proposal for an optional design-object inventory:
`benchmarks/PHASE7_NETLIST_AWARE_PROPOSAL.md` (research only, not implemented).

## 7. Trust Status Model

Two independent dimensions — severity ≠ trust status:

| Status | Meaning |
|---|---|
| `VALIDATED` | every construct fully analyzed within scope |
| `PARTIALLY_VALIDATED` | recognized commands had ignored/unknown options |
| `NETLIST_REQUIRED` | object refs need design context (not an error) |
| `TCL_EXECUTION_REQUIRED` | static scope insufficient (never executed) |
| `UNSUPPORTED` | unrecognized command present |
| `NOT_VALIDATED` | nothing analyzable in input |

Precedence: `UNSUPPORTED > TCL_EXECUTION_REQUIRED > PARTIALLY_VALIDATED > NETLIST_REQUIRED > VALIDATED > NOT_VALIDATED`.

## 8. Analysis Coverage Design

Machine-readable `AnalysisScope` (dict-serializable) attached to every
`CheckResult` as `result.scope`, with `summary_lines()` for humans:

```
Commands found: 25   Fully analyzed: 3   Partially analyzed: 3
Netlist-dependent references: 13   Unsupported commands/Tcl: 0
Options present but not value-analyzed: -from, -lib_cell, -pin, -source, -to
```

Transparent counts only — no fabricated confidence percentage.

## 9. UI Implementation (Checker tab)

One collapsible **"Analysis Coverage"** expander (never floods the Issues
list): trust-status markdown (VALIDATED/PARTIALLY_VALIDATED/NETLIST_REQUIRED/
UNSUPPORTED/TCL_EXECUTION_REQUIRED) + the four count metrics + ignored-option
line. Verified by UI benchmark checks CHK-06/CHK-07 (35/35 now).

## 10. Report Implementation

Generated HTML check reports include an **Analysis Scope** section (with a
"Trust status" line) listing the same counts and ignored options — so a
downloaded report always discloses what was and was not analyzed. CLI `check`
prints the same disclosure. JSON output gains `scope`.

## 11. Adversarial Trust Results

`benchmarks/test_trust_transparency.py` — **8/8**: one unsupported construct,
one netlist-dependent reference, one unknown option, one supported command
with an unsupported option, one unsupported Tcl expression, plus valid inputs —
every case surfaces its limitation; the dangerous "unsupported semantics but
says clean" failure never occurs.

## 12. No-False-Confidence Benchmark

`benchmarks/test_no_false_confidence.py` — **6/6**. For each case: Q1 (did the
validator fully understand?) and Q2 (is the limitation visible in scope +
summary + generated HTML report?). "Validator found no problems" is now
permanently distinguishable from "everything was fully analyzed."

## 13. Full Regression Results

| Suite | Before | After |
|---|---|---|
| pytest | 409/409 | **436/436** (+27 support-boundary tests) |
| Parser golden | 22/22 | 22/22 |
| Semantic golden | 9/9 | 9/9 |
| Reference designs | 8/8 | 8/8 |
| Trust transparency | — | 8/8 |
| No-false-confidence | — | 6/6 |
| UI benchmark | 33/33 | **35/35** (CHK-06/07 added) |
| State isolation | 6/6 | 6/6 |
| Security | 5/5 | 5/5 |
| Preprocessor stress | 21/21 | 21/21 |

No existing deterministic result changed; all additions are additive scope
metadata.

## 14. Files Modified

| File | Change |
|---|---|
| `support_boundary.py` | **new** — trust/coverage model: STANDARD_OPTIONS (48 cmds), INTERPRETED_OPTIONS, RECOGNIZED_COMMANDS, STANDARD_UNRECOGNIZED, NETLIST_COLLECTION_FNS, TCL_EXECUTION_REQUIRED, `analyze_scope()`, `AnalysisScope`, `ConstructStatus` |
| `checker.py` | attaches `scope` (dict) to `CheckResult` |
| `reporter.py` | "Analysis Scope" + "Trust status" disclosure section in HTML reports |
| `app.py` | "Analysis Coverage" collapsible expander in Checker tab |
| `cli.py` | `Analysis scope:` disclosure line in text + JSON output |
| `tests/test_support_boundary.py` | **new** — 27 tests (status precedence, option audit, checker integration, no-false-confidence) |
| `benchmarks/test_trust_transparency.py` | **new** — 8 adversarial trust cases |
| `benchmarks/test_no_false_confidence.py` | **new** — 6 no-false-confidence cases (uses `-comment` after reviewer fix) |
| `benchmarks/generate_support_matrix.py` | **new** — emits `benchmarks/support_matrix.md` |
| `benchmarks/test_ui_app.py` | +CHK-06/CHK-07 expander checks |
| `benchmarks/PHASE7_NETLIST_AWARE_PROPOSAL.md` | **new** — research-only architecture proposal |
| `benchmarks/_probe_scope.py` | temporary probe (removed at end) |

## 15. Remaining Limitations

- General Tcl variable evaluation beyond scalars (loops/procs/expr) — documented as TCL_EXECUTION_REQUIRED, never executed.
- Cross-constraint conflict detection — intentionally deferred to a later phase.
- Netlist-dependent validation — proposed, not implemented (see §proposal).
- Unknown options are surfaced (PARTIAL) but not error-flagged by design.

## 16. Trust Statement

**"What does a clean SDC Validator result actually guarantee?"**

> A clean result guarantees: every command the validator recognizes was parsed
> and checked against its documented rules, no deterministic violation was
> found, and — since Phase 7 — the output explicitly discloses the analysis
> scope (fully analyzed / partially analyzed / netlist-required / unsupported /
> Tcl-execution-required). It does **not** claim: object references resolve in
> the real netlist, timing paths exist, or unanalyzed options are correct.

The distinction "Validator found no problems" vs "Validator was able to fully
analyze everything" is now explicit, machine-readable, and shown in the UI,
CLI, and every generated report.

## 17. Recommended Phase 8

1. **Optional design-object inventory** (from the proposal): start with a JSON
   context layer and reclassify NETLIST_REQUIRED → validated references where
   provable. Additive; SDC-only default unchanged.
2. **Cross-constraint conflict analysis** (deferred from Phase 5) — safe to
   attempt now that the trust model distinguishes "validated" from "partially
   validated", so conflict findings carry precise confidence.
3. Consider a UI summary line at the top of the Checker tab (not only the
   expander) showing the trust status badge for at-a-glance transparency.
