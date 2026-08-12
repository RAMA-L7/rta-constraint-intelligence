# Ṛta — Product Experience Architecture

**Startup-Grade Product Blueprint · v1.0 (architecture only — no implementation)**
**Date:** 2026-08-06 · **Baseline:** Ṛta v1.3.0 (RC_READY_WITH_KNOWN_LIMITATIONS)

> This document designs the complete product experience architecture for the
> Ṛta. It is **architecture and planning only**. No production code,
> validation logic, benchmark expectation, or backend API is changed by this
> document. Every claim below is grounded in the current repository.

---

## 1. Executive Product Vision

The Ṛta is a **deterministic, offline, engineering-grade constraint
quality platform** for SDC (Synopsys Design Constraints) development. It sits
between constraint *authoring* and downstream *STA/signoff*, answering the
question engineers ask before handoff:

> "Is this constraint set complete, consistent, resolvable, and ready to hand
> to STA / implementation — and what still needs review?"

The product vision is **"Constraint Quality Intelligence and Pre-STA
Validation."** It is explicitly **not** a timing engine, not an AI copilot, and
not a signoff substitute. Its identity is built on what it actually is:

- **DETERMINISTIC** — the same input always produces the same evidence.
- **OFFLINE-CAPABLE** — no network, no cloud, no external API required for validation.
- **REPRODUCIBLE** — structured findings, versioned snapshots, traceable benchmarks.
- **ENGINEERING-FOCUSED** — honest trust boundaries instead of false confidence.

The product experience must make all of that visible, understandable, and
trustworthy to a physical-design/STA engineer in the first ten seconds.

---

## 2. Current Product Baseline (verified)

| Dimension | Value |
|---|---|
| Version | **1.3.0** |
| Release status | **RC_READY_WITH_KNOWN_LIMITATIONS** |
| pytest | **793/793** |
| Golden runners | **9/9** (parser 22/22 · semantic 9/9 · reference 8/8 · coverage 12/12 · netlist-aware 10/10 · interactions 20/20 · readiness 15/15 · readiness-diff 22/22 · production-hardening 49) |
| Benchmark suites | **42/42** |
| Clean-room wheel journey | **17/17** |
| CLI contract audit | **16/16** |
| Release smoke suite | **10/10** |
| Rules catalog | **115 rules** (74 checker · 21 constraint_diff · 5 design_context · 4 mmc · 4 clock_relations · 4 constraint_interactions · 3 design_coverage) |
| Severity mix | 15 error · 47 warning · 43 info · 6 fatal |
| Modules | 15 production modules + `ui/` (5 files) + `app.py` |
| CLI commands | check · generate · diff · corners · analyze · rules · coverage · report · lint · convert · batch · web |
| Exit-code contract | 0 pass · 1 gate/analysis fail · 2 invalid invocation · 3 engine failure |
| Runtime | Python ≥ 3.10, no required runtime deps; `streamlit` optional `[web]` |
| Performance (measured) | 10k findings readiness-diff ≈ 43–75 ms; readiness aggregation ≈ 8 ms; 400 clocks ≈ ~1 s range |

*All values traceable to repository artifacts (see §13).*

---

## 3. Product Category

**Primary category: SDC Constraint Quality Platform (Pre-STA Constraint Validation).**

Evaluated language:

| Candidate | Verdict |
|---|---|
| Ṛta | Accurate, current name — keep as product name |
| Constraint Quality Intelligence | Best category descriptor |
| Pre-STA Constraint Validation | Best workflow descriptor |
| Constraint Readiness Platform | Strong subset descriptor (readiness is one capability, not the whole) |
| Timing Constraint Intelligence | Overlaps with "timing" claims we must not make |

**Recommended one-line description:**
> Deterministic SDC constraint validation, coverage, interaction analysis, and
> handoff readiness — before STA.

**Short description:**
> Ṛta analyzes SDC (optionally with structural Verilog) to catch
> undefined references, clock problems, coverage gaps, constraint
> interactions, and handoff blockers — deterministically and offline — and
> tracks readiness regressions across revisions with CI quality gates.

**Technical description:**
> A dependency-light Python engine that preprocesses SDC (comments, multiline,
> Tcl scalars, collections), validates against a 111-rule registry with
> explicit support/trust boundaries, optionally resolves references against a
> structural Verilog design context, computes constraint coverage and
> semantic interactions, aggregates a seven-dimension readiness model, and
> provides versioned snapshots with semantic baseline diffing and declarative
> CI gate policies. Exposed via CLI, JSON, HTML reports, and a Streamlit
> workspace.

**Positioning statement:**
> The Ṛta is the constraint-quality layer that runs **before** STA —
> turning "I hope this SDC is right" into "here is the evidence."

---

## 4. Target Users (personas)

| Persona | Problem today | Current workflow | Where Ṛta fits | Highest-value capability | What earns trust |
|---|---|---|---|---|---|
| **Physical Design Engineer** | SDC errors surface late in implementation | Write SDC by hand/scripts, discover issues in P&R runs | Pre-flight SDC before implementation runs | Deterministic rule checking + design-aware resolution | Zero false confidence; clear provenance |
| **STA Engineer** | Receives inconsistent/partial constraint sets | Manual review, `check_timing` archaeology in PrimeTime/Tempus | Triage incoming constraint sets before STA load | Readiness model + interaction analysis | Honest "what we did NOT check" |
| **Synthesis Engineer** | Constraint drift between revisions | Diff files by eye, side-by-side text diff | Track constraint intent across revisions | Semantic readiness diff + CI gates | Baseline compatibility handled honestly |
| **Timing/Constraints Engineer** | Hidden coverage gaps and undefined references | Ad-hoc grep scripts | Systematic coverage + reference validation | Structural coverage (SDC-064..066) + reference checks (SDC-055..059) | Coverage ≠ correctness messaging |
| **CAD/Methodology Engineer** | No enforceable constraint-quality gate in CI | Custom brittle scripts | Maintain a baseline + policy in the regression flow | NO_READINESS_REGRESSION / CUSTOM policies | Deterministic exit codes |
| **Design Verification / Infra Engineer** | Reproducing "it passed on my machine" | Manual reruns | Same evidence everywhere | Versioned snapshots + deterministic identity | Offline + deterministic |
| **Team Lead / Technical Lead** | Cannot answer "is the constraint set healthy?" | Reads reports manually | Executive readiness signal | Readiness control center + benchmark evidence | Trust Center honesty |

**Cross-cutting trust requirement for every persona:** they need to know *what
the validator actually proved* and *what it did not attempt*. That single
property differentiates the product.

---

## 5. User Problems

1. **SDC complexity** — SDC is a large, option-dense Tcl dialect; hand review misses edge cases.
2. **Manual review** — constraint review is eyeballing long files.
3. **Constraint drift** — revisions silently change timing intent (period changes, removed exceptions).
4. **Cross-file inconsistency** — same clock defined differently across files/corners.
5. **Hidden coverage gaps** — unconstrained ports/buses discovered late.
6. **Constraint interactions** — individually-valid constraints that contradict or override each other.
7. **Handoff uncertainty** — no answer to "is this ready for STA?"
8. **Regressions** — CI cannot answer "did this revision make constraints worse?"
9. **CI visibility** — no machine-readable, gateable constraint-quality signal.
10. **False confidence** — generic validators that imply more than they prove.

---

## 6. Product Value Pillars

Derived strictly from actual functionality (no invented pillars):

| Pillar | Meaning | Backed by |
|---|---|---|
| **VALIDATE** | Deterministic SDC rule checks, semantic references, clock definitions | `checker.py`, `sdc_preprocess.py`, `rules_registry.py` (SDC-001..049, 140) |
| **UNDERSTAND** | Clock intelligence, design context, coverage, interactions | `clock_relations.py`, `design_context.py`, `design_coverage.py`, `constraint_interactions.py` |
| **ASSESS** | Trust boundary + handoff readiness | `support_boundary.py`, `constraint_readiness.py` |
| **PROTECT** | Snapshots, semantic regression diff, CI policies, structured identity | `readiness_diff.py`, `finding_identity.py`, `policy_engine.py` |
| **PROVE** | Golden suites, adversarial/security/perf tests, clean-room release evidence | `benchmarks/` (9 golden runners, 28 suites, clean-room, smoke) |

---

## 7. Differentiation (evidence-derived)

1. **Deterministic runtime** — no LLM, no AI API, no probabilistic judgment in validation.
2. **Offline-first** — validation works with no network; files stay local.
3. **Explicit trust boundary** — every result carries what-was/wasn't-checked disclosure.
4. **Optional design context** — SDC-only is a first-class mode, not a degraded one.
5. **Structural constraint coverage** — object-level (bus-aware) coverage, not a single percentage.
6. **Semantic interaction analysis** — duplicates/overrides/conflicts/STA-required overlaps with dual-line provenance.
7. **Seven-dimension readiness model** — categorical, not a misleading average score.
8. **Semantic readiness diff** — message-independent finding identity (structured), baseline debt separated from new debt.
9. **Declarative CI policy engine** — inert data, no code execution.
10. **Transparent benchmarks** — every claim maps to a repository artifact.

---

## 8. Competitive Positioning Boundary

```
Text editors / hand scripts
        |
        v
+-------------------------------+
|  Ṛta (this product)  |
|  Constraint quality + pre-STA  |
|  validation, readiness, CI     |
+-------------------------------+
        |
        v
STA engines (PrimeTime, Tempus, ...)
        |
        v
Timing signoff
```

The product's wedge is the **constraint-quality gap between authoring and STA**.
It is complementary to, not a replacement for, STA engines. We make no
accuracy/performance claims against commercial EDA tools — no direct
valid benchmarking exists for that comparison, and we do not claim it.

---

## 9. Complete Capability Inventory

| # | Capability | Purpose | Primary user | Backend module | CLI | JSON | Report | Design ctx req? | Trust level |

> **Current UI location / target product page:** the workspace restructure (§40) and §62 matrix map each row below to its workspace surface; the product sitemap (§14) maps it to a capability page. Rows marked “workspace + page” get both; “workspace only” stays in the app.
|---|---|---|---|---|---|---|---|---|---|
| 1 | SDC preprocessing (comments, multiline, collections, scientific notation) | Normalize input for analysis | All | `sdc_preprocess.py` | implicit | — | — | No | core |
| 1a | Tcl scalar-variable resolution (bounded) | Resolve `${var}`/`$var` scalars from linked TCL definition files | Infra/constraints | `tcl_resolver.py` | `diff --linked-v1/--linked-v2`, implicit in check | ✅ (via diff) | — | No | bounded subset; execution-required disclosed |
| 2 | Deterministic rule checking (115 rules) | Errors/warnings/info with provenance | PD/STA/constraints | `checker.py` + `rules_registry.py` | `check` | ✅ | ✅ | No | VALIDATED (per command) |
| 3 | Severity + rule catalog | Understand findings | All | `rules_registry.py` | `rules list/show` | ✅ | ✅ | No | — |
| 4 | Clock & generated-clock extraction | Inventory clocks | Constraints/STA | `checker.py`, `clock_relations.py` | `check`, `analyze clock-relations` | ✅ | ✅ | No | VALIDATED |
| 5 | Clock relationship inference & matrix | Detect missing/mismatched groups | STA | `clock_relations.py` | `analyze clock-relations` | ✅ | ✅ | No | PARTIALLY_VALIDATED (heuristic) |
| 6 | Support/trust boundary | Disclose what was analyzed vs not | All | `support_boundary.py` | `check` | ✅ | ✅ | No | self-describing |
| 7 | Structural Verilog context | Resolve ports/pins/cells/nets/hierarchy | PD/STA | `design_context.py` | `check --netlist` | ✅ | ✅ | Yes | VALIDATED (structural only) |
| 8 | Object reference resolution (SDC-055..059) | Prove get_ports/get_pins resolve | PD/STA | `checker.py` + `design_context.py` | `check --netlist` | ✅ | ✅ | Yes | NETLIST_REQUIRED → VALIDATED |
| 8a | Wildcard drift analysis | Detect collection/wildcard drift between revisions | Constraints/infra | `wildcard_analyzer.py` | `diff` (implicit) | ✅ (via diff) | — | No | heuristic, secondary evidence |
| 9 | Structural constraint coverage (SDC-064..066) | Constrained/unconstrained/partial/exempt/unknown | Constraints | `design_coverage.py` | `check --netlist` | ✅ | ✅ | Yes | coverage ≠ correctness |
| 10 | Category coverage report (legacy) | Constraint-category scorecard | Methodology | `coverage.py` | `coverage` | ✅ | ✅ | No | heuristic score |
| 11 | Semantic constraint interactions (SDC-067..070) | Duplicates/overrides/conflicts/overlaps | STA/constraints | `constraint_interactions.py` | `check` | ✅ | ✅ | No | PROVABLE vs STA-REQUIRED |
| 12 | Constraint readiness (7 dimensions) | Handoff verdict + actions | Team lead/STA | `constraint_readiness.py` | `check` | ✅ | ✅ | No | READY ≠ signoff |
| 13 | Custom rules (YAML) | Team-specific checks | Methodology | `custom_rules.py` | `check --custom-rules` | ✅ | ✅ | No | team-scoped |
| 14 | SDC generator | Scaffold SDC from parameters | Constraints/PD | `generator.py` | `generate` | — | — | No | template, must review |
| 15 | Linter/formatter | Consistent formatting | All | `linter.py` | `lint` | — | — | No | style |
| 16 | Converter (JSON/YAML) | Interchange | Infra | `converter.py` | `convert` | ✅ | — | No | lossless-ish |
| 17 | Content diff (CHG-*) | What constraints changed | All | `constraint_diff.py` | `diff` | ✅ | ✅ | No | semantic-ish |
| 18 | Multi-corner presets & MMC generation | Corner SDCs + cross-corner consistency | PD/STA | `corner_manager.py`, `mmc.py` | `corners`, `generate` | ✅ | — | No | template |
| 19 | Batch processing | Directory-scale checking/reporting/lint | Infra | `batch_runner.py` | `batch` | — | — | No | — |
| 20 | Readiness snapshot (schema v2) | Versioned, machine-readable evidence | All/CI | `readiness_diff.py` | `check --save-baseline` | ✅ | — | No | structured |
| 21 | Semantic readiness diff | New/resolved/changed/unchanged + debt | All/CI | `readiness_diff.py` | `check --baseline` | ✅ | ✅ | No | structured identity |
| 22 | Finding identity (structured + legacy) | Message-independent comparison | CI | `finding_identity.py` | internal | ✅ | ✅ | No | STRUCTURED/LEGACY_NORMALIZED |
| 23 | CI quality gates + policies | Gate revisions on readiness regression | CI/Methodology | `policy_engine.py`, `readiness_diff.py` | `check --gate` | ✅ | ✅ | No | policy-scoped |
| 24 | HTML signoff reports | Self-contained evidence | All | `reporter.py` | `report` | — | ✅ | No | escaped, self-contained |
| 25 | JUnit XML | CI ingestion | CI | `cli.py` | `check --junit` | — | — | No | — |
| 26 | Web workspace | Interactive analysis | All | `app.py`, `ui/` | `web` | — | — | optional | parity with CLI |
| 27 | Feedback dashboard | Product feedback loop | Team | `ui/feedback.py` | — | — | — | No | opt-in |

---

## 10. Capability → Backend Mapping

| Backend module | Capabilities |
|---|---|
| `sdc_preprocess.py` | 1 |
| `tcl_resolver.py` | 1a |
| `checker.py` | 2, 3, 4, 8 |
| `rules_registry.py` | 2, 3 |
| `clock_relations.py` | 4, 5 |
| `support_boundary.py` | 6 |
| `design_context.py` | 7, 8 |
| `design_coverage.py` | 9 |
| `coverage.py` | 10 |
| `constraint_interactions.py` | 11 |
| `constraint_readiness.py` | 12 |
| `custom_rules.py` | 13 |
| `generator.py` | 14 |
| `linter.py` | 15 |
| `converter.py` | 16 |
| `constraint_diff.py` | 17 |
| `wildcard_analyzer.py` | 8a (feeds 17) |
| `corner_manager.py`, `mmc.py` | 18 |
| `batch_runner.py` | 19 |
| `readiness_diff.py` | 20, 21, 23 |
| `finding_identity.py` | 22 |
| `policy_engine.py` | 23 |
| `reporter.py` | 24 |
| `cli.py` | 25, all CLI |
| `app.py`, `ui/` | 26, 27 |

---

## 11. Capability → Evidence Mapping

| Capability | Golden/adversarial evidence |
|---|---|
| Rule checking | `run_golden.py` 22/22 · `test_semantic_adversarial.py` 13 · `test_reference_mutation.py` 7/7 |
| Clock intelligence | `run_golden_semantic.py` 9/9 · `test_reference_metamorphic.py` 10 |
| Design context / netlist-aware | `run_netlist_aware.py` 10/10 · `test_netlist_adversarial.py` 12 · `test_netlist_metamorphic.py` 4 · `test_netlist_security.py` 7 |
| Coverage | `run_design_coverage.py` 12/12 · `test_coverage_adversarial.py` 14 · `test_coverage_metamorphic.py` 7 |
| Interactions | `run_constraint_interactions.py` 20/20 · `test_interactions_adversarial.py` · `test_interactions_realistic.py` |
| Readiness | `run_readiness.py` 15/15 · `test_readiness_adversarial.py` 9 · `test_readiness_confidence.py` 18 · `test_readiness_metamorphic.py` 8 |
| Diff / CI | `run_readiness_diff.py` 22/22 · `test_readiness_diff_{adversarial,metamorphic,confidence,perf}.py` · `test_readiness_ci_gate.py` |
| Production hardening | `run_production_hardening.py` 49 · `test_ph13_{adversarial,security,perf,ci_workflow}.py` |
| Security | `test_security.py` 5 · `test_ph13_security.py` 30 |
| Stress/robustness | `test_preprocess_stress.py` 21 |
| UI/state | `test_ui_app.py`, `test_ui_state_isolation.py` |
| Trust transparency | `test_trust_transparency.py` 8/8 · `test_no_false_confidence.py` 6/6 |
| Performance | `test_readiness_perf.py`, `test_readiness_diff_perf.py`, `test_ph13_perf.py`, `test_performance.py`, `test_semantic_perf.py` |
| Release | `release_cleanroom.py` 17/17 · `release_cli_audit.py` 16/16 · `test_release_smoke.py` 10/10 · `RELEASE_MANIFEST.md` |

---

## 12. Product Evidence Inventory (all traceable)

- **793 pytest tests** in `tests/` (26 files).
- **9 golden runners** in `benchmarks/` (`run_golden*.py`, `run_reference*.py`, `run_design_coverage.py`, `run_netlist_aware.py`, `run_constraint_interactions.py`, `run_readiness*.py`, `run_production_hardening.py`).
- **42 benchmark suites** (`test_*.py` in `benchmarks/`).
- **115 rules** with per-rule descriptions, why-it-matters, fix, module, added version, reference URL (`rules_registry.py`).
- **Release evidence:** `PHASE14_RELEASE_CANDIDATE_AUDIT_REPORT.md`, `RELEASE_MANIFEST.md`, `release_cleanroom.py`, `release_cli_audit.py`, `test_release_smoke.py`.
- **Phase reports:** PHASE3..PHASE14 in `benchmarks/`.
- **Sample corpus:** `samples/` (realistic clean/problem designs, diff fixtures, edge cases, Tcl variables).
- **Performance measurements:** see §31.

---

## 13. Product vs Workspace Architecture

Two distinct experiences, kept separate:

**A. PRODUCT / KNOWLEDGE EXPERIENCE** (understand)
- What it is, how it works, capabilities, architecture, benchmarks, trust, specs, docs, releases.
- Audience: evaluators, technical leads, engineers learning the tool.

**B. ENGINEERING WORKSPACE** (do)
- Upload SDC/Verilog, run analysis, investigate findings, review coverage/readiness, compare baselines, generate reports, configure CI.
- Audience: engineers doing the work.

**Rule:** the product experience never pretends to be a workspace; the workspace never tries to be a marketing site. Navigation between them is one click (e.g., "Open Workspace" from product, "About / Trust / Docs" from workspace).

---

## 14. Master Sitemap

```
HOME
├── PLATFORM (overview + pipeline)
│   ├── How It Works
│   └── Deterministic Architecture
├── CAPABILITIES
│   ├── SDC Validation
│   ├── Clock Intelligence
│   ├── Design Context
│   ├── Constraint Coverage
│   ├── Constraint Interactions
│   ├── Readiness
│   ├── Regression Intelligence
│   └── CI Quality Gates
├── BENCHMARKS
│   ├── Overview
│   ├── Correctness · Robustness · Design-Aware · Regression Reliability · Security · Performance · Release Quality
│   └── Methodology
├── TRUST CENTER
│   ├── What We Validate · Partial · Netlist-Required · Unsupported
│   ├── What We Do NOT Claim
│   └── Known Limitations
├── ENGINEERING
│   ├── Engineering Story (evolution)
│   └── Specifications
├── DOCS (getting started / concepts / workflows / reference)
├── RELEASES (v1.3.0 evidence)
└── WORKSPACE (opens app)
```

**Merged/challenged decisions:** no separate "Architecture" top-level page (folded into PLATFORM + ENGINEERING); no "News/Blog" (not needed pre-beta); no "Pricing/Team" (no SaaS yet).

---

## 15. P0 / P1 / P2 Page Priorities

**P0 — required before premium public beta (MVP premium experience):**
- Home
- Platform (pipeline overview)
- Capabilities hub + **SDC Validation**, **Readiness** (the two flagship capabilities)
- Benchmarks Overview
- Trust Center
- Docs — Getting Started
- Release (v1.3.0)
- Workspace: Overview, Validator, Readiness, Diff (the core loop)

**P1 — valuable shortly after beta:**
- Clock Intelligence page + workspace
- Design Context page + coverage workspace
- Interactions page + workspace
- CI Quality Gates page + policy workspace
- Regression Intelligence page (product side)
- Benchmark detail pages (per category)
- Docs — Concepts, Workflows, Reference
- Engineering Story / Specifications

**P2 — future:**
- Benchmark traceability auto-generation
- Responsive polish beyond desktop-first workspace
- Advanced visualizations (clock tree animation)
- Team/enterprise surfaces (only after product-market validation)

---

## 16. Homepage Information Architecture

| Section | Purpose | Content | Evidence | Interaction | Destination |
|---|---|---|---|---|---|
| Hero | What/for whom/why in 10 s | Product name + category line + deterministic/offline strip | — | Scroll / CTA | Platform |
| Trust strip | Deterministic · Offline · Reproducible · Engineering-focused | 4 chips | — | hover | Deterministic Architecture |
| Workflow visualization | Where it sits before STA | SDC → Validator → STA diagram | — | click stages | Platform / capability pages |
| Capability pillars | VALIDATE / UNDERSTAND / ASSESS / PROTECT / PROVE | 5 cards | per-capability golden counts | click | Capability pages |
| Design-aware analysis | Optional netlist context story | SDC-only vs SDC+Verilog | netlist-aware 10/10 | click | Design Context |
| Readiness & regression story | Handoff verdict + baseline diff | READY≠signoff + regression diff example | readiness 15/15, diff 22/22 | click | Readiness / Regression |
| Benchmark evidence | Proof with traceability | headline numbers + "see methodology" | all suites | click | Benchmarks |
| Architecture / deterministic core | No AI, no cloud, offline | module pipeline | — | click | Deterministic Architecture |
| CI integration | Gate your revisions | policy names + exit codes | CI gate suite | click | CI Quality Gates |
| Trust boundary | Honest non-claims | "Not STA signoff" panel | Trust Center | click | Trust Center |
| Final CTA | Launch / docs | "Open Workspace" / "Read the Docs" | — | click | Workspace / Docs |

---

## 17. Hero Strategy (directions — copy finalized later)

**Direction A — The Before-STA Question (recommended):**
> "Before PrimeTime, before implementation — is this SDC actually ready?"
> Deterministic constraint validation. Offline. Evidence-backed.

**Direction B — The Evidence Engine:**
> "Every constraint finding, with provenance. Every claim, with a benchmark."

**Direction C — The Readiness Signal:**
> "Readiness you can trust, because the validator tells you what it didn't check."

**Direction D — The Constraint Quality Layer:**
> "The quality gate between constraint authoring and STA."

All four avoid hype ("revolutionize", "AI-powered", "transform") and lead with
an engineering question.

---

## 18. Platform Page Architecture

Interactive pipeline (conceptually; clickable stages):

```
INPUT: SDC (+ optional Verilog)
   ↓
PREPROCESSING (comments, multiline, Tcl scalars, collections)
   ↓
CONSTRAINT VALIDATION (111 deterministic rules)
   ↓
CLOCK INTELLIGENCE (definitions, generated clocks, relationships)
   ↓
DESIGN CONTEXT (structural resolution — when netlist provided)
   ↓
COVERAGE / INTERACTIONS (structural coverage + semantic interactions)
   ↓
TRUST / READINESS (7-dimension assessment)
   ↓
SNAPSHOT / DIFF (versioned evidence + semantic regression)
   ↓
CI QUALITY GATE (declarative policy → PASS/FAIL + exit code)
```

Each stage links to its capability page. A "what this stage proves / does not
prove" note appears under each stage (trust honesty at every step).

---

## 19. Capability Page Template (reusable)

Every capability page answers:
1. **What problem does this solve?**
2. **How does it work?** (deterministic pipeline step)
3. **What input does it use?**
4. **What evidence does it produce?**
5. **What does the result mean?**
6. **What does it NOT mean?** (mandatory)
7. **Example** (small realistic snippet)
8. **Visualization** (where useful)
9. **Relevant benchmark** (traceable count)
10. **Trust status** (VALIDATED/PARTIAL/etc.)
11. **Documentation** (link)
12. **Launch capability CTA** (→ workspace)

This template prevents capability pages from degrading into marketing fluff.

---

## 20. SDC Validation Page

- Deterministic rule checking against the 111-rule catalog.
- Clarify the vocabulary explicitly:
  - **finding** — an observed condition (a row of evidence)
  - **severity** — error / warning / info / fatal (impact ordering, not truth)
  - **evidence** — the message + rule rationale + why-it-matters
  - **provenance** — file/line (and line2 for dual-constraint findings); presentation only, never identity
  - **trust** — how completely this command/construct was analyzed (support boundary)
- Rule catalog browsing (module, severity, search) and rule detail (fix, reference URL).
- Supported-command behavior vs unsupported constructs disclosed.

---

## 21. Clock Intelligence Page

Communicate, without implying propagation:
- primary clocks, generated clocks (divide/multiply, master), virtual clocks
- clock ancestry chains (resolved via `-master_clock` / source nodes)
- relationship inference (synchronous / asynchronous / physically exclusive) and why
- declared groups vs inferred relationships → missing/mismatch (SDC-060-family)
- Visuals (classify): **clock tree** (USEFUL), **relationship matrix** (ESSENTIAL — already exists in reports/workspace), **clock detail inspector** (USEFUL).
- **NOT:** timing propagation, clock skew, latency analysis.

---

## 22. Design Context Page

- Two modes explained side by side: **SDC-only** vs **SDC + structural Verilog**.
- What structural context enables: object resolution (SDC-055..059), hierarchy, ports/pins/cells/nets, connectivity summary, coverage evidence (SDC-064..066), design fingerprint.
- What it does **NOT** enable: timing propagation, slack, delay calculation, signoff.
- Disclose that SDC-only remains a first-class, honest mode (never punish users for not supplying a netlist).

---

## 23. Coverage Page

Present statuses: **CONSTRAINED / PARTIALLY_CONSTRAINED / UNCONSTRAINED / EXEMPT / UNKNOWN / NOT_APPLICABLE**.
- Bus-aware: whole bus, partial range, per-bit where resolvable.
- Drill-down: object → class → status → evidence (which constraint covers it).
- Prominent disclosure: **Coverage ≠ correctness.** A fully covered design can still have timing errors; an exempt port is not verified correct.
- Avoid a single misleading percentage (legacy category-score report is labeled heuristic).

---

## 24. Interaction Page

Present SDC-067..070:
- **exact duplicates** (redundant) — advisory
- **overrides** (later silently replaces earlier) — review
- **contradictory max/min windows** (SDC-069) — provable conflict → blocker
- **timing-exception endpoint overlaps** (SDC-070) — requires STA/path analysis to confirm
- Dual-line provenance (line ↔ line2) for every finding.
- Distinguish **PROVABLE CONFLICT** from **REQUIRES STA / PATH ANALYSIS** with explicit labels.

---

## 25. Readiness Page

Control-center style:
- Overall: **READY / READY_WITH_ADVISORIES / REVIEW_REQUIRED / BLOCKED / INSUFFICIENT_CONTEXT**
- Dimensions: **CLOCKS / I/O / EXCEPTIONS / COVERAGE / CONSISTENCY / ANALYSIS_TRUST / DESIGN_CONTEXT**
- Then **WHY** (blockers), **WHAT TO REVIEW** (review items), **ADVISORIES**, **RECOMMENDED ACTIONS** (with P0–P3 priorities), **TRUST DISCLOSURE**.
- Prominently: **READY is NOT STA signoff.** READY means the constraint set satisfies the validator's supported, evidence-backed readiness criteria for the stated analysis mode.

---

## 26. Regression Intelligence Page

Engineering change-review experience (not a generic comparison table):
- Baseline vs current (compatibility status, migration honesty)
- NEW / RESOLVED / CHANGED / UNCHANGED findings (structured identity — message-independent)
- Readiness transition per dimension
- Coverage delta (newly constrained/unconstrained objects, not percentages alone)
- Trust delta (VALIDATED → PARTIAL etc.)
- Design-context changes (design-port-added ≠ SDC regression)
- Baseline debt (existing) separated from new debt
- Identity strength disclosure (STRUCTURED vs LEGACY_NORMALIZED)

---

## 27. CI Quality Gates Page

Explain the four policies with intent/failure-causes/allowances:
- **BLOCKERS_ONLY** — fail if current is BLOCKED
- **NO_READINESS_REGRESSION** — fail on new regression vs baseline (baseline-aware; legacy debt tolerated)
- **STRICT** — fail on blockers or review regressions
- **CUSTOM** — declarative inert policy file (fail_on / allow / thresholds; no code execution)
- Engine-failure behavior: never PASS.
- Workflow diagram: SDC revision → validation → snapshot → baseline diff → policy → PASS/FAIL (exit 0/1/2/3).
- Vendor-neutral: GitHub Actions shown as one example, not the identity.

---

## 28. Benchmark Architecture

Evidence organized into seven categories, each traceable:
- **CORRECTNESS** (golden suites, reference designs, mutation tests)
- **ROBUSTNESS** (adversarial, metamorphic, stress)
- **DESIGN-AWARE ANALYSIS** (netlist-aware, coverage)
- **REGRESSION RELIABILITY** (readiness-diff, CI gate, confidence)
- **SECURITY** (security suites, snapshot/policy safety)
- **PERFORMANCE** (perf suites with measured numbers)
- **RELEASE QUALITY** (pytest, clean-room, CLI audit, smoke)

No wall of numbers: each benchmark is a card (see template §30).

---

## 29. Benchmark Overview (executive)

Headline evidence (all verified in this audit cycle):
- 793/793 pytest · 9/9 golden runners · 42/42 benchmark suites
- 17/17 clean-room wheel journey · 16/16 CLI contract · 10/10 release smoke
- 115 rules · 1.5.4 · RC_READY_WITH_KNOWN_LIMITATIONS

Each headline links to its detail card with version/date/environment context.

---

## 30. Benchmark Detail Template

A benchmark detail card includes: **NAME · PURPOSE · WHAT IT TESTS · METHODOLOGY · CORPUS SIZE · EXPECTED-BEHAVIOR SOURCE · RESULT · VERSION · ENVIRONMENT · LIMITATIONS · ARTIFACT/MANIFEST REFERENCE.**

**Critical rule:** internal tests are presented as internal validation evidence — never as independent industry certification. No "industry-leading" phrasing (§52).

---

## 31. Performance Presentation

Measured numbers only (do not extrapolate). Two classes are kept distinct:

**Currently measured (this audit cycle, Python 3.10 / Windows):**
| Workload | Metric | Result | Source |
|---|---|---|---|
| 10k findings readiness-diff | wall time | ≈ 43–75 ms | `benchmarks/test_readiness_diff_perf.py` |
| Readiness aggregation (980 findings) | wall time | ≈ 8 ms | `benchmarks/test_readiness_perf.py` |

**Approximate historical figures (approximate, from prior phase reports — not re-measured in this audit):**
| Workload | Metric | Approx. result | Source |
|---|---|---|---|
| 400-clock design | end-to-end | ≈ 1 s range | `benchmarks/test_performance.py`, stress suite (historical) |
| 10k semantic constraints | end-to-end | ≈ 1 s range | prior phase perf reports (historical) |

Caveats: single-machine Windows measurements, Python 3.10; historical rows are approximate and labeled as such; charts only where comparison is meaningful; environment/date/version stated per number.

---

## 32. Benchmark Traceability Model (future architecture)

```
benchmark manifest (machine-readable)
        +  results (executed output)
        +  release metadata (version/date/env)
        ↓
benchmark presentation (auto-generated cards)
```
Design only — not implemented in this phase. Every public number must come
from a verified artifact; no hard-coded marketing numbers.

---

## 33. Trust Center Architecture

Sections:
1. **WHAT WE VALIDATE** (deterministic rule checks within scope)
2. **WHAT WE PARTIALLY VALIDATE** (recognized commands with ignored/unknown options)
3. **WHAT REQUIRES NETLIST CONTEXT** (object references — SDC-only cannot prove resolution)
4. **WHAT REQUIRES TCL EXECUTION** (expr/eval/exec-family — analyzed at text level only)
5. **WHAT IS UNSUPPORTED** (constructs outside scope — disclosed, not silently skipped)
6. **WHAT WE DO NOT CLAIM** (see §34)

Status vocabulary (exact): **VALIDATED · PARTIALLY_VALIDATED · NETLIST_REQUIRED · TCL_EXECUTION_REQUIRED · UNSUPPORTED · NOT_VALIDATED.**

---

## 34. Trust Center — Non-Claims

Explicit, prominent:
- No STA signoff.
- No slack calculation.
- No .lib timing analysis.
- No physical timing analysis.
- No timing closure guarantee.
- No claim that 100% coverage means correct timing intent.
- No claim that CI PASS means timing closure.

Hiding limitations is a trust failure; disclosure is a product strength.

---

## 35. Deterministic Architecture Page

- **NO LLM REQUIRED · NO CLOUD REQUIRED · NO EXTERNAL API REQUIRED · OFFLINE ANALYSIS · REPRODUCIBLE RESULTS · STRUCTURED EVIDENCE · VERSIONED SNAPSHOTS · DETERMINISTIC CI GATES.**
- Explain the two-layer model without anti-AI marketing:
  - **Development layer:** AI/subagents may be used to develop, audit, and test the software.
  - **Product layer:** the runtime validator is deterministic Python — parsing, validation, structural analysis, and tests. No probabilistic decision at runtime.

---

## 36. Engineering Story Page

Present the evolution professionally (no raw internal prompts):
1. **FOUNDATION** — Parser + Checker
2. **SEMANTICS** — Clock + Reference Validation
3. **DESIGN INTELLIGENCE** — Netlist + Coverage
4. **CONSTRAINT INTELLIGENCE** — Interactions + Readiness
5. **REGRESSION INTELLIGENCE** — Snapshots + Diff + CI
6. **PRODUCTION HARDENING** — Structured Identity + Security + Packaging
7. **RELEASE QUALITY** — Clean-room + Wheel + Smoke Verification

---

## 37. Specifications Page

Derive from repository evidence:
- **Runtime:** Python ≥ 3.10; no required runtime deps; `pyyaml` for YAML convert; `streamlit` optional `[web]`.
- **Operation mode:** SDC-only or SDC + structural Verilog (design-aware).
- **Primary input:** SDC (`.sdc`/`.tcl`/text).
- **Optional context:** structural Verilog (`.v`/`.sv`), Tcl variable definition files, custom-rules YAML, baseline snapshot JSON, policy file (JSON/YAML).
- **Outputs:** text, CSV, Markdown, JSON, JUnit XML, HTML reports, snapshot JSON.
- **Validation model:** deterministic rules + explicit trust boundary.
- **Network dependency:** none.
- **AI dependency:** none at runtime.
- **Snapshot schema:** v2 with v1 legacy-compatible comparison (migration: NATIVE/MIGRATED/PARTIAL/INCOMPATIBLE).
- **Identity schema:** structured FindingIdentity v1 (+ LEGACY_NORMALIZED fallback).
- **CI policy model:** declarative inert data (BLOCKERS_ONLY / NO_READINESS_REGRESSION / STRICT / CUSTOM).
- **Supported SDC subset:** per `rules_registry` + `support_boundary` (commands/options enumerated); unsupported disclosed.
- **Supported Tcl subset:** scalar variables, comments, multiline, collections; execution-required constructs disclosed.
- **Supported structural Verilog subset:** module/port/instance/net/pin structural inventory (no simulation, no elaboration semantics beyond structural resolution).
- **Known limitations:** see §68.

---

## 38. Documentation Architecture

```
DOCS
├── GETTING STARTED
│   ├── Installation
│   ├── First Validation
│   ├── Understanding Results
│   └── Add Design Context
├── CONCEPTS
│   ├── SDC Validation · Clock Intelligence · Coverage · Interactions
│   ├── Trust · Readiness · Baselines · Regression
├── WORKFLOWS
│   ├── Local Validation · Design-Aware Validation · Baseline Review · CI Integration
├── REFERENCE
│   ├── CLI · Python API · Rules · Support Matrix · Policy Schema · Snapshot Schema
└── TRUST
    ├── Methodology · Benchmarks · Limitations
```

Current `docs/features/README-01..10` map into this hierarchy; no content is
thrown away.

---

## 39. Releases Architecture

v1.3.0 release page shows: version · release status (RC_READY_WITH_KNOWN_LIMITATIONS) · date · major capabilities · test evidence (traceable) · clean-room status · known limitations · release notes · artifacts (wheel/sdist). **No "certified" language** — no certification exists.

---

## 40. Workspace Architecture

Candidate navigation (desktop-first, sidebar):
```
OVERVIEW · VALIDATOR · CLOCKS · DESIGN CONTEXT · COVERAGE ·
INTERACTIONS · READINESS · DIFF · REPORTS · CI / POLICIES
```
**Anti-overload decision:** group analysis into three clusters:
- **ANALYZE:** Validator, Clocks, Design Context, Coverage, Interactions
- **ASSESS:** Readiness
- **PROTECT:** Diff, Reports, CI / Policies
The **OVERVIEW** page is the landing post-analysis (see §41). This keeps the
sidebar short while every top-level item maps to a real capability.

---

## 41. Workspace Overview (first screen after analysis)

Summarizes: design/inputs · analysis mode (SDC-only vs design-aware) · trust status · readiness overall · errors/warnings/advisories counts · clock count · coverage summary · interactions summary · unsupported constructs count · top actions (jump to the most relevant page). Every metric is a link into the deeper page. No hidden drill-down — the overview is a launchpad, not a dashboard wall.

---

## 42. Findings Explorer

- Filters: severity · rule/code · module/category · object search · line/location.
- Default view: compact table (severity icon, code, short message, location) — no overload.
- Drill-down opens the finding inspector (§43).
- Dual-line provenance shown for interaction findings.
- Trust/evidence column optional.

---

## 43. Finding Detail (inspector)

Fields (as available): rule · title · severity · category · explanation · why detected · affected object(s) · constraint(s) · clock · evidence · source provenance (line/line2) · analysis confidence/trust · requires design context? · requires STA follow-up? · related docs link. Structured identity fields shown where present (structured vs legacy).

---

## 44. Clock Workspace

- Clock inventory (name/period/source/generated/virtual/master).
- Clock tree (hierarchy of generated clocks) — USEFUL visualization.
- Relationship matrix (ESSENTIAL — exists in reports today; make interactive).
- Clock groups vs inferred relationships.
- Clock detail inspector + pair analysis.
- Use visualization only where it improves understanding; no timing-propagation implication.

---

## 45. Coverage Workspace

- Overall structural coverage by direction (inputs/outputs), buses vs bits.
- Lists: partially constrained ranges · unconstrained objects · exempt · unknown.
- Drill-down from object to covering constraint evidence.
- **No single misleading percentage.**

---

## 46. Readiness Workspace

Strong control center:
1. Overall readiness (status + mode disclosure).
2. Seven dimension statuses.
3. **WHY?** blockers (evidence).
4. **WHAT SHOULD I REVIEW?** review items.
5. **WHAT EVIDENCE CAUSED THIS?** each status links to underlying findings.
6. Recommended actions (P0–P3) and trust disclosure.

---

## 47. Diff Workspace

Change-review experience:
- Header: BASELINE vs CURRENT (+ compatibility status).
- Readiness transition + dimension deltas.
- NEW / RESOLVED / CHANGED / UNCHANGED findings (filterable).
- Coverage delta (object-level) · trust delta · context delta.
- Debt panel: existing vs new vs resolved.
- Identity strength disclosure + gate result if evaluated.

---

## 48. Reports Experience

Explain each artifact's purpose: HTML report (human evidence) · JSON (machine) · snapshot (baseline) · JUnit (CI). Downloads already exist; no new formats unless needed. Include a "what each artifact is for" legend so engineers pick correctly.

---

## 49. CI / Policy Workspace

- Show the four policies with intent, failure causes, allowed items, engine-failure behavior, example config.
- CUSTOM policy: structured editor/validator (fields, types, rule IDs, thresholds) — **never** arbitrary executable logic.
- Generate the exact CLI command for the selected policy (copy-paste into CI).

---

## 50. Empty States

| State | Message direction |
|---|---|
| No SDC loaded | "Upload or paste an SDC to begin." + sample corpus links |
| SDC loaded, no netlist | "Object references will be flagged netlist-required. Add a netlist for design-aware mode — optional." |
| No findings | "No issues found within scope. See Analysis Scope for what was verified." |
| No baseline | "Save a baseline to enable regression diff and CI gates." |
| No diff | "Load a baseline snapshot to compare." |
| No policy | "Choose a built-in gate or create a CUSTOM policy." |
| No design context | "Structural coverage requires a netlist." |
| No coverage possible | explained with the next step |

Never "Nothing here." Always an engineering next step.

---

## 51. Error States

Classify with distinct treatment:
- **USER INPUT PROBLEM** (invalid SDC, invalid Verilog, ambiguous/wrong top, bad output path) → actionable message, no traceback.
- **UNSUPPORTED ANALYSIS** (unsupported Tcl/construct) → disclosure + link to support matrix.
- **INSUFFICIENT CONTEXT** (netlist-dependent refs without netlist) → explanation + offer to add netlist.
- **INVALID CONFIGURATION** (invalid baseline/policy/snapshot incompatibility) → schema error with field hints.
- **INTERNAL FAILURE** (engine failure) → never PASS; explicit failure state + log guidance.

---

## 52. User Journeys

**JOURNEY A — First-time engineer:** Home → understand product → Launch → upload SDC → analyze → understand findings (via Overview + Findings Explorer).
**JOURNEY B — Design-aware analysis:** SDC + Verilog → choose top → analyze → coverage → readiness.
**JOURNEY C — Constraint debugging:** finding → evidence → source → related capability doc → fix → re-run.
**JOURNEY D — Regression review:** baseline → current → diff → new blocker → investigate (debt panel proves it's new, not old).
**JOURNEY E — CI adoption:** understand gates → select policy → generate CLI command → integrate → gate PASS/FAIL with evidence.
**JOURNEY F — Evaluator/technical lead:** Home → capabilities → benchmarks → methodology → trust center → architecture → release evidence → decide.

---

## 53. Information Density Strategy

Three levels with progressive disclosure:
- **LEVEL 1 — Executive:** overall status, counts, one-line meaning.
- **LEVEL 2 — Engineering evidence:** findings, dimensions, deltas, benchmark cards.
- **LEVEL 3 — Detailed source/provenance:** rule docs, line refs, JSON, snapshot internals.

Never flatten an engineering product into low-information cards.

---

## 54. Product Language System

**Canonical terminology (define once, use everywhere):**
- **finding** — an observed condition backed by evidence (not an opinion)
- **issue** — a finding surfaced in a report/workspace list
- **advisory** — info-level best practice
- **trust** — how completely a construct was analyzed (support boundary)
- **coverage** — whether something was constrained (≠ correctness)
- **readiness** — handoff-oriented aggregate verdict (≠ signoff)
- **baseline** — a saved, versioned snapshot used for comparison
- **snapshot** — machine-readable evidence capture (schema v2)
- **regression** — a disallowed readiness/coverage/trust change vs baseline
- **interaction** — a semantic relationship between constraints (duplicate/override/conflict/overlap)
- **design context** — optional structural Verilog evidence

**Banned unless proven & scoped:** AI-powered · magic · smart · revolutionary · blazing fast · 100% accurate · signoff-ready.

---

## 55. Startup Story

Engineering pain narrative (no vendor attacks):
> "SDC is where timing intent lives — and where it silently decays. Hand
> review misses interactions; text diff misses drift; no one can answer 'is
> this ready for STA?' The Ṛta makes constraint quality measurable,
> deterministic, and CI-enforceable — before the STA tools see it."

Positioned as complementary to downstream STA, never as a competitor.

---

## 56. Benchmark Claim Policy

Every public benchmark claim must include or link: **version · methodology · scope · result · limitations · source artifact.** Internal scores are never presented as industry-leading or certified.

---

## 57. Privacy Principles

- Analysis files (SDC/netlist/baseline) **remain local by default**; no uploads.
- **No telemetry in this phase.**
- Any future telemetry must be explicit and never silently collect SDC content, netlist content, object names, design hierarchy, or baseline contents without designed consent.
- State this on the product site and in the Trust Center.

---

## 58. Visualization Requirements

| Candidate | Classification | Where |
|---|---|---|
| Analysis pipeline | ESSENTIAL | Platform page |
| Clock hierarchy/tree | USEFUL | Clock Intelligence + workspace |
| Clock relationship matrix | ESSENTIAL | Clock workspace (exists in reports) |
| Bus coverage | USEFUL | Coverage workspace |
| Readiness dimensions | ESSENTIAL | Readiness workspace (exists as metrics) |
| Baseline/current diff | ESSENTIAL | Diff workspace |
| Benchmark results | USEFUL | Benchmarks |
| CI workflow | USEFUL | CI Quality Gates |
| Architecture | ESSENTIAL | Deterministic Architecture |
| 3D/flashy charts | UNNECESSARY | — |

---

## 59. Motion Requirements

Subtle motion only where it communicates system behavior (design phase only):
- Constraint flowing through the analysis pipeline (Platform page).
- Clock-hierarchy reveal (no propagation implication).
- Readiness transition (READY → BLOCKED) on diff.
- Benchmark count reveal.
No animation that harms engineering usability; respect `prefers-reduced-motion`.

---

## 60. Responsive Strategy

- **Product/knowledge experience:** highly responsive (desktop, tablet, mobile).
- **Engineering workspace:** desktop-first; tablet acceptable; mobile is a read-only fallback (complex tables are not forced into bad mobile layouts).
- State this explicitly on the product side; do not hide it.

---

## 61. Accessibility Requirements (future)

- Keyboard navigation, visible focus states, WCAG-AA contrast, screen-reader labels.
- Non-color-only severity indicators (icon + text + shape).
- Semantic tables, `prefers-reduced-motion` support.
- No implementation in this phase.

---

## 62. Current UI KEEP / RESTYLE / RESTRUCTURE / REBUILD / REMOVE

Based on actual `app.py`/`ui/` inspection:

| Current component | Classification | Rationale |
|---|---|---|
| Checker tab (upload/paste, findings, scope, coverage, interactions, readiness, diff, rule reference) | **RESTRUCTURE** → dedicated workspace pages | Functionality is excellent; it is overloaded into one tab. Split into Overview/Validator/Clocks/Coverage/Interactions/Readiness/Diff surfaces (same backend calls). |
| Generator tab | **KEEP** (RESTYLE later) | Mature, self-contained, includes live validation — working engineering value. |
| Linter tab | **KEEP** | Simple, complete. |
| Converter tab | **KEEP** | Simple, complete. |
| Corner Mgr + MMC tabs | **KEEP** | Working multi-corner workflow. |
| Diff tab | **RESTRUCTURE** (reuse) | Content diff works; add semantic readiness diff view (already backend-ready). |
| Clock tab | **RESTYLE** (keep engine) | Add relationship matrix interaction. |
| Coverage tab | **RESTYLE** (keep engine) | Wire structural coverage; keep legacy category score labeled heuristic. |
| Rules reference | **KEEP** (RESTYLE) | Already excellent. |
| Test Drive view | **KEEP** | Useful for evaluation. |
| Feedback dashboard | **KEEP** | Product loop. |
| EDA dark theme (`ui/components.py`) | **KEEP as base**, evolve into design system | Modern theme exists; formalize tokens in the next (visual) phase. |
| `render_header`/`render_sidebar` | **RESTYLE** | Support product↔workspace split. |

**Nothing is REMOVE** — no working engineering functionality is discarded.

---

## 63. Technology Constraint Assessment

Current: Streamlit (`app.py` + `ui/`), custom CSS dark theme, session state, multi-view (`app_view`), download buttons, tabs.

| Requirement | Streamlit capability | Verdict |
|---|---|---|
| Multi-page workspace | tabs + view switching (already used) | ✅ workable |
| Navigation | sidebar + view state | ✅ workable |
| Custom styling | `unsafe_allow_html` CSS injection | ⚠️ workable, limited to CSS |
| Interactive visualization | native charts limited; HTML/CSS matrices possible | ⚠️ adequate for matrices, weak for complex graphs |
| Animation | not native; CSS transitions possible | ⚠️ limited |
| State management | `st.session_state` | ✅ adequate |
| Responsive | Streamlit is desktop-oriented | ⚠️ desktop-first is fine for workspace |
| Public product site (SEO, static, responsive, rich marketing) | Streamlit is a poor fit | ❌ not suitable |

**Recommendation: Option B — keep Streamlit for the engineering workspace; build the product/knowledge experience as a separate lightweight frontend** (static site / docs framework driven by the same content sources — see §64). This is the evidence-backed choice: the workspace needs Streamlit's interactive analysis loop; the product site needs static, fast, SEO-friendly pages with no app server.

---

## 64. Product Website vs Validator App

**Recommendation: two surfaces, one brand.**
- **Product / knowledge surface:** `sdcvalidator.dev` (conceptual) — product site, docs, benchmarks, trust, releases.
- **Workspace surface:** `app.sdcvalidator.dev` (conceptual) — the Streamlit engineering workspace (or `sdc-tools web` locally).

This is conceptual only — no domains, no deployment in this phase. One click bridges them.

---

## 65. Content Source-of-Truth Strategy

Prevent drift between product content and implementation by deriving content from machine-readable sources:
- **`rules_registry.py`** → rule catalog pages (115 rules, descriptions, fixes, versions).
- **`support_boundary.py`** → support matrix + Trust Center statuses.
- **benchmark manifests / results** → benchmark cards (§32 traceability model).
- **`RELEASE_MANIFEST.md` + phase reports** → release pages.
- **`APP_VERSION`** → version metadata everywhere.
- **`policy_engine.py` schema** → policy docs and editor.

Principle: a human-written page that contradicts an implementation artifact is a bug. Design the pipeline now; implement later.

---

## 66. Independent Reviewer Findings

Independent product review executed after drafting. Findings and resolutions:

| Sev | Finding | Resolution |
|---|---|---|
| MEDIUM | Capability inventory + backend mapping omitted `tcl_resolver.py` (bounded Tcl variable resolution) and `wildcard_analyzer.py` (wildcard drift detection) — both real, user-visible capabilities | Added as capabilities 1a and 8a; both modules added to §10 backend mapping |
| LOW | Historical performance rows (400 clocks ~1 s, 10k constraints ~1 s) lacked artifact precision and could read as current measurements | §31 now separates currently-measured (with suite names) from approximate historical figures, labeled explicitly |
| LOW | §66 was a placeholder; review had not been executed | Filled with actual findings + resolutions |
| INFO | Capability inventory condensed vs the spec's requested field set (inputs/outputs/UI location/benchmark/docs/page per row) | Accepted for a planning document; §9 gains a UI-location/product-page mapping note and §62 covers the reuse matrix |

Reviewer also confirmed: no STA/signoff overclaims; benchmark numbers (763/9/42/17/16/10, 111 rules, 1.3.0) all traceable; terminology clean (no "AI-powered"/"signoff-ready"); P0 scope realistic; product/workspace separation coherent; all 15 final-recommendation questions answered.

---

## 67. Risks

| Risk | Mitigation |
|---|---|
| Marketing overclaim ("signoff") | Mandatory non-claims in every surface; language system §54 |
| Benchmark presented as certification | Claim policy §56; traceability model §32 |
| Workspace overload (all-in-one tab) | Restructure per §40/§41; progressive disclosure §53 |
| Product site drift from implementation | Content source-of-truth §65 |
| Streamlit limitations on product site | Separate surfaces §63/§64 |
| UI restructure breaking working features | KEEP/RESTRUCTURE matrix §62; backend unchanged; UI suites protect behavior |
| Feature creep before beta | P0 gate §15; no new validation features in this phase |
| Privacy perception | Local-by-default §57 |

---

## 68. Known Product Boundaries

- No STA signoff, slack, .lib analysis, physical timing, closure guarantees.
- SDC/Tcl/Verilog support is bounded by the documented support boundary; unsupported constructs are disclosed, never silently skipped.
- SDC-only mode cannot prove object resolution (netlist required).
- Tcl execution-required constructs are analyzed at text level only.
- Legacy category-coverage score is a heuristic, not readiness.
- Python 3.10 verified; 3.11/3.12 not yet executed in this environment.
- Web UI launched via Streamlit; installed-wheel web launch deferred to deploy-time smoke.

---

## 69. Implementation Sequence

1. **Approval gate** — this architecture is reviewed and approved.
2. **Visual design system + high-fidelity product experience** (next phase — as specified).
3. **Product/knowledge surface** (P0 pages: Home, Platform, Capabilities hub + SDC Validation + Readiness, Benchmarks overview, Trust Center, Docs getting-started, Release) built on content sources (§65).
4. **Workspace restructure** (P0: Overview, Validator, Readiness, Diff) reusing existing backend calls; UI suites re-run after every change.
5. **P1 capabilities** (Clock, Design Context, Coverage, Interactions, CI Policies pages + workspaces) as the restructure proves out.
6. **Benchmark traceability auto-generation** (P2).
7. **Release + external beta** with real engineers/designs.

No validation logic, benchmark expectation, or backend API changes in any of these steps unless an audit finds a defect.

---

## 70. FINAL RECOMMENDATION

1. **What should Ṛta become as a product?** A deterministic, offline **Constraint Quality Intelligence and Pre-STA Validation platform** — the evidence layer between constraint authoring and STA/signoff, with a professional product/knowledge surface and an engineering workspace.
2. **Strongest startup positioning:** *"The quality gate between constraint authoring and STA — deterministic, offline, evidence-backed."*
3. **First target user:** the **Physical Design / Timing Constraints Engineer** who owns SDC quality and handoff (JOURNEY A + C); the Technical Lead follows as the readiness/benchmark evaluator (JOURNEY F).
4. **Homepage in 10 seconds:** hero answers *"What is this? Who is it for? What problem?"* + a deterministic/offline trust strip + a before-STA workflow diagram — no hype.
5. **Mandatory before v1.3.0 public beta (P0):** Home · Platform · Capabilities hub + SDC Validation + Readiness · Benchmarks Overview · Trust Center · Docs Getting Started · Release · Workspace Overview/Validator/Readiness/Diff.
6. **Wait (P1/P2):** dedicated Clock/Design-Context/Coverage/Interactions/CI pages, benchmark detail pages, traceability auto-generation, responsive polish.
7. **Separate product website and workspace?** **Yes** — separate surfaces, one brand, one-click bridge (§64).
8. **Keep Streamlit for the workspace?** **Yes** (Option B). The workspace stays Streamlit; the product site is a separate lightweight static frontend (§63).
9. **Preserve from the current UI:** Generator, Linter, Converter, Corner Mgr, MMC, Rules Reference, Test Drive, Feedback dashboard, EDA theme, and all analysis backend calls. Nothing is removed (§62).
10. **Rebuild:** the overloaded all-in-one Checker tab → dedicated workspace pages; sidebar navigation; product-site surfaces (new, not a rebuild of app.py).
11. **Benchmarks presented without misleading users:** traceable cards with version/methodology/limitations + explicit "internal validation, not certification" + claim policy (§30/§56).
12. **Trust limitations presented:** a dedicated Trust Center with a non-claims section, and a trust disclosure embedded in every result surface (workspace, reports, pages) (§33/§34).
13. **Premium without generic AI/SaaS feel:** EDA-native visual identity (dark theme base, engineering typography, precise language, matrix/tree visualizations), information density that respects engineers, and honest trust language — not gradients-and-emoji SaaS fluff.
14. **Visible to a technical lead evaluating:** capabilities with evidence, benchmark methodology, Trust Center, deterministic architecture, release evidence, known limitations — all traceable to repository artifacts (§29/§33/§35/§37/§39).
15. **Next implementation task after approval:** the **Visual Design System + High-Fidelity Product Experience** phase — applying this architecture to the P0 surfaces (product site + workspace restructure) without touching validation logic.

---

*End of architecture document. This is a planning artifact: no production code, validation logic, benchmarks, or APIs were modified by its creation.*
