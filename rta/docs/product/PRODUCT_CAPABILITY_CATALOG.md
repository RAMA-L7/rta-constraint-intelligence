# SDC Tools — Complete Feature Reference (for startup evaluation)

> **An exhaustive technical reference of the SDC Tools project**: what it is, what inputs it takes,
> every feature, every check/rule it performs, every CLI command, the web UI surface, the data
> formats, the packaging, and the test/sample coverage. Version analyzed: **v1.3.0**
> (build backend `setuptools.build_meta`, Python `>=3.10`).

---

## 1. What the project is

**SDC Tools** is an open-source (MIT) Python toolkit for **Synopsys Design Constraint (SDC)** files —
the industry-standard timing/power/design-rule constraint format used in VLSI synthesis and signoff.
It provides the full constraint lifecycle in one tool:

```
Write ─▶ Validate ─▶ Generate ─▶ Review ─▶ Signoff
  │          │           │           │          │
  │          │           │           │          │
  ▼          ▼           ▼           ▼          ▼
Rules    Checker     Generator   Diff/Matrix   Reports
Engine                              + Coverage
```

**Core value proposition** (from the module docstrings): "Validate, generate, and analyze SDC files —
no EDA tool required." It catches the mistakes that cause silicon failure or thousands of false
timing violations (a missing clock, an incorrect derate, an overly broad wildcard), and it does so
**with zero external dependencies for the core** (stdlib only). YAML (`pyyaml`) and the web UI
(`streamlit`) are optional extras.

**What a user feeds it**: SDC text (paste, file upload, or file path) plus optional TCL variable
files and YAML custom-rule policy files.
**What it produces**: validation results (errors/warnings/info with rule codes), generated SDC text,
linted/reorganized SDC text, structured JSON/YAML, semantic diff reports, clock-relation matrices,
constraint-coverage scores, per-corner multi-corner SDCs + ZIPs, self-contained HTML signoff
reports, and a Streamlit web UI with a feedback dashboard.

---

## 2. Architecture at a glance

```
sdc-tools-main/
├── Core modules (pure Python, stdlib) ────────────────────────────
│   ├── checker.py           # SDC validation (11 errors, 26 warnings, 33 info + clock relations)
│   ├── generator.py         # SDC generation from an SDCParams dataclass
│   ├── linter.py            # SDC formatter + section reorganizer
│   ├── converter.py         # SDC → structured JSON / YAML
│   ├── batch_runner.py      # Directory-wide batch check / report / lint
│   ├── constraint_diff.py   # Semantic SDC diff + 21 change-impact rules (CHG-*)
│   ├── tcl_resolver.py      # TCL $VAR / ${VAR} resolution + source-file dependency tracking
│   ├── wildcard_analyzer.py # Wildcard pattern parse / compare / 0–10 risk scoring
│   ├── clock_relations.py   # Clock relation inference (5 rules) + mismatch detection
│   ├── corner_manager.py    # PVT corner data model + 4 presets + JSON serialization
│   ├── mmc.py               # Multi-corner SDC generation, diff, cross-corner checks, ZIP
│   ├── coverage.py          # 39-item constraint gap analysis across 6 categories
│   ├── custom_rules.py      # YAML-based project-specific validation policies
│   ├── rules_registry.py    # Central documentation of all 95 rule codes (SDC-*, CHG-*)
│   └── reporter.py          # 5 self-contained HTML signoff report types
├── Interfaces ────────────────────────────────────────────────────
│   ├── cli.py               # 12-command CLI (argparse), CI/CD friendly
│   ├── app.py               # Streamlit web UI (10 feature tabs + 2 full views)
│   └── ui/                  # components, feedback, tab_linter, tab_converter, tab_rules, tab_test_drive
├── Packaging & deployment ────────────────────────────────────────
│   ├── pyproject.toml       # setuptools.build_meta; entry point sdc-tools = cli:main
│   ├── Dockerfile           # python:3.11-slim; ENTRYPOINT python cli.py
│   ├── .pre-commit-config.yaml / .pre-commit-hooks/sdc-check.sh
│   ├── sdc-tools.cmd        # Windows CLI wrapper
│   └── .github/workflows/ci.yml  # 3-OS × 3-Python matrix + lint job
├── Samples & docs ────────────────────────────────────────────────
│   ├── samples/             # 19 sample files across 3 subdirectories
│   ├── custom_rules_example.yaml  # 10 example rules
│   ├── docs/features/       # 10 per-feature READMEs
│   └── tests/               # 15 pytest files, 330 collected tests
```

**Dependency graph** (verified):
- `mmc.py` → `generator.py`, `checker.py`, `corner_manager.py`
- `custom_rules.py` → `checker.py` (via `integrate_with_check`)
- `constraint_diff.py` → `tcl_resolver.py`, `wildcard_analyzer.py`
- `checker.py` → `clock_relations.py` (aggregates SDC-060..063)
- `cli.py` → everything; `app.py` → everything via ui modules
- `corner_manager.py` — standalone (no intra-project imports)

---

## 3. Core module: SDC Checker (`checker.py`) — *what it actually checks*

**Entry point:** `check_sdc(text: str) -> CheckResult`

**Input:** one string of SDC text.
**Output:** `CheckResult` with three parts:

| Part | Type | Contents |
|------|------|----------|
| `issues` | `List[Issue(sev, code, msg, line)]` | errors + warnings, each with rule code and source line |
| `info` | `List[InfoItem(code, msg)]` | best-practice suggestions (advisory) |
| `stats` | `dict` | per-command counts (see below) |

`CheckResult.errors` / `.warnings` are convenience filters. Exit contract at CLI level: any error → exit 1.

**Stats keys** (exact): `Clocks, Generated clocks, Virtual clocks, Input delays, Output delays,
False paths, Multicycle paths, Clock groups, Uncertainty, Clk transition, Clk jitter,
Max transition, Max cap, Case analysis, Disable arcs, Timing derate, Oper conditions,
Group paths, Propagated`.

### 3.1 Errors (SDC-001..011)

| Code | Check performed | When it fires |
|------|-----------------|---------------|
| **SDC-001** | Missing clock | No `create_clock` and no `create_generated_clock` |
| **SDC-002** | Duplicate clock name | Two `create_clock` commands share a `-name` |
| **SDC-003** | Generated clock missing `-source` | A `create_generated_clock` has no `-source` flag |
| **SDC-004** | Conflicting divide/multiply | One `create_generated_clock` has both `-divide_by` and `-multiply_by` |
| **SDC-005** | No input delay | Clocks exist but zero `set_input_delay` |
| **SDC-006** | No output delay | Clocks exist but zero `set_output_delay` |
| **SDC-007** | Clock on data port | `create_clock [get_ports ...]` port name matches `data|addr|bus|wdata|rdata|din|dout` |
| **SDC-008** | Input delay ≥ clock period | A `set_input_delay` value `>=` the referenced clock's period (or the min-period clock if unqualified) — leaves no input margin |
| **SDC-009** | Output delay ≥ clock period | Same rule for `set_output_delay` |
| **SDC-010** | Propagated clock on virtual clock | `set_propagated_clock` references a virtual clock |
| **SDC-011** | Invalid case-analysis value | `set_case_analysis` value not in `0, 1, rising, falling` |

### 3.2 Warnings (SDC-020..037)

| Code | Check | When it fires |
|------|-------|---------------|
| **SDC-020** | Suspicious false path | `set_false_path` with both `-from` and `-to`, not obviously async/scan/test |
| **SDC-021** | Multicycle without hold fix | `set_multicycle_path -setup N` (N>1) with no `-hold` |
| **SDC-022** | Unrealistically tight uncertainty | `set_clock_uncertainty` value `< 0.05ns` |
| **SDC-023** | Very high clock uncertainty | value `> 0.5ns` |
| **SDC-024** | Multiple clocks without clock groups | `>1` clocks and no `set_clock_groups` (CDC un-flagged) |
| **SDC-025** | Wildcard `dont_touch` | `set_dont_touch` matching `[all_cells]` or `*` |
| **SDC-026** | Extremely tight `max_transition` | threshold below a floor |
| **SDC-027** | `set_max_delay` without `-datapath_only` | max delay on a potentially multi-cycle path |
| **SDC-028** | No input delay `-min` | `set_input_delay` exists but none has `-min` (hold unchecked) |
| **SDC-029** | No output delay `-min` | same for output delays |
| **SDC-030** | No `set_propagated_clock` | ideal-clock model is over-optimistic for post-layout |
| **SDC-031** | Clock groups missing exclusion type | `set_clock_groups` present but no `-asynchronous` / `-logically_exclusive` / `-physically_exclusive` |
| **SDC-032** | Derate early without late | `set_timing_derate` has `-early` but no `-late` |
| **SDC-033** | Derate late without early | `-late` but no `-early` |
| **SDC-034** | Data check without `-clock` | `set_data_check` missing `-clock` reference |
| **SDC-035** | Excessive disable timing | `>5` `set_disable_timing` commands |
| **SDC-036** | Disable timing without from/to | `set_disable_timing` with neither `-from` nor `-to` (kills all arcs on the cell) |
| **SDC-037** | Half-cycle without hold fix | half-cycle `-setup ... -rise_to/-fall_to` paths with no matching `-hold 0` |

### 3.3 Derate-reasonableness warnings (SDC-040..045)

| Code | Check | When it fires |
|------|-------|---------------|
| **SDC-040** | cell_early derate `< 1.0` | `set_timing_derate -early -cell_delay` below 1.0 |
| **SDC-041** | cell_late derate `> 1.0` | `set_timing_derate -late -cell_delay` above 1.0 |
| **SDC-042** | net_early derate `< 1.0` | `-early -net_delay` below 1.0 |
| **SDC-043** | net_late derate `> 1.0` | `-late -net_delay` above 1.0 |
| **SDC-044** | Unrecognized operating condition | name doesn't match `WORST/BEST/TYP/TYPICAL/SSG/TT/FFG/SS/FF` |
| **SDC-045** | Hold/setup uncertainty ratio | `-hold` not ≈ `0.5×` the `-setup` value (tolerance ±15%) |

### 3.4 Clock-relation checks surfaced by the checker (SDC-060..063)

The checker calls `clock_relations.analyze_clock_relations()` and folds its results in:
- **warning-severity** mismatches (SDC-060, SDC-061) are appended as **checker warnings**;
- **info-severity** findings (SDC-062, SDC-063) are **aggregated into a single info item**
  (e.g. `"N clock pair(s) lack an explicit set_clock_groups declaration (e.g. a/b — inferred async). See the Clock Relations tab / matrix…"`). This prevents hundreds of pair-by-pair lines;
- if the analysis itself throws, an **SDC-140** info item is emitted (`Clock relation analysis skipped: …`).

### 3.5 Info / best-practice suggestions (SDC-100..132, SDC-140)

| Code | Suggestion |
|------|------------|
| SDC-100 | No `sdc_version` declaration — add `set sdc_version 2.2` |
| SDC-101 | No `set_units` — avoid unit mismatches |
| SDC-102 | No `set_max_fanout` |
| SDC-103 | No `set_max_transition` |
| SDC-104 | No `set_max_capacitance` |
| SDC-105 | No `set_load` on outputs |
| SDC-106 | No driving cell / input transition / `set_drive` — input slew ideal |
| SDC-107 | No `set_clock_latency` — model insertion delay pre-CTS |
| SDC-108 | No `set_clock_transition` |
| SDC-109 | No `set_case_analysis` (for scan_en/test_mode) |
| SDC-110 | No `set_ideal_network` (reset/scan_en) |
| SDC-111 | N `set_false_path` — audit each |
| SDC-112 | N `set_multicycle_path` — document each |
| SDC-113 | No `set_dont_use` |
| SDC-114 | No `set_operating_conditions` |
| SDC-115 | No `set_timing_derate` (AOCV/POCVM signoff) |
| SDC-116 | No `set_clock_jitter` |
| SDC-117 | No `group_path` |
| SDC-118 | No `set_clock_gating_check` |
| SDC-119 | N `set_disable_timing` found — verify intentional |
| SDC-120 | N `set_min_delay` — verify no hold conflicts |
| SDC-121 | No wire-load constraints |
| SDC-122 | No `set_max_area` |
| SDC-123 | No power constraints |
| SDC-124 | `set_clock_gating_check` present but no `set_min_pulse_width` |
| SDC-125 | `set_voltage` found but no `create_voltage_area` |
| SDC-126 | Virtual clocks detected |
| SDC-130 | `set_operating_conditions` without corner/PVT comment context |
| SDC-131 | Multiple `set_operating_conditions` (usually one per SDC) |
| SDC-132 | `set_timing_derate` without `set_operating_conditions` |
| SDC-140 | Clock-relation analysis skipped (internal error) |

---

## 4. Core module: SDC Generator (`generator.py`)

**Entry point:** `generate_sdc(p: SDCParams) -> str`

**Input:** a single `SDCParams` dataclass (all fields, defaults):

```
design_name="MY_DESIGN", sdc_version="2.2"
add_units=True, time_unit="ns", cap_unit="pF", res_unit="kOhm"
clocks=[ClockDef(name="clk_core", port="clk", period=5.0, uncertainty=0.15)]
add_clk_jitter=False(0.05) · add_clk_transition=False(0.1) · add_clk_gating=False(setup 0.5/hold 0.2)
add_latency=False(0.5) · add_propagated=False
in_delay_max=1.2, in_delay_min=0.4, out_delay_max=1.5, out_delay_min=0.5
add_drive_cell=True(BUF_X4) · add_input_transition=False(0.1) · add_load=True(0.05)
max_fanout=20, max_transition=0.2, max_cap=0.1, min_cap=None, max_area=None
add_oper_cond=False(WORST) · add_derate=False(late 0.92 / early 1.08; net 1.0)
add_ideal_rst=True(rst_n) · add_scan=False(scan_en) · add_min_pulse=False(0.5)
case_entries=[], disable_arcs=[], path_groups=[PathGroup("reg2reg")]
add_group_path=False · add_wire_load=False(top, "")
false_paths=[], mc_paths=[], half_paths=[]
add_power=False(dyn 100.0 mW / leak 10.0 uW) · dont_use=[]
```

**Output:** one SDC string, emitted in this exact section order (with `# ── Section ──` banners):

1. `set sdc_version {ver}`
2. `set_units -time … -capacitance … -resistance …` (if `add_units`)
3. `# {design}.sdc — generated by SDC Tools <date>` + review NOTE
4. **Clock definitions** — virtual / primary / generated clocks
   (`create_clock`, `create_generated_clock` with `-source`, `-divide_by`/`-multiply_by`,
   `-duty_cycle`, `-edge_shift`, `-invert`, `-preinvert`, `-combinational`, `-add`, conditional `-master_clock`)
5. **Clock attributes** — per clock: `set_clock_uncertainty -setup/-hold` (hold = 50% of setup),
   optional latency, propagated, transition, jitter, gating check
6. **CDC — asynchronous clock groups** (auto-emitted when >1 primary clock):
   `set_clock_groups -asynchronous` with one `-group` per clock
7. **I/O constraints** — input/output delays `-max`/`-min` against the primary clock,
   excluding clock ports (and reset port) via `remove_from_collection [all_inputs] [get_ports …]`;
   driving cell / input transition; output load
8. **Design rule constraints** — `set_max_fanout`, `set_max_transition`, `set_max_capacitance`,
   `set_min_capacitance`, `set_max_area`
9. **Operating conditions** — `set_operating_conditions -max <name>`
10. **Timing derate (AOCV)** — 4 lines: `-late/-early` × `-cell_delay/-net_delay` on `[all_nets]`
11. **Ideal networks** — reset port ideal + false path
12. **Scan / DFT** — `set_case_analysis 0` + ideal on scan port
13. `set_min_pulse_width -low/-high`
14. **Case analysis entries** — per entry (pin or port)
15. **Disable timing arcs** — `set_disable_timing -from … -to … [get_cells …]`
16. **Path groups** — `group_path -name …` (+ `-from/-to/-weight` when set)
17. **Wire load** — mode + model
18. **False paths** — `set_false_path -from … -to …`
19. **Multicycle paths** — `-setup N` **and auto `-hold N-1`**
20. **Half-cycle paths** — `-setup 1 -end -rise_to/-fall_to` + `-hold 0`
21. **Power constraints** — `set_max_dynamic_power … mW`, `set_max_leakage_power … uW`
22. **Dont-use cells** — `set_dont_use [get_lib_cells */<cell>]`

**CLI flags it serves:** `--design/-d`, `--clock/-c` (repeatable, `NAME=PERIOD[:PORT]`),
`--uncertainty/-u`, `--sdc-version`, `--operating-condition`, `--derate`, `--ideal-reset`,
`--reset-port`, `--propagated`, `--scan`, `--scan-port`, `--output/-o`.

---

## 5. Core module: SDC Linter (`linter.py`)

**Entry points:** `lint_sdc(text, fix=True) -> LintResult` · `lint_sdc_file(filepath, fix=True, output_path=None)`

**What it checks (3 issue types):** trailing whitespace · tab characters · lines `>120` chars.
`LintResult` exposes `original_text, formatted_text, issues, line_count_original,
line_count_formatted, warnings, fixed`.

**What fix mode does:** reorders commands into a **canonical 22-section order**, inserts boxed
banners, collapses `\`-continuation commands onto one line, preserves the leading comment header.

**Section order (`SECTION_ORDER`)** and labels:
`header → sdc_version("SDC Version") → units("Units") → clocks("Clock Definitions") →
generated_clocks("Generated Clock Definitions") → clock_attributes("Clock Attributes") →
clock_groups("Clock Groups (CDC)") → io_constraints("I/O Constraints") → false_paths("False Paths") →
multicycle_paths("Multicycle Paths") → max_min_delay("Max / Min Delay") →
case_analysis("Case Analysis") → disable_timing("Disable Timing Arcs") →
design_rules("Design Rule Constraints") → operating_conditions("Operating Conditions") →
timing_derate("Timing Derate (AOCV)") → wire_load("Wire Load Models") →
ideal_network("Ideal Networks / Reset") → power("Power Constraints") → dft("DFT / Scan") →
dont_use("Don't-Use / Don't-Touch Cells") → other("Other Constraints")`.

**Command→category map** covers `set_sdc_version, set_units, create_clock, create_generated_clock,
set_clock_latency/transition/uncertainty/jitter/propagated_clock/clock_gating_check,
set_clock_groups, set_input_delay, set_output_delay, set_driving_cell, set_input_transition,
set_drive, set_load, set_false_path, set_multicycle_path, set_max_delay, set_min_delay,
set_case_analysis, set_disable_timing, set_max_fanout/transition/capacitance/min_capacitance/area,
set_operating_conditions, set_timing_derate, set_wire_load_mode/model, set_ideal_network,
set_max_dynamic_power, set_max_leakage_power, set_min_pulse_width, set_dont_use, set_dont_touch,
group_path, set_voltage, create_voltage_area`.

**CLI:** `lint <file>` with `--check` (exit 1 if issues), `--fix` (in-place), `--output/-o`.

---

## 6. Core module: SDC Converter (`converter.py`)

**Entry points:** `parse_sdc(text, filename="") -> ParsedSDC` · `sdc_to_json(...)` · `sdc_to_yaml(...)`.

**Input:** SDC text (+ optional filename label).
**Output:** structured object serializable to JSON/YAML with this exact schema:

```
filename, sdc_version, units{time,capacitance,resistance}, clocks[], input_delays[],
output_delays[], false_paths[], multicycle_paths[], clock_groups[], timing_derate[],
case_analysis[], constraints_count, clocks_count
```

- `clocks[]` = `{name, period, port, is_generated, is_virtual, master_source, divide_by, multiply_by, waveform, raw}`
- `input/output_delays[]` = `{command, value, clock, ports[], delay_type("max"|"min"), raw}`
- `false_paths / multicycle_paths` = `{command, from_, to, through[], setup, hold, value, raw}`
- `clock_groups[]` = `{type, groups[], raw}`; `timing_derate[]` = `{delay_type, timing_type, value, raw}`; `case_analysis[]` = `{value, target}`
- `constraints_count = clocks + input + output + false_paths + multicycle_paths`

**SDC commands parsed:** `set sdc_version`, `set_units`, `create_clock`, `create_generated_clock`,
`set_input_delay`, `set_output_delay`, `set_false_path`, `set_multicycle_path`, `set_clock_groups`,
`set_case_analysis`, `set_timing_derate`, `set_max_delay`, `set_min_delay`.

**CLI:** `convert <file>` with `--format/-f {json,yaml}` (default json), `--output/-o`.

---

## 7. Core module: Batch Runner (`batch_runner.py`)

**Entry points:** `find_sdc_files(dir, recursive=True)` · `batch_check(dir, verbose=False)` ·
`batch_report(dir, report_type="check"|"coverage", output_dir=None)` · `batch_lint(dir, fix=False)`.

**Behavior:** recursively discovers `**/*.sdc`, applies one operation to each file, aggregates into
`BatchSummary{total, ok, errors, skipped}` (`.print_summary()`).

| Subcommand | Per-file status logic |
|---|---|
| `batch check` | error if checker errors present (warnings never fail); message `"{n} errors, {m} warnings"` |
| `batch report check/coverage` | writes one self-contained HTML per file (`{stem}_{type}.html`) |
| `batch lint [--fix]` | error if `>5` warnings; `--fix` overwrites files in place |

**CLI:** `batch {check|report|lint}`; `batch report <check|coverage> <dir> [-o outdir]`; exits 1 if any file errored.

---

## 8. Core module: Constraint Change Analyzer (`constraint_diff.py`)

**Entry point:** `analyze_constraint_changes(sdc_v1, sdc_v2, linked_files_v1=None, linked_files_v2=None) -> ChangeAnalysisResult`.

**Input:** two SDC versions (text) + optional `{filename: content}` dicts of linked TCL files per version.
**Output:** `ChangeAnalysisResult{changes[], v1_constraints[], v2_constraints[], symbol_table_v1,
symbol_table_v2, wildcard_comparisons, stats}` with filters `fatal_changes` / `warnings` / `info_changes`.
`stats` keys: `v1_constraints, v2_constraints, matched, added, removed, modified, fatal, warnings, info, total_changes`.

**How it works:** joins continuations, strips comments, resolves `$VAR`s via `tcl_resolver`,
parses 34 SDC command types, matches constraints between versions (keyed by command + identifying
fields), and classifies every added/removed/modified constraint against **21 change rules**.

### The 21 change rules (CHG-*)

| Rule | Severity | Trigger |
|------|----------|---------|
| **CHG-FP-001** | fatal | `set_false_path` removed |
| **CHG-FP-002** | fatal | false-path `-from/-to/-through` changed |
| **CHG-FP-003** | info | false path added |
| **CHG-MCP-001** | fatal | multicycle removed (reverts to single-cycle) |
| **CHG-MCP-002** | fatal | setup cycles decreased (timing tightened) |
| **CHG-MCP-003** | warning | setup cycles increased (may hide issues) |
| **CHG-MCP-004** | fatal | setup MCP exists without matching hold (or hold removed) |
| **CHG-CK-001** | warning | clock period decreased (frequency ↑) |
| **CHG-CK-002** | warning | clock uncertainty decreased (margin ↓) |
| **CHG-CK-003** | info | clock uncertainty increased |
| **CHG-CK-004** | info | clock topology changed (added/renamed) |
| **CHG-CK-005** | fatal | generated clock `-divide_by`/`-multiply_by` changed |
| **CHG-DR-001** | warning | early derate reduced (hold margin ↓) |
| **CHG-DR-002** | warning | late derate increased (setup margin ↓) |
| **CHG-WC-001** | warning | wildcard pattern changed (narrowed/broadened/rewritten) |
| **CHG-WC-002** | warning | *(defined but never emitted — see Limitations)* |
| **CHG-IO-001** | warning | I/O delay value changed |
| **CHG-OC-001** | warning | operating conditions changed |
| **CHG-GEN-001** | info | new constraint added in V2 |
| **CHG-GEN-002** | info | constraint removed in V2 |
| **CHG-GEN-003** | info | non-critical field changed |

**CLI:** `diff <v1> <v2>` with `--linked-v1`, `--linked-v2`, `--v1-name`, `--v2-name`, `--json`, `--verbose`.

---

## 9. Supporting modules: TCL resolver (`tcl_resolver.py`) and Wildcard analyzer (`wildcard_analyzer.py`)

### TCL resolver
- `build_symbol_table(main_text, linked_files=None) -> SymbolTable` — parses `set VAR value`
  assignments, detects `source file.tcl`, merges linked-file bindings (main text overrides linked),
  resolves nested `$VAR`/`${VAR}` references (up to 5 passes, longest-name-first).
- `SymbolTable.resolve(text)` / `.get(name, default)` — substitute variables into SDC text.
- `VariableBinding{name, raw_value, resolved_value, source_file, line_number, is_collection}` —
  `is_collection` flags values containing `get_pins/get_ports/get_cells/get_clocks/get_nets/all_*`.

### Wildcard analyzer
- `parse_wildcard(text) -> WildcardPattern{raw, pattern_type, has_wildcards, specificity, risk_score}`.
- `compare_wildcards(v1, v2, command_type) -> WildcardComparison{change_type: same|narrowed|broadened|rewritten, risk_explanation}`.
- `flag_overly_broad(patterns)` — returns patterns with `risk_score >= 7`.
- **Risk scoring (0–10):** `[all_pins/cells/nets/inputs/outputs/registers]` = 9 · bare `[*]` = 8 ·
  `"broad"` specificity = 8 · `>=2 *` or `?` = 4 (moderate) · exactly 1 `*` = 2 (specific) · none = 0 (exact).
- Pattern type inference from `get_pins→pin, get_ports→port, get_cells→cell, get_clocks→clock,
  get_nets→net, all_inputs/all_outputs→port, all_clocks→clock, all_registers→cell, all_nets→net`.

---

## 10. Core module: Clock Relation Analyzer (`clock_relations.py`)

**Entry point:** `analyze_clock_relations(text) -> RelationAnalysisResult`.

**Input:** SDC text. **Output:** `clocks[]`, `pairs[]`, `existing_groups[]`, `mismatches[]`, `stats`.
`stats` keys: `clocks, pairs, synchronous, asynchronous, physically_exclusive, logically_exclusive,
mismatches, missing, constraints`.

**Relation inference (5 rules, in priority order):**
1. **Same-port primary clocks, different periods → `physically_exclusive`** (only one active at a time)
2. **Ancestor/descendant (parent–child generated chain) → `synchronous`**
3. **Shared common ancestor → `synchronous`** (same clock domain)
4. *(registry labels)* different source ports / no common ancestor → **`asynchronous`**
5. default → `asynchronous` (low confidence)

**Mismatch detection (SDC-060..063):**

| Code | Severity | Detects |
|------|----------|---------|
| **SDC-060** | warning | marked `-asynchronous` but should be `-physically_exclusive` (SI pessimism) |
| **SDC-061** | warning | marked exclusive but actually `synchronous` (masks real paths) |
| **SDC-062** | info | asynchronous/exclusive pair with **no** `set_clock_groups` (missing constraint) |
| **SDC-063** | info | marked exclusive but appears `asynchronous` (verify intentional) |

Synchronous pairs marked `-asynchronous` are accepted (conservative), so no mismatch is raised there.

**CLI:** `analyze clock-relations <file>` (+ `--json`). Full pair matrix rendered in the web UI.

---

## 11. Core module: Multi-Corner Manager (`corner_manager.py` + `mmc.py`)

### Corner data model (`Corner`)
`name, operating_condition, voltage=0.72, temperature=-40.0, process_type="SSG",
derate_cell_early=1.08, derate_cell_late=0.92, derate_net_early=1.0, derate_net_late=1.0,
uncertainty_scale=1.0`.

**Validation ranges (`validate_corner`):** voltage 0.3–1.5 V · temperature −55..175 °C ·
process ∈ `{SSG, TT, FFG, SS, FF, SF, FS, SNG, FNG}` · all derates 0.5–1.5 · uncertainty scale 0.5–2.0.

### 4 built-in presets (`CORNER_PRESETS`)

| Preset | Corners |
|--------|---------|
| **Classic 3-corner (Worst/Typ/Best)** | WORST_SSG_0P72V_M40C · TYPICAL_TT_0P80V_25C · BEST_FFG_0P88V_125C |
| **Industrial 5-corner** | above 3 + SSG_0P65V_M40C · FFG_0P95V_125C |
| **Full 8-corner signoff** | above 5 + SS_0P72V_125C · FF_0P88V_M40C · TT_0P80V_0C |
| **Custom (empty)** | [] |

Each preset carries process/voltage/temperature and AOCV derate values plus an uncertainty scale
(1.2 worst / 1.0 typ / 0.8 best …). Serialization: `corners_to_json / corners_from_json`.
`corner_matrix(corners)` produces a per-corner display grid.

### MMC operations (`mmc.py`)
- `generate_corner_sdcs(template: SDCParams, corners) -> {corner_name: sdc_text}` — clones the
  template per corner, applies `design_name` suffix, operating condition, AOCV derates, and scales
  clock uncertainty by `uncertainty_scale`; prepends a corner header comment.
- `diff_corners(sdc_a, sdc_b, name_a, name_b) -> [DiffLine(line_type, text_a, text_b, section)]` —
  section-aware line diff (`equal|added|removed|changed`).
- `check_sdc_multi({corner: sdc}) -> CheckResult` — per-corner checks (prefixed `[corner]`) **plus
  cross-corner consistency rules**: **SDC-050** warning (clock names differ across corners),
  **SDC-051** info (clock period differs), **SDC-053** warning (timing exception missing in some
  corners). *(SDC-054 derate-monotonicity is declared but currently a no-op.)*
- `create_corner_zip({corner: sdc}) -> bytes` — in-memory ZIP for download.

**CLI:** `corners list`, `corners show "<name>"`. Reports: `report check <file>`, `report clock-relations`.

---

## 12. Core module: Constraint Coverage Gap Analysis (`coverage.py`)

**Entry point:** `parse_sdc_coverage(text, filename="") -> CoverageResult`.
**Output:** `categories[]`, `total_items=39`, `total_present`, `total_missing`, `score` (0–100),
`stats{categories, total_items, present, missing, score_pct}`. Category `status`: `good` ≥80,
`warn` ≥50, else `bad`.

**39 items across 6 categories** (verified against source):

| Category | Items | Notes |
|----------|-------|-------|
| 🕐 **Clocks** (9) | create_clock · generated clock · clock latency · clock transition · clock uncertainty · clock jitter · propagated clock · clock groups · clock gating check | uncertainty, propagated, groups are critical |
| 🔌 **I/O Constraints** (6) | input delay max · input delay min · output delay max · output delay min · driving cell/input transition · output load | 4 critical |
| ⚠️ **Timing Exceptions** (7) | false paths · multicycle paths · multicycle hold fix · max delay · min delay · group paths · disable timing arcs | hold-fix critical if MCPs present |
| 📏 **Design Rules** (6) | SDC version · units · max fanout · max transition · max capacitance · max area | fanout/transition critical |
| 📊 **AOCV / Derate** (5) | timing derate · derate early+late · derate cell+net · operating conditions · wire load mode | 3 critical |
| ⚡ **Power / DFT** (6) | max dynamic power · max leakage power · case analysis · dont-use cells · ideal network · min pulse width | — |

**CLI:** `coverage <file>` with `--json`, `--missing-only`.

---

## 13. Core module: Custom Rules Engine (`custom_rules.py`)

**Entry points:** `load_ruleset(yaml_path) -> CustomRuleset` · `load_rulesets_from_dir(dir)` ·
`apply_rules(text, ruleset) -> [CustomRuleResult]` · `apply_rulesets(text, rulesets)` ·
`integrate_with_check(text, rules_dirs) -> (CheckResult, {ruleset: results})`.

**YAML schema** (top level): `name`, `version`, `description`, `rules[]`.
Per-rule fields: `id` (req), `name`, `severity` (`error|warning|info`), `description`, `command` (req),
`condition` (req), `field`, `threshold`, `pattern`, `message`, `tags[]`, `enabled`.

**All 9 condition handlers** (exact condition strings):

| Condition | Rule passes when… |
|-----------|--------------------|
| `present` | ≥1 matching command exists |
| `absent` | no matching command |
| `count_above` | count `<=` threshold |
| `count_below` | count `>=` threshold |
| `count_exactly` | count `==` threshold |
| `value_above` | all extracted values `<=` threshold (extracts `pattern` or `-{field} N`) |
| `value_below` | all extracted values `>=` threshold |
| `regex_match` | zero matches for `pattern` |
| `regex_absent` | zero forbidden matches |

Message templating supports `{count}` and `{value}`. Example ruleset ships at
`custom_rules_example.yaml` (10 rules: CUST-001..CUST-010 covering clock period, propagated clock,
I/O delays, derate, operating conditions, false-path counts, disable-timing counts, dont-use, clock
gating). `samples/test_custom_rules.yaml` has 8 FND-* rules.

**CLI:** `check <file> --custom-rules <yaml> [--custom-rules <yaml> …]`.

---

## 14. Core module: Rules Registry (`rules_registry.py`)

Central documentation source for **all 95 rule codes**. `Rule{code, severity, short_name,
description, why_matters, fix, reference_url, module, added_version}`. Lookup helpers:
`get_all_rules()`, `get_rule(code)`, `get_rules_by_module(m)`, `get_rules_by_severity(s)`.

Breakdown by module (from the registry):
- **checker** — SDC-001..011 (errors), SDC-020..037 + SDC-040..045 (warnings), SDC-100..126,
  SDC-130..132, SDC-140 (info) → **~54 codes**
- **mmc** — SDC-050, 051, 053, 054
- **clock_relations** — SDC-060..063
- **constraint_diff** — 21 × CHG-* rules

**CLI:** `rules list [--module m] [--severity s] [--search kw] [--json]`, `rules show <code>`.

---

## 15. Core module: HTML Report Generator (`reporter.py`)

5 report types, all **fully self-contained HTML** (inline CSS, no CDN, no JS, no external assets):

| Function | Report |
|----------|--------|
| `generate_check_report(result, filename, verbose=False)` | SDC Quality Report — metric cards, issue table, stats grid |
| `generate_diff_report(result, v1_name, v2_name)` | Change Impact Report — per-change cards (fatal/warning/info) |
| `generate_clock_report(result, filename)` | Clock Relations Report — issues, clock-definition table, N×N relation matrix |
| `generate_rules_report(rules, title)` | Rules Registry Report |
| `generate_coverage_report(result, filename)` | Coverage Report — big score, per-category bars + item tables, missing list |

Each page has the footer `Generated by SDC Tools v{APP_VERSION} — <date>`.

**CLI:** `report {check|diff|clock-relations|coverage} <inputs> -o <out.html>`.

---

## 16. CLI reference (all 12 commands)

```
sdc-tools [--version] <command> …

  check <file>        --json · --junit · --output · --custom-rules · --verbose · --format csv|markdown
  generate            --design · --clock NAME=PERIOD[:PORT] (repeat) · --uncertainty · --sdc-version
                      --operating-condition · --derate · --ideal-reset · --reset-port · --propagated
                      --scan · --scan-port · --output
  diff <v1> <v2>      --linked-v1 · --linked-v2 · --v1-name · --v2-name · --json · --verbose
  corners             list · show <preset_name>
  analyze             clock-relations <file> [--json]
  rules               list [--module][--severity][--search][--json] · show <code>
  web                 (launches Streamlit at http://localhost:8501)
  coverage <file>     --json · --missing-only
  report              check <file> · diff <v1> <v2> · clock-relations <file> · coverage <file> · --output
  lint <file>         --check · --fix · --output
  convert <file>      --format json|yaml · --output
  batch               check <dir> [--verbose] · report <check|coverage> <dir> [-o outdir] · lint <dir> [--fix]
```

**Named flags (26):** `--check, --clock, --custom-rules, --derate, --design, --fix, --format,
--ideal-reset, --json, --junit, --linked-v1, --linked-v2, --missing-only, --module,
--operating-condition, --output, --output-dir, --propagated, --reset-port, --scan, --scan-port,
--sdc-version, --search, --severity, --uncertainty, --v1-name, --v2-name, --verbose, --version`.

**Exit-code contract:** `check` exits 1 if any error; `lint --check` exits 1 if any issue;
`batch` exits 1 if any file errored. CI-friendly outputs: JSON, JUnit XML, CSV, Markdown, HTML.

---

## 17. Web UI (Streamlit, `app.py` + `ui/`)

10 feature tabs + 2 full-page views (**"12 tabs"**):

| Tab | What it does |
|-----|--------------|
| 🛡 **Checker** | upload/paste SDC → run check; metric cards; per-issue expanders; best-practice list; stats; optional custom-rules YAML upload; full rule reference with search/filter |
| ⚙️ **Generator** | forms for every generator option → live SDC preview + download; **live validation** of generated SDC; **quick multi-corner generate** (ZIP + per-corner download + cross-corner consistency + corner diff); **compare against baseline** (semantic diff + side-by-side text diff) |
| 📝 **Linter** | fix vs check-only modes; issue list; formatted output + diff view + downloads |
| 🔄 **Converter** | JSON/YAML output; per-type metric cards; download |
| 🔲 **Corner Mgr** | load the 4 presets; add/edit/delete corners with validation; JSON import/export; corner coverage matrix (dataframe) |
| 📦 **MMC SDC** | base template form → per-corner generation, ZIP, corner diff, cross-corner consistency |
| 🔍 **Diff** | V1/V2 upload or paste + linked TCL files → fatal/warning/info change lists, variable-resolution view, side-by-side diff |
| 🕐 **Clock** | clock-relation analysis → 5 metrics, color-coded N×N relation matrix (hover for reason), mismatch/missing lists, all pairs, definitions |
| 📊 **Coverage** | big score, category cards with progress bars, missing-items list, HTML report download |
| 📋 **Rules** | searchable/filterable rule reference; JSON + Markdown downloads |
| 🧪 **Test Drive** (view) | pick a sample SDC (or upload) → **run all 5 features at once** (checker, coverage, clock relations, linter, converter) → unified dashboard + JSON download + feedback prompt |
| 📊 **Community Feedback** (view) | public dashboard: totals, positive/negative/satisfaction, "What users are saying", full entry table |

**Feedback system (`ui/feedback.py`):** `FeedbackEntry{timestamp, feature, rating(1/-1/0), comment,
sdc_file, results_summary}` persisted to `data/feedback.json`. `feedback_widget()` renders thumbs
up/down + optional comment after results in Linter, Converter, Rules, and Test Drive.

**Theme:** modern light theme + full dark-mode support (`inject_css`, Inter font, gradient header,
metric cards, status banners, badges). Sidebar has brand, Test Drive / Feedback buttons, changelog,
GitHub/docs links.

---

## 18. Test suite & sample corpus

### Tests (`tests/`) — 15 pytest files, 330 collected tests
`test_batch_runner.py`(7) · `test_checker.py`(38) · `test_cli.py`(32) · `test_clock_relations.py`(15) ·
`test_constraint_diff.py`(13) · `test_converter.py`(14) · `test_coverage.py`(16) ·
`test_custom_rules.py`(29) · `test_generator.py`(31) · `test_linter.py`(17) ·
`test_regressions.py`(19) · `test_reporter.py`(23) · `test_rules_registry.py`(20) ·
`test_tcl_resolver.py`(30) · `test_wildcard_analyzer.py`(26).
Shared fixtures in `conftest.py`; `run_comprehensive_checks.py` is a standalone subprocess-driven
end-to-end smoke test covering 12 feature areas.

### Samples (`samples/`, 19 files)
- **Clean/valid:** `minimal_sdc.sdc`, `real_design_full.sdc` (32-bit RISC-V, golden reference),
  `check_variants/good_complex.sdc`, `check_variants/minimal_but_valid.sdc`,
  `diff/design_v1.sdc`, `diff/design_v2.sdc`
- **Buggy:** `buggy_no_clocks.sdc`, `warning_heavy.sdc`, `edge_case_malformed.sdc`, `example.sdc`
- **Edge cases:** `edge_case_empty.sdc`, `edge_case_extreme_values.sdc`, `clock_relations.sdc`
  (deliberately wrong clock groups), `constraint_diff_v1/v2.sdc` (byte-identical, differ only via
  `variables_v1/v2.tcl` — demonstrates TCL-variable semantic diff)
- **MMC template:** `multi_corner_template.sdc`; **custom rules:** `test_custom_rules.yaml`,
  root `custom_rules_example.yaml`

---

## 19. Packaging & deployment

| Surface | Detail |
|---------|--------|
| Build backend | `setuptools.build_meta` (requires `setuptools>=68.0`) |
| Package | `sdc-tools` v1.3.0, MIT, `requires-python >=3.10`, entry point `sdc-tools = cli:main` |
| Dependencies | core `pyyaml>=6.0`; extras `web=[streamlit>=1.35]`, `dev=[pre-commit>=3.0]`, `all=[…]` |
| Py-modules | all 16 core modules as top-level modules (flat package) |
| Docker | `python:3.11-slim`, installs requirements + pyyaml, `ENTRYPOINT ["python","cli.py"]` |
| Pre-commit | `sdc-check` (blocks on errors), `sdc-check-verbose` (manual); standalone `sdc-check.sh` with `SDC_TOOLS_MODE=block|warn` |
| Windows wrapper | `sdc-tools.cmd` → `python cli.py %*` |
| CI (`.github/workflows/ci.yml`) | test matrix ubuntu/windows/macos × Python 3.10/3.11/3.12; lint job py_compile + import smoke checks |

---

## 20. Known limitations & honest notes (found during this audit)

- `CHG-WC-002` (wildcard broadened) is defined in the registry but **never emitted** — broadening is
  reported under `CHG-WC-001`.
- `CHG-FP-002`'s "same wildcard" branch is effectively **unreachable** (`compare_wildcards` returns
  `"same"` only for identical strings, but the guard requires them to differ).
- `ChangeAnalysisResult.wildcard_comparisons` is declared but **never populated**.
- `Constraint.line_number` is always `0` from `parse_sdc_constraints`.
- `SDC-054` (derate monotonicity across corners) is a **no-op** in `check_sdc_multi`.
- `converter` I/O-delay `value` extraction is a known quirk: with the standard `-max 1.2` flag form
  it can leave `value=0.0`; `waveform` is never populated; `set_max_delay`/`set_min_delay` are
  appended into the `multicycle_paths` list.
- `linter` `_parse_lines` and `_MULTI_LINE_COMMANDS` are dead code; multi-line commands not ending
  in `\` are dropped when collapsing continuations.
- `generator` emits `-master_clock {master_port}` (a port name, not a clock object) for generated
  clocks with >1 primary clock; `set_min_pulse_width` has no section banner; CLI `--scan-port`
  default (`scan_mode`) differs from the library default (`scan_en`).
- `tcl_resolver` substitution is plain string replacement (not a TCL tokenizer) — it rewrites `$VAR`
  even inside quoted strings/braces; circular references are not detected (loop stops after 5 passes).
- `custom_rules` message templating supports only `{count}` and `{value}` (docstring also mentions
  `{name}` but it is not implemented).
- `corner_manager` imports `field`/`Optional` without using them; `constraint_diff` imports
  `difflib` but never uses it.
- Coverage's `coverage.py` grabs `set_min_capacitance`, `set_wire_load_model`, `set_dont_touch` but
  does **not** surface them as items.
- `batch_lint --fix` overwrites source files in place (by design, but destructive).

---

## 21. Quick mental model — feature → module → CLI → UI

| Feature | Module | CLI | Web tab |
|---------|--------|-----|---------|
| Validate | `checker.py` | `check` | 🛡 Checker |
| Generate | `generator.py` | `generate` | ⚙️ Generator |
| Lint/format | `linter.py` | `lint` | 📝 Linter |
| Convert | `converter.py` | `convert` | 🔄 Converter |
| Batch | `batch_runner.py` | `batch` | (CLI) |
| Semantic diff | `constraint_diff.py` + `tcl_resolver.py` + `wildcard_analyzer.py` | `diff` | 🔍 Diff |
| Clock relations | `clock_relations.py` | `analyze clock-relations` | 🕐 Clock |
| Multi-corner | `corner_manager.py` + `mmc.py` | `corners` | 🔲 Corner Mgr / 📦 MMC SDC |
| Coverage | `coverage.py` | `coverage` | 📊 Coverage |
| Custom rules | `custom_rules.py` | `check --custom-rules` | 🛡 Checker |
| Rule reference | `rules_registry.py` | `rules` | 📋 Rules |
| HTML reports | `reporter.py` | `report` | (downloads) |
| Web UI | `app.py` + `ui/` | `web` | all tabs |
| Test drive + feedback | `ui/tab_test_drive.py` + `ui/feedback.py` | (sidebar) | 🧪 Test Drive / 📊 Feedback |

---

*Document generated from a full source audit of the repository (all modules, tests, samples, docs,
and packaging read or verified). Author: SDC Tools project analysis.*
