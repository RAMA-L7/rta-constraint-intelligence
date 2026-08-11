# Ṛta — Product Taxonomy

> **Document kind:** product architecture — the capability family and how each
> product module maps to real backend evidence.
> **Date:** 2026-08-06 · **Version:** v1.3.0

---

## 1. Product family

The workspace is organized into the following product modules. Each module is
grounded in an existing backend capability — none is created for marketing
symmetry.

| Product module | Purpose (one line) | Backend modules |
|---|---|---|
| **Ṛta Validate** | Deterministic constraint validation with per-finding source provenance | `checker.py`, `rules_registry.py`, `sdc_preprocess.py`, `tcl_resolver.py`, `support_boundary.py` |
| **Ṛta Clocks** | Clock inventory, generated-clock hierarchy and pairwise relationship matrix | `clock_relations.py`, `wildcard_analyzer.py` |
| **Ṛta Context** | Design/netlist context: hierarchy, objects, collection resolution, trust upgrades | `design_context.py`, `wildcard_analyzer.py` |
| **Ṛta Coverage** | Object/bus-oriented constraint coverage with exact bit-range evidence | `design_coverage.py`, `coverage.py` |
| **Ṛta Interactions** | Constraint-to-constraint relationships: duplicates, overrides, contradictions, STA-review overlaps | `constraint_interactions.py` |
| **Ṛta Readiness** | Handoff-oriented readiness verdict across seven dimensions with deterministic actions | `constraint_readiness.py` |
| **Ṛta Diff** | Semantic change review vs a saved baseline: new/resolved/changed/unchanged, trust + coverage deltas | `readiness_diff.py`, `finding_identity.py`, `constraint_diff.py` |
| **Ṛta CI** | Declarative gate policies, CLI command, exit-code contract, engine-failure guarantee | `policy_engine.py`, `readiness_diff.py` (gate evaluation) |

Tooling that does not belong to the core analysis family stays grouped under
**Tools**: Generator, Linter, Converter, Corner Manager, MMC SDC, Rules,
Test Drive, Feedback. These are real capabilities; grouping is navigational,
never a deprecation.

## 2. Module definitions

Each module below uses the same template: purpose · primary user · input ·
analysis · output · trust boundary.

---

### 2.1 Ṛta Validate

- **Purpose:** validate an SDC file against the deterministic rule registry and
  report every finding with severity, rule, message, line (and line₂ where
  relevant), plus an explicit analysis-scope trust statement.
- **Primary user:** PD / STA / synthesis engineers authoring constraints.
- **Input:** SDC text or file; optional Verilog netlist + top module; optional
  custom-rules YAML.
- **Analysis:** preprocessing → bounded Tcl variable resolution → semantic
  checks (SDC-001…043, 060…063, 100…132) → clock-reference resolution →
  optional design-aware reference checking.
- **Output:** issues (error/warning/info), stats, analysis scope, optional
  JSON / JUnit / CSV / Markdown / HTML.
- **Trust boundary:** scope status is always reported (e.g. `NETLIST_REQUIRED`,
  `PARTIALLY_VALIDATED`, `TCL_EXECUTION_REQUIRED`, `UNSUPPORTED`). A clean
  result means “no rule fired”, not “timing proven”.
- **CLI:** `rta check` · **UI:** workspace “Validate” page · **Report:** HTML/JSON.

### 2.2 Ṛta Clocks

- **Purpose:** discover clocks, derive generated-clock ancestry, and classify
  every clock pair as synchronous / asynchronous / physically-exclusive with a
  reason.
- **Primary user:** STA and PD engineers reviewing clock intent.
- **Input:** SDC.
- **Analysis:** clock extraction; generated-clock parent/child resolution via
  `-master_clock`, `-source` nodes and port identity; C(n,2) pairwise inference;
  mismatch detection vs declared `set_clock_groups`.
- **Output:** clock inventory (name/type/period/frequency/source/master),
  hierarchy, pair classification, mismatches (SDC-060…063).
- **Trust boundary:** classification is *inferred* from SDC text — it is not a
  netlist-based structural analysis unless design context is supplied.
- **CLI:** `rta analyze clock-relations` · **UI:** workspace “Clocks” page.

### 2.3 Ṛta Context

- **Purpose:** when a Verilog netlist is supplied, resolve `get_ports` /
  `get_pins` / `get_cells` / `get_nets` / `all_*` collections and upgrade
  reference checking from syntax-level to object-level.
- **Primary user:** engineers validating SDC against a real design.
- **Input:** Verilog netlist (+ top module), SDC.
- **Analysis:** structural parse → object inventory → collection resolution →
  missing-object detection, distinguishing *explicit object missing* from
  *wildcard matched nothing* where the backend supports it.
- **Output:** object counts, hierarchy, resolution status per collection,
  unsupported-expression inventory.
- **Trust boundary:** object resolution ≠ path existence. A resolved pin is not
  proof the timing path exists.
- **UI:** workspace “Context” page · **CLI:** `rta check --netlist FILE`.

### 2.4 Ṛta Coverage

- **Purpose:** answer “was something constrained?” — per input/output port and
  per bus bit-range, with constrained / unconstrained / partial / exempt /
  unknown / not-applicable statuses.
- **Primary user:** PD engineers closing I/O constraint gaps.
- **Input:** SDC (+ netlist for design-aware mode).
- **Analysis:** SDC-only 39-item coverage across 6 categories; design-aware
  object coverage with partial-bus bit-range tracking.
- **Output:** coverage summary, per-bucket counts, bus bit-maps, missing-only list.
- **Trust boundary:** **coverage ≠ correctness** — a fully constrained object
  proves no timing intent error. Disclosed in-product and in reports.
- **CLI:** `rta coverage` · **UI:** workspace “Coverage” page.

### 2.5 Ṛta Interactions

- **Purpose:** detect semantic relationships between constraints: exact
  duplicates, silent overrides, provable contradictions (SDC-069), and
  exception overlaps that require STA review (SDC-070).
- **Primary user:** STA/PD engineers reviewing conflicting or redundant intent.
- **Input:** SDC.
- **Analysis:** constraint normalization → identity → pairwise interaction
  classification with dual-line provenance (line ↔ line₂).
- **Output:** interaction findings with both source lines and a reason.
- **Trust boundary:** overlaps flagged for STA review are *possible* conflicts —
  definitive judgment belongs to timing analysis.
- **UI:** workspace “Interactions” page.

### 2.6 Ṛta Readiness

- **Purpose:** aggregate checker + scope + coverage + interactions into a
  handoff-oriented verdict across seven dimensions with deterministic
  recommended actions (P0…P3).
- **Primary user:** engineers and reviewers deciding “is this ready to hand to
  STA?”.
- **Input:** the aggregate `check_sdc()` result (optionally netlist-aware).
- **Analysis:** readiness dimensions — CLOCKS, I/O, EXCEPTIONS, COVERAGE,
  CONSISTENCY, ANALYSIS_TRUST, DESIGN_CONTEXT — each with a status and summary;
  overall verdict: READY / READY_WITH_ADVISORIES / REVIEW_REQUIRED / BLOCKED /
  INSUFFICIENT_CONTEXT.
- **Output:** verdict, dimension rail, blockers, review items, advisories,
  actions.
- **Trust boundary:** **READY ≠ STA signoff** and **CI pass ≠ timing closure** —
  kept prominent in the UI.
- **CLI:** `rta check` (readiness section) · **UI:** workspace “Readiness” page.

### 2.7 Ṛta Diff

- **Purpose:** compare a constraint set against a saved readiness snapshot and
  answer “what changed and did it regress?”.
- **Primary user:** engineers and CI pipelines protecting constraint quality.
- **Input:** baseline snapshot (JSON, schema v2, identity v1) + current SDC.
- **Analysis:** structured finding identity (not line comparison) →
  new/resolved/changed/unchanged findings, readiness overall delta, coverage
  delta, trust/context delta, compatibility classification (incl. incompatible
  baseline and engine failure).
- **Output:** classification (e.g. `BLOCKING_REGRESSION`), deltas, debt
  (existing/new/resolved).
- **Trust boundary:** an incompatible baseline or engine failure is surfaced,
  never silently passed.
- **CLI:** `rta check --baseline … --gate …` · **UI:** workspace “Diff” page.

### 2.8 Ṛta CI

- **Purpose:** gate constraint quality in CI with declarative policies and a
  stable exit-code contract.
- **Primary user:** CI pipelines and methodology teams.
- **Input:** policy (built-in `BLOCKERS_ONLY`, `NO_READINESS_REGRESSION`,
  `STRICT`, or declarative `CUSTOM` JSON/YAML policy), optional baseline.
- **Analysis:** `evaluate_gate` → pass/fail per policy + reasons.
- **Output:** gate verdict + exit code (0 pass / 1 gate failed / 2 invalid
  invocation / 3 engine failure), GitHub Actions example.
- **Trust boundary:** an engine failure can never produce a passing exit code.
- **CLI:** `rta check --gate … [--gate-policy FILE]` · **UI:** workspace
  “CI / Policies” page.

## 3. Grouping rationale

- **ANALYZE** (Validate, Clocks) — first-order analysis of the constraint text.
- **DESIGN** (Context, Coverage) — design-aware analysis layers.
- **QUALITY** (Interactions, Readiness) — cross-constraint quality and verdicts.
- **CHANGE** (Diff) — regression protection.
- **OUTPUT** (Reports, CI) — artifacts and gates.
- **TOOLS** (Generator … Feedback) — auxiliary capabilities, fully preserved.

No artificial modules were created for symmetry; each group corresponds to a
real analysis layer in the backend.
