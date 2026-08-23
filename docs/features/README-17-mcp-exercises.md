# Ṛta MCP Server — Hands-On Exercises

Work through these exercises to learn every MCP tool Ṛta exposes. Each
exercise is a **prompt you paste into your AI assistant** (OpenCode, Claude
Desktop/Code, Cursor, …) after registering the server — see
[README-16-mcp-server.md](README-16-mcp-server.md) for registration.

Every exercise uses the real files in `samples/`, and every "Modify it"
section shows how to adapt the same prompt to **your own SDC files**.

> **Trust reminder:** the assistant only decides *when* to call tools and
> *how to explain* results. Every number comes from the deterministic
> engine — the same engine as `rta check`. If a tool result and CLI output
> ever disagree, that's a bug worth reporting.

**Sample map**

| File | What's inside |
|---|---|
| `samples/minimal_sdc.sdc` | Bare-minimum SDC — 1 clock, max-only I/O delays |
| `samples/example.sdc` | Typical small design, some warnings |
| `samples/warning_heavy.sdc` | Deliberately warning-rich file |
| `samples/buggy_no_clocks.sdc` | Missing `create_clock` — fatal error case |
| `samples/real_design_full.sdc` | Larger realistic design, 5 clocks |
| `samples/clock_relations.sdc` | Multi-clock file for clock-relation evidence |
| `samples/constraint_diff_v1.sdc` / `_v2.sdc` | Before/after pair for diffing |
| `samples/multi_corner_template.sdc` | Template for multi-corner generation |
| `samples/reset_demo/top.sdc` + `top.v` | Unconstrained reset tree + matching netlist |
| `custom_rules_example.yaml` | Example custom-rules policy to copy |

---

## Exercise 1 — First analysis (`rta_analyze`)

**Goal:** get a readiness verdict and understand blocking findings.

Paste:

```
Use rta_analyze on samples/minimal_sdc.sdc.
Summarize: overall readiness verdict, every finding grouped by severity,
and what you would fix first.
```

Expected: verdict `REVIEW_REQUIRED` (or similar), findings including
SDC-028 / SDC-029 (no `-min` I/O delays), SDC-030 (no propagated clock),
plus category-coverage gaps.

**Modify it:** point at your own block:
```
Use rta_analyze on <your_file>.sdc — list anything blocking pre-STA review.
```

---

## Exercise 2 — Fatal-error case (`rta_analyze`)

**Goal:** see how the engine behaves when nothing works.

```
Run rta_analyze on samples/buggy_no_clocks.sdc. Explain the difference
between this result and exercise 1 — why is the verdict harsher?
```

Expected: an error-class finding for the missing `create_clock`
(SDC-001-style) — all paths unconstrained.

**Modify it:** delete one line from your own SDC and see which rule fires.

---

## Exercise 3 — Netlist-aware checking (`rta_analyze` + netlist)

**Goal:** verify object references against a real netlist.

```
Run rta_analyze on samples/reset_demo/top.sdc with the netlist from
samples/reset_demo/top.v (top module auto-detected).
Which reset-tree findings fire? Then rerun WITHOUT the netlist —
what changes in mode_note?
```

Expected: SDC-151 fires (unconstrained reset tree); with the netlist,
`mode_note` says "SDC + Design Context" and port/pin references are
structurally verified instead of name-matched.

**Modify it:** pass your RTL/gate-level Verilog:
```
Use rta_analyze on <block>.sdc with netlist text from <block>.v, top=<top>.
Report any get_ports/get_pins/get_cells references that don't resolve.
```

---

## Exercise 4 — Project signoff policy (`rta_analyze` + custom rules)

**Goal:** enforce house rules on top of the standard catalog.

First read the policy so the assistant has it:
```
Read custom_rules_example.yaml, then run rta_analyze on
samples/minimal_sdc.sdc passing that YAML as custom_rules.
Which CUST-* rules fail?
```

Expected: CUST-002 fails (no `set_propagated_clock` — required by the
policy), CUST-003-family I/O policies evaluated.

**Modify it:** open `custom_rules_example.yaml`, change the CUST-001 clock
threshold from `10.0` to your project's limit, re-save, rerun. Or write a
two-rule policy of your own (one `present`, one `value_above`) and ask the
assistant to audit your file against it.

---

## Exercise 5 — Lint & format (`rta_lint`)

**Goal:** clean up a messy file into canonical 22-section order.

```
Use rta_lint on samples/warning_heavy.sdc with fix=true.
Show me before/after line counts and summarize every warning.
Then show the formatted text.
```

Expected: warnings list + `formatted_text` reorganized into canonical
section order.

**Modify it:** `fix=false` gives a check-only pass (useful pre-commit);
run against any file in your repo.

---

## Exercise 6 — Structured conversion (`rta_convert`)

**Goal:** machine-readable constraint inventory.

```
Convert samples/example.sdc to JSON with rta_convert, then answer:
how many clocks, what are all the I/O delay endpoints, and are there any
false paths or multicycles?
```

Expected: structured `data` dict — clocks, ports, exceptions parsed out of
TCL text.

**Modify it:** `"format": "yaml"` for a human-reviewable version; useful
for feeding constraints into scripts or reviews.

---

## Exercise 7 — Generate a starting SDC (`rta_generate`)

**Goal:** produce a complete baseline SDC from parameters, then iterate.

```
Use rta_generate with params: design_name=MY_BLOCK, one primary clock
named clk_sys on port clk_p with period 4.0 ns and uncertainty 0.12,
input delays max 0.9/min 0.3, output delays max 1.1/min 0.4.
Then run rta_analyze on the generated SDC — does it pass its own check?
```

Expected: a full SDC (units, clock, I/O, derates, scan/reset sections per
defaults) and a clean-or-nearly-clean analysis — generated SDC passes its
own checker by contract (P1-3).

**Modify it:** add `add_scan=true`, `scan_port=scan_en`, a second divided
clock, or `max_fanout`/`max_transition` values matching your flow; ask the
assistant to regenerate until the analysis is clean.

---

## Exercise 8 — Regression review (`rta_diff`)

**Goal:** catch what changed between two constraint revisions.

```
Run rta_diff with v1=samples/constraint_diff_v1.sdc and
v2=samples/constraint_diff_v2.sdc.
List NEW findings, RESOLVED findings, CHANGED items, debt movement, and
every semantic CHG-* change with its explanation.
```

Expected: readiness-level NEW/RESOLVED/CHANGED plus CHG-* rows (clock
period shifts, I/O edits, false-path/multicycle changes, wildcard risk).

**Modify it:** save yesterday's and today's versions of your own SDC and
ask *"did my edit introduce or resolve any findings?"* — this is the same
evidence CI gates act on.

---

## Exercise 9 — Build a CI baseline (`rta_snapshot` + gate workflow)

**Goal:** create the artifact a merge gate compares against.

```
Use rta_snapshot on samples/example.sdc and give me just the snapshot JSON.
```

Then (one-time setup):
```powershell
# paste/save the assistant's snapshot JSON to .rta/baseline.json
python cli.py check samples\example.sdc --baseline .rta\baseline.json --gate NO_READINESS_REGRESSION
```

Expected: exit code `0` (PASS) when nothing regressed; modify the SDC to
add a blocker and rerun → `1` (FAIL) with reasons.

**Modify it:** commit `.rta/baseline.json` for your block and wire the gate
command into CI — full semantics in [README-14-ci-gate.md](README-14-ci-gate.md).

---

## Exercise 10 — Multi-corner matrix (`rta_corners`)

**Goal:** validate PVT corner definitions and build the matrix.

```
Use rta_corners with these corners:
[{"name":"WC","operating_condition":"","voltage":0.72,"temperature":125.0,"process_type":"SSG"},
 {"name":"BC","operating_condition":"","voltage":0.88,"temperature":-40.0,"process_type":"FF"}]
Any validation errors? Show the matrix.
```

Expected: two validated corners + a 2×2 analysis matrix.

**Modify it:** add a typical `TT` corner at 25 °C, then try an invalid one
(negative voltage) to see the structured error list.

---

## Exercise 11 — Rule lookup & learning (`rta_rules`)

**Goal:** turn rule codes into understanding.

```
Call rta_rules, find everything about SDC-151, SDC-152 and SDC-153, and
explain why blanket false paths on reset trees are dangerous.
```

Expected: severities, descriptions, why-it-matters and fix guidance straight
from the registry (119 rules).

**Modify it:** ask for rules filtered by severity or topic (*"all error-severity
rules related to clocks"*) and have the assistant quiz you.

---

## Capstone — Full review workflow

Chain everything like a real tape-in review on one of your own blocks:

```
Do a full constraint review of my_block.sdc:
1. rta_analyze (with my_block.v as netlist if available)
2. rta_lint to propose a cleaned-up version
3. rta_snapshot to record today's state as our first baseline
4. Summarize a remediation plan ordered by severity, quoting rule codes
   and the exact lines involved.
```

Then iterate: fix the top item, re-run step 1, confirm the finding cleared,
re-snapshot. That loop — analyze → fix → re-analyze → re-baseline — is the
entire daily workflow the MCP surface exists for.

---

## Troubleshooting exercises

| Try this | Expected lesson |
|---|---|
| Ask for `rta_analyze` with an empty `sdc` argument | Structured `MISSING_SDC` / `EMPTY_SDC` error — never a silent PASS (P1-6) |
| Call a made-up tool name | JSON-RPC error `-32602 unknown tool` |
| Feed `samples/edge_case_malformed.sdc` to `rta_convert` | Parser tolerates/reports quirks without crashing |

Full troubleshooting table: [README-16-mcp-server.md §6](README-16-mcp-server.md#6-troubleshooting)
