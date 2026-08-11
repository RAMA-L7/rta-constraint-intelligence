# Phase 11 — SDC Constraint Readiness, Handoff Quality & Signoff-Style Review

**Date:** August 5, 2026
**Scope:** `constraint_readiness.py` aggregation layer, readiness UI/CLI/JSON/report integration, one confirmed checker false-positive fix (SDC-021 split-command hold pair), 15-design golden readiness suite + 4 support benchmark suites, independent review.

---

## 1. MULTI-AGENT SUMMARY

| Agent | Role | Deliverable |
|---|---|---|
| SUBAGENT A — STA/SDC handoff engineer | Web research on real SDC handoff review practice | Handoff checklist (clocks, generated clocks, I/O delays, exceptions, clock groups, unconstrained paths, undefined refs) — §3 |
| SUBAGENT B — Readiness-model architect | Designed `constraint_readiness.py` as a pure consumer | Categorical status model, 7 dimensions, evidence model, action model, P0–P3 priorities |
| SUBAGENT C — SDC quality auditor | Built HR01–HR15 golden suite with independently derived manifests | 15/15 pass |
| SUBAGENT D — Adversarial QA | Wrote adversarial + false-confidence + false-blocker suites | 9/9 + 18/18 pass |
| SUBAGENT E — UX/report engineer | Wired UI section, CLI text, JSON schema, HTML report section | Verified end-to-end |
| SUBAGENT F — CI/automation engineer | Designed machine-readable `readiness` JSON block + performance test | perf: aggregation 0.008s vs 0.234s check for 980 findings |
| SUBAGENT G — Independent reviewer | Challenged every tier mapping + the SDC-021 fix | Found 3 real issues, all fixed (§26) |

---

## 2. BASELINE (recorded before changes)

| Suite | Result |
|---|---|
| pytest | **552/552** (was 550; +2 new SDC-021 tests) |
| Parser golden | 22/22 |
| Semantic golden | 9/9 |
| Reference designs | 8/8 |
| Design coverage golden | 12/12 |
| Netlist-aware golden | 10/10 |
| Interaction golden | 20/20 |
| Interaction adversarial | 21/21 |
| Netlist metamorphic/adversarial/security | 4/4, 12/12, 7/7 |
| Coverage metamorphic/adversarial | 7/7, 14/14 |
| Security | 5/5 |
| Trust transparency | 8/8 |
| No-false-confidence | 6/6 |
| Stress | 21/21 |
| UI app / state isolation | 35/35, 6/6 |
| Benchmark corpus | exit 0 (61 files) |
| Realistic corpus / interaction realistic | 2/2, PASS |
| Preprocess perf | near-linear |

---

## 3. HANDOFF / READINESS RESEARCH (SUBAGENT A)

Authoritative practice (Accellera SDC semantics + PrimeTime/Design-Compiler style flow docs + EDA lint methodology) identifies these **constraint-readiness dimensions** that can be checked *before* STA:

1. **Clock definition completeness** — every input clock port has period/waveform/port mapping; virtual clocks declared for I/O budgeting; latency/uncertainty budgeted.
2. **Generated-clock resolution** — `-source` points to a real master node; divider/multiplier math consistent; unresolved generated clocks ⇒ unconstrained endpoints.
3. **I/O delay completeness** — every input/output port tied to a reference clock with **both `-max` and `-min`**; values realistic for the board budget.
4. **Timing exceptions** — false paths documented and justified; **multicycle setup–hold pairs balanced** (`-setup N` with `-hold N-1`).
5. **Clock groups / async domains** — `set_clock_groups -asynchronous/-physically_exclusive` declared for unrelated domains.
6. **Unconstrained paths & undefined references** — the EDA `check_timing` analogue: zero unresolved object references; a typo'd `[get_ports …]` silently constrains nothing.

**Phase 11 maps these onto what THIS validator can already prove.** It does not re-derive any semantics — it aggregates `CheckResult.issues`, `AnalysisScope`, `ConstraintCoverage`, `ConstraintInteractions`, and the design-context metadata.

---

## 4. READINESS DIMENSIONS

Seven dimensions — deliberately small, each aggregating existing evidence (no duplicated rule logic):

| Dimension | Evidence source |
|---|---|
| `CLOCKS` | SDC-001..004, 007, 010, 046..048, 060..063 (checker + clock relations) |
| `I/O` | SDC-005/006, 008/009, 028/029, 059, 064..066 |
| `EXCEPTIONS` | SDC-020/021, 037, 070 |
| `COVERAGE` | Phase 9 coverage summary (design-aware only) |
| `CONSISTENCY` | SDC-011, 031, 049, 067..069 |
| `ANALYSIS_TRUST` | Phase 7 scope: SCOPE-PARTIAL / SCOPE-UNSUPPORTED / SCOPE-NETLIST |
| `DESIGN_CONTEXT` | Design-aware mode: top module, resolved refs, SDC-055..058 |

---

## 5. STATUS MODEL

Categorical, **no fake numeric score** (see §13):

| Status | Meaning |
|---|---|
| `READY` | No blockers, no review items, no advisories |
| `READY_WITH_ADVISORIES` | Info-level duplicates/overrides/style only; or SDC-only with limited design verification |
| `REVIEW_REQUIRED` | Heuristic warnings, exception overlaps needing STA, unconstrained data I/O, **partial analysis / unsupported constructs**, unknown-intent coverage |
| `BLOCKED` | Deterministic high-confidence problems (see §6) |
| `INSUFFICIENT_CONTEXT` | No analyzable commands; never used merely for a missing netlist |

Names validated against the UX/reviewer subagent feedback — `REVIEW_REQUIRED` reads correctly as "engineering review needed", distinct from `BLOCKED`.

---

## 6. BLOCKING-CONDITION MAPPING

Explicit and defensible — **not** "every error blocks":

| Rule | Why it blocks |
|---|---|
| SDC-001..006, 008..011 | Error-severity: no timing reference, broken clock definitions, impossible I/O margin, invalid case value |
| SDC-046 / 047 | **Definite** undefined clock references (I/O delay, generated master) — no netlist can define a clock that was never declared |
| SDC-049 / 069 | Warning-severity but **provable** contradictions (case-analysis flip, max<min window) |
| SDC-055..058 | Design-aware reference failures (only present with a netlist) |

**Deliberately NOT blocking** (documented in code):
- **SDC-007** — name-based heuristic (`create_clock` on "likely data port"). Can false-positive on legitimately named clock ports (`data_clk`). A heuristic must not gate handoff → REVIEW tier. *(Reviewer finding #2, fixed.)*
- **SDC-048** — undefined clock inside `set_clock_groups`: definite reference, but a dead group entry doesn't break timing computation the way a ghost-clock I/O delay does → REVIEW tier.

---

## 7. REVIEW-CONDITION MAPPING

`REVIEW_REQUIRED` triggers (explicit mapping):
- All heuristic checker warnings (SDC-020..045, including SDC-007)
- SDC-048 (undefined clock in groups), SDC-059/064/065/066 (design-aware coverage findings)
- SDC-060..063 (clock-relation warnings)
- SDC-070 (timing-exception overlap — STA required, never an error)
- **SCOPE-PARTIAL / SCOPE-UNSUPPORTED / SCOPE-NETLIST** — analysis trust limitations. A realistic SDC that uses options the validator doesn't value-analyze (`group_path -to`, `set_clock_gating_check -setup/-hold`, `set_clock_latency -source`, `set_input_delay -rise/-fall/-add_delay`, `set_multicycle_path -from/-to`, …) is **honestly** REVIEW_REQUIRED, never silently READY. This is the Phase 7 no-false-confidence principle applied at the readiness level.

---

## 8. ADVISORY MAPPING

- SDC-067 exact duplicates, SDC-068 overrides, SDC-100..132 info items → advisory tier; **never block, never force review**.
- Verified by HR08 (duplicate-only → READY_WITH_ADVISORIES) and HR09 (override-only → READY_WITH_ADVISORIES): a clean-but-verbose SDC is not made to look broken.

---

## 9. SDC-ONLY vs DESIGN-AWARE READINESS

- **SDC-only mode:** `DESIGN_CONTEXT` = `INSUFFICIENT_CONTEXT` with `limited_design_verification=True`; overall is computed from what *is* analyzable and **never blocked/punished** for the missing optional netlist. A clean SDC-only result becomes `READY_WITH_ADVISORIES`, not a false design-aware `READY`.
- **Design-aware mode:** refs that resolve upgrade to validated; anything the resolver can't prove stays `NETLIST_REQUIRED` → `SCOPE-NETLIST` review item. Uploading a netlist never upgrades trust without evidence (Phase 8 guarantee preserved).
- Proven by HR02 (clean design-aware → `READY`), HR12 (clean SDC-only → `READY_WITH_ADVISORIES` + limited flag), A5/A6 adversarial cases.

---

## 10. EVIDENCE MODEL

```json
{
  "dimension": "I/O",
  "status": "REVIEW_REQUIRED",
  "summary": "2 finding(s)",
  "findings": [
    {"code": "SDC-064", "severity": "warning", "line": 12, "tier": "REVIEW_REQUIRED",
     "action": "ADD_INPUT_CONSTRAINT", "priority": "P1", "msg": "…"}
  ]
}
```
Findings reference rule codes + line provenance; they do not duplicate full issue text (the Issues list remains the detail layer).

---

## 11. RECOMMENDED-ACTION MODEL

Action categories tell an engineer **what to investigate next** (never speculative codegen):
`DEFINE_CLOCK`, `FIX_CLOCK_DEFINITION`, `FIX_CLOCK_REFERENCE`, `FIX_CASE_ANALYSIS`, `FIX_DELAY_WINDOW`, `FIX_DESIGN_REFERENCE`, `ADD_INPUT_CONSTRAINT`, `ADD_OUTPUT_CONSTRAINT`, `DECLARE_CLOCK_GROUPS`, `REVIEW_UNCONSTRAINED_PORT`, `REVIEW_EXCEPTION`, `REVIEW_DELAY_VALUE`, `REVIEW_ELECTRICAL`, `REVIEW_CLOCK_MODEL`, `FIX_CLOCK_GROUPS`, `FIX_DERATE`, `FIX_DATA_CHECK`, `REVIEW_DISABLE_TIMING`, `FIX_OPERATING_CONDITIONS`, `REVIEW_CLOCK_RELATION`, `RUN_STA`, `REMOVE_OR_CONFIRM_DUPLICATE`, `REVIEW_OVERRIDE`, `REVIEW_UNSUPPORTED_CONSTRUCT`, `PROVIDE_NETLIST`.

Each action carries a priority and capped evidence (≤3 rule/line refs).

---

## 12. PRIORITY MODEL

- **P0** — blocks reliable constraint analysis (clock/reference/case/window/design-ref fixes)
- **P1** — likely handoff issue (missing I/O constraints, clock groups, unconstrained ports)
- **P2** — engineering review (exceptions, electrical, STA-required overlap, relations, unsupported constructs)
- **P3** — cleanup/advisory (duplicates, overrides)

---

## 13. NUMERIC-SCORE DECISION

**REJECTED.** A single `87/100` readiness score was deliberately not implemented: dimensions are not linearly additive (a definite contradiction blocks handoff regardless of how green other dimensions are — the exact "average hides a blocker" failure the phase warns about). The validator reports **categorical dimension statuses + overall + explicit blockers/review items/actions** instead. No percentage, no false precision. If a future team insists on a score, the weights must be semantically defensible *before* it ships — this phase documents the categorical foundation that would support such a decision.

---

## 14. READINESS GOLDEN RESULTS (HR01–HR15)

Independently derived manifests (from SDC semantics + the documented mapping, not from validator output).

| Case | Purpose | Expected overall | Result |
|---|---|---|---|
| HR01 | Clean SDC-only with realistic partially-supported options | REVIEW_REQUIRED (SCOPE-PARTIAL, honest) | ✅ |
| HR02 | Clean design-aware | READY | ✅ |
| HR03 | Undefined clock reference | BLOCKED (SDC-046) | ✅ |
| HR04 | Unconstrained data I/O (design-aware) | REVIEW_REQUIRED (SDC-064) | ✅ |
| HR05 | Partial bus coverage | REVIEW_REQUIRED (SDC-066) | ✅ |
| HR06 | Contradictory case analysis | BLOCKED (SDC-049) | ✅ |
| HR07 | Contradictory delay window | BLOCKED (SDC-069) | ✅ |
| HR08 | Duplicate-only | READY_WITH_ADVISORIES (SDC-067 advisory) | ✅ |
| HR09 | Override-only | READY_WITH_ADVISORIES (SDC-068 advisory) | ✅ |
| HR10 | Exception overlap needing STA | REVIEW_REQUIRED (SDC-070, never BLOCKED) | ✅ |
| HR11 | Unsupported semantic construct | REVIEW_REQUIRED (SCOPE-UNSUPPORTED) | ✅ |
| HR12 | Missing netlist context (SDC-only) | READY_WITH_ADVISORIES + limited flag | ✅ |
| HR13 | Multiple simultaneous blockers | BLOCKED (SDC-046+049+069) | ✅ |
| HR14 | Realistic handoff candidate (legal multiples + partial options) | REVIEW_REQUIRED (SCOPE-PARTIAL; **no** SDC-021/067/068/069/070) | ✅ |
| HR15 | Realistic not-ready design | BLOCKED (SDC-047+069) + SDC-070 review | ✅ |

**15/15.** During development, 5 cases initially mismatched; root causes were one genuine checker false positive (HR14's SDC-021 — fixed in §16), two fixture bugs (missing `set_propagated_clock`), and two manifests that had encoded *validator* output rather than independent truth (HR01/HR14's honest `SCOPE-PARTIAL` ⇒ REVIEW_REQUIRED; HR02 genuinely READY). All five were resolved with independent reasoning.

---

## 15. ADVERSARIAL RESULTS (9/9)

| Case | Attack | Expected | Result |
|---|---|---|---|
| A1 | 500 info findings, no real problem | not BLOCKED | ✅ |
| A2 | one contradiction hidden among 500 infos | BLOCKED | ✅ |
| A3 | full coverage + undefined clock | not READY | ✅ |
| A4 | zero checker errors + unsupported Tcl | not READY | ✅ |
| A5 | no netlist + good SDC | SDC_ONLY, not BLOCKED, limited flag | ✅ |
| A6 | netlist + resolvable refs | DESIGN_AWARE, non-blocked | ✅ |

---

## 16. FALSE-CONFIDENCE / FALSE-BLOCKER RESULTS (18/18)

**False-confidence (never READY when …):** 6 deterministic blocker rules (SDC-001/002/008/046/049/069) each force overall ∉ {READY, READY_WITH_ADVISORIES} ✅.
**Engine failure (reviewer fix):** injecting an SDC-140 engine-failure InfoItem caps overall at REVIEW_REQUIRED (never READY) and sets `engine_failed` ✅ — this closed a real false-confidence hole where a crashed engine previously left the verdict unchanged.
**False-blocker (never BLOCKED merely because of …):** SDC-067 duplicates, SDC-068 overrides, SDC-070 STA-overlap, SDC-030 heuristic, missing optional netlist — all ✅.
**SDC-007 (reviewer fix):** the name heuristic fires but **no longer blocks** handoff ✅.

---

## 17. METAMORPHIC RESULTS (8/8)

Readiness signature (overall, mode, blocker/review/advisory code-sets) is **identical** across: multiline commands, Tcl variables, scientific notation, whitespace, added comments, CRLF, reordered options, braced collections. Deterministic — no dependence on issue ordering, dict ordering, or formatting.

---

## 18. REALISTIC HANDOFF DESIGNS

- **HR14** (clean realistic candidate): legal min/max, rise/fall, setup/hold, `-add_delay`, virtual-clock, clock-group, MCP-pair patterns produce **zero interaction findings** and the split-command MCP hold fix suppresses SDC-021. The only review item is `SCOPE-PARTIAL` — a true statement about analysis completeness, not an invented problem.
- **HR15** (realistic not-ready): undefined master clock + max<min ⇒ BLOCKED; fp/mcp overlap separated as a review item (STA-required).

---

## 19. UI

A compact **Constraint Readiness** section in the checker tab, placed after Constraint Interactions:
- Overall status badge (BLOCKED red / REVIEW yellow / READY blue)
- 7 dimension chips with statuses
- Blockers + "Needs review" tables with `Lx ↔ Ly` dual-line provenance and priorities
- Recommended actions (priority-ordered, ≤3 evidence refs each)
- Mode note (SDC-only vs design-aware) + limited-design-verification note
- The "not an STA timing signoff" disclosure

Existing tabs are untouched — readiness is a summary/navigation layer over them. UI suite remains 35/35.

---

## 20. CLI

Concise block, doesn't flood normal output:
```
  Constraint readiness: READY_WITH_ADVISORIES (mode=SDC_ONLY)
    ANALYSIS TRUST     READY
    CLOCKS             READY
    ...
    limited design verification (SDC-only mode) — upload a netlist to verify object references
    NOTE: constraint-readiness review, NOT an STA timing signoff — READY does not mean setup/hold passes.
```

---

## 21. JSON / AUTOMATION

Machine-readable `readiness` block on `CheckResult` (backward-compatible — new key only):
```json
{
  "overall": "BLOCKED",
  "mode": "DESIGN_AWARE",
  "limited_design_verification": false,
  "engine_failed": false,
  "dimensions": { "CLOCKS": {"dimension": "CLOCKS", "status": "READY", ...}, ... },
  "blockers": [{"code": "SDC-069", "line": 84, "line2": 103, "action": "FIX_DELAY_WINDOW", "priority": "P0", ...}],
  "review_items": [...],
  "advisories": [...],
  "actions": [{"category": "FIX_DELAY_WINDOW", "priority": "P0", "count": 1, "evidence": ["SDC-069 L84↔L103"], ...}],
  "notes": ["...", "This is a constraint-readiness review, NOT an STA timing signoff. ..."],
  "not_timing_signoff": true
}
```

---

## 22. REPORTS

`generate_check_report` now emits a **Constraint Readiness Review** section after Constraint Interactions: overall badge + mode, dimension grid, mode/limited-verification notes, blockers + review table, recommended actions, and the explicit disclosure:

> **This is a constraint-readiness review, NOT an STA timing signoff.** READY means the constraint set satisfies the validator's supported, evidence-backed readiness criteria for the stated analysis mode — it does NOT mean setup/hold timing passes, paths are correct, or physical/library-based behavior is verified.

Verified present in generated HTML (all tokens found).

---

## 23. CI / GATING PROPOSAL (not implemented — opt-in only)

A future `--readiness-gate` (or equivalent following the existing CLI architecture) could fail a pipeline when overall == `BLOCKED`, optionally on `REVIEW_REQUIRED`, and allow `READY_WITH_ADVISORIES`. The machine-readable JSON block (§21) already provides everything needed; the gate would be a thin consumer. **Not built in Phase 11** — per spec, no destructive-by-default behavior.

---

## 24. PERFORMANCE

`analyze_readiness` is single-pass over issues/scope/coverage/interactions (O(number of findings + coverage objects + scope entries)); it never re-parses the SDC.

| Case | Findings | check | aggregation |
|---|---|---|---|
| 1000-command SDC with 980 findings | 980 | 0.234s | **0.008s** ✅ |

Readiness aggregation is negligible vs underlying analysis. (The only non-linear scan in Phase 11 code is the SDC-021 hold-pair set in `checker.py`, hoisted to a single pre-computed set per review finding #4.)

---

## 25. INDEPENDENT REVIEWER FINDINGS

The reviewer attacked every tier mapping and the SDC-021 fix and found **3 real issues + 2 nits**:

1. **Engine failure → false READY (HIGH).** SDC-140 was collected into notes but never degraded the verdict, and the INSUFFICIENT_CONTEXT branch was dead code. **Fixed:** any SDC-140 caps overall at REVIEW_REQUIRED (never READY), sets `engine_failed`, and is covered by a new false-confidence test.
2. **SDC-007 (name heuristic) blocked handoff (MEDIUM).** A legitimately named `data_clk` clock port could BLOCK readiness on a name guess. **Fixed:** moved to REVIEW tier with a documented rationale + test.
3. **SDC-048 tier asymmetry (LOW).** Same undefined-reference class as 046/047 but REVIEW. **Fixed:** documented explicitly why (group entries are advisory; ghost-clock I/O delays break timing computation).
4. **SDC-021 hold-set rebuilt per command (NIT).** **Fixed:** hoisted to one set.
5. **Global `-hold` (no endpoints) not credited for global setup (NIT).** **Accepted** as a deliberate conservative direction (extra advisory, never a missed warning), documented in code.

The reviewer also verified: worst-dimension-wins aggregation is correct; `limited_design_verification` correctly bumps READY→READY_WITH_ADVISORIES; buckets/actions are deterministically sorted; readiness is O(N); HR01/HR14/HR02 manifest statuses are independently defensible.

---

## 26. FILES MODIFIED (Phase 11)

| File | Change |
|---|---|
| `constraint_readiness.py` | **New.** Readiness aggregation layer (statuses, dimensions, tiers, actions, priorities, engine-failure cap) |
| `checker.py` | Wired `result.readiness`; **SDC-021 fix** (split-command `-hold` pair on identical endpoints now counts as the fix; different-endpoint/global holds don't) |
| `app.py` | Constraint Readiness UI section |
| `cli.py` | Readiness block in text + JSON output |
| `reporter.py` | Constraint Readiness Review HTML section + STA-signoff disclosure |
| `tests/test_checker.py` | +2 SDC-021 regression tests (split-pair suppression, different-endpoints still fires) |
| `benchmarks/readiness/` | **New.** HR01–HR15 SDC fixtures, 2 Verilog netlists, manifest.json |
| `benchmarks/run_readiness.py` | **New.** Golden runner (15/15) |
| `benchmarks/test_readiness_adversarial.py` | **New.** 9 checks |
| `benchmarks/test_readiness_confidence.py` | **New.** 18 false-confidence/false-blocker checks |
| `benchmarks/test_readiness_metamorphic.py` | **New.** 8 variants |
| `benchmarks/test_readiness_perf.py` | **New.** 3 checks |

---

## 27. FULL REGRESSION (post-changes)

| Suite | Result |
|---|---|
| pytest | **552/552** |
| Parser golden | 22/22 |
| Semantic golden | 9/9 |
| Reference designs | 8/8 |
| Design coverage golden | 12/12 |
| Netlist-aware golden | 10/10 |
| Interaction golden | 20/20 |
| **Readiness golden** | **15/15** |
| Readiness adversarial / confidence / metamorphic / perf | 9/9, 18/18, 8/8, 3/3 |
| Netlist meta/adv/security | 4/4, 12/12, 7/7 |
| Coverage meta/adv | 7/7, 14/14 |
| Security / trust / no-false-confidence | 5/5, 8/8, 6/6 |
| Stress | 21/21 |
| UI app / state | 35/35, 6/6 |
| Benchmark corpus / realistic corpus / interaction realistic | exit 0, 2/2, PASS |
| Preprocess perf | near-linear |

No prior suite regressed. The SDC-021 fix changes behavior only where a correct `-hold` fix exists in a separate command — verified against golden c17 (same-command pair stays clean), RD06 (unfixed pair still fires, exactly 1), and 66 checker/regression unit tests.

---

## 28. REMAINING LIMITATIONS

- **REVIEW_REQUIRED is common on realistic SDCs** — most real files use options the validator doesn't value-analyze (e.g. `group_path -to`, `set_clock_gating_check`, `set_clock_latency -source`, `set_max_delay -from/-to`). This is *honest*, but the CLI/UI wording must keep it readable as "analysis-completeness review", not "design is bad".
- **Tier mappings are a maintained table** — new rules in future phases must be added to BLOCKER/REVIEW/ADVISORY sets consciously (a missing mapping falls back to severity-based defaults, which is safe but should be reviewed).
- **Readiness ≠ coverage ≠ correctness** — a `READY` verdict covers only what the validator can prove; netlist-dependent claims remain unverified in SDC-only mode (explicitly disclosed).
- **No readiness snapshot/diff or CI gate yet** — proposed for Phase 12 (§30).
- **Numeric score intentionally absent** — teams wanting one must first define defensible weights.

---

## 29. TRUST STATEMENT

**What does READY mean?**
> "The constraint set satisfies the validator's supported, evidence-backed readiness criteria for the stated analysis mode." — no deterministic blockers, no review-tier items, no advisories (or, in SDC-only mode, an explicit limited-design-verification advisory that is disclosed, not hidden).

**What does READY NOT mean?**
> NOT timing clean. NOT signoff complete. NOT "setup/hold passes". NOT "paths are correct". NOT "library/physical behavior verified". NOT "the design is unconstrained-free" in SDC-only mode.

The validator never says READY when a deterministic blocker exists, when an analysis engine failed (engine_failed cap), when constructs were only partially understood (SCOPE-PARTIAL → REVIEW), or when unsupported semantics were present (SCOPE-UNSUPPORTED → REVIEW). And it never says BLOCKED merely for informational duplicates/overrides, STA-required overlaps, heuristics, or a missing optional netlist.

---

## 30. PHASE 12 RECOMMENDATION

1. **Readiness diff** (`before.sdc` vs `after.sdc`) — reuse `constraint_diff.py` + readiness JSON to report *status transitions* (READY → BLOCKED etc.), the highest-value next step for regression gating.
2. **Baseline readiness snapshot** — persist `baseline_readiness.json` per design; detect new blockers/review items/coverage regressions in CI.
3. **Opt-in CI gate** — `--readiness-gate` (fail on BLOCKED; optional fail on REVIEW_REQUIRED; never default-on).
4. **`-hold` global fix credit** — decide whether a global `set_multicycle_path 1 -hold` should credit a global setup 2 (currently deliberately conservative).
5. **Readiness UX polish** — per-dimension drill-down links from the summary to the detailed tabs, and clearer copy for the very common REVIEW_REQUIRED-via-partial-analysis case.

---

*Phase 11's answer to "what does a clean validator result guarantee?" is now explicit, measurable, and machine-readable: a READY verdict is scoped to what was actually analyzed, in the mode actually used — and every limitation is disclosed in the UI, CLI, JSON, and report.*
