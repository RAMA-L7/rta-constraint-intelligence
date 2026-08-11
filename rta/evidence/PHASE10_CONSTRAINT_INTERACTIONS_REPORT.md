# Phase 10 — Constraint Interactions: Semantic Conflict, Redundancy, Override & Exception-Interaction Analysis

## 1. Multi-Agent Execution Summary

| Subagent | Responsibility | Findings |
|---|---|---|
| SDC/STA Semantics Researcher | Authoritative interaction semantics for I/O delays, uncertainty, clocks, exceptions | Replacement semantics for `set_input_delay`/`set_output_delay`/`set_clock_uncertainty`/electrical (last value wins per mode); `-add_delay` = accumulation; `-min`/`-max`, `-rise`/`-fall`, `-setup`/`-hold` are independent modes; max<min window is provably impossible; object overlap ≠ path overlap |
| Constraint Normalization Architect | Normalized `ConstraintRecord` | Identity tuple = (command, objects, clock, min_max, rise_fall, setup_hold, add_delay, endpoints, datapath_only) + separate `modes` set capturing the *whole command's* declared modes |
| Timing-Exception Specialist | fp/mcp/max/min interactions | Only endpoint-identical overlaps reported as POSSIBLE_CONFLICT (info, STA-required); never ERROR; max<min conflict requires provably identical endpoint sets |
| Design-Context Specialist | Resolved-object comparison | Wildcards resolved via `DesignContext` where provable; unresolvable wildcards stay wildcard tokens and block provable-equality claims |
| Adversarial QA | False-conflict hunting | 21/21 legal-looking-but-valid cases produce ZERO findings (incl. combined `-max -min`, MCP setup/hold pairs, add_delay, bus subsets, virtual clocks, clean 21-constraint design) |
| Performance Engineer | Indexing vs O(N²) | Grouping by semantic key; exception overlap via endpoint index — near-linear common path (10k constraints ≈ 0.56s) |
| UI/Report Engineer | Interaction presentation | Separate "Constraint Interactions" section (never floods Issues); dual-line `Lx ↔ Ly` provenance |
| Independent Reviewer | Challenge every rule + benchmark | Found 3 real bugs + 2 polish items (below) — all fixed and regression-tested |

**Disagreements resolved:** The reviewer challenged the mode-set equality requirement for overrides; after re-deriving SDC semantics (a later command restating ONE mode of a multi-mode command *with a different value* genuinely overrides that mode while the min survives), the requirement was kept only for exact duplicates, not overrides. Both behaviors are now unit-tested.

## 2. Baseline

Run before any production change (recorded 2026-08-05):

| Suite | Result |
|---|---|
| pytest | 506/506 PASS |
| Parser golden | 22/22 |
| Semantic golden | 9/9 |
| Reference designs | 8/8 |
| Design coverage golden | 12/12 |
| Netlist-aware golden | 10/10 |
| UI | 35/35 |
| State isolation | 6/6 |
| Security | 5/5 |
| Stress | 21/21 |
| Trust transparency | 8/8 |
| No-false-confidence | 6/6 |

## 3. Authoritative Interaction Semantics Table

| Command | Repeated same identity | -add / -add_delay | -min/-max | -rise/-fall | -setup/-hold | Ordering |
|---|---|---|---|---|---|---|
| set_input_delay | Replace per mode (last wins) | accumulate | independent | independent | n/a | yes (replacement) |
| set_output_delay | Replace per mode (last wins) | accumulate | independent | independent | n/a | yes (replacement) |
| set_clock_uncertainty | Replace per mode | n/a | n/a | independent | independent | yes (replacement) |
| set_load / set_input_transition / set_driving_cell | Replace | n/a | n/a | n/a | n/a | yes (replacement) |
| set_multicycle_path | Replace value (edge/phase variants legal) | n/a | n/a | n/a | setup/hold independent | yes |
| set_false_path | Accumulate (distinct paths) | n/a | n/a | n/a | n/a | no |
| set_max_delay / set_min_delay | Replace per endpoints | n/a | max vs min = window | rise/fall independent | n/a | max<min = impossible |
| set_case_analysis | Replace (contradiction owned by SDC-049) | n/a | n/a | n/a | n/a | yes |
| create_clock / create_generated_clock | Duplicate-name owned by SDC-002 | -add where supported | n/a | n/a | n/a | n/a |

**Proven SDC semantics used:**
- A later `set_input_delay`/`set_output_delay`/`set_clock_uncertainty`/electrical constraint for the same (object, clock, mode, edge) **replaces** the earlier value unless `-add_delay` is present (accumulation).
- `-min`/`-max`, `-rise`/`-fall`, `-setup`/`-hold` are independent analysis modes — never duplicates of each other.
- `set_max_delay < set_min_delay` on provably identical endpoints is an impossible timing window (requires max ≥ min).
- Object endpoint overlap between timing exceptions does **NOT** prove path overlap — path interaction requires STA/path analysis.

## 4. Normalized ConstraintRecord Design

```python
ConstraintRecord:
  command, index (file order), start_line, end_line
  objects: FrozenSet[str]     # normalized "port:din" / "pin:u/q" tokens
  clock, from_set, to_set, through_set
  min_max, rise_fall, setup_hold
  modes: FrozenSet[str]       # modes the WHOLE source command declared
  add_delay, datapath_only
  value: float | None, value_str
  identity() -> tuple         # semantic identity WITHOUT value
```

- **Grouping by identity** (dict keyed on normalized tuple) makes the common path near-linear.
- **`modes`** distinguishes a full command `-max 2.0 -min 0.5` from a partial re-specification `-max 2.0` — critical for the `combined_min_max` false-positive case.
- Values normalized through `parse_number` so `0.25` ≡ `2.5e-1`; variables resolved by the shared preprocessor before records are built.

## 5. Exact Duplicate Semantics (SDC-067, info)

Identical normalized command (same identity + same value + same declared mode set) repeated later → redundant no-op. One finding per duplicated command *pair* (per-pair dedup, anti-flooding). Handles: whitespace, multiline, variable-derived, scientific-notation, option reordering, braced collections.

**Provable-only rule:** two commands are duplicates only when their **mode sets match**. `-max 2.0 -min 0.5` then `-max 2.0` is a partial re-specification — NOT a duplicate.

## 6. Semantic Duplicate Semantics

Differing text, same normalized meaning → collapsed into the exact-duplicate path via numeric normalization (`2.0` vs `2.000`, `0.25` vs `2.5e-1`) and variable resolution. No separate rule needed — normalization makes them provably identical.

## 7. Legal Multiple Semantics — NEVER FLAGGED

- `-min` + `-max` on same object/clock
- `-rise` + `-fall`
- `-setup` + `-hold`
- different clocks, different ports, different hierarchy (pin vs port), different wildcard collections
- `-add_delay` accumulation
- virtual-clock independent references
- different bus bit-ranges
- clock-groups + explicit false path redundancy (common valid practice)

Adversarial suite: **21/21 legal-looking cases produce zero findings** (see §19).

## 8. Override / Redefinition Semantics (SDC-068, info)

Replacement-semantics commands with same identity, later value differs, no `-add_delay` → the earlier value is dead. Requires mode-set equality is **NOT** required here (a later `-max 6.0` after `-max 5.0 -min 1.5` genuinely replaces max while min survives).

## 9. I/O Delay Interactions

Same port/clock/mode/edge + different value → OVERRIDE (SDC-068, info). Same value → EXACT_DUPLICATE (SDC-067, info). min/max or rise/fall pairs → legal. `-add_delay` → accumulation, legal.

## 10. Clock Definition Interactions

Deliberately NOT implemented — duplicate/conflicting clock names are owned by the existing **SDC-002** rule; same-source primary clocks are handled by `clock_relations` (physically-exclusive). No double-reporting (CI06, CI07).

## 11. Uncertainty Interactions

`-setup`/`-hold` and `-rise`/`-fall` independent → legal. Same mode + same value → duplicate. Same mode + different value → override.

## 12. Case-Analysis Interactions

Contradictory `set_case_analysis` on same object is owned by existing **SDC-049** (warning, dual-line). Same-value repeats are harmless → not double-reported (CI10, CI11).

## 13. Electrical Constraint Interactions

`set_load` / `set_input_transition` / `set_driving_cell`: same object, different value → override (replacement semantics). No conflict rule (replacement is authoritative SDC behavior).

## 14. Timing-Exception Interactions

- **Duplicate false path** (endpoint-identical, no value): SDC-067 (info).
- **fp vs mcp/max/min overlap** with provably identical start AND end endpoint sets: SDC-070 **POSSIBLE_CONFLICT** (info, confidence MEDIUM) with explicit "requires STA/path analysis" wording — never an error.
- Partial overlap (same `-from`, different `-to`) → not reported (no path overlap provable).
- Wildcard/unresolvable endpoints → not reported.

## 15. Object Overlap vs Path Overlap

Explicitly distinguished and documented in every SDC-070 message: "Exact path interaction is NOT provable statically — requires STA/path analysis." Object resolution is never claimed as path existence.

## 16. Rules Implemented

| Rule | Purpose | Severity | Evidence |
|---|---|---|---|
| **SDC-067** | Exact/semantic duplicate constraint (redundant no-op) | info | replacement semantics; repeated identical command is a no-op |
| **SDC-068** | Overridden constraint (earlier value dead) | info | replacement semantics, last-wins per mode |
| **SDC-069** | Contradictory max/min delay window (max < min, provably identical endpoints) | warning | max ≥ min is a mathematical requirement of the delay window |
| **SDC-070** | Timing-exception endpoint overlap (fp vs mcp/max/min) | info | object overlap ≠ path overlap; STA required to confirm |

All findings carry dual-line provenance (`line` = later command, `line2` = earlier) via the existing `Issue.line2` mechanism. Registered in `rules_registry.py`, rendered in UI/CLI/JSON/report.

## 17. Rules Intentionally NOT Implemented

- Repeated `set_multicycle_path` with different N (edge/phase variants legally coexist — high false-positive risk; CI15).
- Same-name clock conflicts (SDC-002 owns it).
- Contradictory `set_case_analysis` (SDC-049 owns it).
- `set_max_delay` and `set_min_delay` both present on overlapping-but-non-identical endpoint sets (not provable statically).
- Any conflict requiring path enumeration, library data, or STA.

## 18. Golden Interaction Results (benchmarks/constraint_interactions/)

`benchmarks/run_constraint_interactions.py` — **20/20 cases match expected behavior**:

| Case | Purpose | Expected → Got |
|---|---|---|
| CI01 | exact duplicate input delay | 1× SDC-067 ✓ |
| CI02 | legal min/max pair | 0 ✓ |
| CI03 | legal rise/fall pair | 0 ✓ |
| CI04 | legal -add_delay accumulation | 0 ✓ |
| CI05 | repeated identical output delay | 1× SDC-067 ✓ |
| CI06/CI07 | duplicate/conflicting clock | 0 (SDC-002 owned) ✓ |
| CI08 | duplicate uncertainty | 1× SDC-067 ✓ |
| CI09 | legal setup/hold uncertainty | 0 ✓ |
| CI10/CI11 | duplicate/contradictory case analysis | 0 (SDC-049 owned) ✓ |
| CI12 | duplicate false path | 1× SDC-067 ✓ |
| CI13 | fp vs mcp overlap | 1× SDC-070 ✓ |
| CI14 | valid setup/hold MCP pair | 0 ✓ |
| CI15 | repeated MCP different N | 0 (documented limitation) ✓ |
| CI16 | max 5 < min 10 | 1× SDC-069 ✓ |
| CI17 | clock-group + fp redundancy | 0 ✓ |
| CI18 | variable-derived duplicate | 1× SDC-067 ✓ |
| CI19 | scientific-notation duplicate | 1× SDC-067 ✓ |
| CI20 | realistic mixed design | 1× 067, 1× 068, 1× 069 ✓ |

## 19. Adversarial False-Positive Results

`benchmarks/test_interactions_adversarial.py` — **21/21 cases produce zero false findings**: different clocks, different ports, min/max, rise/fall, setup/hold, add_delay, pin-vs-port, wildcard sets, virtual clocks, generated clocks, bus subsets, variable-derived ports, combined `-max -min` single command, MCP setup/hold pair, max-delay different endpoints, from-only vs from/to, uncertainty different clocks, case-analysis different pins, clock-group+fp redundancy, multi-object same value, and a realistic **clean design with 21 legal repeated constraints**.

## 20. Metamorphic Results

`benchmarks/test_interactions_metamorphic.py` — **8/8 variants produce identical findings**: multiline, scientific notation, variables, whitespace, comments, CRLF, option reordering, braced collections.

## 21. Realistic-Design Results

`benchmarks/test_interactions_realistic.py` — **PASS**:
- **Clean** realistic multi-clock block (2 primary + 2 virtual clocks, clock groups, uncertainty, min/max, rise/fall, add_delay, MCP setup/hold, max/min window, case analysis, loads): **zero findings** across 24 constraints.
- **Problem** (4 injected defects: duplicate din_a, overridden qout 5.0→6.0, max 4 < min 8, fp overlapping MCP domain): all 4 detected (1× SDC-067, 1× SDC-068, 1× SDC-069, 4× SDC-070), no extras, dual-line provenance on all.

## 22. Performance

`benchmarks/test_interactions_perf.py` — grouping by semantic identity + endpoint indexing keep the common path near-linear:

| Constraints | Time |
|---|---|
| 100 | 21 ms |
| 1,000 | 61 ms |
| 10,000 | 556 ms |

Reviewer found and I fixed an accidental O(N²) in the exception-overlap path (index was built but then the full `others` list was re-scanned per fp); it now iterates only indexed candidates.

## 23. UI / CLI / JSON / Report Integration

- **UI (app.py):** new "Constraint Interactions" section (collapsed by default) with summary counts and category-labeled findings; info-severity issues now render with a 🔵 Info badge instead of being mistaken for warnings.
- **CLI (cli.py):** interaction summary + findings in JSON output; concise text summary in check output.
- **Report (reporter.py):** "Constraint Interactions" HTML section with stats grid, findings table (code/category/severity/Lx↔Ly/message), and a disclosure note distinguishing duplicates/overrides/SDC-069/SDC-070.
- **JSON:** machine-readable `interactions: {summary, findings[]}` on CheckResult — backward-compatible.

## 24. Independent Reviewer Findings (all fixed)

1. **Duplicate anchor bug** (false negative): after a mode-mismatched record, the per-value anchor was never advanced, so a later genuinely-identical pair was missed. Fixed — `first_by_val[r.value] = r` re-anchors. Regression test: `test_anchor_after_mode_mismatch`.
2. **SDC-070 provenance order-dependent**: when fp appeared *after* the other exception, `line2 > line`. Fixed — always line = later, line2 = earlier. Regression test: `test_fp_after_mcp_line_convention`.
3. **Accidental O(N²)** in exception overlap. Fixed via single `id_to_rec` map + candidate-only iteration.
4. **Override with `value=None`** (malformed `-max` with no number) could emit "overridden by value None". Fixed — skip None-valued last record. Regression test: `test_override_skips_none_value_last`.
5. **Info-severity rendering** — confirmed UI now renders info findings with the blue Info badge (CSS class existed).

## 25. Full Regression

| Suite | Before | After |
|---|---|---|
| pytest | 506/506 | **550/550** |
| Parser golden | 22/22 | **22/22** |
| Semantic golden | 9/9 | **9/9** |
| Reference designs | 8/8 | **8/8** |
| Design coverage golden | 12/12 | **12/12** |
| Netlist-aware golden | 10/10 | **10/10** |
| Constraint interaction golden | — | **20/20** |
| Interaction adversarial | — | **21/21** |
| Interaction metamorphic | — | **8/8** |
| Interaction realistic | — | **PASS** |
| Interaction performance | — | **PASS** |
| UI benchmark | 35/35 | **35/35** |
| State isolation | 6/6 | **6/6** |
| Security | 5/5 | **5/5** |
| Stress | 21/21 | **21/21** |
| Trust transparency | 8/8 | **8/8** |
| No-false-confidence | 6/6 | **6/6** |
| Benchmark corpus | 61 files | **61 files** |

## 26. Files Modified

- `constraint_interactions.py` — **new**: normalized records, grouping/indexing, interaction rules
- `checker.py` — CheckResult.interactions field + analyzer wiring
- `rules_registry.py` — SDC-067/068/069/070 registered
- `app.py` — Constraint Interactions UI section + info-severity badge fix
- `cli.py` — interactions in JSON/text output
- `reporter.py` — Constraint Interactions HTML section
- `tests/test_constraint_interactions.py` — **new**: 44 tests
- `tests/test_rules_registry.py` — new rules
- `benchmarks/constraint_interactions/` — **new**: CI01–CI20 SDC files + manifest
- `benchmarks/run_constraint_interactions.py` — **new** golden runner
- `benchmarks/test_interactions_{adversarial,metamorphic,perf,realistic}.py` — **new**

## 27. Remaining Limitations

- Repeated multicycle with different N is intentionally silent (edge/phase variants legal).
- Exception overlaps are POSSIBLE_CONFLICT, never proven conflicts — STA required.
- Endpoint sets must be provably identical for max<min; wildcard/bus-range partial overlaps are skipped.
- Semantic duplicates via wildcard equivalence are only provable with design context.
- `set_clock_groups` redundancy (asynchronous groups + explicit fp) is legal practice — not flagged.

## 28. Trust Statement

**What does a reported semantic conflict actually guarantee?**

- **SDC-069 (DEFINITE_CONFLICT)** guarantees the constraint window is mathematically impossible from the SDC alone — max < min on provably identical endpoints. No STA needed. High confidence.
- **SDC-067 / SDC-068** guarantee the normalized commands are provably identical/overriding per SDC replacement semantics — deterministic, high confidence, but info-severity (they may be intentional).
- **SDC-070 (POSSIBLE_CONFLICT)** guarantees only *object* overlap, explicitly NOT path overlap — the message says STA/path analysis is required to confirm whether the same timing path is affected. This is a candidate for review, never an error.

A *clean* interaction result means: no provable duplicates, overrides, impossible windows, or exception overlaps were found. It does **not** mean all timing intent is coherent — non-provable interactions (wildcards, netlist-dependent paths, edge/phase variants) remain outside what SDC-only static analysis can decide, and the tool says so rather than guessing.

## 29. Phase 11 Recommendation

- **Optional design-context hardening for SDC-070**: with a netlist, endpoint sets resolve further (wildcards expand), narrowing which fp/mcp overlaps remain possible — currently wildcard overlaps are silently skipped.
- **Ordering-aware multicycle review** with explicit `-edge`/`-start`/`-end` handling (currently only setup/hold) once a real corpus shows the false-positive rate is acceptable.
- **UI drill-down**: allow clicking an SDC-070 finding to highlight both source lines in the checker text view.
- **Cross-suite sweep**: fold the interaction golden/manifest into `run_benchmark.py` so the full corpus reports interaction counts alongside checker/linter stats.
