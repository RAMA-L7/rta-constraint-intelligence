# Ṛta — Full-Chip Design Context Extension Plan

> **Document kind:** design scoping / architecture decision · **Status:** draft for review — **no implementation until approved** · **Date:** 2026-08-12 · **Module:** `rta/engine/context/design_context.py` (1,228 lines, load-bearing for Checker, Coverage, Clock Relations)
>
> **Scope discipline:** per `MIGRATION_PLAN.md` §1, changes to this module follow "behavior-preserving" and "one commit per surface" at the *design* level too. This doc answers the six scoping questions; implementation is a separate, gated phase.

---

## 0. What exists today (verified against the module)

`parse_verilog(text: str, top: str = "") -> ParseOutcome` parses **one text blob** into one `DesignContext`. Within that single blob it already:

- handles multiple `module` definitions (ANSI + non-ANSI port lists)
- builds multi-level hierarchy with full paths (`DesignInstance.path`, e.g. `"u_core/u_reg"`) and parent tracking
- carries a structural connectivity layer (`module_port_dirs`, `pin_nets`, `net_pins`) for driver/load classification
- resolves top modules: **unique top → auto; explicit `top=` → honor; multiple candidates → error + `top_candidates`**

The gap is precisely what `README.md` states: real designs are **split across many files**, and the module has no file-set notion — no filelist ingestion, no cross-file module resolution. `` `include ``/`` `define `` are stripped as inert text (verified at `parse_verilog` line ~407).

**Critical constraint discovered during scoping (affects Q2 and Q6):** `rta/evidence/test_netlist_security.py` statically scans `design_context.py` for banned primitives — `open(`, `pathlib`, `tempfile`, `subprocess`, `socket`, `urllib`, `shutil`, `eval(`, `exec(`, `os.system`, `os.popen`, `__import__` — and fails if any appear in the module body. **The parser module must never perform file I/O.** All file reads belong to a separate loader module.

---

## 1. Q1 — Input model: filelist (`.f`) as primary, directory+glob as convenience

**Recommendation: filelist is the primary interface; directory+glob is a thin convenience wrapper on top.**

Rationale:

- A `.f` filelist is the industry lingua franca for full-chip flows (Synopsys/Primetime/MDC), is paired naturally with a `-top` flag, and is the least ambiguous description of "the design."
- No precedent exists in-repo (no `filelist` matches anywhere; `rta/examples/samples/` has no `.v` files) — so we are free to pick the standard, not a local convention.
- Directory+glob (`--netlist-dir dir --glob "*.v"`) is a convenience for the common case, implemented as a wrapper that *produces a filelist* internally — one code path, one resolution engine.

Supported `.f` subset (documented, degrade-safe, never silent):

| Directive | Handling |
|---|---|
| one path per line | included |
| `#` comments / blank lines | skipped |
| `-v <file>` (Verilog library file) | included like a source |
| `-f <file>` (nested filelist) | followed, with a **cycle guard** (visited-set) |
| `+incdir+<path>` | parsed and recorded, **no-op this phase** (see Q2) — surfaced in `ParseOutcome.warnings` so the user knows include resolution is off |
| `*` globs inside paths | expanded (via `glob` in the loader module) |
| `-y <dir>` (library dir) | **unsupported this phase** — clean warning, not silent |

---

## 2. Q2 — `` `include `` handling: stay inert, document gaps per finding

**Recommendation: keep `` `include `` inert in the parser; do NOT implement real include resolution in this phase.**

Reasons:

1. **Security contract forbids it in the parser module** (see §0). Real include resolution requires file reads; `design_context.py` must stay free of `open(`/`pathlib`. The only place it could legally live is the new loader module.
2. Even in the loader, naive textual include expansion is *semantically risky* — `` `ifdef`` guards and macro arguments make textual inclusion change the design read in ways the module's "provable references only" ethos cannot certify. The module's own philosophy: anything unresolved **stays NETLIST_REQUIRED**, never silently assumed.
3. Consistent with the existing "Not supported" list in the module docstring and the security test `include_directive` case (directive stripped inert, module still parses).

**What we do instead:**

- The loader **pre-scans** each file for `` `include `` directives and records them in `ParseOutcome.warnings` (e.g. `` `include "defs.v" not resolved — any references gated behind it stay NETLIST_REQUIRED ``) — per-finding honesty, zero behavior change.
- Documented **follow-up** (explicitly out of this phase): real include expansion implemented *only in the loader module*, with its own security review and adversarial tests (cycle guards, path containment, `` `ifdef`` handling). Requires an explicit security-contract extension, so it is a separate decision.

---

## 3. Q3 — Cross-file module resolution: read-all-then-resolve (joined-blob)

**Recommendation: read-all-then-resolve, via a single joined parse. No incremental/streaming resolution.**

Design:

1. The new loader reads every file in the filelist (in order) as **utf-8 with `errors="replace"`** (consistent with the CLI's existing `argparse.FileType("r", encoding="utf-8")`; matters on win32), then **normalizes per-file boundaries** before joining: (a) ensures every file's text ends with a `\n`; (b) detects an unterminated `/* ...` block comment at EOF per file and emits a warning (a file ending mid-comment would otherwise swallow the start of the next file once comment-stripping runs on the joined blob).
2. The joined blob (files joined with `\n` separators) is handed to the **existing, unchanged** `parse_verilog(joined, top=top)`. This reuses the module's already-proven multi-module-in-one-blob machinery — an instance in file A of type `foo` defined in file B resolves because the namespace is per-parse, exactly as it already is for multi-module single files.
3. The loader additionally does a cheap **duplicate-module pre-scan** (regex over stripped text) and emits a warning per duplicate. (The current parser silently last-wins on duplicates — fine for single files, a real signal at full-chip scale. Detecting it in the loader keeps the parser untouched.)
4. Provenance: v1 records `ParseOutcome.sources = [file paths read]` (new additive field, default `[]`). **Known limitation of this phase (stated explicitly for users):** any `Issue.line` / warning line numbers produced by the multi-file path are **joined-blob-relative, not source-file-relative** — references still resolve and findings still fire correctly, but line numbers should be treated as approximate. Per-file line attribution would require the internal refactor below — a documented follow-up, not required for correctness.

**Why not incremental per-file resolution:** memory is not the constraint (a 100k-object netlist is a few MB of text); the joined-blob approach is strictly simpler, matches how the module already handles multi-module files, and touches zero parser internals. Streaming is only justified if the perf envelope (Q5) is exceeded — it is not.

**Follow-up (documented, not this phase):** refactor the statement loop to carry a `(source_file, line_offset)` provenance tuple so warnings/errors carry file attribution. This is the *only* parser-internal change envisioned.

---

## 4. Q4 — Top-module selection at full-chip scale: explicit-with-inference-fallback (already built)

**Recommendation: reuse the existing selection logic verbatim. It already implements the desired policy:**

| Case | Behavior (already in `parse_verilog`) |
|---|---|
| exactly one module never instantiated by any other | auto-selected |
| `top=` supplied | honored (error if not found in the full module set) |
| two+ candidates | error listing `top_candidates`; caller must pass `--top` |

At full-chip scale the inference ("module never instantiated in the whole file set") works automatically because the whole file set is one parse. The loader only **forwards** `top`. No new logic. The CLI gains `--top` alongside `--filelist` (mirrors the existing `check --netlist --top` pair).

---

## 5. Q5 — Performance envelope: reuse existing budget, no streaming

Existing evidence (`rta/evidence/test_netlist_perf.py`, `PHASE8_NETLIST_AWARE_REPORT.md`):

- Measures 1k / 10k / 100k design objects; the **enforced** gate is the 10k/1k scaling ratio `< 8.0` (the `>60s at 10k` figure appears in the test docstring as *motivation*, not as an assertion).
- Post-O(N²)-fix measured **linear 0.90× scaling; 100k-object parse ≈ 11.8s** (single file, dev machine).

**Stated budget for the multi-file path (new):**

- Same per-object cost as single-file plus `O(total bytes)` file I/O. No hard wall-clock assertion in CI (machine-dependent), consistent with the existing benchmark's philosophy; the *stated* expectation is **100k-object multi-file parse ≤ ~15s wall** (11.8s + I/O + join headroom).
- The existing 10k/1k ratio gate is **reused unchanged** for the multi-file path.
- **Conclusion: naive read-all-then-resolve (Q3) is viable; streaming is not needed.**

A multi-file perf test extends `test_netlist_perf.py`: generate the same synthetic 1k/10k/100k flop netlists **split across files** (e.g. `top.v` + 10 per-file `core_*.v` chunks) and assert the same ratio gate + a no-regression comparison against the single-file numbers.

---

## 6. Q6 — Backward compatibility: additive entry point in a NEW loader module

**Recommendation: new module `rta/engine/context/design_project.py`; zero changes to `design_context.py` or its callers.**

This is forced by the security contract (§0): `parse_verilog_filelist` must read files, so it **cannot live in `design_context.py`** (the static scan would fail). Placement:

```
rta/engine/context/design_project.py   (NEW — loader: file I/O, .f parsing, globbing, joining, duplicate pre-scan)
rta/engine/context/design_context.py   (UNCHANGED — parser + DesignContext + ParseOutcome; gains only the additive `sources` field)
```

**Public API (new):**

```python
# design_project.py
def parse_verilog_filelist(paths: Sequence[str], top: str = "",
                           incdirs: Optional[List[str]] = None) -> ParseOutcome
    """Read+join the given .v files (or filelist paths) and parse as one design.
    Returns the SAME ParseOutcome/DesignContext types as design_context.parse_verilog."""

def expand_filelist(path: str) -> List[str]
    """Parse a .f filelist into an ordered list of source paths (handles -v, -f,
    +incdir+ (recorded, no-op), # comments, globs; raises on missing files)."""
```

- `parse_verilog_filelist` accepts a list of paths **or** a single `.f` filelist path (dispatch on suffix / `is_dir`), so both interfaces from Q1 share one entry point.
- `ParseOutcome.sources: List[str]` — new additive field on the existing dataclass, default `[]`, so callers (CLI/UI) can display which files were read. No existing consumer constructs `ParseOutcome` positionally except `parse_verilog` itself (verified), so the addition is safe.
- Optional later: root-level shim + `rta/infrastructure/scripts/gen_shims.py` entry for `design_project`.

**Existing consumers — impact table:**

| Consumer | How it uses the parser today | Change needed | In this phase? |
|---|---|---|---|
| `checker.py` (via `check_sdc(..., context=)`) | consumes a `DesignContext` | **none** | — |
| `design_coverage.py`, `constraint_interactions.py` | consume a `DesignContext` | **none** | — |
| `support_boundary.py` | `resolve_collection(..., ctx)` | **none** | — |
| CLI `check --netlist FILE [--top]` (`rta/cli/cli.py:215`) | `parse_verilog(v_text, top=)` | add `--filelist FILE` (mutually exclusive with `--netlist`) + `--incdir`; same `DesignContext` downstream | ✅ **yes** (mirrors existing flag, cheap, unblocks the feature) |
| API `/api/analyze` (`rta/api/api_server.py:137`) | `parse_verilog(netlist_text, top=)` | multi-file upload (filelist text + files) | follow-up (SPA dormant) |
| Streamlit app `_netlist_upload_widget` (`legacy/streamlit/app.py:98`) | single-file upload | multi-file/filelist uploader widget | follow-up (product UI, separate PR) |
| evidence runners / smoke / tests | `parse_verilog(...)` | new fixtures + new runner | ✅ **yes** (test plan §9) |

**Scope split:** this phase = new loader module + `sources`/`context_scope` fields + CLI `--filelist/--top/--incdir` + fixtures/tests/security additions. API + Streamlit upload wiring = separate follow-up commits (one commit per surface, per §0 discipline). **Exception:** the mode selector + scope badge UI (§7.3) is independent of the engine and may land first.

---

## 7. Explicit mode model — block-level vs full-chip (user-facing clarity)

The product already has a visible two-state analysis mode (`SDC_ONLY` ↔ `DESIGN_AWARE`, surfaced as `mode`, `analysis_mode`, `mode_note`, and an "Analysis mode" caption). **This plan makes design-aware scope a third, explicit, always-visible dimension — `block` vs `full_chip` — so users can never mistake one for the other.**

### 7.1 Mode model: mode = input interface, never content inference

| Mode | Determined by | CLI | Streamlit widget | What it claims |
|---|---|---|---|---|
| `SDC_ONLY` | no design context supplied | (no flag) | no netlist uploaded | SDC-only validation; object references stay `NETLIST_REQUIRED` (first-class, never punished) |
| `BLOCK` (design-aware) | **one** netlist file | `--netlist file.v` | single-file uploader | references resolve against this one file's module set; anything outside stays `NETLIST_REQUIRED` |
| `FULL_CHIP` (design-aware) | **filelist** input | `--filelist chip.f [--top T] [--incdir D]` | filelist uploader (+ top name, incdir) | references resolve across the whole file set; top inferred or explicit |

**Clarity rules (load-bearing):**

- Mode is a property of the **input interface the user chose**, not of the file content's hierarchy depth. A single file containing multi-module hierarchy is still `BLOCK`; a flattened one-file chip supplied as a filelist still counts as `FULL_CHIP` — and the loader **warns** when a filelist expands to one file ("filelist resolves to a single file — did you mean `--netlist`?") so the interface stays honest.
- `BLOCK` mode never resolves a reference that lives in another file — it is surfaced `NETLIST_REQUIRED` per the module's provable-references-only ethos (no silent cross-file guessing).
- `FULL_CHIP` mode with unresolved top → existing ambiguous-top error + candidates, or honors `--top`.
- Both design-aware modes remain **optional**; SDC-only stays first-class.

### 7.2 Backward-compatible representation

Existing fields are untouched; the new dimension is **orthogonal and additive**:

- `ParseOutcome.context_scope: str = "block"` — set to `"full_chip"` by `parse_verilog_filelist` (default keeps every existing single-file call site at `block`; zero behavior change).
- API/CLI response gains `context_scope`; existing `mode` (`SDC_ONLY | DESIGN_AWARE`) and `analysis_mode` are unchanged so readiness-diff and downstream consumers keep working.
- `mode_note` strings become scope-aware (human-readable):
  - block: `SDC + Design Context (block-level, top=chip_a, 1 file)`
  - full-chip: `SDC + Full-Chip Context (12 files, top=chip_top, sources=chip.f)`
- **readiness-diff rule addition:** within `DESIGN_AWARE`, a `block ↔ full_chip` scope change also yields `PARTIALLY_COMPARABLE` (different evidence basis), mirroring the existing `SDC_ONLY ↔ DESIGN_AWARE` handling in `readiness_diff.py`.

### 7.3 Interface spec — Streamlit app (the product at 8502)

1. **Mode selector** at the top of the existing netlist expander (segmented control, mirrors the app's existing tab/radio patterns):
   - `🧱 Block-level — one .v file`
   - `🏭 Full-chip — .f filelist (+ files)`
   - Selection swaps the upload area (single uploader ↔ filelist uploader + `top` name input + optional incdir input).
   - Until the engine lands, Full-chip shows an informative disabled state ("lands with the full-chip engine") — the selector and badge ship first.
2. **Persistent scope badge** in each analysis tab's summary row (Checker/Clock/Coverage/Interactions/Readiness/Diff):
   - `SDC-only` · `🧱 Block-level · top=X` · `🏭 Full-chip · N files · top=Y`
3. **Per-mode caption** under the badge: block = "references resolve against this one file"; full-chip = "references resolve across the whole file set — modules in other files are visible".
4. Download payloads (the analysis JSON buttons) include `context_scope` so an exported result is self-describing.

### 7.4 Interface spec — CLI and API

- CLI: `--netlist` and `--filelist` are **mutually exclusive** (argparse conflict error); `--filelist` pairs with existing `--top` + new `--incdir`. Scope line in `--format text` output: `analysis scope: block-level (1 file, top=X)` / `analysis scope: full-chip (12 files, top=Y)`; JSON output adds `context_scope`.
- API `POST /api/analyze`: accept either `netlist` (single text, as today) or `filelist: [{name, content}]` + optional `top`; response gains `context_scope` and the scope-aware `mode_note` above.
- `reporter.py` HTML "Analysis mode" row gains the scope (e.g. `SDC + Full-Chip Context`).
- Website capability pages (`rta/website/capabilities/context.html` etc.) describe both modes side by side.

---

## 8. New/changed signatures (summary)

| Symbol | Change |
|---|---|
| `design_context.parse_verilog(text, top="")` | **unchanged** (signature + behavior) |
| `design_context.ParseOutcome` | **+`sources: List[str]`** (additive, default `[]`) **+`context_scope: str`** (additive, default `"block"`) |
| `design_project.parse_verilog_filelist(paths \| filelist_path, top="", incdirs=None)` | **new**; returns `ParseOutcome` with `context_scope="full_chip"` |
| `design_project.expand_filelist(path)` | **new** (`.f` → ordered paths) |
| CLI `check` | **+`--filelist FILE`, +`--incdir DIR`** (mutually exclusive with `--netlist`); `--top` already exists; scope line + `context_scope` in output |
| API `/api/analyze` | **+`filelist` request variant; +`context_scope` in response** (follow-up commit) |
| Streamlit netlist widget | **+mode selector + scope badge** (UI commit, can land before the engine) |

---

## 9. Test plan sketch

Mirrors the existing single-file "catches a typo'd port name against the netlist" check in `smoke_test.py` (`test_design_context_catches_typo`), extended across file boundaries.

**New fixture: `rta/evidence/netlist_aware/fullchip/`** (or a new `NA11..NA13` family — decide with the evidence-owner convention; the fixture set below is the contract):

```
chip.f                      # top.v, core.v, lib/flop.v (+ a `-v` line and a `+incdir+` line to prove tolerance)
top.v    module top (...) instantiates u_core (from core.v); ports clk, data_in, data_out
core.v   module core (...) instantiates u_flop (from lib/flop.v); cross-file instance
lib/flop.v  module flop (...)  third file down the hierarchy
dup.v    (separate case) re-declares module core  → duplicate-module warning expected
```

Tests (pytest `rta/tests/test_design_context.py` + `rta/tests/test_design_project.py`):

1. **cross-file parse**: `parse_verilog_filelist([top.v, core.v, lib/flop.v], top="top")` → context with `instances["u_core"]` and `instances["u_core/u_flop"]` both present and module-resolved across files.
2. **typo across a file boundary** (the headline case): SDC references `[get_ports data_otp]` (SDC in `top.v`'s file), netlist has `data_out` → `validate_design_references` emits the SDC-055-class finding; assert the same needle as the single-file smoke test.
3. **cross-file pin reference resolves**: `[get_pins u_core/u_flop/D]` resolves (port dirs come from `lib/flop.v`), not `NETLIST_REQUIRED`.
4. **filelist format tolerance**: `.f` with `#` comments, `-v`, `+incdir+` → parses, `+incdir+` appears in `ParseOutcome.warnings`.
5. **top inference**: filelist with a unique top → auto-selected; with two un-instantiated tops → error + `top_candidates`; `top=` disambiguates.
6. **duplicate module across files** → warning, deterministic (documented last-wins) outcome.
7. **missing file / cycle in nested `-f`** → clean error/warning, no crash (adversarial).
8. **file-boundary hazards** (locks in Q3 boundary normalization): a file whose last line is a `//` comment **without a trailing newline**, and a file ending in an unterminated `/*` — assert the next file's module still parses and the unterminated-comment case surfaces a warning, never a silent merge error.
9. **security regression**: existing `test_netlist_security.py` keeps passing (parser still has no file I/O) **plus** a new check that `design_project.py` *does* the file I/O (so the boundary is explicit, not accidental).
10. **perf**: extend `test_netlist_perf.py` with the split-across-files 1k/10k/100k case; same ratio gate.
11. **mode model** (locks in §7): `parse_verilog` returns `context_scope="block"` and `parse_verilog_filelist` returns `"full_chip"`; CLI `--netlist`+`--filelist` together → argparse conflict error; scope-aware `mode_note` strings; `context_scope` present in `--format json`; single-file filelist triggers the "did you mean `--netlist`?" warning; readiness-diff of `block ↔ full_chip` yields `PARTIALLY_COMPARABLE`.
12. **UI (AppTest, lands with the mode selector)**: mode selector renders; switching modes swaps the upload area; scope badge text reflects the chosen mode; SDC-only state shows no badge.

**Regression gates for the implementation phase:** `pytest rta/tests -q` · `python3 smoke_test.py` · `run_netlist_aware.py` (existing 10/10 must hold) · `test_netlist_security.py` (7/7 must hold).

**Mode-model gates:** existing `test_ui_app.py` (37/37) and `test_workspace_ux.py` (31/31) must hold — the new `context_scope`/`mode_note` are additive, and the Streamlit scope-badge change is covered by AppTest #12.

---

## 10. Explicitly out of scope (deferred, not forgotten)

- Real `` `include `` expansion (Q2 — needs security-contract decision)
- Per-finding file provenance (Q3 follow-up refactor)
- API + Streamlit multi-file upload wiring (Q6 — separate surface commits)
- Library-directory (`-y`) filelist support
- Website capability-page mode descriptions (marketing copy, can be trimmed to a follow-up)
