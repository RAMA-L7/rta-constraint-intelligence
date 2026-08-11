# Phase 7 — Optional Netlist-Aware Validation (Architecture Proposal)

**Status:** RESEARCH ONLY — not implemented in Phase 7. This document describes what
becomes possible if a future phase accepts an optional design-object inventory
alongside the SDC.

## Problem statement

Phase 7 established the trust boundary: SDC-only analysis classifies every
`[get_ports ...]` / `[get_pins ...]` / `[get_cells ...]` reference as
NETLIST_REQUIRED. That is honest but coarse. With a lightweight design-object
inventory, many of these become **deterministically checkable**, moving the
validator from "cannot verify" to "verified" for whole classes of references.

## Conceptual architecture

```
SDC text
   │
   ▼
Shared Preprocessor ──► LogicalCommand(s)
   │                          │
   ▼                          ▼
support_boundary.analyze_scope   semantic validators (checker etc.)
   │                          │
   │   optional               ▼
   │   ──────────────────►  Design Context Layer
   │                              ▲
   │                              │  optional input
   ▼                              │
AnalysisScope                 Netlist / Object Inventory
(now with resolved refs)          (ports, pins, cells, nets, hierarchy)
```

The SDC pipeline is **unchanged** when no inventory is supplied — the netlist
layer degrades gracefully to today's NETLIST_REQUIRED status.

## Input formats (ranked by implementation cost)

| Format | Content | Cost | Coverage |
|---|---|---|---|
| Lightweight object inventory (JSON/YAML) | port/pin/cell/net name lists + parent/child hierarchy | Low | get_ports/get_pins/get_cells/get_nets, wildcards, hierarchy refs |
| Verilog netlist | full design structure | High (needs elaboration) | everything above + timing paths |
| SDC-sourced `all_inputs`/`all_outputs` projections | from set_* constraint objects | Minimal | partial only |

**Recommendation:** a compact `design_context.json` (or YAML) is the highest
value-per-cost first step. It matches the project's existing converter/JSON
tooling and needs no Verilog parser.

## Checks that become possible

| Current status | With design context | Example |
|---|---|---|
| NETLIST_REQUIRED: `[get_ports foo]` | **Definite**: undefined port → error; defined → validated | `get_ports data_in` vs actual port list |
| NETLIST_REQUIRED: `[get_pins block/reg/D]` | **Definite**: invalid hierarchy → error | typo'd `U_DIV/clkoutp` |
| NETLIST_REQUIRED: wildcard `{clk*}` | **Resolvable**: empty match → warning; else validated | `[get_clocks {clk_a clk_b}]` |
| UNRESOLVABLE: unconstrained port analysis | **Possible**: real ports with no I/O delay → advisory | missing `set_input_delay` on a real input |
| NETLIST_REQUIRED: generated-clock `-source` | **Possible**: verify source object exists | `create_generated_clock -source [get_pins U/clk]` |
| Timing-exception overlap | **Possible with paths**: only with netlist elaboration | false path vs multicycle path overlap |

## Explicit non-goals

- No full Verilog elaboration, no gate-level timing engine, no library (.lib)
  parsing. The design context is a **name/hierarchy inventory**, not a netlist
  simulator.
- SDC-only analysis must remain the default and must never degrade.

## API sketch (conceptual)

```python
@dataclass
class DesignContext:
    ports: Set[str]
    pins: Set[str]          # "hier/inst/D" style, normalized
    cells: Set[str]
    nets: Set[str]
    children: Dict[str, List[str]]   # hierarchy parent → children
    # optional
    port_is_input: Set[str]
    port_is_output: Set[str]

def resolve_collection(expr: str, ctx: DesignContext) -> Resolution:
    """Return DEFINED / UNDEFINED / EMPTY_WILDCARD / NETLIST_DEPENDENT."""
```

`analyze_scope(text, ctx: Optional[DesignContext] = None)` reclassifies
references when `ctx` is present; `checker.check_sdc` gains an optional
`context=` parameter so **existing callers are untouched**.

## New rules enabled (future, not Phase 7)

| Rule (proposed) | Condition | Severity |
|---|---|---|
| SDC-050 undefined port/pin/cell reference | get_* name not in inventory | error |
| SDC-051 empty wildcard collection | wildcard matches nothing | warning |
| SDC-052 unconstrained port | real input/output port has no delay constraint | warning |
| SDC-053 invalid hierarchy reference | `a/b/c` parent missing | error |

## Migration risk

- Low: the layer is additive; SDC-only behavior unchanged (verified by existing
  436 pytest + 22/22 golden + 8/8 reference suites).
- The NETLIST_REQUIRED → VALIDATED reclassification must be **opt-in** so
  existing golden/UI expectations stay stable.
