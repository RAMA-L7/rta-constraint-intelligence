# Glossary

> **Document kind:** authoritative terminology reference.
> **Purpose:** every term in this glossary has one definition. Using a term in a different sense is a product error.
> **Scope:** applies to all product surfaces, documentation, code comments, and public communication.
> **Last updated:** 2026-08-07

---

## Product Terms

### Constraint Intelligence

The domain Ṛta operates in: the analysis of SDC constraint sets for completeness, consistency, resolvability, and coherence — as a system, not as isolated commands. Ṛta is a Constraint Intelligence Platform.

### Constraint Quality

Whether a constraint set is complete, consistent, resolvable, and coherent. Ṛta measures constraint quality. It does not measure timing closure.

### Block-Level Constraint Intelligence

The current scope of Ṛta Version 1: constraint intelligence for a single block, module, or IP. Does not include subsystem, top-level, or multi-block analysis.

### Subsystem Constraint Intelligence

Future scope (Version 2): constraint intelligence across multiple blocks, clock domains, and interfaces within a subsystem. Not implemented.

### Top-Level Constraint Intelligence

Future scope (Version 3): constraint intelligence for an entire chip, including global clock trees, top-level I/O, and cross-subsystem interactions. Not implemented.

---

## Core Concepts

### SDC

Synopsys Design Constraints — the industry-standard format for expressing timing intent. Ṛta analyzes SDC files. SDC vocabulary (`create_clock`, `set_clock_groups`, etc.) is never renamed.

### Finding

An observed condition backed by evidence. Every finding has a severity, rule code, message, and source provenance (line number, and line₂ where two lines matter). Findings are not opinions.

### Severity

The impact ordering of a finding: **error** (must fix), **warning** (should review), **info** (best practice), **fatal** (critical failure). Severity describes impact, not truth.

### Rule

A deterministic check implemented in the analysis engine. Each rule has a unique code (e.g., `SDC-001`), a severity, a description, a "why it matters" explanation, a suggested fix, and a reference. There are 111 rules in Version 1.

### Evidence

A rerunnable artifact in the repository that proves a product claim. Evidence includes pytest tests, golden runners, benchmark suites, release smoke tests, CLI contract audits, and clean-room checks. Every public number must trace to evidence.

### Golden Runner

A benchmark runner that compares the tool's output against independently derived expected outcomes. The expected behavior is derived from SDC semantics, not from the tool's output. Golden runners prove correctness, not just consistency.

### Benchmark Suite

A pytest-based test suite in `benchmarks/` that validates a specific category of behavior: correctness, robustness, design-aware analysis, regression reliability, security, performance, or release quality.

---

## Analysis Concepts

### Readiness

A handoff-oriented aggregate verdict indicating whether a constraint set is ready for STA. Readiness is NOT timing signoff. Readiness has five possible verdicts: READY, READY_WITH_ADVISORIES, REVIEW_REQUIRED, BLOCKED, INSUFFICIENT_CONTEXT.

### Readiness Dimension

One of seven dimensions that contribute to the readiness verdict: CLOCKS, I/O, EXCEPTIONS, COVERAGE, CONSISTENCY, ANALYSIS_TRUST, DESIGN_CONTEXT. Each dimension has its own status and evidence.

### Trust

How completely a construct was analyzed. The Trust Model defines six statuses: VALIDATED, PARTIALLY_VALIDATED, NETLIST_REQUIRED, TCL_EXECUTION_REQUIRED, UNSUPPORTED, NOT_VALIDATED. Trust is the product's first-class credibility mechanism.

### Trust Disclosure

A mandatory statement on every surface that presents analysis results, disclosing what was checked, what was partially checked, and what was skipped. Trust disclosures are not footnotes; they are first-class content.

### Coverage

Whether something was constrained. Coverage ≠ correctness. A fully constrained object can still have incorrect timing intent. This distinction is mandatory wherever coverage is presented.

### Design Context

The optional structural Verilog netlist supplied alongside the SDC file. Design context upgrades reference checking from syntax-level to object-level. Without it, object references are reported as NETLIST_REQUIRED.

### Constraint Interaction

A semantic relationship between two constraints: exact duplicate, silent override, provable contradiction (SDC-069), or STA-review overlap (SDC-070). Interactions have dual-line provenance (line ↔ line₂).

### Baseline

A saved, versioned snapshot of a readiness analysis. Used for regression comparison and CI gating. Baselines use schema v2 with v1 compatibility.

### Regression

A disallowed readiness, coverage, or trust change versus a saved baseline. Detected by the readiness diff engine and evaluated by CI gate policies.

---

## Trust Model Terms

### VALIDATED

Constructs fully analyzed by the rule engine. The tool can vouch for the result.

### PARTIALLY_VALIDATED

Some options or constructs not fully value-analyzed. The tool discloses what was and was not checked.

### NETLIST_REQUIRED

Object references need design context (Verilog netlist) to be resolved. Without a netlist, the tool says so.

### TCL_EXECUTION_REQUIRED

Tcl execution constructs are present (eval, expr, exec). The tool detects but does not execute them. They are analyzed at the text level only.

### UNSUPPORTED

Constructs outside the tool's support boundary. Detected and disclosed, never silently skipped.

### NOT_VALIDATED

Nothing could be validated (empty or invalid input). The tool reports this explicitly.

---

## Readiness Terms

### READY

No blockers, no review items, advisories only. The constraint set satisfies the tool's readiness criteria. This is NOT timing signoff.

### READY_WITH_ADVISORIES

No blockers; advisory-level items present. The constraint set is functional but has best-practice recommendations.

### REVIEW_REQUIRED

Review items present, possibly including STA follow-ups. The constraint set needs human review before handoff.

### BLOCKED

Blockers present. The constraint set has error-level findings that must be addressed before handoff.

### INSUFFICIENT_CONTEXT

Not enough evidence for a verdict. Typically means a netlist is needed or critical analysis scope is missing.

---

## Evidence Terms

### Release Smoke

A test suite (`test_release_smoke.py`) that verifies documented workflows work correctly: install, CLI commands, output formats, workspace launch.

### CLI Contract Audit

A test (`release_cli_audit.py`) that verifies the CLI's exit-code contract, JSON output purity, and version output across all commands.

### Clean-Room Wheel Journey

A test (`release_cleanroom.py`) that builds a wheel, installs it in a fresh environment, and verifies it works from any working directory.

### Adversarial Suite

A test suite that attempts to break the tool with malformed, extreme, or unexpected inputs. Proves robustness.

### Metamorphic Suite

A test suite that verifies that semantically equivalent inputs produce semantically equivalent outputs. Proves determinism.

### Performance Suite

A test suite that measures wall-time for specific workloads and verifies they fall within acceptable bounds.

---

## Process Terms

### Product Charter

The constitution of Ṛta. Defines what the product is, what it is not, where it is going, and what must never change. Highest-priority document in the repository. All other documents implement it.

### Operating System

The internal handbook. Defines principles, processes, decision-making, quality gates, naming, design, release, and community standards. Implements the Charter's principles as operational processes.

### RFC (Request for Comments)

A formal proposal for a new feature or significant change. Required before implementing anything that touches the engine, the Trust Model, or the product boundary.

### ADR (Architecture Decision Record)

A record of a significant architectural decision: what was decided, why, what alternatives were considered, and what the consequences are. ADRs are immutable once accepted.

### Definition of Done

A feature is done when it has correct output, tests (happy path, edge case, error), trust boundary documentation, accurate evidence numbers, and no regressions. (See Operating System §5.)

### Definition of Trust

A surface has Trust Integrity when every finding has severity, rule, evidence, and provenance; every result carries scope disclosure; every clean result communicates "no rule fired" rather than "correct"; and every performance number includes environment context. (See Operating System §6.)

### Definition of Evidence

Evidence is a rerunnable artifact in the repository that proves a product claim. (See Operating System §7.)

---

## CI Terms

### Exit-Code Contract

The deterministic CLI exit-code convention: 0 = pass, 1 = gate failed, 2 = invalid invocation, 3 = engine failure. Engine failure can never produce a passing result.

### Gate Policy

A declarative policy for CI quality gates: BLOCKERS_ONLY, NO_READINESS_REGRESSION, STRICT, or CUSTOM. Policies are inert data, not executable code.

### Engine Failure Guarantee

An analysis or policy engine failure must never produce a passing verdict or passing exit code. This is a hard invariant.

---

## Architecture Terms

### Frozen Engine

The deterministic analysis pipeline is considered frozen. Changes require architecture review and full regression. The engine is the product's core asset.

### Open Core

The model where the deterministic engine, CLI, reports, benchmarks, and documentation are MIT-licensed (Community), while future team and enterprise features are additive commercial scope. Nothing that exists today moves behind a paywall.

### Single Wheel

The product ships as a single Python wheel. All backend modules, the CLI, the workspace, and the website ship together. `pip install sdc-tools[web]` is the complete installation.

### Offline-First

The product runs entirely locally. No network, no cloud, no external API required for analysis. Data never leaves the machine. This is a trust boundary, not a feature flag.

---

## Brand Terms

### Ṛta

The visible product name. Unicode U+1E5A (lowercase r with dot below). Always rendered with the dot below on user-facing surfaces.

### rta

The technical ASCII identifier. Used in CLI invocations, environment variables, file paths, and the future Python package namespace.

### sdc-tools

The backward-compatible CLI alias and current package name. Retained for compatibility. `rta` is the primary entry point.

---

*This glossary is the single source of truth for terminology. If a term is used differently in any document, this glossary takes precedence. Update this glossary when new terms are introduced; never modify a term's definition without updating every surface that uses it.*
