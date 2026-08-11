# Ṛta — Capability Map

> **Document kind:** inventory of every real capability with its backend
> module, interfaces, trust level, limitations and benchmark evidence.
> **Date:** 2026-08-06 · **Version:** v1.3.0

No capability below is invented; each maps to a module in this repository.
Confidence levels follow the trust vocabulary: **VALIDATED** (fully analyzed),
**PARTIALLY_VALIDATED**, **NETLIST_REQUIRED**, **TCL_EXECUTION_REQUIRED**,
**UNSUPPORTED**, **NOT_VALIDATED**.

---

## 1. Core analysis capabilities

### 1.1 SDC preprocessing
- **Backend:** `sdc_preprocess.py`
- **Input:** raw SDC text · **Output:** normalized, line-annotated command stream.
- **Trust:** VALIDATED for supported constructs.
- **Limitations:** Tcl execution constructs are detected, not executed.
- **CLI:** `rta check` (implicit) · **UI:** Validate · **Report:** findings only.

### 1.2 Bounded Tcl variable resolution
- **Backend:** `tcl_resolver.py`, `sdc_preprocess.py`
- **Input:** `set <var> <value>` + `$var` / `${var}` references.
- **Trust:** PARTIALLY_VALIDATED — bounded subset; execution constructs excluded.
- **Evidence:** `tests/test_tcl_resolver.py`.

### 1.3 Deterministic validation (rule engine)
- **Backend:** `checker.py`, `rules_registry.py`
- **Rules:** SDC-001…043, SDC-060…063, SDC-100…132 (checker + clock relations +
  coverage + interactions modules).
- **Output:** `CheckResult` (issues with code/severity/msg/line/line2, stats,
  scope).
- **Trust:** VALIDATED for analyzed commands; scope status always reported.
- **CLI:** `rta check` · **UI:** Validate · **Report:** HTML/JSON/JUnit.

### 1.4 Analysis-scope / support-boundary disclosure
- **Backend:** `support_boundary.py`
- **Output:** `NETLIST_REQUIRED` / `TCL_EXECUTION_REQUIRED` / `PARTIALLY_VALIDATED`
  / `UNSUPPORTED` / `NOT_VALIDATED` status with command counts.
- **Trust:** core transparency feature — a “no errors” result never reads as
  “everything proven”.
- **Evidence:** `tests/test_support_boundary` (via `test_checker.py`), phase 7 reports.

### 1.5 Clock extraction & generated-clock ancestry
- **Backend:** `clock_relations.py`
- **Output:** clock inventory (name/period/source/master/divide_by), ancestor chains
  resolved via `-master_clock`, `-source` nodes, and port identity.
- **Trust:** PARTIALLY_VALIDATED — inference from SDC text; netlist strengthens it.
- **CLI:** `rta analyze clock-relations` · **UI:** Clocks.

### 1.6 Clock relation classification & mismatch detection
- **Backend:** `clock_relations.py`
- **Output:** C(n,2) pairs classified synchronous / asynchronous /
  physically-exclusive with reasons; mismatches vs declared `set_clock_groups`
  (SDC-060…063).
- **Trust:** PARTIALLY_VALIDATED — inference, not structural analysis.
- **Performance:** ancestor sets precomputed; 150-clock design analyzed in
  O(N²) within the guard time (see `test_large_design_relations_fast_and_correct`).
- **CLI:** `rta analyze clock-relations` · **UI:** Clocks matrix.

### 1.7 Design / netlist context
- **Backend:** `design_context.py`, `wildcard_analyzer.py`
- **Input:** Verilog (structural subset) + optional top module.
- **Output:** ports/pins/cells/nets counts, hierarchy, per-collection resolution
  (RESOLVED / EMPTY / UNSUPPORTED EXPRESSION).
- **Trust:** NETLIST_REQUIRED semantics — supplied netlist upgrades reference
  checks; absence is disclosed.
- **CLI:** `rta check --netlist FILE [--top NAME]` · **UI:** Context.
- **Evidence:** netlist-aware benchmark suites, phase 8/9 reports.

### 1.8 Constraint coverage (SDC-only)
- **Backend:** `coverage.py`
- **Output:** 39-item coverage across 6 categories with score and missing list.
- **Trust:** PARTIALLY_VALIDATED; coverage ≠ correctness (disclosed).
- **CLI:** `rta coverage` · **UI:** Coverage (SDC-only mode).

### 1.9 Design-aware coverage & partial-bus evidence
- **Backend:** `design_coverage.py`
- **Output:** per-port status (constrained / unconstrained / partial / exempt /
  unknown / not-applicable) with exact bus bit-ranges.
- **Trust:** NETLIST_REQUIRED — runs only with design context.
- **UI:** Coverage (bus strips) · **Evidence:** coverage metamorphic/adversarial suites.

### 1.10 Constraint interactions
- **Backend:** `constraint_interactions.py`
- **Output:** exact duplicates, silent overrides, provable conflicts (SDC-069),
  STA-review overlaps (SDC-070), legal multiples — with dual-line provenance.
- **Trust:** PARTIALLY_VALIDATED; overlaps needing STA are flagged as review, not
  verdicts.
- **UI:** Interactions · **Evidence:** interaction suites + phase 10 report.

### 1.11 Constraint readiness
- **Backend:** `constraint_readiness.py`
- **Output:** overall verdict + seven dimensions + blockers/review/advisories +
  deterministic actions (P0…P3).
- **Trust:** READY ≠ STA signoff (prominent in UI/reports/CLI).
- **CLI:** `rta check` (readiness section) · **UI:** Readiness.

### 1.12 Readiness snapshots & semantic diff
- **Backend:** `readiness_diff.py`, `finding_identity.py`
- **Output:** baseline snapshot (schema v2, identity v1), diff classification
  (BLOCKING_REGRESSION etc.), new/resolved/changed/unchanged, debt, coverage &
  trust deltas, compatibility (incl. incompatible-baseline and engine-failure
  classification).
- **Trust:** identity-based comparison, not line comparison.
- **CLI:** `rta check --save-baseline … --baseline …` · **UI:** Diff.

### 1.13 CI gate policies
- **Backend:** `policy_engine.py`, `readiness_diff.py`
- **Policies:** BLOCKERS_ONLY, NO_READINESS_REGRESSION, STRICT, declarative
  CUSTOM (JSON/YAML).
- **Exit-code contract:** 0 pass / 1 gate failed / 2 invalid invocation /
  3 engine failure. Engine failure never passes.
- **CLI:** `rta check --gate … [--gate-policy FILE]` · **UI:** CI / Policies.
- **Evidence:** CLI contract tests (`TestCliCustomPolicy`), phase 12/13 reports.

### 1.14 Custom rules
- **Backend:** `custom_rules.py`
- **Input:** YAML rulesets · **Output:** pass/fail per custom rule.
- **CLI:** `rta check --custom-rules FILE` · **UI:** Tools → Rules.

### 1.15 Semantic constraint diff (CHG rules)
- **Backend:** `constraint_diff.py`
- **Output:** added/removed/modified changes (CHG-*) between two SDC files.
- **CLI:** `rta diff old.sdc new.sdc`.

## 2. Tooling capabilities

| Capability | Backend | CLI | Trust notes |
|---|---|---|---|
| SDC generator | `generator.py` | `rta generate` | deterministic templates |
| SDC linter | `linter.py` | `rta lint` | formatting only |
| SDC converter (JSON/YAML) | `converter.py` | `rta convert` | parser-backed |
| Corner manager (MMC) | `corner_manager.py` | `rta corners` | presets + validation |
| MMC SDC generator | `mmc.py` | via UI | corners × constraints |
| Batch processor | `batch_runner.py` | `rta batch` | check/lint/report dirs |

## 3. Product surfaces

| Surface | Tech | Status |
|---|---|---|
| Workspace (premium) | `api_server.py` + `webui/` (vanilla JS, stdlib server) | production |
| Marketing website | `site/` (static HTML/JS) | production |
| Streamlit workspace | `app.py` + `ui/` | legacy, still shipped |
| CLI | `cli.py` (entry points `sdc-tools`, `rta`) | production |
| HTML reports | `reporter.py` | production |

## 4. Open-core consideration

Per [OPEN_CORE_STRATEGY.md](OPEN_CORE_STRATEGY.md): all capabilities above are
**Community** (open). Nothing existing is scheduled for a future paywall;
future commercial scope is additive (team/enterprise collaboration).
