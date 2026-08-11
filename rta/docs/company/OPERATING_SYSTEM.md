# Ṛta — Operating System

> **Document kind:** internal handbook — the operating principles, processes, and standards that govern how Ṛta is built, shipped, and maintained.
> **Status:** living document · **Owner:** founding team · **Review:** quarterly.
>
> This is not a design spec or a project plan. It is the system of how we work.

---

## 1. Company Principles

These are not aspirations. They are the rules that override everything else when a decision is ambiguous.

### 1.1 We verify. We do not guess.

Every claim the product makes must trace to evidence. No number appears on the website, in a report, or in a CLI that does not have a rerunnable artifact behind it. This applies to benchmark counts, rule counts, test counts, and performance numbers. An engineer at a semiconductor company trusts this product with silicon-quality decisions. That trust is earned by evidence, not by language.

### 1.2 Evidence over assumptions.

When we do not know, we say so. The Trust Model (VALIDATED · PARTIALLY_VALIDATED · NETLIST_REQUIRED · TCL_EXECUTION_REQUIRED · UNSUPPORTED · NOT_VALIDATED) is enforced in every surface — CLI output, workspace UI, HTML reports, website, and documentation. "No errors" is never presented as "everything proven."

### 1.3 Deterministic over probabilistic.

The analysis engine is deterministic Python. Identical input produces identical output. This is a hard product constraint, not a current limitation. No LLM, no model inference, no probabilistic judgment enters the runtime analysis path. This may change how we develop; it must not change what ships.

### 1.4 Trust before automation.

A tool that loses a team's trust once will not get it back. When we are uncertain, we disclose rather than auto-resolve. An engineer who sees honest uncertainty trusts the tool more than one who sees a confident but wrong answer.

### 1.5 Constraint Quality before Timing Closure.

RICTA measures constraint quality. We do not compute timing. READY ≠ STA signoff. CI pass ≠ timing closure. Coverage ≠ correctness. Object resolution ≠ path existence. These distinctions are not footnotes. They are the product's first-class identity.

### 1.6 Honest limitations are better than false confidence.

We will always be the tool that tells you what it did not check. That is its value proposition. Never trade honesty for perceived completeness.

### 1.7 The standard is not ours to rename.

SDC, SDC commands, SDC rule codes, `set_clock_groups`, `create_clock` — these are the Synopsys Design Constraints standard. We use its vocabulary exactly. Brand lives on product surfaces, not on the standard's language.

### 1.8 Open core is additive.

Nothing that exists today is moved behind a paywall. Future commercial scope extends capability (policies, baselines, team workflows, governance); it never degrades what is already open. The engine is the brand; closing it would destroy trust and contradict the Trust Model.

---

## 2. Decision Making

### 2.1 Decision principles

- **Decisions are documented.** Every significant architecture, product, or process decision is recorded as an ADR (see [ADR_TEMPLATE.md](ADR_TEMPLATE.md)). Decisions not written down are not decisions.
- **Decisions have owners.** A single person owns each decision. Consensus is consulted, not required.
- **Decisions are revisable.** No decision is permanent. When context changes, the ADR records the update.
- **The frozen backend is a decision boundary.** Changes to the deterministic analysis engine require the full architecture review process. Changes to frontends, documentation, CI, or packaging follow the standard review.

### 2.2 Decision authority

| Domain | Authority | Review |
|---|---|---|
| Deterministic engine (parser, rules, analysis) | Engineering lead | Architecture review + full regression |
| Product surface (UI, website, docs) | Product lead | Product review + UI benchmark |
| Trust model / disclosure | Trust review (all founders) | Must not weaken honesty contract |
| Open-core boundary | Company lead | Community impact assessment |
| Release / versioning | Release owner | Release review checklist |
| Naming / brand | Brand owner | Brand audit (per BRAND_MIGRATION_AUDIT) |

### 2.3 Escalation

When a decision falls outside defined authority, the founders resolve it. When founders disagree, the principle that preserves engineer trust wins. (See Principle 1.4.)

---

## 3. Engineering Culture

### 3.1 What we value

- **Precision.** Say exactly what the code does. No hand-waving.
- **Evidence.** Every claim has a runner. Every number has a source.
- **Reproducibility.** Same commit, same environment, same result.
- **Brevity.** The code, the docs, and the PR should say only what needs to be said.
- **Honesty about scope.** A function that does not handle a case says so.
- **Defensive coding.** The analysis engine can never produce a passing result on failure. That discipline extends to everything we ship.

### 3.2 What we do not value

- Clever code that is hard to verify.
- Marketing language in technical surfaces.
- Tests that assert a number without testing the claim behind it.
- Documentation that describes what a feature should do rather than what it actually does.
- "It works on my machine" — determinism means it works everywhere or we know exactly why it does not.

### 3.3 The frozen engine

The deterministic backend is our product's core asset. Every module in the root directory that participates in the analysis pipeline is protected:

- **No performance-only changes** without a benchmark demonstrating the improvement.
- **No refactoring** that changes observable behavior without a regression in the golden suites.
- **No new dependencies** in the core engine without an architecture decision.

---

## 4. How Product Decisions Are Made

### 4.1 The product question

Before every feature or change, the team answers: "Does this make Ṛta feel more like a company engineers will trust for the next 20 years?" If the answer is no, we do not do it.

### 4.2 Product decision process

1. **State the problem.** What engineer is experiencing what friction, and how often.
2. **State the constraint.** What the Trust Model, the deterministic architecture, or the open-core boundary prohibits.
3. **Propose the solution.** What the feature changes, in engineering language.
4. **Verify evidence.** What benchmark or test proves the change works.
5. **Trust review.** Does the feature introduce any surface where the tool could misrepresent its own scope?
6. **Decision and record.** The ADR records the decision, the owner, and the rationale.

### 4.3 What is NOT a product decision

- "It would be nice to have" — features must trace to an engineer's workflow.
- "Competitors have it" — we build what the Trust Model permits, not what marketing requires.
- "It makes the UI prettier" — visual changes are valid only when they improve engineering density or trust clarity.

---

## 5. Definition of Done

A feature is done when **all** of the following are true:

1. The deterministic engine produces correct, verified output for the new capability.
2. At least one test covers the happy path, one test covers a boundary/edge case, and one test covers an error/unsupported condition.
3. The trust boundary for the new capability is documented (what it validates, what it does not, what requires context).
4. The capability maps to a CLI surface or workspace page that an engineer can reach.
5. The capability is named according to the Naming Standards (Section 17).
6. The capability is mentioned in README (or docs/features) with accurate numbers.
7. No existing test regresses.
8. The release checklist (Section 15) is updated.
9. The ADR (or RFC) is recorded.

A feature is NOT done when the code "works." It is done when the product tells the truth about what it does.

---

## 6. Definition of Trust

Trust is the property that the tool never overstates what it has verified.

A surface has **Trust Integrity** when:

- Every finding has a severity, rule code, evidence message, and source provenance.
- Every result carries an analysis scope disclosure (what was and was not checked).
- Every "clean" result explicitly communicates "no rule fired" rather than "correct."
- Every readiness verdict carries the "NOT an STA signoff" disclaimer.
- Every performance number includes environment context (OS, Python version, date).
- Every benchmark number links to its artifact.

**Trust failures** include (but are not limited to):

- Reporting a number on the website without a runner.
- Presenting coverage as correctness.
- Using a benchmark number that is stale relative to the current code.
- Omitting trust statuses from a workspace page that computes them.
- Claiming "AI-powered" or "smart" in any product surface.

---

## 7. Definition of Evidence

Evidence is a rerunnable artifact in the repository that proves a product claim.

A valid evidence artifact:

1. Lives in `tests/` or `benchmarks/` and is runnable with `python -m pytest <path> -q`.
2. Has a machine-readable expected outcome (golden JSON, assertions, or exit code).
3. Verifies a specific, stated claim (not just "tests pass").
4. Is versioned with the same commit it supports.

**Evidence categories** (per `BENCHMARK_EVIDENCE_MAP.md`):

| Category | What it proves | Example |
|---|---|---|
| Correctness | Golden match, reference design, mutation sensitivity | `run_golden.py`, `test_reference_mutation.py` |
| Robustness | Adversarial, metamorphic, stress | `test_*_adversarial.py`, `test_*_metamorphic.py` |
| Design-aware | Netlist, coverage | `run_netlist_aware.py`, `test_coverage_*` |
| Regression reliability | Baseline diff, CI gate, identity | `run_readiness_diff.py`, `test_readiness_ci_gate.py` |
| Security | XSS, injection, snapshot safety | `test_security.py`, `test_netlist_security.py` |
| Performance | Wall-time benchmarks | `test_*_perf.py` |
| Release quality | Pytest, smoke, CLI audit, clean-room | `test_release_smoke.py`, `release_cli_audit.py` |

**Evidence staleness** is a trust failure. If the code changes and a suite does not run in CI, the associated claim is unverified.

---

## 8. Documentation Standards

### 8.1 The hierarchy

| Document type | Purpose | Owner | Location |
|---|---|---|---|
| README | First-contact product description | Product lead | `README.md` |
| Brand Foundation | Naming, positioning, trust principles | Brand owner | `docs/rta/BRAND_FOUNDATION.md` |
| Trust Model | What is validated, what is not | Trust review | `docs/rta/TRUST_MODEL.md` |
| Product Taxonomy | Module definitions and backend mapping | Product lead | `docs/rta/PRODUCT_TAXONOMY.md` |
| Capability Map | Inventory of all capabilities with evidence | Product lead | `docs/rta/CAPABILITY_MAP.md` |
| Feature docs | Per-module reference documentation | Engineering lead | `docs/features/README-*.md` |
| Product architecture | Experience design and page specifications | Product lead | `docs/product/*.md` |
| Operating System | This document | Founding team | `docs/company/OPERATING_SYSTEM.md` |
| ADRs | Architecture decision records | Decision owner | `docs/company/ADR_*.md` |
| RFCs | Feature proposals under review | Feature proposer | `docs/company/RFC_*.md` |
| Phase reports | Post-phase evidence and findings | Phase owner | `benchmarks/PHASE*.md` |
| CHANGELOG | User-facing version history | Release owner | `CHANGELOG.md` |

### 8.2 Writing rules

1. **Technical, not marketing.** Engineering documentation does not use "powerful," "revolutionary," "AI-powered," or "smart."
2. **Past tense for what exists, present tense for what it does.** "The validator checks" not "the validator will check."
3. **Numbers have sources.** Every claim of "780 tests" must be verifiable by running the test suite.
4. **Trust boundaries are prominent, not footnotes.** Every capability page carries its trust disclosure as a first-class section.
5. **Banned words** (in product surfaces and docs): AI-powered · magic · smart · revolutionary · blazing fast · 100% accurate · signoff-ready · guaranteed timing closure.
6. **One canonical one-liner.** The product description is one string used consistently across README, website `<title>`, workspace sub-brand, and footer. Currently: *"Constraint Intelligence for Digital Design."*

### 8.3 Documentation is never stale

A documentation page that contradicts the implementation is a bug. The content source-of-truth pipeline (per PRODUCT_EXPERIENCE_ARCHITECTURE §65) derives content from machine-readable sources: `rules_registry.py` → rule pages, `support_boundary.py` → trust status pages, benchmark manifests → evidence cards. Until automation exists, every release checklist item requires a manual doc-surface audit.

---

## 9. Architecture Review Process

### 9.1 When an architecture review is required

- Any change to the deterministic engine's module boundaries or public APIs.
- Any change to the analysis pipeline (parsing, checking, reporting).
- Any new backend module that imports or extends checker, sdc_preprocess, or rules_registry.
- Any packaging or dependency change.
- Any change to the Trust Model's status vocabulary.

### 9.2 What the review covers

1. **Correctness.** Does the change preserve determinism (identical input → identical output)?
2. **Evidence.** What new or modified test/golden suite proves the change?
3. **Trust.** Does the change introduce any surface where the tool could misrepresent its scope?
4. **Performance.** Does the change degrade the existing performance envelope? (Per the measured baselines: readiness-diff 10k findings ≈ 43–75ms; readiness aggregation ≈ 8ms; 400 clocks ≈ ~1s.)
5. **Regression.** Does the full test suite (780+ tests) pass? Do the golden runners pass? Does the release smoke pass?
6. **Packaging.** Does the wheel still build, install, and serve from a clean environment?

### 9.3 How the review is conducted

1. The proposing author opens an RFC (see [RFC_TEMPLATE.md](RFC_TEMPLATE.md)).
2. At least one other engineer reviews the RFC.
3. The RFC is resolved (approved / rejected / revised) before implementation begins.
4. After implementation, the full regression is run and results are included in the PR.
5. The architecture owner approves the merge.

---

## 10. Product Review Process

### 10.1 When a product review is required

- Any new user-facing surface (workspace page, website page, CLI command, HTML report section).
- Any change to the trust disclosure language.
- Any change to benchmark numbers on public surfaces.
- Any change to the product name, tagline, or positioning language.

### 10.2 What the review covers

1. **Trust integrity.** Does every finding, result, or metric carry its scope disclosure?
2. **Honesty.** Does the surface imply capabilities the backend does not have?
3. **Accuracy.** Are all numbers traceable to verified artifacts?
4. **Consistency.** Does the surface use the canonical naming, the canonical CLI identity, and the canonical one-liner?
5. **Engineering density.** Does the surface respect the engineer's attention? (No generic-SaaS fluff, no glassmorphism, no fake percentages.)
6. **Accessibility.** Does the surface convey information through icon + label + shape, never color alone? Does it respect `prefers-reduced-motion`?

### 10.3 How the review is conducted

1. The author opens a PR with the product change.
2. The product lead (or a designated reviewer) reviews against the [PRODUCT_REVIEW_CHECKLIST.md](PRODUCT_REVIEW_CHECKLIST.md).
3. Findings are addressed before merge.
4. For website changes: the live site is visually inspected locally before merge.

---

## 11. Release Review Process

### 11.1 Release readiness criteria

A release is ready when:

1. **All tests pass.** The full `tests/` suite (780+ tests) passes with no failures.
2. **All golden runners pass.** Every `run_*.py` runner in `benchmarks/` produces green.
3. **All benchmark suites pass.** Every `test_*.py` suite in `benchmarks/` produces green.
4. **Release smoke passes.** `test_release_smoke.py` passes (verifies documented workflows).
5. **CLI contract audit passes.** `release_cli_audit.py` passes (exit codes, JSON purity).
6. **Clean-room wheel journey passes.** `release_cleanroom.py` passes (wheel builds, installs, serves, works from any cwd).
7. **No stale evidence numbers.** Every claim on the website, README, and release page matches the current artifact counts.
8. **Documentation is current.** README, CHANGELOG, and the release page reflect the version being released.
9. **Known limitations are stated.** The release page lists known limitations with no understatement.

### 11.2 Release naming

- **v1.3.x** — patch releases (bug fixes, documentation, infrastructure).
- **v1.4.0** — minor releases (new capabilities that do not change the Trust Model).
- **v2.0.0** — major releases (changes to the Trust Model, breaking CLI or package changes).
- Pre-releases use `-rc.1`, `-beta.1`, etc.

### 11.3 Release process

1. Author opens a release PR with CHANGELOG entry and version bump.
2. Full release review checklist is completed (see [ENGINEERING_CHECKLIST.md](ENGINEERING_CHECKLIST.md)).
3. Evidence numbers are re-verified on the release branch.
4. PR is merged.
5. Tag is created: `v<version>`.
6. Release page is updated on the website.
7. PyPI package is published (when applicable).

---

## 12. Benchmark Review Process

### 12.1 The evidence contract

No marketing number exists without a runner. The benchmark review is not optional; it is the product's core credibility mechanism.

### 12.2 When benchmarks are reviewed

1. Before every release (release review process, Section 11).
2. When a public-facing surface presents a number (product review process, Section 10).
3. When a new benchmark suite is added (architecture review process, Section 9).

### 12.3 What is verified

- The suite is runnable and produces deterministic output.
- The expected outcome matches the current behavior.
- The expected outcome is correct (the test is actually validating the claim, not just passing).
- The number is stated with its environment context (OS, Python version, date).
- The claim links to its artifact (runner file, manifest, or phase report).

### 12.4 Evidence staleness protocol

When the code changes:
1. Re-run the full benchmark suite.
2. If the numbers change, update every public-facing reference (website, README, release page, docs).
3. If the numbers do not change, no action needed.
4. **Never update a number without re-running the runner.**

---

## 13. Quality Gates

### 13.1 Pre-merge gates

Every PR must pass:

1. `python -m pytest tests/ -q` — all tests green.
2. No regressions in the golden suites (run the relevant `run_*.py` for changed modules).
3. Documentation is updated for any user-facing change.
4. ADR is recorded for any architecture change.
5. The [ENGINEERING_CHECKLIST.md](ENGINEERING_CHECKLIST.md) is satisfied.

### 13.2 Pre-release gates

Every release must pass:

1. All items in the pre-merge gates.
2. All golden runners green.
3. All benchmark suites green.
4. Release smoke green.
5. CLI contract audit green.
6. Clean-room wheel journey green.
7. Evidence numbers re-verified.
8. Known limitations documented.
9. CHANGELOG and release page updated.

### 13.3 CI contract

The CI pipeline protects the following:
- `tests/` suite runs on every push and PR.
- Benchmark suites run on release branches (targeted expansion required).
- Engine failure never produces a passing result (exit code 3 contract).

---

## 14. Naming Standards

### 14.1 Identity layers

| Layer | Standard | Example |
|---|---|---|
| Visible brand | `Ṛta` (Unicode U+1E5A, always with the dot) | Website, workspace title, reports |
| Product modules | `Ṛta Validate`, `Ṛta Clocks`, `RIPTA Context`, etc. | Workspace pages, docs |
| Technical CLI | `rta` (primary), `sdc-tools` (alias) | `rta check design.sdc` |
| Python identifiers | `rta` (ASCII, for env vars, paths, future package) | `rta/engine/...` (future) |
| Package/wheel | `sdc-tools` / `sdc_tools` (current) | `pip install sdc-tools` |
| Rule codes | `SDC-001`…`SDC-132`, `CHG-*` | Findings, reports |
| Version | Semantic: `v<major>.<minor>.<patch>` | `v1.3.0` |

### 14.2 Naming rules

1. **Never rename SDC standard vocabulary.** `set_clock_groups` is always `set_clock_groups`, never "ṛta groups."
2. **Never abbreviate the brand in product surfaces.** `Ṛta`, never `RTA` or `Rta` (without the dot below) on user-facing surfaces.
3. **ASCII identifiers for code.** The `rta` identifier is used in paths, environment variables, file names, and CLI invocations.
4. **New features get English names.** Module names describe what the module does, not the brand. `constraint_readiness.py`, not `rta_readiness.py`.
5. **The CLI follows the invoked name.** `--version` output, headers, and `prog` follow whether the user typed `rta` or `sdc-tools`.

### 14.3 Terminology

- **finding** — an observed condition backed by evidence (not an opinion).
- **severity** — error / warning / info / fatal (impact ordering, not truth).
- **trust** — how completely a construct was analyzed.
- **coverage** — whether something was constrained (≠ correctness).
- **readiness** — handoff-oriented aggregate verdict (≠ signoff).
- **baseline** — a saved, versioned snapshot used for comparison.
- **regression** — a disallowed readiness/coverage/trust change vs baseline.

---

## 15. Design Standards

### 15.1 The visual identity

**Order emerging from complexity.** Individual constraints are chaotic in isolation; Ṛta resolves them into coherent, readable structure. Every visual choice serves that idea.

### 15.2 Design primitives (from the domain, not generic)

- **Clock edges** — vertical ticks representing clock events.
- **Clock trees** — primary node branching into generated-clock children.
- **Timing arcs** — curved links between constrained objects.
- **Netlist nodes** — ports, pins, cells as distinct node glyphs.
- **Buses** — bit-range strips showing covered/uncovered slices.
- **Constraint links** — directed connectors (override, conflict, legal multiple).
- **Boundaries** — the trust boundary as a visual edge between "analyzed" and "not analyzed."

### 15.3 Forbidden patterns

- Mythological, religious, or ornamental cultural motifs (the name is inspired by order, not decoration).
- AI sparkles, brains, robots, magic stars, neural-network blobs.
- Generic chip or bolt logos.
- Glassmorphism, glow effects, gradient-heavy SaaS aesthetics.
- Fake percentage gauges, confidence rings, "95% ready" displays.

### 15.4 Dark-first

The engineering workspace is permanently dark (like STA tooling). The marketing site is dark with strict AA contrast. Light theme is a future option, not a current requirement.

### 15.5 Status language

Every status = **icon + label + shape**. Never color alone.

| Status type | Values |
|---|---|
| Severity | ERROR / WARNING / INFO / FATAL |
| Trust | VALIDATED / PARTIALLY_VALIDATED / NETLIST_REQUIRED / TCL_EXECUTION_REQUIRED / UNSUPPORTED / NOT_VALIDATED |
| Readiness | READY / READY_WITH_ADVISORIES / REVIEW_REQUIRED / BLOCKED / INSUFFICIENT_CONTEXT |

### 15.6 Engineering density

Compact tables, rails, inspectors. Hierarchy from spacing, surface contrast, borders, and typography — not shadows, cards, or glassmorphism. The workspace is dense by design; it respects the engineer's attention.

---

## 16. Documentation Standards

*(Cross-reference: Section 8.2 Writing Rules.)*

Every document in the repository must:

1. State its document kind and status at the top (e.g., "living document", "architecture decision record", "design specification only").
2. Include a date and version.
3. End with a note of what it does and does not change (for planning/design documents).
4. Be reviewed before merging.

The one exception is CHANGELOG.md, which is append-only during a release cycle.

---

## 17. Engineering RFC Process

### 17.1 What an RFC is

An RFC (Request for Comments) is a proposal for a new feature, capability, or significant change. It is the formal way to propose work before implementation begins.

### 17.2 When an RFC is required

- A new feature or capability.
- A change to the deterministic engine.
- A change to the Trust Model or trust vocabulary.
- A new public surface (CLI command, workspace page, API endpoint).
- A change to packaging or dependencies.
- A change to the open-core boundary.
- A release.

### 17.3 When an RFC is NOT required

- Bug fixes that do not change observable behavior.
- Documentation-only changes.
- Test additions for existing features.
- CI or infrastructure changes that do not affect product surfaces.
- Cosmetic CSS changes in the workspace or website.

### 17.4 RFC lifecycle

```
Draft → Review → Accepted/Rejected → Implemented → Closed
```

1. **Draft**: Author creates `docs/company/RFC_<number>_<slug>.md` from the template. PR is opened.
2. **Review**: At least one engineer reviews. Discussion happens on the PR.
3. **Accepted/Rejected**: Author records the decision, rationale, and any conditions.
4. **Implemented**: Work proceeds per the accepted RFC. The RFC is not modified after acceptance (append a note if context changes).
5. **Closed**: The RFC is merged after implementation or marked rejected.

### 17.5 RFC numbering

Sequential: `RFC_001`, `RFC_002`, etc. The number is reserved in the PR title.

---

## 18. ADR Process

### 18.1 What an ADR is

An ADR (Architecture Decision Record) captures a significant architectural decision: what was decided, why, what alternatives were considered, and what the consequences are.

### 18.2 When an ADR is required

- Any architecture review (Section 9).
- A change to the Trust Model.
- A change to the analysis pipeline.
- A new dependency.
- A change to packaging or module boundaries.
- A decision to accept or reject a technical risk.

### 18.3 When an ADR is NOT required

- Product surface changes (use product review).
- Bug fixes.
- Documentation or test changes.
- CI infrastructure changes (unless they affect the evidence contract).

### 18.4 ADR lifecycle

ADRs are **immutable once accepted.** If a decision is superseded, a new ADR is written that references the old one. The old ADR's status is updated to "Superseded by ADR_XXX."

```
Proposed → Accepted/Rejected [Superseded]
```

### 18.5 ADR numbering

Sequential: `ADR_001`, `ADR_002`, etc. The number is reserved in the PR title.

---

## 19. How New Features Are Proposed

See the RFC process (Section 17). In summary:

1. Write an RFC following [RFC_TEMPLATE.md](RFC_TEMPLATE.md).
2. Open a PR with the RFC.
3. At least one engineer reviews.
4. Decision is recorded in the RFC.
5. If accepted, implementation proceeds with the [ENGINEERING_CHECKLIST.md](ENGINEERING_CHECKLIST.md).
6. The ADR records the architectural decision separately.

---

## 20. How Features Are Rejected

A feature is rejected when:

1. **It contradicts the Trust Model.** If the feature would misrepresent the tool's scope or create false confidence, it is rejected.
2. **It requires probabilistic analysis.** LLM, ML inference, or model-based judgment in the runtime is rejected (per Principle 1.3).
3. **It is an "AI-powered" feature.** Any feature marketed with AI language is rejected (per Principle 1.3).
4. **It degrades the open-core boundary.** Moving existing open functionality behind a paywall is rejected (per Principle 1.8).
5. **It has no evidence.** A feature that cannot be verified by a test, golden suite, or benchmark is rejected.
6. **It is premature.** A feature that serves an unvalidated user need (no engineer has requested it) is deferred to the backlog, not implemented.

Rejection is recorded in the RFC with the rationale. The rejected RFC is merged as a record of what was considered and why.

---

## 21. Roadmap Planning

### 21.1 The roadmap is maturity-based, not date-based

No arbitrary dates. Items are gated by product milestones:

- **Foundation** ✅ — Identity, brand, documentation, CLI alias, workspace.
- **Product Experience** — The next major phase. From-scratch application UI, motion system, technical visualizations.
- **Developer Experience** — Install polish, CLI completion, CI evidence bundles.
- **Community** — Docs site, example library, contribution guide, benchmark dashboard.
- **Team Product** [speculative] — Shared baselines, policy catalogs, trend dashboards.
- **Enterprise** [speculative] — Governance, audit trails, support.

### 21.2 P0/P1/P2 priorities

Features are tagged P0 (required before public beta), P1 (valuable shortly after), or P2 (future). P0 items are not negotiable; P1 items are time-sensitive; P2 items are tracked but not scheduled.

### 21.3 Explicitly NOT planned

- LLMs / generative AI in the analysis path.
- Licensing / paywalls for existing open features.
- Cloud processing of customer SDC/netlist data without explicit opt-in.

---

## 22. Sprint Planning

### 22.1 Cadence

Two-week sprints. Each sprint has a clear objective and a defined "done" state.

### 22.2 Sprint structure

| Activity | When | Who |
|---|---|---|
| Sprint planning | Day 1 | Engineering lead + product lead |
| Daily async check-in | Every day | Team (async, text-based) |
| Sprint review | Last day | Full team + demo |
| Sprint retrospective | After review | Full team |

### 22.3 What goes in a sprint

- Items from the backlog that are unblocked and match the sprint objective.
- Bug fixes for regressions discovered in CI or manual testing.
- Documentation updates required for an in-progress feature.
- Infrastructure work that unblocks a P0/P1 item.

### 22.4 What does NOT go in a sprint

- "Nice to have" work without a clear owner.
- Features that have not passed the RFC process.
- Refactoring without a stated benefit and benchmark.

---

## 23. Issue Lifecycle

### 23.1 Issue types

| Type | Description | Example |
|---|---|---|
| Bug | Something is wrong | "SDC-007 fires on comments" |
| Feature | New capability requested | "Add clock-tree SVG visualization" |
| Documentation | Docs are missing, stale, or wrong | "docs/features says 40+ rules" |
| Trust | Trust model or disclosure concern | "Site says 710 tests, actual is 780" |
| Infrastructure | CI, packaging, tooling | "CI should run benchmark suites" |
| Research | Investigation needed | "Explore FastAPI vs stdlib for API server" |
| Security | Security concern | "XSS risk in user-controlled SDC text" |

### 23.2 Issue states

```
Open → In Progress → In Review → Closed
                ↓
            Deferred (P2, backlog)
```

### 23.3 Issue labeling

- **Priority:** `P0` (urgent, blocks release or credibility), `P1` (important, next sprint), `P2` (tracked, future).
- **Phase:** `foundation`, `product-experience`, `dx`, `community`, `enterprise`.
- **Domain:** `engine`, `ui`, `website`, `docs`, `ci`, `packaging`, `brand`.
- **Status:** `needs-triage`, `ready`, `blocked`, `in-progress`, `in-review`.

---

## 24. GitHub Workflow

### 24.1 Branch naming

| Branch type | Pattern | Example |
|---|---|---|
| Feature | `feature/<slug>` | `feature/clock-tree-viz` |
| Fix | `fix/<slug>` | `fix/evidence-number-stale` |
| RFC | `rfc/<number>-<slug>` | `rfc/003-release-process` |
| Release | `release/v<version>` | `release/v1.4.0` |

### 24.2 PR requirements

1. Title follows conventional format: `feature: ...`, `fix: ...`, `docs: ...`, `rfc: ...`.
2. Description references the issue or RFC number.
3. All CI checks pass.
4. At least one engineer reviews (two for engine changes).
5. The [ENGINEERING_CHECKLIST.md](ENGINEERING_CHECKLIST.md) is satisfied.
6. CHANGELOG is updated (for user-facing changes).
7. Evidence numbers are re-verified (if the change affects any claimed number).

### 24.3 Merge strategy

- **Squash merge** for features and fixes (clean history).
- **Merge commit** for RFCs and ADRs (preserve the discussion history).

---

## 25. Branch Strategy

### 25.1 Main branch

`main` is always deployable. Every commit on `main` passes the full test suite. No direct commits to `main`.

### 25.2 Development flow

```
main ← feature/fix branches ← PR + review + CI
```

### 25.3 Release flow

```
main ← release/v1.4.0 branch (release review) ← tag v1.4.0
```

---

## 26. Release Strategy

### 26.1 Release cadence

Releases are triggered by feature completion, not by dates. A release is cut when the release review checklist (Section 11) is satisfied.

### 26.2 Pre-release communication

For RC releases: the release page states the pre-release status clearly. "RC_READY_WITH_KNOWN_LIMITATIONS" is a documented state, not a marketing statement.

### 26.3 Post-release

After each release:
1. Verify the tag on GitHub.
2. Update PyPI (when applicable).
3. Update the website release page.
4. Update the CHANGELOG.
5. Run the release smoke suite against the tagged commit.

---

## 27. Community Contributions

### 27.1 The invitation

Ṛta Community is MIT-licensed. Contributions are welcome for:

- Bug fixes with tests.
- Documentation improvements.
- Benchmark additions (new golden cases, edge cases, reference designs).
- CI improvements.
- New features that pass the RFC process and do not change the Trust Model.

### 27.2 Contribution workflow

1. Read [CONTRIBUTING.md](../../CONTRIBUTING.md).
2. Open an issue describing the change.
3. Fork, create a feature branch, implement, test.
4. Open a PR with the issue reference.
5. Address review feedback.
6. Merge (squash for features, merge-commit for RFCs).

### 27.3 What we need most

- Real-world SDC files (anonymized) for benchmark expansion.
- Verilog netlists for design-aware testing.
- CI integration examples (GitHub Actions, GitLab CI, Jenkins).
- Documentation reviews from actual STA/PD engineers.

---

## 28. Open Source Governance

### 28.1 The open-core boundary

| Scope | License | Status |
|---|---|---|
| Deterministic engine | MIT | Open now |
| CLI and reports | MIT | Open now |
| Benchmarks and tests | MIT | Open now |
| Documentation | MIT | Open now |
| Workspace UI | MIT | Open now |
| Marketing website | MIT | Open now |
| Team collaboration features | TBD | Future, additive |
| Enterprise governance | TBD | Future, additive |
| Support offering | TBD | Future, additive |

### 28.2 Governance principles

1. The engine is the brand. Closing it destroys trust.
2. Differentiation is workflow, not analysis. Teams pay for shared state and process.
3. Data portability. Any future cloud feature must work with the same local formats.
4. No vendor lock-in. The CLI remains the integration boundary.

### 28.3 Community health

- All PRs receive a response within 7 days (acknowledgment + triage).
- Issues receive a response within 3 days.
- Security reports receive a response within 24 hours.

---

## 29. Commercial Feature Governance

### 29.1 The rule

Commercial scope is additive. It never degrades what is already open.

### 29.2 Candidate commercial scope (future, not implemented)

1. Team baselines and shared policies.
2. Centralized history and dashboards.
3. Enterprise CI integration (native apps, audit trails).
4. Collaboration (review flows, annotations, assignments).
5. Governance and analytics (org-level coverage, signoff exports).
6. Support offering.

### 29.3 What is never commercial

- The deterministic engine.
- The rule catalog.
- The Trust Model.
- The CLI.
- The benchmark evidence.

---

## 30. Long-Term Product Philosophy

### 30.1 The 20-year question

Every product decision is tested against: "Does this make Ṛta feel more like a company engineers will trust for the next 20 years?"

### 30.2 What we are building

A deterministic, offline, evidence-backed constraint intelligence layer that sits between constraint authoring and STA. We are the quality gate. We are not STA, not signoff, not AI, not a cloud service.

### 30.3 What we will never do

- Claim timing closure or signoff capability.
- Use LLMs in the analysis path.
- Sell or lose customer constraint data.
- Move existing open features behind a paywall.
- Present coverage as correctness or readiness as signoff.

### 30.4 What we will always do

- Tell the truth about what we checked and what we did not.
- Keep every benchmark claim backed by a rerunnable artifact.
- Maintain the Trust Model as the product's first-class identity.
- Release evidence that an engineer can verify independently.
- Respect the engineer's attention and trust.

---

*End of Operating System. This is a living document. Changes follow the ADR process for principle changes and the product review process for process changes.*
