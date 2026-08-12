# Feature 13: Example Library — real constraint sets with golden outcomes

> **Purpose:** ready-to-run examples for evaluating Ṛta or learning the
> tool. Every entry below is a real fixture in the repo with an expected
> outcome asserted by the evidence runners — not a toy.
> **CLI path:** install with `pip install rta-constraint-intelligence` and run
> the commands from anywhere (they use absolute fixture paths).

---

## 1. Quick start (60-second demo)

```bash
pip install -U rta-constraint-intelligence
rta --version                      # Ṛta v1.5.6

# Full end-to-end on a realistic multi-clock SoC → one HTML report
rta analyze all \
  "$E/reference_designs/rd02_multi_clock_soc/rd02_multi_clock_soc.sdc" \
  -o report.html

# Design-aware check (SDC + netlist, top module named)
rta check "$E/netlist_aware/NA01_valid_single_module.sdc" \
  --netlist "$E/netlist_aware/NA01_valid_single_module.v" --top top
```

Set `E` once per shell: `E="<your-repo>/rta/evidence"` (or the installed
package path — `python -c "import rta, os; print(os.path.dirname(rta.__file__))"`).

---

## 2. Netlist-aware pairs (SDC + Verilog, `rta/evidence/netlist_aware/`)

Each `NA##` is a `.sdc` + `.v` pair exercising one design-aware capability.
Run: `rta check <NA##>.sdc --netlist <NA##>.v --top top --verbose`.

| ID | Demonstrates | Expected outcome |
|----|--------------|------------------|
| NA01 | valid single module; clean design-aware validation | 0 errors; all references resolvable |
| NA02 | typo'd `get_ports clk` vs netlist | **SDC-055** (Design Object Not Found) |
| NA03 | multi-level hierarchy (`u_core/u_reg0`) | nested instances/pins resolve |
| NA04 | buses (`data_in[3]`, `data_in[*]`, `addr_out[9]`) | bus references resolve |
| NA05 | wildcard collections | `debug_*` resolves; `bogus_*` → **SDC-056** (Empty Collection) |
| NA06 | generated clock `pll_out` missing from netlist | **SDC-055** on `pll_out`; trust = PARTIALLY_VALIDATED |
| NA07 | bad hierarchy path `u_core/u_nope/Q` | **SDC-057** (Invalid Hierarchy Reference) |
| NA08 | multiple nonexistent objects | **SDC-055** ×N |
| NA09 | two candidate top modules (`chip_a`/`chip_b`) | parse ambiguity — pick `--top` explicitly |
| NA10 | large netlist (17 instances, nested) | clean parse; perf benchmark fixture |

## 3. Reference designs (full-chip-ish blocks, `rta/evidence/reference_designs/`)

Each `rd##/` is a complete design folder with its own SDC. Golden outcome:
**RD01–RD06 are `ok: true`** (clean or benign findings); **RD07 is the broken
design** — expect errors; RD08 is the large/perf design.

| ID | Design | What to try |
|----|--------|-------------|
| RD01 | single clock | `rta check` — clean baseline |
| RD02 | multi-clock SoC | `rta analyze all` → full HTML report (the flagship demo) |
| RD03 | generated-clock hierarchy | `rta analyze clock-relations` + `--netlist` cross-check |
| RD04 | DDR-style interface | I/O delay + interface constraint review |
| RD05 | multimode | `set_case_analysis` / mode coverage |
| RD06 | timing exceptions | false-path/multicycle patterns |
| RD07 | **broken design** | `rta check` → errors (proves detection works) |
| RD08 | large design | perf / `--netlist` sweep |

## 4. Feature-demo fixtures

| Location | Demonstrates | Run & expect |
|----------|--------------|--------------|
| `samples/reset_demo/top.sdc` + `top.v` | F2 — unconstrained reset tree | `rta check top.sdc --netlist top.v --top top` → **SDC-151** |
| `samples/reset_demo/blanket.sdc` | F2 — blanket wildcard false path | `rta check blanket.sdc --netlist top.v --top top` → **SDC-152** (plus SDC-150 rationale lint; no DFT signal, so SDC-155 stays silent — for SDC-155 use a file with a `scan_en` case analysis + all-flops cut) |
| `samples/reset_demo/covered.sdc` | F2 clean case | targeted `set_false_path -from [get_ports rst_n]` → no SDC-151..153 |
| `samples/reset_demo/sync.v` | F3 — reset synchronizer shape | swap netlist → **SDC-153** |
| `rta/evidence/valid/full_featured.sdc` | every constraint category in one file | `rta check --verbose` → broad Info coverage, minimal noise |
| `rta/evidence/invalid/*.sdc` (9 files) | each real defect class | `rta batch check` → all fail with the expected rule |
| `rta/evidence/golden/` (10 categories) | golden regression corpus | `python rta/evidence/run_golden.py` → **22/22** |

## 5. Batch sweep patterns

```bash
# One-line regression sweep of a whole category
rta batch check "$E/valid"        # all clean
rta batch check "$E/invalid"      # all fail — proves detection

# Golden regression suites (repo developers)
python rta/evidence/run_golden.py           # 22/22
python rta/evidence/run_readiness.py        # 15/15
python rta/evidence/run_golden_semantic.py  # 9/9
```

## 6. Golden outcomes are machine-checked

Every expected outcome above is asserted by the evidence runners and the
`rta/tests` suite (823 tests). If a fixture's behavior changes, the golden
runners fail — the library can't silently rot. Adding a new example: create
the SDC (+netlist) under `rta/evidence/<category>/`, record the expected
outcome in that category's `manifest.json`, and re-run `run_<category>.py`.
