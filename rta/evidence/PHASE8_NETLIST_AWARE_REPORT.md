# Phase 8 — Optional Verilog/Netlist-Aware SDC Validation

## 1. Multi-Agent Summary

| Agent | Responsibility | Outcome |
|---|---|---|
| **A — Verilog/Netlist Architect** | Smallest safe structural parser | Internal structural subset parser (`design_context.py`), no heavy dependency |
| **B — SDC Collection Semantics Engineer** | get_ports/pins/cells/nets, wildcards, all_* semantics | Bounded resolver: RESOLVED / EMPTY / UNDEFINED / UNSUPPORTED, fnmatch globs, `[*]` bit wildcard |
| **C — Security Engineer** | Uploaded Verilog must be DATA | `design_context.py` contains no exec/eval/subprocess/file/socket primitives; `` `include``/`` `define`` stripped inert; verified 7/7 |
| **D — Adversarial QA** | Break parser/resolver | 12/12: malformed modules, duplicate modules, NUL/shebang prefix, strings containing keywords, escaped identifiers, deep hierarchy |
| **E — UI/UX Engineer** | Optional workflow, obvious mode | Checker tab expander "Optional: design context (Verilog)" + "Analysis mode:" caption |
| **F — Performance Engineer** | 1k/10k/100k objects | Found + fixed an O(N²) statement splitter (`code[i:]` slicing); now linear 0.90x scaling, 100k parse 11.8s |
| **G — Independent Reviewer** | Challenge parser/classifications/security | 8 findings → all fixed: NA10 added, metamorphic coverage extended, `_strip_comments` escaped-quote fix, positional-connection resolution, unified skip-list, net bit-range check, unused import, trust-status note documented |

**Disagreement resolution:** reviewer challenged "trust upgrades only with evidence" for the resolved-but-undefined case (SDC-055 error + NETLIST_REQUIRED status). Resolved as a *documented conservative choice*: a definite error is raised, and the scope keeps NETLIST_REQUIRED rather than claiming full understanding of an input containing errors.

## 2. Baseline (before changes)

pytest 436/436 · parser golden 22/22 · semantic golden 9/9 · reference designs 8/8 · trust 8/8 · no-false-confidence 6/6 · UI 35/35 · state 6/6 · security 5/5 · stress 21/21.

## 3. Phase 7 Proposal Review (architecture decision record)

| Proposal | Decision | Rationale |
|---|---|---|
| JSON inventory as highest value-per-cost | **MODIFY** | Phase 8 explicitly targets Verilog; JSON inventory also supported via `DesignContext.from_inventory()` |
| `resolve_collection` API | **KEEP** | Implemented as specified (RESOLVED/EMPTY/UNDEFINED/NETLIST_DEPENDENT) |
| `analyze_scope(text, context=None)` | **KEEP** | Implemented; opt-in trust upgrades |
| SDC-050..053 rules | **REJECT** | MMC owns 050-054 → used SDC-055..059 instead |

## 4. Verilog Parser Decision

**No parser library.** pyverilog/hdlConvertor/sly are unavailable (verified via import) and a heavy dependency contradicts the project's minimal-footprint philosophy (pyyaml + streamlit only). A **small internal structural subset parser** was built and is *safe enough* because:
- It is a name/hierarchy inventory, not an elaborator (per the Phase 7 proposal's own non-goals).
- Degrade-safe: unsupported constructs produce explicit warnings/errors, never silent wrong context.
- No execution surface; hostile input verified inert (security 7/7).

## 5. Supported Verilog Subset

- `module` headers, ANSI + non-ANSI port lists
- `input/output/inout` declarations with `[msb:lsb]` ranges
- `wire`/`tri`/`supply0/1`/`uwire`/`trireg` net declarations
- Instances: named `.pin(expr)`, **positional** (resolved via instantiated module's port order), multi-instance `,` lists, `\escaped` identifiers, scalar + `name[msb:lsb]` arrays
- `assign`/`parameter`/`generate`/`specify` skipped; `always`/`initial` blocks begin/end-balanced and skipped
- comments `//`, `/* */`, strings (incl. `\"` escapes), `module`/`endmodule` as statement boundaries

## 6. Unsupported Verilog/SystemVerilog

- Behavioral RTL semantics, functions/tasks internals, `defparam`, `macromodule`, UDPs, class/interface, `include`/`define` (stripped as inert), netlist elaboration, timing/power libraries. Never executed; surfaced via warnings or clean parse errors.

## 7. DesignContext Architecture

```
SDC text + optional Verilog
         │
         ▼
parse_verilog(text, top="") → ParseOutcome
   modules → top detection (unique | explicit | AMBIGUOUS error)
         │
         ▼
DesignContext(top_module, ports[DesignPort], instances[path→DesignInstance],
              nets, pins, module_ports)
         │
         ├─ resolve_collection(kind, args, ctx) → Resolution
         ├─ validate_design_references(text, ctx) → SDC-055..059
         └─ check_sdc(text, context=ctx)   (checker, optional param)
```

Also `DesignContext.from_inventory(dict)` supports the Phase 7 JSON inventory format.

## 8. Collection-Resolution Semantics

| Form | Result | Example |
|---|---|---|
| Exact port/cell/pin/net | RESOLVED / UNDEFINED | `[get_ports clk]` |
| Braced list `{a b}` | RESOLVED (all) | `[get_ports {clk rst_n}]` |
| Glob `*`/`?` | RESOLVED / EMPTY | `[get_ports data_*]` |
| Bit select `[3]` | RESOLVED / UNDEFINED (out of range) | `data_in[9]` on `[7:0]` → UNDEFINED |
| `[*]` bit wildcard | RESOLVED | `data_in[*]` |
| Hierarchical `u_core/*`, `u_core/u_reg0/D` | RESOLVED / EMPTY / UNDEFINED | nested instance expansion |
| `all_inputs`/`all_outputs`/`all_ports` | RESOLVED (dynamic) | direction-filtered |
| `all_registers`/`all_cells`/`all_nets` | RESOLVED (class) | design pool non-degenerate |
| `get_clocks`/`all_clocks` | SDC-defined, skipped | never netlist-resolved |

## 9. Bus Handling

- `input [7:0] data_in` → port with msb=7, lsb=0.
- `data_in` / `data_in[3]` (in range) / `data_in[*]` resolve; `data_in[9]` → UNDEFINED (SDC-055). Verified NA04.
- `get_nets bus[9]` on a `[3:0]` net now also range-checked (reviewer finding).

## 10. Hierarchy Handling

- Nested instances expanded recursively via a parent-indexed walk (O(instances)).
- `u_core/u_reg0/D` resolves; `u_core/u_nope/D` → SDC-055 (pin missing) **and** SDC-057 (parent `u_core/u_nope` missing). Verified NA03/NA07.
- Top module: unique top auto-selected; multiple candidates → **explicit ambiguity** (never silent); `--top` overrides; missing top → error. Verified NA09.

## 11. Object-Existence Validation (SDC-055)

Only with design context. `[get_ports nonexistent]` / `[get_pins bad/path]` / `[get_cells u_nope]` → error with SDC line. Never produced in SDC-only mode.

## 12. Empty-Collection Validation (SDC-056)

Wildcard with zero matches → warning. Distinguishes explicit-UNDEFINED (error) from wildcard-EMPTY (warning). `debug_*` (exists) vs `bogus_*` (empty) verified NA05.

## 13. Unconstrained-Port Analysis (SDC-059)

Conservative warning for data-pattern input/output ports with no `set_input_delay`/`set_output_delay`. Exempts clock/reset/scan/test/mode/en/power names and clock ports (via `create_clock` refs). Verified NA08 (D4 found; clk + data_out correctly exempt).

## 14. SDC-Only vs Design-Aware Behavior

| Mode | Netlist refs | Trust status | Rules |
|---|---|---|---|
| SDC only (default) | NETLIST_REQUIRED | unchanged | none of 055-059 |
| SDC + context, refs resolve | VALIDATED | upgrade | none |
| SDC + context, ref unresolved | NETLIST_REQUIRED | no upgrade | SDC-055/056/057 as applicable |
| SDC + context, unsupported expr | NETLIST_REQUIRED | no upgrade | none (never claimed) |

Verified: same SDC goes NETLIST_REQUIRED → VALIDATED when a matching netlist is supplied; SDC-only output is byte-identical in issue set.

## 15. AnalysisScope Integration

- `analyze_scope(text, context=None)`; `_resolve_level()` returns FULL only when **every** supported non-clock ref resolves.
- `scope.design` = `{analysis_mode: "design_aware", top_module, modules, ports, instances, nets, pins}` serialized into JSON/CLI/report.
- Trust never upgrades without evidence; unsupported expressions stay NETLIST_REQUIRED.

## 16. Golden Netlist-Aware Results — **10/10**

NA01 valid (VALIDATED) · NA02 missing port (055) · NA03 hierarchy (resolves) · NA04 buses (055 on bit 9) · NA05 wildcards (056 on bogus_*) · NA06 generated clocks (055 on pll_out) · NA07 timing exceptions (055+057) · NA08 broken design (all 4 injected defects) · NA09 multiple tops (ambiguity) · NA10 large netlist (17 instances).

## 17. Adversarial Results — **12/12**

Incomplete module (degrades with warning), duplicate modules (ambiguity), undefined instantiated module, `endmodule` without `;`, escaped identifiers, comments/strings containing fake modules, deep hierarchy, malformed port list, behavioral-only, similar-name non-cross-match, 2000-name wildcard.

## 18. Metamorphic Results — **4/4**

Whitespace/comments/line-breaks, CRLF, ANSI vs non-ANSI port lists, named vs positional connections — all produce identical facts.

## 19. Security Results — **7/7**

Hostile content (include/define directives, exec-like strings, python shebang, NUL bytes) is inert; static scan confirms `design_context.py` has no exec/eval/subprocess/file/socket primitives.

## 20. Performance

| Objects | Parse | Glob (u0*) | Exact | Full design-aware check |
|---|---|---|---|---|
| 1,000 | 0.11s | 1.3ms | ~0ms | 9ms |
| 10,000 | 1.07s | 14ms | ~0ms | 1ms |
| 100,000 | **11.8s** | 124ms | 0.1ms | 1ms |

Scaling ratio 10k/1k = 0.90x (linear). **An O(N²) bug was found and fixed:** `_split_statements` sliced `code[i:]` per character (quadratic string copies) — replaced with `startswith` + word-boundary check. 100k parse dropped 226s → 11.8s.

## 21. UI/CLI/Report Integration

- **UI:** Checker tab expander "🔗 Optional: design context (Verilog netlist)" (upload + paste + top field); "Analysis mode:" caption under Run Check; Analysis Coverage expander shows design metadata.
- **CLI:** `sdc-tools check x.sdc --netlist x.v [--top T]` — prints "Design context: top (3 ports, 3 instances)" and design-aware findings with line numbers.
- **Reports/JSON:** HTML report gains a "Design Context" stat block; JSON includes `scope.design`.

## 22. False Positives Discovered

- **SDC-059 heuristic**: single-letter stems (`i/o/q/d`) can flag block-level flop output ports named `q` — documented, warning-level, conservative exemptions in place. Reviewer noted; acceptable for a warning.
- Trust status for resolved-but-undefined refs stays NETLIST_REQUIRED alongside a definite SDC-055 error — documented conservative choice (an error is already raised).

## 23. False Negatives Discovered

- Non-declared module types (`mystery u1(...)`) still record the instance (hierarchy usable) but their internal structure can't be expanded — documented; no wrong facts claimed.
- Hierarchical net references (`u_core/t0`) resolve only as top-level nets materialized from connections, not fully flattened — honest limitation.

## 24. Full Regression

| Suite | Before | After |
|---|---|---|
| pytest | 436/436 | **476/476** (+40 design-context tests) |
| Parser golden | 22/22 | 22/22 |
| Semantic golden | 9/9 | 9/9 |
| Reference designs | 8/8 | 8/8 |
| Netlist-aware golden | — | **10/10** |
| Metamorphic | — | **4/4** |
| Adversarial | — | **12/12** |
| Netlist security | — | **7/7** |
| Trust transparency | 8/8 | 8/8 |
| No-false-confidence | 6/6 | 6/6 |
| UI benchmark | 35/35 | 35/35 |
| State isolation | 6/6 | 6/6 |
| Security | 5/5 | 5/5 |
| Preprocessor stress | 21/21 | 21/21 |
| Benchmark corpus | 61 files | 61 files |

## 25. Files Modified

| File | Change |
|---|---|
| `design_context.py` | **new** — Verilog subset parser, DesignContext, resolver, SDC-055..059 validation |
| `checker.py` | `check_sdc(text, context=None)` — design-aware findings + scope |
| `support_boundary.py` | `analyze_scope(text, context=None)`, `_resolve_level()`, `scope.design` |
| `rules_registry.py` | SDC-055..059 (module `design_context`) |
| `cli.py` | `check --netlist/--top`, scope/design disclosure, rules filter text |
| `app.py` | Checker-tab netlist expander + Analysis mode caption + rules filter |
| `reporter.py` | Design Context section in HTML reports |
| `tests/test_design_context.py` | **new** — 40 tests (parser/resolver/hierarchy/bus/integration/security) |
| `tests/test_rules_registry.py` | valid-module set += design_context |
| `benchmarks/netlist_aware/` | NA01-NA10 (`.v` + `.sdc`) + `manifest.json` |
| `benchmarks/run_netlist_aware.py` | **new** golden runner |
| `benchmarks/test_netlist_{metamorphic,adversarial,security,perf}.py` | **new** suites |

## 26. Remaining Limitations

- Parser is a structural subset, not an elaborator — behavioral/`generate`/`defparam` internals not expanded.
- Hierarchical net names not fully flattened (`u_core/t0` unresolvable via get_nets unless top-level).
- SDC-059 is a conservative heuristic (single-letter port stems may warn).
- No timing/power/library analysis — intentionally out of scope (Stage 25).

## 27. Trust Statement

**"What additional claims can the validator safely make when a compatible design netlist is supplied?"**

> With a supplied structural netlist, the validator can now claim: supported
> `get_ports`/`get_pins`/`get_cells`/`get_nets`/`all_*` references **resolve
> against the actual design** (or are definitely missing / empty); hierarchy
> paths are verified; and data-pattern boundary ports are checked for I/O
> delays. Trust status upgrades to VALIDATED only where every supported
> reference provably resolves — everything else stays visibly
> NETLIST_REQUIRED, and unsupported constructs are never silently claimed.

## 28. Phase 9 Recommendation

1. **Design-object inventory export**: add a `sdc-tools context extract design.v --top T --output context.json` command producing the Phase 7 inventory format, so netlists can be versioned/reused without re-parsing Verilog.
2. **Generated-clock source verification**: when a netlist is present, verify `create_generated_clock -source` objects exist (currently only the generic collection check covers it — a dedicated message would be clearer).
3. **UI polish**: show design-aware rule badges (SDC-055..059) in the Rule Reference filter; consider a side-by-side SDC-only vs design-aware comparison panel.
