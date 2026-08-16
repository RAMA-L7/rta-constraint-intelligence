# Ṛta Engineer Test Kit

A self-contained set of real-world SDC + netlist fixtures for testing every
feature of Ṛta the way a design engineer would on a real project. Each set
carries exactly the inputs its feature needs (SDC alone, or SDC + netlist
pair) and documents the expected findings.

Tool version verified against: **v1.5.6** (CLI: `python cli.py`, or the
installed `rta` command).

## The canonical block

Most sets are built around one realistic two-clock block, `apb_uart_top`:

| File | What it is |
|---|---|
| `shared/apb_uart_top.v` | Top module: APB slave + UART core, /2 divider instance |
| `shared/apb_div2.v` | /2 divider cell (`u_div2/out` is the generated-clock pin) |
| `shared/apb_uart_core.v` | Core: APB register file + UART TX/RX on the divided clock |
| `shared/apb_uart_netlist.v` | Combined single-file netlist (what `--netlist` loads) |

Ports: `clk`, `rst_n`, APB bus (`apb_psel/penable/pwrite/paddr[11:0]/pwdata[31:0]/prdata[31:0]/pready`),
UART (`rxd`/`txd`), DFT pins (`scan_en`, `test_mode`). `rst_n` fans out to
every flop reset pin; `clk_div2` comes from `u_div2`.

Every netlist-aware set contains its own copy of `apb_uart_netlist.v` so the
folder is fully self-contained.

## How to run everything

Use the `rta` console command (or `python cli.py` from the repo root). Run
each command from the repo root so relative paths line up.

## Set-by-set guide

### 01_block_full — reference (good) block
Files: `apb_uart.sdc` + `apb_uart_netlist.v`
```
rta check engineer_test_kit/01_block_full/apb_uart.sdc --netlist engineer_test_kit/01_block_full/apb_uart_netlist.v --top apb_uart_top
```
Expected: **0 errors, 2 warnings** (SDC-020 confirm-false-path x2: rst_n and
rxd/txd). No SDC-151..157, no blockers. Readiness: REVIEW_REQUIRED.

### 02_check_variants — checker edge cases (SDC only)
| File | Expected |
|---|---|
| `no_io_delays.sdc` | SDC-005, SDC-006 (errors) |
| `io_exceeds_period.sdc` | SDC-008 (input delay > period) |
| `missing_generated_source.sdc` | SDC-003 (generated clock without `-source`) |
| `duplicate_clocks.sdc` | SDC-002 (duplicate clock name) |
| `empty.sdc` | SDC-001 (no clock defined) |

### 03_clock_relations — clock relation analysis (SDC only)
```
rta analyze clock-relations <file>
```
| File | Expected |
|---|---|
| `dual_port_async.sdc` | SDC-060 mismatch (async should be physically_exclusive) |
| `async_no_groups.sdc` | SDC-062 info (no clock groups declared) |
| `gen_chain.sdc` | Clean, 3 clock pairs, 0 mismatches |

### 04_coverage — design-aware coverage (SDC + netlist)
```
rta coverage engineer_test_kit/04_coverage/partial_bus.sdc --netlist engineer_test_kit/04_coverage/apb_uart_netlist.v --top apb_uart_top
```
Expected: `apb_paddr` is 12 bits but only `[3:0]` is constrained, so the bus
is PARTIAL (SDC-065); the other APB inputs are unconstrained (SDC-064).

### 05_design_context — object resolution (SDC + netlist)
```
rta check <file> --netlist engineer_test_kit/05_design_context/apb_uart_netlist.v --top apb_uart_top
```
| File | Expected |
|---|---|
| `typo_port.sdc` | SDC-055 (`datat_in` does not exist) |
| `wildcard_nomatch.sdc` | SDC-056 (`apb_*_x` matches nothing) |
| `bad_hierarchy.sdc` | SDC-055 + SDC-057 (`u_core/u_nope` missing) |

### 06_scan_dft — DFT/scan checks (SDC + netlist)
```
rta check <file> --netlist engineer_test_kit/06_scan_dft/apb_uart_netlist.v --top apb_uart_top
```
| File | Expected |
|---|---|
| `scan_unconstrained.sdc` | SDC-154 (scan_en has no set_case_analysis) |
| `scan_blanket.sdc` | SDC-155 (blanket cut in DFT design) + SDC-152 (blanket covers reset tree) + SDC-020 |

### 07_reset_cdc — async reset & CDC (SDC + netlist)
```
rta check <file> --netlist engineer_test_kit/07_reset_cdc/apb_uart_netlist.v --top apb_uart_top
```
| File | Expected |
|---|---|
| `reset_unconstrained.sdc` | SDC-151 (rst_n tree, no exception) |
| `reset_blanket.sdc` | SDC-152 (wildcard covers reset tree) |
| `reset_covered.sdc` | No SDC-151..153 (targeted exception present) |
| `sync_stage/top.sdc` + `sync.v` | SDC-153 (reset also drives data pins; run with `--netlist sync_stage/sync.v --top top`) |

### 08_derate_ocv — derate methodology (SDC only)
```
rta check --verbose <file>
```
| File | Expected |
|---|---|
| `flat_on_16nm.sdc` | SDC-156 info (flat derates on SS_0P72V_16C corner) |
| `mixed_methodology.sdc` | SDC-157 info (flat + sigma derates mixed) |

### 09_rationale — exception comments (SDC only)
| File | Expected |
|---|---|
| `no_comment.sdc` | SDC-150 (false path without comment) |
| `commented.sdc` | No SDC-150 (comment present; SDC-020 still shows) |

### 10_generate — SDC generator (no input files needed)
```
rta generate -d apb_uart -c clk=10.0:clk -c clk_div2=5.0 -u 0.15 --operating-condition SS_0P72V_16C --derate --ideal-reset --reset-port rst_n --propagated --scan --scan-port scan_en -o engineer_test_kit/10_generate/generated.sdc
```
`generated.sdc` is the golden output.

### 11_lint — linter / formatter
```
rta lint --check engineer_test_kit/11_lint/messy.sdc    # exit 1
rta lint engineer_test_kit/11_lint/messy.sdc -o engineer_test_kit/11_lint/linted.sdc
rta lint --check engineer_test_kit/11_lint/linted.sdc   # exit 0
```
`linted.sdc` is the golden formatted output.

### 12_convert — SDC to JSON/YAML
```
rta convert engineer_test_kit/12_convert/apb_uart.sdc -f json -o engineer_test_kit/12_convert/apb_uart.json
rta convert engineer_test_kit/12_convert/apb_uart.sdc -f yaml -o engineer_test_kit/12_convert/apb_uart.yaml
```

### 13_diff — semantic constraint diff
```
rta diff engineer_test_kit/13_diff/v1.sdc engineer_test_kit/13_diff/v2.sdc --linked-v1 engineer_test_kit/13_diff/defs_v1.tcl --linked-v2 engineer_test_kit/13_diff/defs_v2.tcl
```
Expected: CHG-CK-006 (period 10 -> 12 via TCL), CHG-IO-001 (txd delay 3.0 ->
2.5), CHG-FP-003 (new rst_n false path), CHG-GEN-001/002 (added/removed IO).

### 14_baseline_gate — baseline + CI gates
```
rta check engineer_test_kit/14_baseline_gate/apb_uart.sdc --netlist engineer_test_kit/14_baseline_gate/apb_uart_netlist.v --top apb_uart_top --save-baseline engineer_test_kit/14_baseline_gate/baseline.json
```
Then compare regressions under two policies:
```
rta check .../changed.sdc --netlist ... --top apb_uart_top --baseline .../baseline.json --gate STRICT
   -> FAIL (new blocker SDC-006)
rta check .../changed_review_only.sdc --netlist ... --top apb_uart_top --baseline .../baseline.json --gate STRICT
   -> FAIL (new review item)
rta check .../changed_review_only.sdc --netlist ... --top apb_uart_top --baseline .../baseline.json --gate CUSTOM --gate-policy engineer_test_kit/14_baseline_gate/gate_policy.yaml
   -> PASS (team-review-flow allows review items, blocks new blockers)
```
`gate_policy.yaml` is the lenient team-review CUSTOM policy example.

### 15_corners — PVT corner presets
```
rta corners list -o engineer_test_kit/15_corners/corners_list.txt
rta corners show "Full 8-corner" -o engineer_test_kit/15_corners/corner_full_8corner.txt
```

### 16_batch — directory batch processing
```
rta batch check engineer_test_kit/16_batch/batch_in
rta batch lint engineer_test_kit/16_batch/batch_in
rta batch report check engineer_test_kit/16_batch/batch_in --output-dir engineer_test_kit/16_batch/reports
rta batch report coverage engineer_test_kit/16_batch/batch_in --output-dir engineer_test_kit/16_batch/reports_cov
```
Expected: 4 files, 2 OK / 2 errors (empty.sdc, invalid.sdc).

### 17_report — HTML signoff reports
```
rta report check 01_block_full/apb_uart.sdc --netlist ... --top apb_uart_top -o 17_report/report_check.html
rta report diff 13_diff/v1.sdc 13_diff/v2.sdc --linked-v1 ... --linked-v2 ... -o 17_report/report_diff.html
rta report clock-relations 03_clock_relations/dual_port_async.sdc -o 17_report/report_clock_relations.html
rta report coverage 04_coverage/partial_bus.sdc -o 17_report/report_coverage.html
```

### 18_test_drive — realistic two-clock block (validate → diff → gate → report)
A believable DMA-engine block (`dma_engine_top`, AHB slave + stream engine,
`clk_ahb` + `clk_periph` primaries + `clk_div2` generated clock). This is the
workflow teaching set: V1 is the known-good baseline, V2 is an engineer's
change that **dropped the `stream_out` output delay** and left the new
peripheral-domain exception undocumented.

Files: `dma_engine.sdc` (V2, current), `dma_engine_v1.sdc` (baseline),
`dma_engine_top.v` (netlist), `baseline.json` (V1 readiness snapshot).

```
# 1. Validate the current state (design-aware)
rta check engineer_test_kit/18_test_drive/dma_engine.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top
#    -> SDC-059 + SDC-065: stream_out has no output delay (the regression)
#    -> SDC-020 x2: false paths need confirmation

# 2. Clock relations: the peripheral-domain group is missing
rta analyze clock-relations engineer_test_kit/18_test_drive/dma_engine.sdc
#    -> SDC-062 x3 missing constraints (clk_ahb/clk_periph among them)

# 3. Diff: what changed vs the reviewed baseline
rta diff engineer_test_kit/18_test_drive/dma_engine_v1.sdc \
  engineer_test_kit/18_test_drive/dma_engine.sdc
#    -> CHG-GEN-002 removed set_output_delay stream_out
#    -> CHG-GEN-003 clock group lost clk_periph

# 4. CI gate: the regression must be blocked
rta check engineer_test_kit/18_test_drive/dma_engine.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top \
  --baseline engineer_test_kit/18_test_drive/baseline.json --gate STRICT
#    -> FAIL (exit 1): new unconstrained output port vs baseline
rta check engineer_test_kit/18_test_drive/dma_engine_v1.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top \
  --baseline engineer_test_kit/18_test_drive/baseline.json --gate STRICT
#    -> PASS (exit 0)

# 5. Report
rta report check engineer_test_kit/18_test_drive/dma_engine.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top \
  --baseline engineer_test_kit/18_test_drive/baseline.json --gate STRICT \
  -o engineer_test_kit/18_test_drive/report.html
```

Expected (verified, v1.5.8): V2 validate = 0 errors / 4 warnings; V1 gate
STRICT = PASS (exit 0); V2 gate STRICT = FAIL (exit 1) with the unconstrained
`stream_out` listed as the regression.

## Engine fixes surfaced by this kit (v1.5.6 -> next)

1. **Reset-tree detection missed `rst_n` pins.** `design_context._pin_role`
   and `async_reset_check._pin_role` recognized `rst`, `reset`, `rstn`, ... but
   not `rst_n`, the most common reset naming. SDC-151/152/153 silently never
   fired for such designs. Fixed by adding `rst_n`, `reset_n`, `arst_n`
   suffixes.
2. **Semantic diff missed period increases.** Only a period DECREASE produced
   CHG-CK-001; an increase (10 -> 12 ns) was invisible. Added CHG-CK-006.
3. **IO delay value changes misreported as remove+add.** The comparison key
   included the numeric value, so a 3.0 -> 2.5 change looked like a deletion
   plus a new constraint instead of a modified one. The key now matches on
   endpoint + mode (not value), so CHG-IO-001 reports the modification.

## Rules reference

119 rules across 7 modules (`rta rules list`). The advanced rules exercised
here: SDC-150..157 (rationale, reset/CDC, scan/DFT, derate methodology).
