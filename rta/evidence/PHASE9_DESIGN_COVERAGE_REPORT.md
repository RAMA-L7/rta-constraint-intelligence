# PHASE 9 — DESIGN-AWARE CONSTRAINT COVERAGE REPORT

**SDC Validator — Structural Timing-Intent Analysis without an STA Engine**

---

## 1. Multi-Agent Execution Summary

| Agent | Responsibility | Findings / Outcome |
|---|---|---|
| **STA/SDC Semantics Engineer** (conceptual) | What coverage conclusions are safe without timing libraries | Coverage = "was it constrained?" must never imply "was it constrained correctly?". Clock structural fanout proves connectivity, NOT propagation through sequential timing arcs. |
| **Netlist Graph Architect** (conceptual) | Lightweight connectivity in DesignContext | Added indexed `net_pins` / `pin_nets` maps + `net_drivers()` / `net_loads()` / `pin_direction()` / `pin_name()` lookups. Connectivity only — no timing propagation. |
| **Constraint Coverage Engineer** (implementation) | `design_coverage.py` | Per-object status model (CONSTRAINED / UNCONSTRAINED / PARTIALLY_CONSTRAINED / EXEMPT / UNKNOWN / NOT_APPLICABLE), bus bit-math, exception endpoint status, clock structural resolution. |
| **Adversarial QA** | `test_coverage_adversarial.py` | Found 2 genuine false positives pre-release: `strap_0` (constant port through generic mux pin → misclassified DATA) and `jtag_tck` (JTAG clock not name-recognized). Both fixed. Final: 14/14. |
| **Performance Engineer** | `test_coverage_perf.py` | 5→100 ports / 10→500 instances measured; coverage O(ports + constraints), no quadratic blowup. |
| **UI/Report Engineer** (implementation) | app.py / cli.py / reporter.py | Constraint Coverage expander (UI), text + JSON coverage output (CLI), HTML coverage section (reports), backward compatible. |
| **Independent Reviewer** (`code-reviewer`) | Challenge all claims | Found 2 correctness bugs (duplicate-finding between SDC-059 and SDC-064/065; token-boundary name matching) + perf/UX notes. ALL findings addressed (see §20). |

**Disagreement resolution:** reviewer claimed `data_in` in NA08 triggers both SDC-059 (name) and SDC-064 (structural). Verified with a reproducer — confirmed. Resolution: structural evidence supersedes the name heuristic (SDC-059 becomes the no-structural-evidence fallback), and NA08's manifest expectation updated accordingly with documented rationale.

---

## 2. Baseline (recorded before Phase 9 production changes)

| Suite | Baseline | Post-Phase 9 |
|---|---|---|
| pytest | 476/476 | **506/506** (+30 design-coverage tests) |
| Parser golden | 22/22 | 22/22 |
| Semantic golden | 9/9 | 9/9 |
| Reference designs | 8/8 | 8/8 |
| Netlist-aware golden | 10/10 | 10/10 |
| Netlist metamorphic | 4/4 | 4/4 |
| Netlist adversarial | 12/12 | 12/12 |
| Netlist security | 7/7 | 7/7 |
| Trust transparency | 8/8 | 8/8 |
| No-false-confidence | 6/6 | 6/6 |
| Security | 5/5 | 5/5 |
| Preprocess stress | 21/21 | 21/21 |
| UI | 35/35 | 35/35 |
| State isolation | 6/6 | 6/6 |
| **New:** Design-coverage golden | — | **12/12** |
| **New:** Coverage metamorphic | — | **7/7** |
| **New:** Coverage adversarial | — | **14/14** |
| **New:** Coverage perf | — | PASS |

---

## 3. SDC-059 Review

SDC-059 (Phase 8) was a **name-based** unconstrained-port heuristic. Phase 9 review concluded:

- **Keep:** it remains the only option in SDC-only style designs where a port connects only to generic/non-data pins or where no structural evidence exists.
- **Defect found:** when a port had structural data evidence AND a data-ish name, both SDC-059 (name) and SDC-064/065 (structural) fired for the same port — double reporting.
- **Fix:** SDC-059 now **defers to structural evidence**. If `classify_port_structure` returns a definitive structural class (CLOCK/RESET/SCAN/TEST/CONTROL/CONSTANT/DATA), SDC-059 stays silent; it only fires as a name-based fallback when classification is UNKNOWN. This *removes* findings, never adds them — Phase 8 golden (NA08) expectation updated with documented rationale (D4 now detected via SDC-064).
- **Not expanded:** SDC-059 was NOT broadened. The structural rules own structurally-evidenced ports.

---

## 4. Structural Connectivity Graph Architecture

Extended `design_context.py` with **connectivity-only** structures (no timing semantics):

```
port → net ──┐
             ├─→ instance pin (input)   [net_loads]
             └─← instance pin (output)  [net_drivers]
```

- `module_port_dirs`: per-module `{module_name: {port: direction}}` — needed to know each instance pin's direction at any hierarchy depth.
- `pin_nets`: `{hierarchical_pin: net_name}` and `net_pins`: `{net_name: [pins]}` — populated during flattening, both indexed dicts (no scans).
- API: `net_drivers(net)`, `net_loads(net)`, `pin_direction(pin)`, `pin_name(pin)`.
- **No arrival/required times, no delays, no arcs.** The graph answers "what is structurally connected to what", never "how fast".

This enables the structural port classifier: a top-level port's net → instance pins → pin names (`clk`, `d`, `q`, `rstn`, `se`, `b`, …) give structural evidence of role.

---

## 5. Input Coverage Semantics

For each top-level input port:

1. Classify structurally (`classify_port_structure`): CLOCK / RESET / SCAN / TEST / CONTROL / CONSTANT / DATA / INOUT / UNKNOWN.
2. Exempt classes (CLOCK, RESET, SCAN, TEST, CONTROL, CONSTANT, INOUT) → **EXEMPT** — visible in the summary but never reported unconstrained. Rationale: no `set_input_delay` is expected by design convention for these.
3. Collect `set_input_delay` references (via the shared preprocessor → logical commands → `get_ports` collections, wildcards resolved against the design).
4. `set_case_analysis` on a port also marks it **CONSTRAINED** (its timing intent is deliberately pinned to a constant — SDC convention).
5. Data-class port with no reference → **UNCONSTRAINED** (definite → SDC-064). Non-data, non-exempt (UNKNOWN intent) → **UNKNOWN** status only, never an error.

**Conservative rule:** only structurally-evidenced DATA ports produce definite unconstrained findings.

---

## 6. Output Coverage Semantics

Mirror of inputs via `set_output_delay` (+ `set_case_analysis`). A definitive structural DATA output with no `set_output_delay` → **UNCONSTRAINED** → SDC-065. Outputs of unknown intent → **UNKNOWN** status only.

Direction bucketing bug fixed during development: exempt **outputs** (e.g. a clock-output port) were previously counted in the `inputs` bucket of the summary; they are now bucketed by direction.

---

## 7. Bus Coverage

`_bus_covered()` computes coverage from the set of referenced bit-specs against the bus's `[msb:lsb]`:

- Whole-bus reference (`data_in`, `data_in[*]`) → **CONSTRAINED**
- Full-range reference covering all bits → **CONSTRAINED**
- Provable subset (`data_in[3:0]` on an 8-bit bus) → **PARTIALLY_CONSTRAINED** → **SDC-066**, message lists exactly which bits are covered
- Bit references clamped to the declared range; out-of-range bits do not inflate coverage
- Wildcards (`data_*`) resolve against the design and contribute whole-bus coverage for every match

**No "32 unconstrained bits" noise:** a single whole-bus collection marks the entire bus constrained. Partial coverage is only reported when provable from the SDC collections.

---

## 8. Clock Structural Coverage

For each `create_clock` / `create_generated_clock`:

- **Virtual clock** (no collection) → `structurally_resolved=False`, `is_virtual=True`.
- Real target resolved against the design → `structurally_resolved=True`; `fanout` = number of structural loads on the target's net.
- Status: `RESOLVED` (exists + has structural fanout, or is a port) vs `NO_STRUCTURAL_FANOUT` (exists but drives nothing — possible dead target).
- **Explicit non-claim:** structural connectivity does **NOT** prove clock propagation through sequential timing arcs — no libraries, no timing. `NO_STRUCTURAL_FANOUT` is a coverage status, not an error rule (a partial netlist can legitimately produce it).

---

## 9. Generated-Clock Analysis

- `-source` and target collections resolved against the design.
- Source existence + structural fanout recorded (`RESOLVED` / `NO_STRUCTURAL_FANOUT`).
- "Source/target both exist but structurally unrelated" is **NOT** diagnosed: proving structural unrelatedness reliably requires full netlist elaboration, and false positives here are expensive. Left as `UNKNOWN`/documented limitation.

---

## 10. Timing-Exception Endpoint Coverage

For `set_false_path` / `set_multicycle_path` / `set_max_delay` / `set_min_delay`, each `-from/-to/-through/-rise_*/-fall_*` collection is resolved. Aggregate status:

- all resolve → **OBJECTS_RESOLVED**
- any empty wildcard → **EMPTY_COLLECTION**
- any explicit missing object → **PARTIALLY_RESOLVED**
- unsupported expression → **UNSUPPORTED**
- no supported endpoints → **PATH_EXISTENCE_UNKNOWN**

**Mandatory distinction preserved:** object resolution ≠ path existence. Status wording never claims "false path validated" — it reports *endpoints resolved*; applicability requires timing analysis. Reported as machine-readable coverage status only (no error rule).

---

## 11. Coverage Model

Machine-readable `ConstraintCoverage` with per-object records:

```
inputs:   [{name, direction, class, status, evidence, line}]
outputs:  [same]
clocks:   [{name, period, target, structurally_resolved, fanout, is_virtual, status}]
exceptions: [{command, line, status, endpoints}]
summary:  {inputs{...}, outputs{...}, clocks{...}, exceptions{...},
           coverage_is_not_correctness: true}
```

Object statuses are never forced into a constrained/unconstrained binary. `UNKNOWN` intent is a first-class status.

---

## 12. Coverage vs Correctness (mandatory distinction)

- **Coverage** = "was this object constrained?" — the Phase 9 model.
- **Correctness** = "was it constrained correctly?" — existing checker rules (SDC-008/009/046, etc.).

They are strictly separated: coverage never suppresses a correctness finding, and a "100% coverage" summary never claims timing closure. A covered port can still violate SDC-008. `coverage_is_not_correctness: true` is embedded in every summary to keep consumers honest.

---

## 13. Rules Added (design-aware only, all warning, fire only with design context)

| Rule | Severity | Purpose | Evidence basis |
|---|---|---|---|
| **SDC-064** | warning | Structurally-evidenced data INPUT with no `set_input_delay` | Port's net drives instance data pins (D/DIN/DATA) — stronger than name heuristics |
| **SDC-065** | warning | Structurally-evidenced data OUTPUT with no `set_output_delay` | Port's net driven by instance data pins (Q/DOUT) |
| **SDC-066** | warning | Bus with provable partial bit coverage | Bit-set math against declared `[msb:lsb]` range |

Free ID block `SDC-064..066` verified in `rules_registry.py` before use (SDC-060..063 owned by clock_relations; 055..059 by design_context). Registered with `module="design_coverage"`; rules-registry test and UI module filter updated accordingly.

---

## 14. Golden Coverage Results — `benchmarks/design_coverage/`

**12/12** — DC01..DC12, expectations independently derived in `manifest.json`:

- DC01 fully constrained (no findings) · DC02 missing input delay → SDC-064 · DC03 missing output delay → SDC-065 · DC04 clock/reset exclusions (exempt, never flagged) · DC05 full bus (no finding) · DC06 partial bus → SDC-066 · DC07 virtual-clock I/O (clocks on virtual clock legal, covered) · DC08 generated clock (source resolved) · DC09 valid exceptions (OBJECTS_RESOLVED) · DC10 empty exception endpoint (EMPTY_COLLECTION status) · DC11 multi-clock interface with async groups · DC12 intentionally mixed (partial bus + missing output delay).

---

## 15. Realistic-Design Results

RD01–RD08 (Phase 6) and NA01–NA10 (Phase 8) continue to pass unchanged (8/8, 10/10). Phase 9 coverage added on top of these without altering any existing expectation. DC suite uses multi-module designs (flop + reg_out instances, buses, scan/reset pins) rather than single-command fixtures.

---

## 16. Metamorphic Results — **7/7**

Coverage is invariant under semantically equivalent changes: scientific notation vs decimal periods, comments added, CRLF vs LF, extra whitespace, braced vs unbraced port collections. (Bus range variants that change the *set of covered bits*, e.g. `data_in[7:0]` vs `data_in[7:4]`, are correctly NOT equivalent and were removed from the equivalence set during development — the engine distinguishes them.)

---

## 17. Adversarial False-Positive Results — **14/14**

Anti-false-positive targets all pass: `clk`, `clock`, `reset_n`, `rst_n`, `scan_en`, `scan_in/out`, `test_mode`, `jtag_*`, `debug_*`, `cfg_mode`, `strap_0`, `bidir` (inout), virtual-clock I/O, generated clocks, wildcards, partial buses.

**Two genuine false positives found and fixed during development:**
1. `strap_0` (constant/strap port) connected only to a generic mux `b` pin → generic-pin structural "DATA" evidence outweighed the CONSTANT name class. **Fix:** exempt-class name evidence now overrides weak/generic structural DATA evidence; only *specific* structural roles (CLOCK via `clk` pin, RESET via `rstn`/`arstn`, D/Q data pins) beat name evidence.
2. `jtag_tck` (JTAG test clock) not name-recognized. **Fix:** JTAG family (`jtag_*`, `tck`, `tms`, `tdi`, `tdo`, `trst`) added to name classification.

---

## 18. Performance

`test_coverage_perf.py` (deterministic generated netlists):

| Ports | Instances | parse | coverage |
|---|---|---|---|
| 5 | 10 | 0.007s | 0.005s |
| 25 | 50 | 0.012s | 0.005s |
| 50 | 100 | 0.021s | 0.011s |
| 100 | 500 | 0.129s | 0.026s |

Coverage is O(ports + constraints + collection matches) — indexed net/pin maps, SDC preprocessed exactly **once** per analysis and shared across all sub-analyses (the initial implementation re-preprocessed per port; reviewer-flagged, fixed). Clock-pair analysis remains the dominant cost on huge clock counts and is unchanged.

---

## 19. UI / CLI / JSON / Report Integration

- **checker:** `CheckResult.coverage` dict populated only when `context` is supplied; empty dict in SDC-only mode. SDC-064/065/066 appended to issues only in design-aware mode.
- **UI (app.py):** "Constraint Coverage" expander in the Checker tab (inputs/outputs/clocks/exceptions buckets, constrained/unconstrained/exempt/partial/unknown counts) + rules-reference module filter includes `design_coverage`. Findings stay in the Issues panel; coverage is a separate section.
- **CLI:** `--netlist`/`--top` runs emit a concise coverage summary (text + JSON via `--format json`). Backward compatible — no coverage output in SDC-only mode.
- **Reports (reporter.py):** HTML check report gains a Constraint Coverage section after Analysis Scope. JSON metadata includes coverage.
- **Coverage ≠ correctness** is carried through every surface (`coverage_is_not_correctness`).

---

## 20. Independent Reviewer Findings — all addressed

| # | Finding | Resolution |
|---|---|---|
| 1 | **Duplicate-finding bug:** SDC-059 + SDC-064/065 both fire for the same structurally-data port | SDC-059 defers to structural evidence; NA08 manifest updated with rationale; unit test updated |
| 2 | **Token-boundary name matching:** substring `en` matched `open`/`length`/`den`; `_pin_role` suffix matching could hit `contest` etc. | Token-boundary matching implemented (word-boundary / `_`-separated token matching, suffix boundaries for pin roles) |
| 3 | O(N²) coverage: per-port re-preprocessing | Preprocess once; logical-command list shared; line index built once |
| 4 | Exempt outputs bucketed into inputs summary | Bucket by direction |
| 5 | `data_in[*]` vs `data_in[7:4]` equivalence test bug (test-side) | Test corrected — genuinely non-equivalent |
| 6 | Reviewer raised NA10 golden coverage + positional-connection coverage | Already covered by Phase 8 suites; re-verified 10/10 |
| 7 | Test that merely encodes implementation | All golden expectations independently derived in manifest.json with `reason` fields |

---

## 21. Full Regression Results (all executed)

| Suite | Result |
|---|---|
| pytest | **506/506** |
| Parser golden | 22/22 |
| Semantic golden | 9/9 |
| Reference designs | 8/8 |
| Netlist-aware golden | 10/10 |
| Netlist metamorphic | 4/4 |
| Netlist adversarial | 12/12 |
| Netlist security | 7/7 |
| **Design-coverage golden** | **12/12** |
| **Coverage metamorphic** | **7/7** |
| **Coverage adversarial** | **14/14** |
| **Coverage perf** | PASS |
| Trust transparency | 8/8 |
| No-false-confidence | 6/6 |
| Security | 5/5 |
| Preprocess stress | 21/21 |
| UI | 35/35 |
| State isolation | 6/6 |

---

## 22. Files Modified

| File | Change |
|---|---|
| `design_context.py` | Connectivity graph (`module_port_dirs`, `pin_nets`, `net_pins`, `net_drivers/net_loads/pin_direction/pin_name`), `classify_port_structure` + token-boundary `_name_class`/`_pin_role`, bus range-reference resolution, SDC-059 structural deferral |
| `design_coverage.py` | **New** — coverage engine, status model, bus bit-math, exception/clock coverage, `analyze_coverage`, `coverage_findings` (SDC-064/065/066) |
| `checker.py` | `CheckResult.coverage` + `coverage_findings` wiring (design-aware only) |
| `rules_registry.py` | SDC-064/065/066 registered (`module=design_coverage`) |
| `cli.py` | Coverage summary in text/JSON output + help text |
| `app.py` | Constraint Coverage expander + module filter entry |
| `reporter.py` | Constraint Coverage HTML section |
| `tests/test_design_coverage.py` | **New** — 30 tests |
| `tests/test_design_context.py` | SDC-059 test updated for structural deferral |
| `tests/test_rules_registry.py` | `design_coverage` module added to valid set |
| `benchmarks/design_coverage/` | DC01–DC12 (.v + .sdc), shared `_design_v1..3.v`, `manifest.json`, `run_design_coverage.py` |
| `benchmarks/test_coverage_metamorphic.py` / `test_coverage_adversarial.py` / `test_coverage_perf.py` | **New** suites |
| `benchmarks/netlist_aware/manifest.json` | NA08 D4 detection SDC-059 → SDC-064 (documented) |

---

## 23. Remaining Limitations

- **No STA:** arrival/required times, slack, setup/hold calculation, cell/RC delays, OCV, CPPR, SI — deliberately out of scope.
- **Path existence unknown:** exception endpoint resolution never proves a timing path exists.
- **Generated-clock source/target structural-unrelatedness:** not diagnosed (would require full elaboration; high false-positive risk).
- **Name heuristics remain evidence, not truth** — a port named `data_en` could classify CONTROL even if it drives flop D pins (conservative direction: fewer false positives, possible false negatives).
- **`NO_STRUCTURAL_FANOUT`** for a clock is a status, not proof the clock is dead — partial netlists are common.
- **Inout ports** are handled conservatively (EXEMPT/NOT_APPLICABLE unless explicitly delayed).
- Bus coverage is provable only for static bit references resolvable by the collection resolver; dynamic/expression-based bit selects stay UNKNOWN.

---

## 24. Trust Statement

**What does "100% constraint coverage" mean in this validator?**

It means: *every top-level boundary port of the supplied design was either referenced by a supported I/O delay / case-analysis constraint, or classified exempt (clock/reset/scan/test/control/constant/inout) by structural + name evidence; every supported clock target was structurally resolved; every supported timing-exception endpoint collection resolved to real objects.*

It does **NOT** mean:
- timing will close (no STA performed)
- constraints are correct (coverage ≠ correctness; SDC-008/009/046 etc. still apply)
- exempt classifications are provably correct (name evidence is heuristic)
- paths referenced by exceptions actually exist (object resolution ≠ path existence)
- unsupported collections were analyzed (they stay UNKNOWN/UNSUPPORTED, never upgraded)

**Confidence per capability (structure-aware):**
- Parsing/preprocessing: HIGH · Clock extraction: HIGH · Generated clocks: HIGH (period/ancestry) · I/O constraint extraction: HIGH · Port structural classification: MEDIUM (name heuristics remain) · Bus coverage: HIGH (provable bit math) · Exception endpoint resolution: MEDIUM · Coverage vs correctness separation: HIGH · Unconstrained findings (SDC-064/065/066): HIGH confidence, low false-positive rate (14/14 adversarial).

---

## 25. Phase 10 Recommendation

Evidence from Phase 9: coverage analysis is stable (12/12 golden, 14/14 adversarial, 7/7 metamorphic), the SDC-only behavior is untouched, and the coverage/correctness separation is embedded everywhere.

Recommended Phase 10 focus, in order of engineering value:

1. **Semantic conflict detection (deferred from Phase 5)** — the parser/preprocessor + coverage architecture is now stable enough to revisit duplicates/overrides/conflicts (I/O delay override semantics, timing-exception overlap) with the established evidence-first discipline.
2. **Optional bus-aware constraint quality:** detect whole-bus `set_load`/`set_input_transition` vs bit-level conflicts where provable.
3. **UI polish:** surface coverage summary in the Checker tab summary line (already in expander), and consider a small "Coverage" column in reports.
4. **Re-verify on a third-party real SDC corpus** (public open-source cores) to measure false-positive rate in the wild — the strongest remaining trust question.

Do NOT build: STA, path enumeration, library parsing. The boundary established in Phases 7–9 should be defended.
