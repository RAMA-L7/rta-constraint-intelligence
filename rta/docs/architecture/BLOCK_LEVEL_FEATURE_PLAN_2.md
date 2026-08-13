# Ṛta — Block-Level Feature Plan 2 (8 candidates, design gate)

> **Status:** design gate — nothing implemented. Reviewed against the live codebase
> (rules registry, `checker.py`, `clock_relations.py`, `dft_scan_check.py`,
> `design_context.py`, `design_coverage.py`) before writing, so every claim below
> is verified, not assumed.
> **Discipline:** additive-only. Existing engine modules and all 826 tests stay
> behavior-identical; every feature lands as new SDC codes + a guarded section in
> `check_sdc` calling a new standalone module — the exact pattern used by Phases
> 8–10 and F1–F4. No existing code or severity is touched.
> **Date:** 2026-08-13 · **Baseline:** v1.5.6, 119 rules (98 `SDC-*` + 21 `CHG-*`).

---

## 0. What exists today (verified against the code)

F1–F4 shipped (v1.5.2–v1.5.6, `SDC-150..157`). This plan searches for the *next*
round of genuine gaps. Full current coverage:

| Area | Existing coverage | Verified at |
|---|---|---|
| Clocks | `SDC-001/002/007`, 100, 107/108/116 — missing clock, duplicate names, clock-on-data-port, latency/transition/jitter advisories | `checker.py` |
| Generated clocks | `SDC-003/004/047` — missing `-source`, both `-divide_by`+`-multiply_by`, undefined `-master_clock` | `checker.py` 265 |
| I/O delays | `SDC-005/006/008/009/028/029/046/059/064/065/066` — missing, oversized, `-min`-only, undefined `-clock`, bus bit-partial, structural gaps | `checker.py`, `design_coverage.py` |
| Exceptions | `SDC-020/021/027/034/037/069/070/150` — rationale, MCP setup/hold pairing, half-cycle MCP, `-datapath_only`, max<min, overlaps | `checker.py`, `constraint_interactions.py` |
| Clock groups | `SDC-024/031/048/060/061/062/063` — completeness, undefined refs, async-vs-exclusive | `clock_relations.py` |
| Case analysis / DFT | `SDC-011/049/109/154/155` — values, contradictions, scan_en mode coverage, blanket scan cuts | `dft_scan_check.py` |
| Derate / OCV | `SDC-032/033/040-045/054/115/132/156/157` — pairing, direction, ranges, corners, methodology | `checker.py`, `derate_methodology.py` |
| Resets / CDC | `SDC-151/152/153` — unconstrained reset trees, blanket cuts, sync-stage shape | `async_reset_check.py` |
| Design-aware refs | `SDC-055/056/057/058` — object existence, wildcards, hierarchy, top selection | `design_context.py` |
| Best-practice info | `SDC-100-126, 130-132, 140` — ~28 advisory items | `checker.py` |
| Connectivity | `pin_nets`/`net_pins`/`module_port_dirs` + pin classification `CLOCK / RESET / SCAN / TEST / CONSTANT` | `design_context.py` |

**Verified NOT a gap:** F3 Phase B (scan-chain shape detection + lock-up-latch
guard) is already implemented in `dft_scan_check.py` (`SCAN_CHAIN_MIN_LINKS = 2`,
`_scan_chain_instances`, guard text in the module docstring L32–38). Any
"scan-chain detection" candidate was therefore rejected.

---

## 1. Research method

1. Dumped all 119 rules from the live registry (code + severity + description).
2. Four parallel web-research passes: (a) SDC semantic pitfalls where tools
   silently accept wrong constraints; (b) feature inventory of existing
   checkers (OpenSTA `check_timing`, OpenROAD, Vivado timing DRC / `report_utds`,
   PrimeTime `check_timing` / `report_analysis_coverage` / `report_constraints`,
   Tempus, open-source SDC linters); (c) industry signoff review checklists;
   (d) which checks are structurally detectable from an SDC + netlist alone.
3. Every candidate was then verified against the actual code to prove it is a
   genuine gap (the "Verified at" columns above) and does not duplicate an
   existing rule.

---

## 2. G1 — Generated-clock & waveform option validation (→ SDC-158)

### What
Value/count sanity on `create_generated_clock` and `create_clock` options:
`-divide_by` / `-multiply_by` must be positive integers; `-edges` must supply
exactly 3 edge indices; `-edges_shift` exactly 3 shifts; `-waveform` must have
2 values with rising < falling; `-invert` combined with `-edges` is the only
legal `-invert` form (invalid with `-divide_by`).

### Why it matters (verified gap)
`checker.py` L265 only rejects having *both* `-divide_by` and `-multiply_by`.
`clock_relations.py` L109–135 parses the values with no sanity check —
`divide_by=0` silently computes `gen_period = master_period * 0 = 0` (a
zero-period clock). `-edges {1 3}` (2 values) is accepted as-is. These are the
classic copy-paste divider-chain errors: silently wrong periods, no parser
error.

### Design
- **New module:** `rta/engine/analysis/generated_clock_check.py` (name TBD).
- **Rule:** `SDC-158` (warning) "Generated clock / waveform option invalid".
- Pure text/value checks — no netlist, no clock model.
- Provable-only: every sub-check is a literal violation of SDC syntax
  semantics (count of `-edges` values, sign/zero of `-divide_by`, etc.).

### Effort: S. Test plan
- `-divide_by 0` → SDC-158; `-edges {1 3}` → SDC-158; valid
  `-edges {1 3 5}` / `-divide_by 4` → clean; golden corpus zero new fires.

---

## 3. G2 — Undefined-clock-reference sweep (→ SDC-159)

### What
Extend the existing "referenced clock must be defined" checks beyond their
current scope. Today `SDC-046` covers `set_input_delay/set_output_delay -clock`,
`SDC-047` covers `create_generated_clock -master_clock`, and `SDC-048` covers
`set_clock_groups`. The sweep adds every other command that takes
`[get_clocks X]`: `set_data_check -clock`, `set_max_delay`/`set_min_delay`
`-from`/`-to`, `set_multicycle_path` clock refs, `set_clock_uncertainty`,
`set_clock_latency`, `set_propagated_clock`.

### Why it matters (verified gap)
`checker.py` L114–135 already has the resolver (parses `-clock [get_clocks ...]`
refs, handles wildcards conservatively), but the diagnostic is only wired to
I/O-delay commands. A typo'd clock name inside an exception **silently
constrains nothing** — the file validates clean while the intended path stays
unconstrained.

### Design
- **New module:** `rta/engine/analysis/clock_ref_check.py` (name TBD), or a
  guarded section in `checker.py` reusing the existing resolver.
- **Rule:** `SDC-159` (warning) "Undefined clock referenced in timing command".
- Wildcards inside collections (`[get_clocks {clk* sync*}]`) stay
  unresolvable-by-design (no finding) — same convention as `SDC-046`.

### Effort: S. Test plan
- `set_data_check -clock [get_clocks typo_clk]` → SDC-159; defined clock →
  clean; `[get_clocks *]` → clean; golden corpus zero new fires.

---

## 4. G3 — Endpoint completeness, the `check_timing` analog (→ SDC-160, TAB)

### What
The industry-standard completeness check (PrimeTime/Tempus/OpenSTA
`check_timing` categories `no_clock` and `unconstrained_internal_endpoints`):
1. every sequential clock pin has a *defined* clock reaching it;
2. every sequential data pin is structurally reachable from a constrained
   source (port with I/O delay, defined clock, or covered by an exception).

### Why it matters (verified gap)
`SDC-001` fires only when *zero* clocks exist. `design_coverage.py` covers
ports/clocks/exceptions, not internal sequential endpoints. Nothing in the
registry reports "this flop's clock pin has no clock" or "this flop's D-pin is
reachable from nothing" — internal endpoints with no timing requirement are
silently arbitrary.

### Design
- **New module:** `rta/engine/analysis/endpoint_completeness.py` (name TBD).
- Netlist-aware (design-aware mode only; skipped in SDC-only mode like F2).
- Reuses `design_context` connectivity (`net_pins`/`pin_nets`) and the
  flop-identification already proven by SDC-151's reset-pin fanout logic.
- **Rule:** `SDC-160` (warning) "Unconstrained sequential endpoint".
- Provable-only, with documented exemptions: structurally constant nets
  (the classifier's `CONSTANT` class) and scan/test pins (SDC-154/155 domain)
  never fire.
- **Fixed thresholds, no knobs** (per project convention, cf. F2's ≥2 rule):
  a clock pin is either reached by a defined clock or not; a data pin is either
  reachable from a constrained source or not — no tunable count.

### Effort: M. Test plan
- Synthetic netlist: flop clocked by a net with no `create_clock` → SDC-160
  (no_clock); flop D-pin reachable only from an unconstrained input port →
  SDC-160 (endpoint); fully constrained design → clean; SDC-only mode → skipped.

---

## 5. G4 — ICG / clock-gating check completeness (→ SDC-161, TAB)

### What
Detect latch-based integrated clock gating (ICG) shapes in the netlist and flag
gated branches with no `set_clock_gating_check` and/or no timing coverage on
the enable path.

### Why it matters (verified gap)
`coverage.py` L115/L150–152 only counts the *presence* of
`set_clock_gating_check`; `SDC-118` is a generic info advisory. No rule detects
ICG cells structurally and asks whether their enable timing is actually
covered — a known signoff miss (gated-branch enables fall under `check_timing`
`no_clock`/unconstrained categories).

### Design
- **New module:** `rta/engine/analysis/clock_gating_check.py` (name TBD).
- Pattern-match ICG-shaped cells (latch + AND combos, or `*ICG*`/`*LAT*`
  vendor cell names) using the same connectivity approach as
  `dft_scan_check._scan_chain_instances`.
- **Rule:** `SDC-161` (warning) "Gated clock branch without gating check" —
  fires only when an ICG shape is provable AND the branch has no
  `set_clock_gating_check` and no covering exception.
- **Severity decision point (like F4):** the "no gating check" half may be
  pre-CTS-legitimate; keep the finding at warning only when the enable path is
  also unconstrained, else info. To be confirmed with the domain engineer.

### Effort: M. Test plan
- Synthetic netlist with an ICG-shaped cell, no `set_clock_gating_check` →
  SDC-161; with the check present → clean; no ICG shapes → zero fires.

---

## 6. G5 — Memory interface completeness (→ SDC-162, TAB)

### What
Detect memory-macro-shaped instances (SRAM/BRAM/register-file vendor names and
port patterns: address / data-in / data-out / WE / CS / CLK) and flag
address/data/control pins with no I/O delay or exception coverage.

### Why it matters (verified gap)
No RAM/SRAM/register-file detection exists anywhere in the engine. Memory
interface timing is per-IP and easily forgotten — unconstrained memory pins
produce silently-arbitrary setup/hold requirements.

### Design
- **New module:** `rta/engine/analysis/memory_interface_check.py` (name TBD).
- **Heuristic, documented, degrade-safe:** vendor-name patterns
  (`*SRAM*`, `*RAM*`, `*spram*`, `ts1n*`, `*rf*` register files, …) +
  port-shape signatures. Unknown macros → the finding says
  "memory-shaped instance, cannot prove pin coverage" (info), never a wrong
  assertion — consistent with the project's provable-only ethos.
- **Rule:** `SDC-162` (warning) "Unconstrained memory interface pin" (info when
  only the heuristic, not proof, is available).

### Effort: M. Test plan
- Synthetic netlist with a named SRAM macro, unconstrained address bus →
  SDC-162; with `set_output_delay` on the bus → clean; ambiguous shape → info,
  never warning.

---

## 7. G6 — General CDC flop-crossing check (→ SDC-163, DEFERRED)

### What
Cross-domain flop→flop paths (launch flop on clock A, capture flop on clock B)
with no synchronizer shape and no covering exception. F2 (SDC-151–153) covers
**reset trees** specifically; this is the general clock-domain case.

### Why it matters
The industry's core CDC structural check; today only reset-shaped CDC is
covered. Verified as a genuine gap, but it needs per-flop clock-domain
assignment (tracing clock nets to each flop's clock pin), which is the largest
netlist-modeling lift of this round.

### Design (scoped, not built now)
- **New module (later):** `rta/engine/analysis/cdc_check.py`.
- **Rule:** `SDC-163` (warning) "Cross-domain path without synchronizer or
  exception".
- **Decision:** implement after (or together with) the full-chip
  `design_context` extension (`FULLCHIP_DESIGN_CONTEXT_PLAN.md`), where
  cross-file clock-domain tracing lands naturally. Deferred by design, not
  forgotten.

### Effort: L (deferred). Test plan (when built)
- Two-clock synthetic netlist, unsynchronized cross-domain path → SDC-163;
  2-FF synchronizer shape → clean; clock-group exception → clean.

---

## 8. G7 — Blanket I/O-delay wildcards (→ SDC-164)

### What
Mirror of SDC-152 for I/O delays: `set_input_delay ... [all_inputs]` or
`set_output_delay ... [all_outputs]` — a blanket cut that masks per-interface
timing review.

### Why it matters (verified gap)
SDC-028/029 check `-min` presence; SDC-066 checks bus bit-partial coverage;
nothing flags the blanket `[all_inputs]`/`[all_outputs]` form. Unlike SDC-152
(a reset tree provably covered by a wildcard), blanket I/O delays are
legitimate in many single-clock flows — hence **info**, not warning.

### Design
- Guarded section in `checker.py` (or the G2 module).
- **Rule:** `SDC-164` (info) "Blanket I/O delay wildcard".

### Effort: S. Test plan
- `set_input_delay ... [all_inputs]` → SDC-164; per-port delays → clean;
  golden corpus: `real_design_full.sdc` and `full_featured.sdc` must stay
  clean or justify the info item (corpus sweep decides).

---

## 9. G8 — Test-mode pin coverage beyond `scan_en` (→ SDC-165)

### What
Netlist-aware: pins classified `TEST`/`SCAN` by `design_context` (beyond the
`scan_en` family SDC-154 handles) with no `set_case_analysis` assignment.

### Why it matters (verified gap)
`design_context.py` classifies `SCAN/TEST` pins; SDC-154 covers the
`scan_en`-family naming pattern specifically; SDC-109 is a generic info hint.
`test_mode`/`test_se`/`shift_en`-style pins with no mode assignment are the
same silent blend-shift-and-capture failure, just outside SDC-154's naming net.

### Design
- Extend the F3 module (`dft_scan_check.py`) with a design-aware section —
  additive, no signature change.
- **Rule:** `SDC-165` (warning) "Test-mode pin without case analysis" (SDC-only
  mode: fires on `test_mode`/`test_se` naming only, like SDC-154; netlist mode:
  uses the classifier).

### Effort: S. Test plan
- Netlist with a `test_mode` pin, no case analysis → SDC-165; with
  `set_case_analysis` → clean; no TEST/SCAN pins → zero fires.

---

## 10. Rejected candidates (checked, not gaps)

| Candidate | Why rejected |
|---|---|
| Scan-chain shape detection | Already shipped (F3 Phase B, `dft_scan_check.py`) |
| MCP setup/hold pairing, half-cycle paths | SDC-021/037 |
| Clock-mux glitch grouping, async-vs-exclusive | SDC-060/061/062/063 |
| `set_max_delay` < `set_min_delay`, exception overlaps | SDC-069/070 |
| Virtual-clock I/O methodology | Weak signal; legitimately varies by flow |
| Uncertainty/jitter double-count | Legitimate practice (uncertainty includes jitter) |
| UPF / level-shifters / power-domain timing | Out of pure block-SDC scope (roadmap-def erred) |
| Min pulse width | Noise at block level without STA data |
| Async-FIFO gray-code false paths | Too deep for SDC-only; folds into deferred G6 |

---

## 11. New/changed signatures (summary)

| Feature | New module | New codes | Signature |
|---|---|---|---|
| G1 | `generated_clock_check.py` | `SDC-158` | `generated_clock_findings(text) -> list[Finding]` |
| G2 | `clock_ref_check.py` | `SDC-159` | `clock_ref_findings(text, commands) -> list[Finding]` |
| G3 | `endpoint_completeness.py` | `SDC-160` | `endpoint_findings(text, ctx) -> list[Finding]` (ctx optional) |
| G4 | `clock_gating_check.py` | `SDC-161` | `gating_findings(text, ctx) -> list[Finding]` |
| G5 | `memory_interface_check.py` | `SDC-162` | `memory_findings(text, ctx) -> list[Finding]` |
| G6 | `cdc_check.py` (later) | `SDC-163` | `cdc_findings(text, ctx) -> list[Finding]` |
| G7 | (in `checker.py` section) | `SDC-164` | — |
| G8 | (extends `dft_scan_check.py`) | `SDC-165` | additive arg, no signature break |

- Each called from a new guarded `try/except` section in `check_sdc` (the
  Phase 8/9/10 + F1–F4 pattern).
- **No existing signature changes.** Rules registry: pure `_r(...)` additions,
  codes in the 158+ range to avoid collision.

---

## 12. Decisions — resolved

1. **UI presentation of G3/G4/G5:** **three separate tabs** (confirmed with the
   product owner), each following the proven Mechanism-B recipe:
   `Timing Completeness` (G3) · `Clock Gating` (G4) · `Memory Interfaces` (G5).
   Each gets: engine module → rules registered → `tab_<name>` added to
   `st.tabs([...])` in `legacy/streamlit/app.py` → `add_parser()` in
   `rta/cli/cli.py` (`rta completeness`, `rta gating`, `rta memory`) →
   `rta report <name>` HTML report → evidence golden fixtures.
2. **G1/G2/G7/G8 are Checker rules, not tabs** — granular findings that belong
   in the Checker output (same as F1–F4); no new UI surface.
3. **Severities:** G1/G2/G3/G5/G8 warning (provable); G4 warning-with-info-half
   **pending domain-engineer sign-off** (F4-style decision point); G7 info
   (legit in many flows); G4's bare "no gating check" half info.
4. **Fixed thresholds, no config knobs** (project convention, cf. F2's ≥2 and
   SDC-022's 0.05 ns): G3's endpoint definitions and G5's memory pin rules are
   boolean/provable, not tunable counts.
5. **G6 deferred to the full-chip phase** (`FULLCHIP_DESIGN_CONTEXT_PLAN.md`) —
   it needs cross-file clock-domain tracing; not built in this round.
6. **Order:** Phase 1 (SDC-only rules G1/G2/G7/G8 — fastest, no UI) → Phase 2
   (netlist-aware tabs G3/G4/G5) → G6 later. No speculative reordering.

---

## 13. Phased delivery

**Phase 1 — Checker rules (no new tabs):**
SDC-158 (G1) · SDC-159 (G2) · SDC-164 (G7) · SDC-165 (G8).

**Phase 2 — Three analysis tabs (Mechanism B, 5-layer recipe):**
| Tab | CLI | Report | Rule | Module |
|---|---|---|---|---|
| Timing Completeness | `rta completeness` | `rta report completeness` | SDC-160 | `endpoint_completeness.py` |
| Clock Gating | `rta gating` | `rta report gating` | SDC-161 | `clock_gating_check.py` |
| Memory Interfaces | `rta memory` | `rta report memory` | SDC-162 | `memory_interface_check.py` |

**Phase 3 (deferred):** Clock Domain Crossing tab (G6, SDC-163) with full-chip.

---

## 14. Test plan (shared gates)

- New synthetic fixtures per feature (listed in each section above).
- **Noise gate:** each new rule must produce **zero new fires** on the existing
  `golden/`, `valid/`, `netlist_aware/`, `readiness/`, and `reset_demo`
  fixtures (or justify each fire as a true positive, F2/F4-style).
- **Evidence sync:** regenerate `RELEASE_EVIDENCE.json` via
  `python rta/evidence/build_evidence.py` (rule count changes to 123 after
  Phase 1, 126 after Phase 2) — same drift discipline as v1.5.0→v1.5.6.
- **Regression:** full `pytest rta/tests -q` (826 → 826+new, all green) +
  `smoke_test.py` + readiness/golden/golden-semantic runners.
- **Docs:** new codes appear in `rta rules list/show`, the UI rules reference,
  and the CLI guide; new tabs documented in the web UI feature docs.

---

## 15. Explicitly out of scope (deferred, not forgotten)

- Full-chip / hierarchical resolution (planned separately in
  `FULLCHIP_DESIGN_CONTEXT_PLAN.md`; G6 grows from it).
- Product Experience visualizations (clock tree, relation matrix, etc.).
- Any LLM/generative component in the analysis path (ruled out by roadmap).
- Changing or renumbering any existing SDC code or its severity.
