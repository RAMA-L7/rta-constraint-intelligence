# Ṛta — Block-Level Feature Plan (4 candidates, design gate)

> **Status:** design gate — nothing implemented. Reviewed against the live codebase
> (rules registry, `check_sdc`, `design_context.py`) before writing, so every claim
> below is verified, not assumed.
> **Discipline:** additive-only. Existing engine modules and all 767 tests stay
> behavior-identical; each feature lands as a new SDC code block + a guarded
> `try/except` section in `check_sdc` calling a new standalone module — the exact
> pattern already used by Phases 8 (`design_context`), 9 (`design_coverage`), and
> 10 (`constraint_interactions`).

---

## 0. What exists today (verified against the code)

| Area | Existing coverage | Verified at |
|---|---|---|
| Rule registry | 104 `SDC-*` codes, `_r(code, sev, name, desc, why, fix, url, module)` | `rules_registry.py` |
| False-path advisory | `SDC-020` suggests "Add a comment explaining why" — advisory only, nothing checks | line 110 |
| Derate value sanity | `SDC-032/033/040-043/054` — flat-value direction/monotonic checks | lines 179–297 |
| Case analysis | `SDC-011` (value), `SDC-049` (contradiction), `SDC-109` (info: missing `set_case_analysis` for DFT/test signals — shallow single-signal hint) | lines 99, 271, 475 |
| Duplicate/override | `SDC-067/068/070` via `constraint_interactions.py` | lines 363–386 |
| No-matching-objects | `SDC-055/056` via `design_context.py` | lines 303–332 |
| Connectivity | `pin_nets` / `net_pins` / `module_port_dirs` + pin classification `CLOCK / RESET / SCAN / TEST / CONSTANT` | `design_context.py` 87–104, 1053 |
| Checker plug-in pattern | guarded `try/except` sections calling standalone modules | `checker.py` 694–735 |

**Key enabler:** `design_context.py` already classifies pins as
`CLOCK / RESET / SCAN / TEST / CONSTANT` (line 1053) and provides
`net_pins`/`pin_nets` connectivity — the structural data Features 1 and 3 need
is **already computed**; no new data model required for F1.

---

## 1. F1 — Rationale-comment linting (cheapest, closes SDC-020's loop)

### What
A new rule requiring an explanatory comment near suspicious timing exceptions.

### Why it matters
`SDC-020` already *tells* the engineer to document false paths, but nothing
enforces it. An undocumented false path is a "silent killer": a future engineer
can't tell whether it hides a real violation. Field sources treat constraints as
first-class versioned artifacts; the comment requirement makes the tool's own
advice enforceable.

### Design
- **New module:** `rta/engine/analysis/rationale_lint.py` (name TBD) — pure
  text/line-proximity check; **no new data model**.
- **Rule(s):** one warning, applied to `set_false_path`, `set_multicycle_path`,
  and `set_case_analysis` lines:
  - `SDC-150` (warning) "Timing exception without rationale comment"
    - Fires when an exception line's leading comment block (say, the 3 lines
      immediately above, or an inline `#` on the same line) contains no
      non-trivial comment text (≥ ~10 chars, excluding pure `#` separators).
    - Modifiers reduce noise: don't fire if the exception is already covered by
      a `set_clock_groups`-style structural exception, or if the file has a
      header-level comment explaining the exception policy.
- **Where it runs:** new guarded section in `check_sdc` (both SDC-only and
  design-aware modes — it needs neither a netlist nor a clock model).
- **False-positive budget:** must stay quiet on `samples/real_design_full.sdc`
  style files with documented exceptions; only genuinely undocumented lines fire.

### Effort: S. Test plan
- Synthetic fixture: false path with comment above → clean; same without → one
  `SDC-150`; inline `# why` → clean; comment mentioning "async CDC" → clean.
- Regression: 767 existing tests unaffected (new rule, new codes only).

---

## 2. F2 — Async reset & CDC structural completeness (highest value)

### What
Flag **unconstrained reset/CDC structures** — nets that structurally drive many
flip-flop reset or clock pins but have no (or provably too-broad) timing
exception — with the structural evidence attached.

### Why it matters
Teams routinely blanket `set_false_path`/`-asynchronous` over async-reset and
CDC paths without verifying the applied mechanism. Both failure modes are
silent: *under-constraining* (reset tree with no exception at all — false hold
violations or missed CDC analysis) and *over-constraining* (a wildcard false
path matching far more instances than intended). The reset-synchronizer input
path is a known blind spot (sync input vs deassertion path need distinct
handling, not one blanket false path).

### Design
- **New module:** `rta/engine/analysis/async_reset_check.py` (name TBD).
- **Inputs (all already exist):**
  - `design_context.py` connectivity (`net_pins`/`pin_nets`) to find top-level
    ports/nets that fan out to many flop reset (`RESET` class) or clock
    (`CLOCK` class) pins → candidate reset nets and CDC boundaries.
  - The parsed SDC command list (already in `check_sdc`) for exception coverage.
- **Rules (all warnings, provable-only):**
  - `SDC-151` (warning) "Unconstrained reset tree" — a net structurally driving
    ≥ N (default 2? configurable) reset pins with **no** exception touching it.
  - `SDC-152` (warning) "Suspect blanket false path" — a wildcard
    `set_false_path -from * -to *` or `-asynchronous` clock-group covering a
    reset/CDC net that the structural data shows should be *individually*
    constrained (sync-input vs deassertion distinction).
  - `SDC-153` (warning) "Reset synchronizer input unconstrained" — if the
    classifier can see a flop whose data pin connects to the reset net's
    synchronizer shape (stretch; only if structurally provable, else deferred).
- **Trust rule (matches project ethos):** anything the resolver cannot prove
  stays silent or `NETLIST_REQUIRED` — never a false positive. SDC-only mode:
  these rules are skipped entirely (no context).
- **Composition:** reuses `validate_design_references` findings; adds the
  structural reset/CDC axis on top. Complements (does not duplicate) SDC-020.

### Effort: M. Test plan
- Synthetic netlist + SDC pairs: (a) reset net, no exception → SDC-151;
  (b) reset net, wildcard false path → SDC-152; (c) reset net with targeted
  false path + comment → clean; (d) no netlist → rules skipped, zero findings.
- Reuse existing `netlist_aware/NA*.v` fixtures where shapes overlap.

---

## 3. F3 — DFT/scan-mode constraint completeness (new category, bigger lift)

### What
Flag missing/incomplete `scan_enable` (and `test_mode`) case-analysis coverage
across the three distinct modes — **function, scan shift, scan capture** — where
the correct pattern is `set_case_analysis 0` for function/capture and
`set_case_analysis 1` for shift (or per-team convention). The failure is silent
and specific: without a case-analysis value, STA blends shift-timing and
capture-timing paths into one report.

### Why it matters
Genuinely new category — `SDC-109` (info) only hints that *a* DFT signal lacks
case analysis; nothing checks *mode completeness* or the lock-up-latch false
path trap (do not false-path flops absent from the scan chain, even though they
appear in non-scan reports).

### Design
- **New module:** `rta/engine/analysis/dft_scan_check.py` (name TBD).
- **Phase A (SDC-only, no netlist):** completeness of `set_case_analysis` on
  `scan_en`-style signals:
  - `SDC-154` (warning) "Scan enable without mode coverage" — a
    `scan_en`/`scan_enable`/`test_mode` port has case analysis but not for all
    three modes (detect via presence/absence of 0 and 1 assignments).
  - `SDC-155` (warning) "Scan false path too broad" — `set_false_path` matching
    `scan`-named or all flops where the netlist (if present) shows scan-chain
    shapes; without netlist, fire only on provably-broad wildcards.
- **Phase B (design-aware, needs netlist):** scan-chain *shape* detection —
  long single-input shift chains identifiable from connectivity. **Requires a
  small, additive extension** to the `design_context` pin classifier (new pin
  class hint `SCAN_SHIFT`), or a new module that reuses `net_pins` without
  touching `design_context.py` internals. **Decision point in §6.**
- **Lock-up latch guard:** never recommend false-pathing scan-chain-present
  flops; document in fix text.

### Effort: M–L. Test plan
- Synthetic: scan_en with only `0` → SDC-154; with both 0 and 1 → clean;
  wildcard scan false path without netlist → SDC-155; with netlist showing
  shift chain → structural finding.
- Must stay green on `golden/` corpus (no DFT → no findings).

---

## 4. F4 — AOCV/POCV-aware derate methodology (niche; confirm demand)

### What
A **methodology-consistency** axis on top of the existing value-sanity derate
checks: flag flat single-number derates on flows whose operating conditions
suggest an advanced (≤16nm) node where table-based AOCV or sigma-based POCV is
the expected methodology.

### Why it matters
A derate strategy correct for an old node silently persists after migration —
reintroducing excess pessimism (wasted area/power on phantom violations) or
insufficient margin (real risk missed). The existing SDC-032/033/040-043/054
cannot see this because they only validate values, not methodology.

### Design
- **New module:** `rta/engine/analysis/derate_methodology.py` (name TBD).
- **Heuristics (provable-only, no node-size magic):**
  - `SDC-156` (info) "Flat derate on advanced-node flow" — fires only when the
    file itself carries signals of a small-node flow: `set_operating_conditions`
    names containing `16`, `7`, `5`, `3` (nm), or POCV/AOCV keywords
    (`-pocv`, `sigma`, `derate_table`), *and* uses only flat `set_timing_derate`.
  - `SDC-157` (info) "Derate methodology mix" — flat derate alongside
    table/sigma derates in one file (inconsistency flag).
- **Severity is info, never warning/error** — a flat derate is *correct* for
  many blocks; this is advisory, matching the project's "never overclaim"
  ethos. Gate: confirm with the intended user base whether this earns a
  warning slot.

### Effort: M. Test plan
- Synthetic: operating-condition `SS_0P72V_16C` + flat derate → SDC-156 (info);
  same without node hint → clean; table + flat mix → SDC-157; golden corpus
  unaffected.

---

## 5. New/changed signatures (summary)

| Feature | New module | New codes | Signature changes |
|---|---|---|---|
| F1 | `rationale_lint.py` | `SDC-150` | `rationale_findings(text, commands) -> list[Finding]` |
| F2 | `async_reset_check.py` | `SDC-151/152/153` | `reset_findings(text, ctx) -> list[Finding]` (ctx optional) |
| F3 | `dft_scan_check.py` | `SDC-154/155` (+Phase B) | `dft_findings(text, ctx) -> list[Finding]` |
| F4 | `derate_methodology.py` | `SDC-156/157` | `derate_methodology_findings(text) -> list[Finding]` |

- Each is called from a new guarded section in `check_sdc` following the
  existing Phase 8/9/10 pattern (`try: ... except: SDC-140 skip note`).
- **No existing signature changes.** `check_sdc(text, context)` unchanged.
- Rules registry: pure additions (`_r(...)` calls), new codes in the 150+ range
  to avoid collision.

---

## 6. Decisions — resolved (reviewer sign-off)

1. **F3 Phase B (scan-chain shape detection):** **keep it in the new module**
   using only existing `net_pins` — zero touch to `design_context.py` on first
   pass. `design_context` is load-bearing for three other features; extending
   it only happens later, as its own reviewed refactor, if the shape logic
   proves genuinely reusable. *(resolved: new module first)*
2. **F2 reset threshold:** **fixed default (≥2 reset-pin fanout) + documented.**
   No config knob — a configurable threshold defers a judgment call onto users
   and adds a config surface to maintain/test. Consistent with existing fixed
   constants (e.g. the 0.05 ns uncertainty threshold in SDC-022). If real usage
   shows ≥2 is wrong, that's a data-driven change to the default, not a new
   knob. *(resolved: fixed + documented)*
3. **F4 severity:** **info-level** (matches the no-overclaim ethos; flat OCV
   derate is legitimate for many designs and warning-level would add alarm
   fatigue). To be confirmed with the domain engineer before any warning
   upgrade — architecture doesn't decide this alone. *(resolved: info, pending
   engineer sign-off)*
4. **Order:** **F1 → F2 → F3 → F4.** No speculative reordering; F3 jumps the
   queue only if an engineer with real DFT pain asks. F1 ships first (cheapest,
   closes the loop on existing SDC-020 advice); F2 immediately after F1's
   regression gate is green. *(resolved: F1 approved, F2 sequenced)*

**F1 status: SHIPPED** (v1.5.2, `SDC-150`, module `rationale_lint.py`).
**F2 status: SHIPPED** (v1.5.4, `SDC-151..153`, module `async_reset_check.py`).
Implementation notes: F2 is design-aware only (skipped in SDC-only mode), uses
the fixed ≥2 reset-pin threshold as approved, and produced **zero noise** on the
existing `netlist_aware` fixture corpus (NA01 is covered by a targeted
`set_false_path -from [get_ports rst_n]`; NA10's flops have no reset pins).

**F3 status: SHIPPED** (v1.5.5, `SDC-154..155`, module `dft_scan_check.py`).
Implementation notes — two data-driven refinements validated against the
project's own golden corpus (the approved plan's literal test cases were
adjusted where the corpus proved them too loud):
1. **SDC-154 fires only on TOTAL absence of mode coverage** (a
   scan-enable/test-mode signal referenced with no `set_case_analysis`, or
   only non-mode values like rising/falling). A single-value assignment
   (`set_case_analysis 0` **or** `1`) is legitimate per-mode block practice —
   the READY fixtures HR02/HR12 use it, and the plan's literal "only 0 →
   SDC-154" would have broken the readiness golden (13/15).
2. **SDC-155's broad-cut trigger requires a FULLY-blanket cut** (both -from
   and -to sides all_*/*) in a provably-DFT file; targeted scan constraints
   (`-through [get_pins U_SCAN*/scan_en]`, `-from [get_ports scan_en]`) are
   the RECOMMENDED pattern and never fire (they appear in
   `false_paths_valid.sdc` and `full_featured.sdc`). Phase B chain-shape
   detection (SI→Q→SI→Q, ≥2 links from `net_pins` only) fires only when a
   cut matches all flops.
Readiness golden 15/15, golden 22/22, golden-semantic 9/9, and zero noise on
the `netlist_aware`, `golden/`, `valid/`, and `reset_demo` fixtures.

---

## 7. Test plan (shared gates)

- New synthetic fixtures per feature (listed in each section above).
- **Evidence sync:** after any rule additions, regenerate
  `RELEASE_EVIDENCE.json` via `python rta/evidence/build_evidence.py` (rule
  count changes) — same drift discipline as v1.5.0→v1.5.1.
- **Regression:** full `pytest rta/tests -q` (767 → 767+new, all green) +
  `smoke_test.py` 19/19 + `rta analyze all` on the evidence corpus unchanged
  counts for existing codes.
- **Docs:** new codes appear in `rta rules list/show`, UI reference table, and
  the CLI guide's rule section.

---

## 8. Explicitly out of scope (deferred, not forgotten)

- Full-chip / hierarchical resolution (already planned separately in
  `FULLCHIP_DESIGN_CONTEXT_PLAN.md`; F2/F3 Phase B grow naturally from it).
- Clock-tree / relation-matrix / bus-coverage visualizations (Product
  Experience tier).
- Any LLM/generative component in the analysis path (ruled out by roadmap).
- Changing or renumbering any existing SDC code or its severity.
