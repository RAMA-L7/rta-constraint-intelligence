# Ṛta CLI — Engineer's Guide to Every Feature

> **Version:** 1.5.6 · **Command:** `rta` · **Platform:** Linux / macOS / Windows (Python ≥ 3.10)

This guide walks through **every feature** of Ṛta's command-line interface. Everything below was verified against the v1.5.6 release — the examples are real command output, not pseudocode.

---

## 1. Installation

### Option A — install from PyPI (recommended for testers)

```bash
pip install rta-constraint-intelligence
```

```bash
rta --version          # Ṛta v1.5.6
```

> The Streamlit UI (section 14) is an optional extra: `pip install "rta-constraint-intelligence[web]"`.

### Option B — run from the repository (no install)

```bash
git clone https://github.com/RAMA-L7/rta-constraint-intelligence
cd rta-constraint-intelligence
pip install -r requirements.txt
python cli.py check samples/real_design_full.sdc     # or: python cli.py <command>
```

On Windows there is also a `rta.cmd` shortcut in the repo root.

### Try it immediately

```bash
rta check samples/real_design_full.sdc     # run from the repo root
```

---

## 2. Command overview

| Command | Purpose | Typical use |
|---|---|---|
| `rta check` | Validate an SDC file (errors/warnings/info) | Before every synthesis run |
| `rta generate` | Generate a synthesis-ready SDC from parameters | New block bring-up |
| `rta diff` | Semantic diff between two SDC versions | Constraint change review |
| `rta corners` | List/inspect PVT corner presets | MMC setup |
| `rta analyze clock-relations` | Clock group inference & mismatch detection | Clock domain sanity |
| `rta analyze all` | **One-shot E2E** — check + coverage + clock + interactions + readiness | Full block review |
| `rta rules` | Browse the SDC rule registry | Look up what an SDC-NNN code means |
| `rta coverage` | Constraint gap analysis (coverage vs. missing) | Signoff readiness |
| `rta report` | HTML signoff reports (check/diff/clock/coverage) | Documentation / review |
| `rta lint` | Reorganize + clean up SDC formatting | House style |
| `rta convert` | SDC → JSON/YAML structured output | Tool integration |
| `rta batch` | Run check/lint/report over a directory of SDCs | Regression runs |
| `rta web` | Launch the Streamlit web workspace | Interactive use |

Run `rta <command> --help` for the exact flags of any command. (The legacy name `rta` was dropped in the rebrand — the command is `rta`.)

---

## 0. ⚠️ Read this first: file paths

In every example below, `my_block.sdc` (and `old.sdc`, `new.sdc`, `my_block.v`, …) is a **placeholder for your real file path** — either a relative path from the directory you're in, or an absolute path:

```bash
# from the directory that contains the file:
rta check my_block.sdc

# from anywhere, using a relative or absolute path:
rta check ../designs/my_block.sdc
rta check C:/work/designs/my_block.sdc        # Windows
rta check /home/you/designs/my_block.sdc      # Linux/macOS
```

If the tool says `can't open '...': No such file or directory`, the path is wrong or the file isn't there — check the filename and the directory you're in (`pwd` / `dir`).

---

## 3. `rta check` — validate an SDC file (the core feature)

Parses an SDC and runs **40+ semantic checks**, reporting:

- **Errors** (`SDC-001..011`…) — must fix; synthesis would produce wrong results
- **Warnings** (`SDC-020..061`, `SDC-150..155`) — should review; potential design issues
- **Info** (`SDC-100..132`) — best practices
- **Rationale linting** (`SDC-150`) — flags `set_false_path` / `set_multicycle_path` / `set_case_analysis` lines that lack an explanatory comment (the advice SDC-020 already gives, now enforced). Pure text check — no netlist needed
- **Async reset / CDC completeness** (`SDC-151..153`) — design-aware only (needs `--netlist`): flags reset trees (nets driving ≥2 flop reset pins) with no targeted timing exception (`SDC-151`), blanket wildcard false paths that hide the sync-input vs deassertion distinction (`SDC-152`), and reset synchronizer sync-stage shapes with no exception (`SDC-153`). Provable-only: SDC-only mode stays silent
- **DFT / scan-mode completeness** (`SDC-154..155`) — Phase A runs in both modes: flags a `scan_en`/`test_mode`-style signal referenced in the SDC with NO `set_case_analysis` mode assignment (`SDC-154`; a single-value `0` or `1` is legitimate per-mode practice), and a fully-blanket false path (`-from [all_inputs] -to [all_registers]`, `*`) in a DFT design (`SDC-155`). Phase B (needs `--netlist`) detects scan-chain shapes (SI→Q→SI→Q shift chains) and flags cuts matching all flops — never false-path flops present in the scan chain (lock-up latch guard)
- **AOCV/POCV derate methodology** (`SDC-156..157`, info-level) — advisory methodology-consistency axis on top of the value-sanity derate rules: `SDC-156` flags flat-only `set_timing_derate` values on a flow that signals a small node (a `set_operating_conditions` name like `SS_0P72V_16C`, an `Nnm` mention, or a POCV/AOCV keyword in a named condition); `SDC-157` flags flat derates mixed with sigma/table-based derates in one file. Both are info (never warning) by design — flat OCV derate is legitimate for many designs. Temperatures (25C/125C) and voltage fractions (0P7V) never match a node hint. Shown with `rta check --verbose` or in JSON output
- **Stats** — clocks, delays, exceptions found
- **Readiness review** — a 7-dimension signoff-readiness verdict (Clocks, I/O, Exceptions, Coverage, Consistency, Analysis Trust, Design Context)

```bash
rta check my_block.sdc
rta check my_block.sdc --verbose          # also show info items
rta check my_block.sdc --json             # machine-readable (CI)
rta check my_block.sdc -f csv             # csv / text / markdown
rta check my_block.sdc -o report.txt      # write to file
rta check my_block.sdc --junit -o junit.xml   # JUnit XML for CI
```

**Exit codes (important for CI):** `0` = no errors found, `1` = errors found.

```bash
rta check samples/buggy_no_clocks.sdc; echo $?    # prints 1 (errors)
rta check samples/minimal_sdc.sdc;     echo $?    # prints 0
```

### CI quality gate

```bash
rta check my_block.sdc --gate STRICT
# --gate choices: BLOCKERS_ONLY | NO_READINESS_REGRESSION | STRICT | CUSTOM
# 0 = pass, 1 = gate blocked, 2 = gate error
```

A gate policy can be supplied from YAML with `--gate-policy policy.yaml`.

### Design-aware checking (optional netlist)

Supply a Verilog netlist (RTL or gate-level, block-level scope) to verify that
every `get_ports` / `get_pins` / `get_cells` reference actually resolves:

```bash
rta check my_block.sdc --netlist my_block.v
rta check my_block.sdc --netlist my_block.v --top my_block_top   # if multiple top candidates
```

When a netlist is present, the checker additionally runs **SDC-055..059**
(netlist resolution) and **SDC-064..066** (design-aware coverage). Without a
netlist, object references are reported as `NETLIST_REQUIRED` — an honest
"cannot prove this" rather than a silent pass.

### Custom rules (YAML policies)

```bash
rta check my_block.sdc --custom-rules my_rules.yaml
# --custom-rules is repeatable; see docs/features/README-07-custom-rules.md
```

---

## 4. `rta generate` — create a synthesis-ready SDC

Generate a complete SDC from parameters — useful for new blocks or golden-file comparison.

```bash
rta generate -d MY_CHIP -c clk=10.0:sys_clk > my_chip.sdc
```

More complete example:

```bash
rta generate \
  -d riscv_core \
  -c clk=10.0:sys_clk \
  -c clk2=5.0:clk_axi \
  -u 0.2 \
  --operating-condition "SS_0P72V_125C" \
  --derate \
  --ideal-reset --reset-port rst_n \
  --propagated \
  --scan --scan-port scan_mode \
  -o riscv_core.sdc
```

| Flag | Meaning |
|---|---|
| `-d / --design NAME` | Design name (default `MY_DESIGN`) |
| `-c / --clock NAME=PERIOD[:PORT]` | Add a clock (repeatable). `clk=10.0:sys_clk` = 10 ns clock on port `sys_clk` |
| `-u / --uncertainty NS` | Clock uncertainty (default 0.15) |
| `--operating-condition NAME` | PVT operating condition |
| `--derate` | Add AOCV timing derate commands |
| `--ideal-reset` | `set_ideal_network` + `set_false_path` on reset |
| `--propagated` | Add `set_propagated_clock` |
| `--scan` | Add DFT scan-mode case analysis |

Output includes a review warning: generated values are a starting point, not signoff.

---

## 5. `rta diff` — semantic constraint diff

Detects **hidden changes** between two SDC versions — beyond text diffing, it
understands semantics, resolves TCL variables, and catches wildcard drift:

```bash
rta diff old.sdc new.sdc
rta diff old.sdc new.sdc --json
rta diff old.sdc new.sdc --verbose          # show V1/V2 text of changes
rta diff old.sdc new.sdc -o changes.txt
```

With linked TCL variable definitions (repeatable):

```bash
rta diff v1.sdc v2.sdc --linked-v1 vars_v1.tcl --linked-v2 vars_v2.tcl
```

**What it reports:** Added / Removed / Modified constraints, plus Fatal,
Warning, and Info change categories (`CHG-*` codes). Try it on the samples:

```bash
rta diff samples/constraint_diff_v1.sdc samples/constraint_diff_v2.sdc
```

---

## 6. `rta corners` — PVT corner presets

Manage and inspect predefined multi-corner (MMC) collections:

```bash
rta corners list
#   Classic 3-corner (Worst/Typ/Best)  (3 corners)
#   Industrial 5-corner  (5 corners)
#   Full 8-corner signoff  (8 corners)
#   Custom (empty)

rta corners show "Classic 3-corner"      # partial match OK — full detail per corner
rta corners list -o corners.txt
```

---

## 7. `rta analyze` — clock domain analysis & the one-shot E2E run

### `rta analyze clock-relations` — clock domain analysis

Infers expected clock relations and flags mismatches (incorrect clock groups):

```bash
rta analyze clock-relations my_block.sdc
rta analyze clock-relations my_block.sdc --verbose   # show all clock pairs + definitions
rta analyze clock-relations my_block.sdc --json -o clocks.json
rta analyze clock-relations my_block.sdc --netlist my_block.v   # cross-check clock source ports
```

Example finding (`SDC-062`): a clock pair that should be `-physically_exclusive`
but is specified `-asynchronous`, or is missing a `set_clock_groups` entirely.
With `--netlist`, clock-definition lines are additionally cross-checked against
the design (e.g. SDC-055 — a clock source port that doesn't exist).

### `rta analyze all` — the one-shot full-block E2E run

Runs **every deterministic analysis** over the same SDC (+ optional netlist)
and emits one combined result — the fastest way to get the complete picture of
a block before STA:

```bash
# one text summary of check + coverage + clocks + interactions + readiness
rta analyze all my_block.sdc

# one HTML report containing every section — shareable / archivable
rta analyze all my_block.sdc -o full_report.html

# design-aware (same engine as rta check --netlist)
rta analyze all my_block.sdc --netlist my_block.v --top top -o full_report.html

# machine-readable for CI
rta analyze all my_block.sdc --json -o full.json
```

The HTML report includes sections for **Issues**, **Coverage**, **Clock
Relations**, **Constraint Interactions**, **Constraint Readiness**, and (with a
netlist) **Design-Aware Coverage**. Exit code matches `rta check`: `0` = no
errors, `1` = errors found — so it works as a CI gate too.

---

## 8. `rta rules` — the rule registry

Look up what any SDC code means, why it matters, and how to fix it:

```bash
rta rules list                              # every rule
rta rules list -m checker                   # by module: checker, mmc, clock_relations,
                                            #   constraint_diff, design_context, design_coverage
rta rules list -s warning                   # by severity: error, warning, info, fatal
rta rules list --search clock               # keyword search
rta rules show SDC-060                      # full detail for one code
rta rules list --json -o rules.json
```

```bash
rta rules show SDC-060
#   Code:       SDC-060
#   Severity:   warning
#   Name:       Async Instead of Physically Exclusive
#   Description: Clock pair marked -asynchronous but should be -physically_exclusive...
#   Fix:        Change to 'set_clock_groups -physically_exclusive' for clocks sharing the same source port.
```

---

## 9. `rta coverage` — constraint gap analysis

Measures which constraint categories are covered vs. missing — 39 items across
6 categories (SDC-only mode). A **score out of 100** plus the missing list:

```bash
rta coverage my_block.sdc
rta coverage my_block.sdc --missing-only   # show only the gaps
rta coverage my_block.sdc --json -o coverage.json
rta coverage my_block.sdc --netlist my_block.v --top top   # design-aware port coverage
```

```bash
rta coverage samples/real_design_full.sdc --json
# keys: version, file, score_pct, total_items, total_present, total_missing, ...
```

With a netlist, coverage becomes design-aware (SDC-064..066): constraints are
verified against actual design objects instead of assumed — the output adds a
design-aware section (inputs/outputs/clocks/exceptions port coverage).

---

## 10. `rta report` — HTML signoff reports

Generate professional HTML reports for documentation, review, or signoff:

```bash
rta report check my_block.sdc -o check_report.html
rta report check my_block.sdc --netlist my_block.v --top top -o check_report.html   # design-aware
rta report diff old.sdc new.sdc -o diff_report.html
rta report clock-relations my_block.sdc -o clocks_report.html
rta report coverage my_block.sdc -o coverage_report.html
```

Each report is a self-contained HTML page (branded with the Ṛta title and
styling) suitable for sharing or archiving.

---

## 11. `rta lint` — reorganize & clean SDC formatting

Consistent section ordering, spacing, and formatting:

```bash
rta lint my_block.sdc                    # print formatted output
rta lint my_block.sdc --check            # exit 1 if not lint-clean (CI gate, no output)
rta lint my_block.sdc --fix              # rewrite the file in place
rta lint my_block.sdc -o formatted.sdc   # write to a new file
```

```bash
rta lint samples/real_design_full.sdc --check && echo "lint-clean"
# → "SDC file is lint-clean"
```

---

## 12. `rta convert` — SDC → JSON/YAML

Parse an SDC and emit structured data for tool integration:

```bash
rta convert my_block.sdc                 # JSON to stdout
rta convert my_block.sdc -f yaml         # YAML
rta convert my_block.sdc -f json -o my_block.json
```

Output includes `sdc_version`, `units`, `clocks`, `input_delays`,
`output_delays`, exceptions, and more.

---

## 13. `rta batch` — run across a directory

```bash
rta batch check samples/            # check every .sdc in a directory
rta batch lint samples/             # lint every .sdc
rta batch report samples/           # generate a report per .sdc
```

```bash
rta batch check samples/check_variants
# Batch Summary: Total 2, OK 2, Errors 0, Skipped 0
```

Ideal for regression runs: check an entire constraint suite and get a summary
table plus per-file exit behavior.

---

## 14. `rta web` — pointing to the tool UI

`rta web` now prints how to launch the product tool instead of starting a
server. The earlier workspace surface (port 8501) has been retired as the
product UI to avoid two competing tool interfaces:

```bash
rta web
# Ṛta — the workspace web UI at :8501 has been retired.
# The product tool is the Streamlit UI. Launch it with:
#     streamlit run legacy/streamlit/app.py
```

### The Streamlit app (12 tabs) — `legacy/streamlit/app.py`

The full 12-tab interactive workspace (Checker, Generator, Linter, Converter,
Corner Mgr, MMC SDC, Diff, Clock, Coverage, Interactions, Readiness, Rules)
is the Streamlit app and the product tool. It requires the `web` extra:

```bash
pip install "rta-constraint-intelligence[web]"
streamlit run legacy/streamlit/app.py     # from the repo root → http://localhost:8502
```

A **live hosted instance** of the Streamlit app is also available at the URL
provided separately — no install needed to try it. Both UIs run the same
deterministic engine as the CLI.

---

## 15. Suggested workflow for an engineer

```bash
# 1. The complete picture in one command (recommended starting point)
rta analyze all my_block.sdc --netlist my_block.v --top top -o my_block_report.html

# 2. Baseline quality — how bad is it?
rta check my_block.sdc --verbose

# 3. What's missing?
rta coverage my_block.sdc --missing-only

# 4. Verify object references against the netlist (if available)
rta check my_block.sdc --netlist my_block.v --top top

# 5. Fix issues → re-check until clean
rta check my_block.sdc            # exit 0 = no errors

# 6. Keep the style consistent
rta lint my_block.sdc --check

# 7. Before a hand-off, generate the HTML report
rta report check my_block.sdc -o my_block_report.html

# 8. When constraints change, review the semantic diff
rta diff baseline.sdc my_block.sdc
```

---

## 16. Troubleshooting

| Symptom | Fix |
|---|---|
| `command not found: rta` | Reinstall: `pip install rta-constraint-intelligence`; on Windows ensure the Python `Scripts` folder is on `PATH` |
| `ModuleNotFoundError: streamlit` on `rta web` | Install the extra: `pip install "rta-constraint-intelligence[web]"` |
| `rta check` says `NETLIST_REQUIRED` | Expected in SDC-only mode — supply `--netlist` to enable design-aware checks |
| Multiple top candidates in netlist | Pass `--top <module>` explicitly |
| Rule code you don't recognize | `rta rules show <CODE>` |
| Wrong Python version | Ṛta requires Python ≥ 3.10 |

---

## 17. Sample files (use these to explore every feature)

| File | What it demonstrates |
|---|---|
| `samples/minimal_sdc.sdc` | Small clean SDC — 0 errors, some warnings |
| `samples/real_design_full.sdc` | Large realistic design with multiple findings |
| `samples/buggy_no_clocks.sdc` | Missing clocks — guaranteed errors |
| `samples/warning_heavy.sdc` | Warning-heavy file |
| `samples/edge_case_malformed.sdc` | Malformed content |
| `samples/edge_case_empty.sdc` | Empty file handling |
| `samples/edge_case_extreme_values.sdc` | Extreme numeric values |
| `samples/constraint_diff_v1.sdc` / `_v2.sdc` | Pair for `rta diff` |
| `samples/clock_relations.sdc` | Pair analysis for `rta analyze clock-relations` |
| `samples/multi_corner_template.sdc` | Multi-corner template |
| `rta/evidence/netlist_aware/NA*.v` | 10 netlist fixtures for `--netlist` (valid, hierarchy, buses, wildcards, broken design, multiple tops, large) |

---

## 18. Quick reference card

```
check   rta check f.sdc [--json|--junit|-f csv|--netlist v.v|--top T|--custom-rules y]
generate rta generate -d CHIP -c clk=10.0:port [-u 0.15] [--derate|--scan|--propagated]
diff    rta diff a.sdc b.sdc [--json] [--linked-v1 t.tcl] [--linked-v2 t.tcl]
corners rta corners list | rta corners show "<name>"
analyze rta analyze clock-relations f.sdc [--verbose|--json] | rta analyze all f.sdc [--netlist v.v] [-o r.html|--json]
rules   rta rules list [-m mod] [-s sev] [--search q] | rta rules show SDC-060
coverage rta coverage f.sdc [--missing-only|--json|--netlist v.v]
report  rta report {check|diff|clock-relations|coverage} ... -o out.html   # check also: --netlist v.v
lint    rta lint f.sdc [--check|--fix|-o out.sdc]
convert rta convert f.sdc [-f json|yaml] [-o out]
batch   rta batch {check|lint|report} <dir>
web     rta web           # needs [web] extra
```

**Exit codes:** `0` pass · `1` check errors / lint not clean / gate blocked · `2` gate error.

---

*Ṛta — deterministic constraint-quality layer that runs before STA. No LLMs, no EDA tool required. MIT licensed.*
