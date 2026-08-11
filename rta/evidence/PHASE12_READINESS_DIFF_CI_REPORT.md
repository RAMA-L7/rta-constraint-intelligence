# PHASE 12 — READINESS DIFF, REGRESSION DETECTION, BASELINES & CI QUALITY GATES

## 1. Multi-agent summary

| Agent | Role | Outcome |
|---|---|---|
| EDA / SDC regression engineer | What changes between two constraint revisions are engineering-meaningful | Baseline must be *context*, not an excuse; semantic identity beats line numbers |
| Diff architect | Stable semantic identities + snapshot model | `readiness_diff.py`: `ReadinessSnapshot` (JSON, schema v1), finding identity from (rule, severity, normalized message), not lines |
| CI / DevOps engineer | Safe gates, exit codes, baseline workflows | 4 opt-in policies, 0/1/2/3 exit contract, `--save-baseline`/`--baseline`/`--gate`, engine failure never PASSes |
| SDC semantics reviewer | No false regressions from equivalent SDC | Metamorphic invariant: formatting / variables / sci-notation / reordering / CRLF produce ZERO delta |
| Adversarial QA | Fool the diff system | 10 attack cases: value-change pairing, clock rename, netlist port added, removed-constraint-coverage-worse, etc. |
| UX / report engineer | Concise engineering regression view | CLI "READINESS DIFF" block, HTML section, JSON `readiness_diff`, app.py baseline uploader + diff expander |
| Performance engineer | Diff stays cheap | 10k findings diff ≈ 43–75 ms, near-linear |
| Independent reviewer | Challenge identity, compatibility, gates | Found 4 real issues (all fixed, see §29) |

## 2. Baseline

Before changes (from Phase 11 sign-off):

- pytest: 552/552
- Parser golden: 22/22 · Semantic golden: 9/9 · Reference designs: 8/8
- Design coverage: 12/12 · Netlist-aware: 10/10 · Constraint interactions: 20/20
- Readiness golden: 15/15 · Readiness adversarial: 9/9 · False-confidence: 18/18 · Metamorphic: 8/8
- UI: 35/35 · State: 6/6 · Security: 5/5 · Stress: 21/21

## 3. Existing `constraint_diff.py` review

- **KEEP** — it compares SDC *content* (semantic constraint diff: what constraints changed).
- **EXTEND (separately)** — Phase 12 is the *analysis/readiness* diff (what engineering consequences changed). The two diff types are deliberately separate: `constraint_diff.py` = "what constraints changed"; `readiness_diff.py` = "what consequences changed".
- **DO NOT USE** `constraint_diff.py`'s line-anchored pairing for readiness comparison — findings move under formatting; readiness identity is semantic.

## 4. Constraint diff vs readiness diff

| | Constraint diff (existing) | Readiness diff (new) |
|---|---|---|
| Question | What constraints changed? | What engineering consequences changed? |
| Units | SDC commands/values | Findings, readiness, coverage, trust, interactions |
| Identity | Constraint text | Semantic finding identity (rule + normalized message) |

## 5. Snapshot architecture

```
CheckResult (issues/scope/coverage/interactions/readiness)
        + optional DesignContext
                    ↓
            build_snapshot()        ← readiness_diff.py
                    ↓
   ReadinessSnapshot (JSON, schema_version=1)
     tool_version · analysis(mode/top/design_fingerprint/engine_failed)
     readiness(overall/dimensions) · findings(identity) · coverage(per-object)
     scope(construct→level) · interactions(category)
```

Stored evidence is normalized, not rendered strings. Line numbers are provenance only (each finding keeps `line`/`line2` for drill-down but identity never depends on them).

## 6. Snapshot schema / versioning

- `SCHEMA_VERSION = 1`, `tool_version` from `rules_registry.APP_VERSION`.
- `validate_snapshot()`: required keys, types, mode enum, boolean `engine_failed`, findings list.
- `load_snapshot()`: untrusted input — 20 MB safety cap, JSON parse, validation; any error ⇒ `None` (caller must fail safely; nothing is ever executed from a baseline).
- Round-trip verified (`snapshot_to_json` → `load_snapshot` → identical).

## 7. Baseline compatibility

`classify_compatibility()` returns:

- **COMPATIBLE** — same schema/mode/design context.
- **COMPATIBLE_WITH_CONTEXT_CHANGE** — top module / design fingerprint / tool version differ (netlist changed, or baseline is stale — a staleness reason is emitted).
- **PARTIALLY_COMPARABLE** — analysis MODE changed (SDC-only ↔ design-aware): coverage/trust deltas are only partially meaningful across modes.
- **INCOMPATIBLE** — schema mismatch / corrupt baseline. The gate refuses to run (exit 2).

## 8. Design-context identity

`design_fingerprint(context)` — deterministic SHA-256 over the design's own structure (top module, module names, top-level port names+directions, instance paths, net names). Never raw source content. Same design ⇒ same fingerprint; any structural change changes it. Used to attribute coverage findings to the DESIGN change rather than the SDC revision.

## 9. Stable finding identity

`finding_identity(code, severity, msg)` → `(full_id, base_id)`:

- **full_id** = (rule, severity, normalized message) — exact semantic key. Used for UNCHANGED/NEW/RESOLVED matching.
- **base_id** = (rule, message with numbers blanked) — detects CHANGED (same finding, value/severity changed).
- `normalize_msg` collapses whitespace, strips embedded "line N"/"lines A and B" refs, canonicalizes numerics (2.0→2, 2.5e-1→0.25), and **preserves bracketed bit-select ranges** (`data[3:0]` ≠ `data[7:4]` — bus ranges are object identity, not values).
- Line numbers are provenance only — the permanent line-movement test (RDIF03) proves a moved finding stays UNCHANGED.

## 10. Finding delta model

`_multiset_delta` (multiset semantics; duplicate identical findings stay distinct):

1. Match identical `full_id`s (min-count intersection) → **UNCHANGED**.
2. Leftover baseline occurrences → candidates for **RESOLVED**.
3. Leftover current occurrences → candidates for **NEW**.
4. Pair remaining by `base_id` → **CHANGED** (value/severity changed); leftover are NEW / RESOLVED.

Per-key index bookkeeping (regression-tested): two findings in two different `base_id` groups both pair correctly — a global index set used to collide.

## 11. Readiness delta

`_readiness_delta`: baseline/current overall + per-dimension, with transition semantics (UNCHANGED / IMPROVEMENT / REGRESSION / CONTEXT_CHANGE for non-ordinal statuses). READY→BLOCKED = regression; BLOCKED→READY = improvement; ordinal only where statuses are truly ordered (INSUFFICIENT_CONTEXT is handled specially).

## 12. Dimension delta

Per-dimension statuses tracked separately (CLOCKS, I/O, EXCEPTIONS, COVERAGE, CONSISTENCY, ANALYSIS_TRUST, DESIGN_CONTEXT) — "CLOCKS REGRESSED but COVERAGE stable" is more actionable than a single overall.

## 13. Coverage delta

Object-level, not percentage-only: newly-unconstrained / newly-constrained / new objects / removed objects / partial-bus changes per input and output bucket. A removed constraint that leaves a real port unconstrained is surfaced as REVIEW_REGRESSION (never a blanket "improvement" — false-improvement test).

## 14. Trust delta

Per-construct level transitions (FULL→PARTIAL = regression; UNSUPPORTED→ABSENT = improvement). A construct ABSENT from a revision has no trust problem (treated as FULL). Adding unsupported Tcl ⇒ trust regression even with zero SDC errors; removing it ⇒ improvement.

## 15. Interaction delta

Phase 10 findings compared by identity: new/resolved duplicates, overrides, contradictions, STA-review overlaps.

## 16. Regression classification

`classify_regression()` (never a single accuracy score):

1. **ENGINE_FAILURE** — analysis engines crashed (SDC-140): evidence incomplete, never a clean verdict.
2. **CONTEXT_CHANGE** — design context changed AND every new finding is a design-context code (SDC-055..059, SDC-064..066) ⇒ delta explained by netlist/top change, not the SDC revision. A new deterministic blocker is NEVER masked this way (blockers always win below).
3. **BLOCKING_REGRESSION** — new deterministic blocker.
4. **REVIEW_REGRESSION** — new review-tier finding / newly-unconstrained object / trust regression.
5. **ADVISORY_REGRESSION** — only new advisory/info findings.
6. **IMPROVEMENT** — blockers/review items resolved or readiness improved.
7. **CONTEXT_CHANGE** (fallthrough) / **NEUTRAL_CHANGE**.

## 17. CI gate policies

All opt-in (`--gate`), never active by default:

- **BLOCKERS_ONLY** — fail if current analysis is BLOCKED (works without a baseline).
- **NO_READINESS_REGRESSION** — fail only if the revision introduces a blocking/review regression vs baseline (baseline-aware adoption: pre-existing blockers/review items unchanged by the baseline are accepted).
- **STRICT** — fail on blockers or review regressions.
- **CUSTOM** — reserved; returns NOT_CONFIGURED (exit 2).

## 18. Exit-code contract

Used ONLY when `--gate` is requested (otherwise legacy behavior is preserved: 1 if errors else 0):

| Code | Meaning |
|---|---|
| 0 | gate passed |
| 1 | analysis/readiness gate failed |
| 2 | invalid invocation/input (missing/incompatible/corrupt baseline, unknown policy, baseline-dependent policy without `--baseline`) |
| 3 | analysis engine failure (SDC-140) — a gate can never report PASS |

## 19. Engine-failure behavior

Phase 11 proved engine failure must not produce false READY. Phase 12 extends it: if the current run's analysis engines failed, `evaluate_gate` returns FAIL/exit 3 for **every** policy — a CI gate never reports PASS on incomplete evidence, even if no new blockers were found.

## 20. Baseline update workflow

Explicit and safe — baselines are never silently overwritten:

```
validate → inspect READINESS DIFF → approve → regenerate (--save-baseline) → commit baseline
```

- `--save-baseline JSON` writes a snapshot (a failure to write exits 2).
- `--baseline JSON` compares against it; nothing is written implicitly.
- Stale baselines (tool-version mismatch, changed top/netlist, mode change, schema mismatch) are surfaced via compatibility status and never silently trusted.

## 21. Golden diff results (RDIF01–22) — 22/22

| Case | Classification | Compatibility |
|---|---|---|
| RDIF01 identical | NEUTRAL_CHANGE | COMPATIBLE |
| RDIF02 whitespace-only | NEUTRAL_CHANGE | COMPATIBLE |
| RDIF03 line movement | NEUTRAL_CHANGE | COMPATIBLE |
| RDIF04 sci-notation | NEUTRAL_CHANGE | COMPATIBLE |
| RDIF05 variable/literal | NEUTRAL_CHANGE | COMPATIBLE |
| RDIF06 new undefined clock | BLOCKING_REGRESSION | COMPATIBLE |
| RDIF07 resolved blocker | IMPROVEMENT | COMPATIBLE |
| RDIF08 new unconstrained input | REVIEW_REGRESSION | COMPATIBLE |
| RDIF09 resolved unconstrained | IMPROVEMENT | COMPATIBLE |
| RDIF10 new duplicate only | ADVISORY_REGRESSION | COMPATIBLE |
| RDIF11 new override only | ADVISORY_REGRESSION | COMPATIBLE |
| RDIF12 new SDC-069 | BLOCKING_REGRESSION | COMPATIBLE |
| RDIF13 new SDC-070 review | REVIEW_REGRESSION | COMPATIBLE |
| RDIF14 trust regression | REVIEW_REGRESSION | COMPATIBLE |
| RDIF15 trust improvement | IMPROVEMENT | COMPATIBLE |
| RDIF16 new design port | CONTEXT_CHANGE | COMPATIBLE_WITH_CONTEXT_CHANGE |
| RDIF17 changed top module | CONTEXT_CHANGE | COMPATIBLE_WITH_CONTEXT_CHANGE |
| RDIF18 incompatible baseline | — (INCOMPATIBLE, gate exit 2) | INCOMPATIBLE |
| RDIF19 engine failure | ENGINE_FAILURE (gate exit 3) | COMPATIBLE |
| RDIF20 realistic clean improvement | IMPROVEMENT | COMPATIBLE |
| RDIF21 realistic regression | BLOCKING_REGRESSION | COMPATIBLE |
| RDIF22 multiple changes | BLOCKING_REGRESSION (new blocker dominates; resolved blocker visible) | COMPATIBLE |

## 22. CI-gate results

- BLOCKERS_ONLY: clean PASS / blocked FAIL / advisory-only PASS.
- NO_READINESS_REGRESSION: old blockers unchanged PASS · old warnings unchanged PASS · new blocker FAIL · resolved blocker PASS · new review item FAIL · new advisory-only PASS · no baseline FAIL exit 2.
- STRICT: clean PASS · new blocker FAIL · new review FAIL · old review unchanged PASS.
- Engine failure: FAIL exit 3 under every policy.
- Incompatible baseline: FAIL exit 2. Unknown/CUSTOM policy: NOT_CONFIGURED exit 2.
- Baseline file safety: missing keys / bad JSON / empty / oversized all rejected.

## 23. Adversarial results

- Same rule on different objects: no UNCHANGED pairing (1 resolved + 1 new).
- Same object value changed: exactly 2 CHANGED (SDC-008 + SDC-068 across two identity groups), 0 NEW/RESOLVED.
- Line reorder: no delta. Duplicate added: advisory only.
- Clock rename: SDC-008 (name in message) pairs NEW+RESOLVED; SDC-068 (name-less message) UNCHANGED; classification BLOCKING_REGRESSION (safe: like blocker under a new name).
- Netlist port added: CONTEXT_CHANGE, never BLOCKING.
- Removed constraint with coverage worsened: REVIEW_REGRESSION with `din_b` in newly-unconstrained, never IMPROVEMENT.
- Sci-notation equivalence: UNCHANGED.
- Wildcard vs bus reference: no false CHANGED pairing.

## 24. Metamorphic results

Semantically equivalent transformations produce NO regression (permanent invariant): blank-lines+extra-spacing, variable-derived values, scientific notation, valid option reordering, comments+CRLF. All NEUTRAL_CHANGE/IMPROVEMENT, zero new/resolved findings, COMPATIBLE.

> Note: `;`-joined single-line SDC is NOT an equivalent form in this parser (the preprocessor treats the whole line as one command → PARTIAL trust). It is excluded from the equivalence set and reported honestly as a parser limitation.

## 25. False-improvement results

A removed warning is NOT an improvement when coverage worsens: deleting `set_input_delay` for `din_b` (design-aware) ⇒ new SDC-064 + newly-unconstrained `din_b` ⇒ REVIEW_REGRESSION, not IMPROVEMENT. Removing unsupported Tcl IS an improvement (trust improves, nothing lost).

## 26. False-regression results

Line movement + reformat (11.0 vs 1.1e1, same ordering) ⇒ 0 new, 0 resolved, NEUTRAL — findings never keyed by line. A harmless reformat never fails a NO_REGRESSION gate.

## 27. Performance

| Findings | Diff time | Gate time |
|---|---|---|
| 100 | 0.4 ms | <0.1 ms |
| 1,000 | 2.6 ms | <0.1 ms |
| 10,000 | 43–75 ms | <0.1 ms |

Near-linear (Counter + grouping by identity; no all-pairs). 10× findings ≈ 10–17× time, well within budget. Snapshot build ≈ one extra pass over results.

## 28. UI / CLI / JSON / report changes

- **CLI**: `check --save-baseline JSON`, `--baseline JSON`, `--gate POLICY`; text "READINESS DIFF (vs baseline)" block; exit-code contract (0/1/2/3) applied only when `--gate` given; legacy behavior preserved otherwise. `report check --baseline` attaches the diff to the HTML report.
- **JSON**: `readiness_diff` object (classification, compatibility, findings deltas, coverage/trust/interaction deltas, gate verdict) — backward-compatible addition.
- **HTML report**: "Readiness Diff" section with blockers/review items/advisories, and the "CI PASS ≠ timing pass" disclosure.
- **UI (app.py)**: optional baseline-snapshot upload + a compact "Readiness Diff vs baseline" expander (overall change, new/resolved blockers, coverage/trust regressions) in the Checker tab.

## 29. Independent reviewer findings (all fixed)

1. **`_multiset_delta` index collision (HIGH)** — a global `used_cur` index set collided across different `base_id` groups; two changed findings in two groups mis-paired (1 CHANGED + 1 NEW + 1 RESOLVED instead of 2 CHANGED). Fixed with per-key candidate consumption; regression-tested in `tests/test_readiness_diff.py` and the adversarial suite.
2. **CLI gate silently skipped without `--baseline` (HIGH)** — `--gate NO_READINESS_REGRESSION` without `--baseline` never evaluated the gate (block was gated on `baseline`), so a clean SDC exited 0 — a false PASS hazard. Fixed: `--gate` is always evaluated; baseline-dependent policies without a baseline return FAIL/exit 2. Tested in `test_cli.py`.
3. **Trust-delta inversion (MEDIUM)** — a construct ABSENT from a revision was treated as ord-5 (worst), so *adding* unsupported Tcl looked like improvement and *removing* it looked like regression. Fixed: absent ≡ no trust problem (ord 0). Regression-tested (RDIF14/15).
4. **`"FULL"` missing from `_TRUST_ORD` (MEDIUM)** — construct levels are `FULL/PARTIAL/NETLIST_REQUIRED/TCL_EXECUTION_REQUIRED/UNSUPPORTED`, but the ord table keyed on trust-status names; a new `set (variable)` (FULL) registered as a trust regression. Fixed with the correct level keys (+ legacy aliases).
5. **Bus bit-selects merged by number-blanking (MEDIUM)** — `data[3:0]` vs `data[7:4]` normalized to the same base identity. Fixed: bracketed ranges are preserved verbatim (object identity). Tested.
6. **Tool-version staleness ignored (MEDIUM)** — added: version mismatch ⇒ COMPATIBLE_WITH_CONTEXT_CHANGE with a "regenerate baseline" reason.
7. **`PARTIALLY_COMPARABLE` dead code (LOW)** — now used for analysis-mode changes (SDC-only ↔ design-aware), where coverage/trust deltas are only partially meaningful.
8. **Minor** — `_status_delta` shadowed its parameter; renamed. Temp files cleaned up.

## 30. Full regression results

| Suite | Result |
|---|---|
| pytest (incl. new `test_readiness_diff.py` + CLI baseline tests) | **602/602** (was 552; +50 new tests) |
| Parser golden | 22/22 |
| Semantic golden | 9/9 |
| Reference designs | 8/8 |
| Design coverage golden | 12/12 |
| Netlist-aware golden | 10/10 |
| Constraint interactions golden | 20/20 |
| Readiness golden (Phase 11) | 15/15 |
| Readiness-diff golden (Phase 12) | 22/22 |
| CI gate suite | PASS |
| Readiness-diff adversarial / metamorphic / confidence / perf | ALL PASS |
| Security / Trust / No-false-confidence / Semantic adversarial | 5/5 · 8/8 · 6/6 · 13/13 |
| Reference metamorphic / mutation / cross-module | 10/10 · 7/7 · OK |
| Netlist metamorphic / adversarial / security | 4/4 · 12/12 · 7/7 |
| Coverage metamorphic / adversarial | 7/7 · 14/14 |
| Readiness adversarial / confidence / metamorphic / perf | 9/9 · 18/18 · 8/8 · 3/3 |
| UI / State / Stress | 35/35 · 6/6 · 21/21 |
| Realistic corpus / interactions-realistic | PASS · PASS |

## 31. Files modified

- `readiness_diff.py` (new) — snapshot model, identity, deltas, classification, gates, exit codes.
- `cli.py` — `--save-baseline` / `--baseline` / `--gate`, JSON + text output, exit-code contract, `report check --baseline`.
- `reporter.py` — Readiness Diff HTML section.
- `app.py` — baseline uploader + Readiness Diff expander.
- `tests/test_readiness_diff.py` (new, 33 tests) · `tests/test_cli.py` (+11 baseline/gate tests).
- `benchmarks/readiness_diff/` (RDIF01–22 SDC/Verilog corpus + manifest) · `benchmarks/run_readiness_diff.py` · `benchmarks/test_readiness_diff_{adversarial,metamorphic,confidence,perf}.py` · `benchmarks/test_readiness_ci_gate.py`.

## 32. Remaining limitations

- Finding identity is message-derived: if a checker message omits a semantic discriminator (e.g. SDC-068 omits the clock name), a rename can leave that finding UNCHANGED while the clock-mentioning findings change. Structured identity ingredients (command/objects/clock) are a future hardening (Phase 12 spec §8 lists them; implemented as rule+severity+message proxy).
- `;`-joined single-line SDC is not an equivalent form (parser limitation) — reported honestly via PARTIAL trust, never silently.
- Design fingerprint covers structure (top/ports/instances/nets), not internal logic; a pure connectivity change with identical names is not detected as a context change.
- `PARTIALLY_COMPARABLE` (mode change) is surfaced but the gate does not auto-fail it — it is reported for human judgment. A policy to force regeneration is future work.

## 33. TRUST STATEMENT

**What does a PASS from the readiness CI gate guarantee?**

> "No *disallowed constraint-readiness regression* was detected under the selected policy and stated analysis context, on evidence the validator actually produced."

Concretely, under `NO_READINESS_REGRESSION`, PASS means: relative to a validated baseline snapshot, the revision introduced no new deterministic blocker and no new review-tier finding, trust did not regress, and no previously-constrained design object became unconstrained — using semantic finding identity (formatting/line-movement invariant).

**What does it NOT guarantee?**

- **NOT** that timing passes — the gate performs constraint-readiness analysis, never STA. CI PASS ≠ TIMING PASS.
- **NOT** that the SDC is fully understood — unsupported/Tcl constructs are surfaced as trust status, and `BLOCKERS_ONLY` deliberately does not check them.
- **NOT** correctness of constructs outside the supported analysis scope (trust boundary is disclosed separately).
- **NOT** that the baseline itself is perfect — only that the *revision* did not regress relative to it (baseline-aware adoption). A new deterministic blocker always fails the gate, even if the baseline was already imperfect.
- **NOT** path-level correctness of timing exceptions — endpoint overlap is surfaced as "requires STA", never as proof of path conflict.
- **NOT** a sign that the design is ready for handoff — only that the validator's readiness criteria hold for the stated mode (SDC-only vs design-aware are reported distinctly).

The baseline is context, not an excuse: an existing blocker is accepted only because it was already present and unchanged; a newly introduced one fails the gate.

## 34. Phase 13 recommendation

1. **Structured finding identity** — extend the snapshot with per-finding `command`/`objects`/`clock` semantic keys so renames of name-less messages (SDC-068) pair correctly; keep message identity as fallback.
2. **Baseline regeneration policy** — add an explicit `--gate CUSTOM` configuration surface (policy file) and a `--check-baseline-stale` CI entry that fails when the baseline predates the validator build.
3. **GitHub Actions example** — a documented generic workflow (checkout → install → save baseline → gate → preserve JSON/report artifact) without hard-coding CI internals into the engine.
4. **Readiness diff UI drill-down** — link each diff row to the underlying issue/coverage/trust evidence in the existing tabs.
5. **Design fingerprint v2** — include a lightweight connectivity signature so pure connectivity changes are detected as context changes.
