# Ṛta — High-Coverage SDC Validation Fixture Report

> **Status:** complete. One realistic, production-style block SDC that exercises
> **100% coverage across Ṛta's 39 measured SDC coverage categories** (39/39).
> **Coverage is NOT correctness** — verified independently (construct-to-line
> mapping + removal tests). No engine behavior was changed; no coverage number
> was hard-coded or manufactured.
>
> **Sprint scope:** fixture + netlist + V1/V2 pair + regression tests + report
> only. No UI, no features, no strategy, no unrelated fixtures, no engine edits.

---

## 1. Fixture purpose

Prove that Ṛta's SDC constraint coverage can reach 100% on a **believable,
internally coherent block-level SDC** — not on a synthetic list of unrelated
commands — and that the coverage number is *real* (every covered category maps
to an actual constraint construct; deleting a constraint flips exactly its
category).

## 2. Design scenario

`ahb_spi_ctrl_top` — an **AHB-slave SPI master controller** (40nm LP, 100 MHz
AHB / 25 MHz SPI), a common block-level integration unit:

- **Clocks:** `clk_ahb` (primary, 10 ns), `clk_spi` (primary, 40 ns),
  `clk_ahb_div2` (generated, /2 from `u_div2/out` on `clk_ahb`),
  `vclk_ahb` (virtual, external AHB-master timing reference).
- **CDC:** AHB domain (and its /2) declared asynchronous to the SPI domain
  and the virtual clock — every async pair covered by `set_clock_groups`.
- **I/O:** AHB slave input setup/hold (vs `vclk_ahb`), AHB read-data output,
  SPI MISO input / SCLK-MOSI-CS_N outputs (vs `clk_spi`), IRQ output.
- **Exceptions:** async reset false path, MISO→AHB synchronizer false path,
  multiply→accumulate multicycle (setup 2 / hold 1), datapath-only max delay,
  min delay guard, two path groups, one disabled timing arc.
- **DFT / power:** functional-mode case analysis (scan/test), ideal reset +
  scan-enable, ICG gating check + min pulse width, dynamic/leakage budgets,
  dont-use cells, wire-load mode, AOCV derate, operating conditions.

Every constraint has a documented engineering reason in the file header and
inline comments; none was added merely for keyword coverage.

## 3. Files created / modified

| File | Purpose |
|---|---|
| `engineer_test_kit/19_high_coverage/ahb_spi_ctrl.sdc` | **The fixture** (V2, 100%) |
| `engineer_test_kit/19_high_coverage/ahb_spi_ctrl_v1.sdc` | Earlier revision (V1, 82.1%) for `rta diff` |
| `engineer_test_kit/19_high_coverage/ahb_spi_ctrl_top.v` | Matching netlist (design-aware mode) |
| `tests/test_high_coverage_fixture.py` | 19 regression tests (semantic contract) |
| `engineer_test_kit/README.md` | New `19_high_coverage` section |
| `engineer_test_kit/manifest.json` | New kit set `19_high_coverage` |

No engine, rule, API, or UI file was modified.

## 4. Coverage before / after

| Measurement | Before (flagship `real_design_full.sdc`) | After (this fixture) |
|---|---|---|
| Coverage score | 82.1% | **100.0%** |
| Present / total | 32 / 39 | **39 / 39** |
| Missing | 7 | **0** |

The 7 categories the flagship lacked, now each covered by a real construct:
`set_clock_jitter`, `set_clock_gating_check`, `set_min_delay`, `group_path`,
`set_wire_load_mode`, `set_ideal_network`, `set_min_pulse_width`.

## 5. Exact coverage categories → SDC construct → line → result

Verified by re-running `parse_sdc_coverage` over the fixture (line numbers
from the actual file):

| Coverage category | Item | SDC construct | Line | Result |
|---|---|---|---|---|
| Clocks | Primary clock | `create_clock -name clk_ahb` | 24 | present |
| Clocks | Generated clock | `create_generated_clock -name clk_ahb_div2` | 35 | present |
| Clocks | Clock uncertainty | `set_clock_uncertainty` | 42 | present |
| Clocks | Clock latency | `set_clock_latency -source` | 45 | present |
| Clocks | Clock transition | `set_clock_transition` | 46 | present |
| Clocks | Clock jitter | `set_clock_jitter` | 48 | present |
| Clocks | Propagated clock | `set_propagated_clock` | 49 | present |
| Clocks | Clock groups | `set_clock_groups -asynchronous` | 57 | present |
| Clocks | Clock gating check | `set_clock_gating_check` | 51 | present |
| I/O | Input delay (max) | `set_input_delay -max ... -clock vclk_ahb` | 65 | present |
| I/O | Input delay (min / hold) | `... -min 0.3` (same cmds) | 65/71 | present |
| I/O | Output delay (max) | `set_output_delay -max ... -clock vclk_ahb` | 68 | present |
| I/O | Output delay (min / hold) | `... -min 0.4` (same cmds) | 68/73/76 | present |
| I/O | Driving cell / input transition | `set_driving_cell -lib_cell BUF_X4` | 78 | present |
| I/O | Output load | `set_load 0.05 [all_outputs]` | 81 | present |
| Exceptions | False paths | `set_false_path` ×2 | 87/90 | present |
| Exceptions | Multicycle paths | `set_multicycle_path -setup 2` | 96 | present |
| Exceptions | Multicycle hold fix | `set_multicycle_path -hold 1` | 97 | present |
| Exceptions | Max delay | `set_max_delay -datapath_only 8.0` | 103 | present |
| Exceptions | Min delay | `set_min_delay 1.0` | 105 | present |
| Exceptions | Group paths | `group_path` ×2 | 112/113 | present |
| Exceptions | Disable timing arcs | `set_disable_timing` | 124 | present |
| Design Rules | SDC version | `set sdc_version 2.2` | 15 | present |
| Design Rules | Units | `set_units` | 19 | present |
| Design Rules | Max fanout | `set_max_fanout 16` | 128 | present |
| Design Rules | Max transition | `set_max_transition 0.20` | 129 | present |
| Design Rules | Max capacitance | `set_max_capacitance 0.08` | 130 | present |
| Design Rules | Max area | `set_max_area 50000` | 131 | present |
| AOCV/Derate | Operating conditions | `set_operating_conditions -max WORST` | 136 | present |
| AOCV/Derate | Timing derate | `set_timing_derate` ×4 | 140–143 | present |
| AOCV/Derate | Derate early + late | `-early` + `-late` | 141/140 | present |
| AOCV/Derate | Derate cell + net | `-cell_delay` + `-net_delay` | 140–143 | present |
| AOCV/Derate | Wire load mode | `set_wire_load_mode top` | 148 | present |
| Power/DFT | Ideal network | `set_ideal_network` ×2 | 153/154 | present |
| Power/DFT | Max dynamic power | `set_max_dynamic_power 100 mW` | 158 | present |
| Power/DFT | Max leakage power | `set_max_leakage_power 10 mW` | 159 | present |
| Power/DFT | Min pulse width | `set_min_pulse_width` ×2 | 161/162 | present |
| Power/DFT | Case analysis (DFT) | `set_case_analysis 0` ×2 | 118/119 | present |
| Power/DFT | Dont-use cells | `set_dont_use` ×2 | 166/167 | present |

## 6. Rule IDs exercised

Checker + analysis findings on the fixture: **0 errors, 0 warnings, 3 info**
(SDC-126 virtual-clock advisory, SDC-130 corner-context advisory, clock-relation
info aggregation). Clock relations: **0 mismatches, 0 missing, 0 advisories**
(all 6 pairs have a declared or provable relationship). The full rule registry
(119 rules) applies; the fixture was designed so no rule has grounds to fire.

## 7. Errors / warnings

- **0 errors** — the SDC parses cleanly and no rule detects a violation.
- **0 warnings** — every timing exception carries a rationale comment
  (SDC-150 satisfied), every I/O delay has a `-min` (SDC-028/029 satisfied),
  multicycle has its hold fix (SDC-021 satisfied), derates are methodologically
  consistent (SDC-032/033/040–043 satisfied), groups carry an exclusion type
  (SDC-031 satisfied).
- **3 info** — advisory trust disclosures, not defects.

## 8. Design-aware results (SDC + netlist)

`ahb_spi_ctrl_top.v` resolves every object the SDC references:

| Dimension | Result |
|---|---|
| Ports / instances | 17 ports, 6 instances, 22 nets, 36 pins |
| Inputs | 11 total — 6 constrained, 5 exempt (clock/reset/scan/test), **0 unconstrained** |
| Outputs | 6 total — **6 constrained**, 0 unconstrained, 0 partial |
| Clocks | 4 defined, 3 structurally resolved (virtual clock has no net) |
| Exceptions | 6 total — **6 resolved**, 0 empty collections, 0 unsupported |
| SDC-055/056/057 (object resolution) | **none** |
| SDC-064/065/066 (design coverage findings) | **none** |

The design-aware tier independently confirms the SDC's claims: no unconstrained
data port, no vacuous exception.

## 9. Limitations

1. **100% is the SDC-only coverage denominator (39 items / 6 categories).** It
   is *presence* of constraint categories — **not** correctness, not zero
   findings (the coverage CLI states this), not STA signoff, not timing closure.
2. **The generator cannot express everything this fixture needs**, so the
   fixture is hand-authored in production style (same approach as the flagship
   `real_design_full.sdc`):
   - generated clock observed at an **internal pin** (`[get_pins u_div2/out]`),
   - **virtual clock inside `set_clock_groups`**,
   - `set_max_delay` / `set_min_delay` (no generator options),
   - explicit I/O port collections (the generator's
     `[remove_from_collection [all_inputs] ...]` form defeats SDC-059's
     conservative name-capture).
   The generator remains correct and tested for what it does support.
3. **Virtual clock has no structural fanout** — `vclk_ahb` is not
   netlist-resolvable by design (honest, not a defect).
4. Readiness is `REVIEW_REQUIRED` in both modes, driven by the honest
   ANALYSIS TRUST disclosure (10 partially-analyzed commands — options the
   scope model records as ignored, e.g. `-clock`, `-from`, `-virtual`). This is
   the product's documented trust behavior, not a fixture defect.

## 10. Full test results

| Suite | Result |
|---|---|
| New regression tests (`tests/test_high_coverage_fixture.py`) | **19 passed** |
| Full pytest suite | **1247 passed** (1228 baseline + 19 new) |
| Smoke suite (`rta/evidence/test_release_smoke.py`) | 10 passed |
| Comprehensive checks (`tests/run_comprehensive_test.py`) | 32/32 passed |
| Linter on fixture | lint-clean (exit 0) |
| Converter (JSON / YAML) | parses, 4 clocks, 2 input / 3 output delays, 2 FP, 2 MCP, 1 group |
| `rta diff` V1→V2 | 8 added constraints, 0 removed, 0 fatal, 0 warnings |
| HTML report (check + coverage) | both render |

## 11. Independent validation (coverage is real)

Beyond the number itself:

- **Construct-to-line table** (section 5) maps every covered category to its
  actual command line.
- **Removal tests** (in the regression suite): deleting any one of the seven
  previously-missing constructs drops coverage to exactly **38/39 (97.4%)** and
  flags *that* category; deleting all seven reproduces exactly **32/39
  (82.1%)** — identical to V1 and the flagship fixture. The score is therefore
  a deterministic function of the SDC content, not a hard-coded constant.

## 12. Confirmation: no engine behavior changed

`git status`/`git diff` scoped to the sprint shows **only** the new fixture
set, its regression test, and the kit README/manifest rows. No file under
`rta/engine/`, `rta/cli/`, `rta/api/`, or `rta/tools/` was modified. All
1,247 tests pass on the unmodified engine.

## 13. Confirmation: no coverage number manufactured

The 39/39 result is produced by the unmodified `parse_sdc_coverage` on a
fixture whose 39 covered constructs are individually verifiable (section 5)
and whose score provably responds to content changes (section 11). No rule,
coverage calculation, registry, or result JSON was altered, and no finding
was fabricated or suppressed.

## 14. What does "100%" mean?

**100% coverage across Ṛta's 39 measured SDC coverage categories** — and
**Coverage is NOT correctness.** Every one of the 39 categories Ṛta's engine
can legitimately recognize is represented by a real, coherent, explainable
construct in one believable block SDC, in both SDC-only and design-aware
modes, with 0 errors and 0 warnings. It is not "100% of all possible SDC
commands ever" and it is not a correctness/signoff claim — both of which the
engine's own trust disclosures already state.
