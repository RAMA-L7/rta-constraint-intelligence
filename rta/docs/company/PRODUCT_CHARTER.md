# Ṛta — Product Charter

> **Document kind:** constitution · **Status:** foundational · **Effective:** 2026-08-07
> **Authority:** highest-priority product document. If a future feature, proposal, or contributor action conflicts with this Charter, the Charter wins.
> **Review:** annual · **Amendment:** requires unanimous founding-team approval + a new ADR.

---

## Preamble

Semiconductor timing constraints are the bridge between design intent and silicon behavior. That bridge is fragile: a single missing clock, a contradictory delay window, an unconstrained bus — each can cost weeks of engineering iteration. Today, constraint quality is verified by hand, by intuition, and by the expensive feedback of downstream tools discovering problems too late.

Ṛta exists to change this.

We build a **Constraint Intelligence Platform** — deterministic, offline, evidence-backed — that verifies constraint quality before STA consumes it. We do this with honesty about what we check, what we do not, and what requires further analysis. We do this for engineers who trust their tools with silicon-quality decisions.

This document defines what Ṛta is, what it is not, where it is going, and what must never change.

---

## 1. Product Identity

### 1.1 What Ṛta is

**Ṛta** ("Ri-ta") is a semiconductor software startup building a **Constraint Intelligence Platform** for digital design.

The first product is **deterministic SDC validation and constraint intelligence**: the analysis layer that runs between constraint authoring and STA, answering the question every constraint owner asks before handoff:

> "Is this constraint set complete, consistent, resolvable, and ready to hand to timing analysis — and what still needs review?"

### 1.2 What happened before

The project originated as an internal research prototype called "SDC Validator." That prototype was validated through extensive deterministic engineering work and is now considered a proven internal foundation. The engineering engine derived from it is mature and frozen.

From this point forward, everything belongs to Ṛta. The prototype's technical legacy lives on; its name does not.

### 1.3 The name

**Ṛta** — Unicode U+1E5A (lowercase r with dot below). Pronounced "Ri-ta," two syllables, stress on the first.

The visible product name is always **Ṛta**. The technical ASCII identifier is **`rta`**. The standard's vocabulary (SDC, `set_clock_groups`, `SDC-001`) is never renamed.

---

## 2. Current Product — Version 1

### 2.1 Scope

Version 1 is **Block-Level Constraint Intelligence**.

It analyzes SDC files (optionally with structural Verilog netlists) and answers questions about constraint quality at the block level — individual modules, IPs, or design partitions.

### 2.2 Required input

- **SDC** (Synopsys Design Constraints) file or text

### 2.3 Optional input

- **Structural Verilog** netlist + top module name
- **Custom rules** (YAML)
- **Baseline snapshot** (JSON, schema v2)
- **Policy file** (JSON/YAML)

### 2.4 Capabilities

The following capabilities exist in Version 1. No other capabilities are claimed.

| Capability | What it does |
|---|---|
| **SDC Validation** | Deterministic rule engine (111 rules) with severity, provenance, and source-line tracing |
| **Clock Intelligence** | Clock inventory, generated-clock ancestry, pairwise relationship matrix |
| **Generated Clock Analysis** | Hierarchy resolution via `-master_clock`, `-source` nodes, port identity |
| **Constraint Coverage** | Object-level and bus-level coverage with exact bit-range evidence |
| **Constraint Interactions** | Duplicates, overrides, contradictions (SDC-069), STA-review overlaps (SDC-070) |
| **Design-aware Validation** | Netlist-aware object resolution (get_ports / get_pins / get_cells / get_nets) |
| **Readiness Analysis** | Seven-dimension readiness verdict with deterministic recommended actions |
| **Trust Transparency** | Per-result analysis scope disclosure (VALIDATED · PARTIAL · NETLIST_REQUIRED · TCL_EXECUTION_REQUIRED · UNSUPPORTED · NOT_VALIDATED) |
| **Readiness Diff** | Semantic baseline comparison (new / resolved / changed / unchanged) with finding identity |
| **CI Gate** | Declarative policy engine with deterministic exit-code contract |
| **Reports** | Self-contained HTML reports, JSON output, JUnit XML |
| **Benchmarks** | Rerunnable evidence suites proving every product claim |
| **Engineering Evidence** | Golden runners, adversarial/metamorphic/security/performance suites, clean-room release verification |

### 2.5 What is NOT in Version 1

These capabilities do not exist and must not be claimed:

- Timing propagation or slack calculation
- Physical timing analysis
- Clock latency or skew computation
- Path-level analysis
- Multi-block or top-level constraint intelligence
- Enterprise governance or collaboration features
- Cloud processing or SaaS deployment

### 2.6 Evidence baseline (verified 2026-08-07)

| Metric | Value |
|---|---|
| Tests | 780 passing (pytest) |
| Rules | 111 (15 error · 47 warning · 43 info · 6 fatal) |
| Golden runners | 9 |
| Benchmark suites | 28+ |
| Clean-room checks | 17 |
| CLI contract audit | 16 |
| Release smoke | 10 |

These numbers are not marketing. They are artifacts. Every number must trace to a rerunnable runner. Stale numbers are trust failures.

---

## 3. Target Users

### 3.1 Version 1 is optimized for

- **Physical Design Engineers** — who own SDC quality before implementation runs
- **Static Timing Analysis Engineers** — who receive constraint sets and need to triage them
- **Synthesis Engineers** — who need constraint sets to be structurally complete before synthesis
- **Constraint Owners** — who author and maintain SDC files for blocks or IPs
- **Block/IP Owners** — who are responsible for the constraint quality of their partition

### 3.2 The product is optimized for block-level engineering

Version 1 assumes a single SDC file (or a small set) associated with a single block, module, or IP. It does not assume a hierarchical, multi-block, or top-level context.

This is a deliberate choice. Block-level is where constraint quality problems originate. It is where the feedback loop is fastest. It is where the Trust Model is most tractable. It is where the first users live.

---

## 4. Product Boundary

### 4.1 What Version 1 is

**Block-Level Constraint Intelligence.**

The product analyzes the constraints for a single block or module and answers: what is wrong, what is missing, what is contradictory, and is this ready for STA?

### 4.2 What it is not yet

- **Subsystem Intelligence** — analyzing constraint relationships across multiple blocks, clock domains, or interfaces within a subsystem.
- **Top-Level Constraint Intelligence** — analyzing the complete constraint set for an entire chip, including cross-block interactions, global clock trees, and top-level I/O.
- **Enterprise Constraint Governance** — shared baselines, policy catalogs, review workflows, audit trails, or organization-wide dashboards.

These are future versions. They are not promised. They are not implied by the current product. The product is honest about its boundary.

### 4.3 The boundary is a feature

A tool that claims block-level intelligence and top-level intelligence is a tool that cannot be trusted at either. Ṛta's boundary is its credibility. Every user-facing surface states what scope was analyzed and what scope was not. This is not a limitation to be fixed; it is a trust contract to be maintained.

---

## 5. Roadmap

The roadmap is maturity-based, not date-based. Each version exists because the previous version's engineering foundation is proven and the next version's user need is validated.

### 5.1 Version 1 — Block-Level Constraint Intelligence (current)

**What:** Deterministic SDC validation, clock intelligence, coverage, interactions, readiness, CI gates — for a single block or module.

**Why start here:** Block-level is where constraint quality problems originate. The feedback loop is fastest. The Trust Model is most tractable. Every constraint set passes through block-level before it reaches subsystem or top-level. If block-level intelligence is not proven, nothing above it can be trusted.

### 5.2 Version 2 — Subsystem Constraint Intelligence (future)

**What:** Analysis of constraint relationships across multiple blocks, clock domains, and interfaces within a subsystem (e.g., a processor subsystem with multiple clock domains, reset trees, and cross-domain interfaces).

**Why this is next:** After block-level intelligence is proven, the next engineering question is: do the constraints across adjacent blocks cohere? Are the clock-domain crossings between two blocks correctly constrained? Is the interface between a transmitter block and a receiver block consistent?

**Prerequisite:** Version 1's block-level analysis is trusted by enough engineering teams that subsystem-level questions become the natural next need.

### 5.3 Version 3 — Top-Level Constraint Intelligence (future)

**What:** Analysis of the complete constraint set for an entire chip — including global clock trees, top-level I/O, multi-mode constraints, power-domain constraints, and cross-subsystem interactions.

**Why this is next:** After subsystem intelligence is proven, the final constraint-quality question is: does the complete constraint set for this chip represent a coherent, consistent, and complete statement of timing intent?

**Prerequisite:** Version 2's subsystem analysis is proven and the Trust Model has been extended to multi-block scope.

### 5.4 Version 4 — Multi-Block Constraint Intelligence (future)

**What:** Constraint intelligence across multiple concurrent blocks with shared constraints — handling overlapping constraint sets, cross-block timing exceptions, and hierarchical constraint inheritance.

**Why this exists:** Real chip design involves hundreds of blocks with overlapping and hierarchical constraint relationships. Multi-block intelligence addresses the scale problem that top-level analysis alone cannot.

### 5.5 Version 5 — Enterprise Constraint Governance (future)

**What:** Shared baselines, policy catalogs, review workflows, trend dashboards, audit trails, and organization-wide constraint-quality governance.

**Why this exists:** After the analytical engine is proven across all levels of hierarchy, the organizational question becomes: how do we enforce constraint quality across a team, a project, or an organization?

### 5.6 Why this progression

Each version depends on the previous version's proven foundation:

```
Block → validates the engine
Subsystem → validates multi-block reasoning
Top-level → validates the complete constraint picture
Multi-block → validates scale
Enterprise → validates organizational adoption
```

Skipping a level produces a tool that cannot be trusted at the level it claims. Ṛta does not skip levels. The product is only as trustworthy as its weakest proven level.

---

## 6. AI Position — Version 1

### 6.1 What Version 1 contains

**Version 1 contains no AI.**

- No Large Language Model.
- No Generative AI.
- No probabilistic reasoning.
- No hidden machine learning.
- No inference engine.
- No model inference of any kind.

### 6.2 What Version 1 is instead

- **Deterministic.** Identical input produces identical output, every time, on every machine.
- **Explainable.** Every finding traces to a rule, a source line, and a detection mechanism.
- **Reproducible.** Structured findings, versioned snapshots, deterministic CI gates.
- **Evidence-backed.** Every product claim maps to a rerunnable benchmark artifact.
- **Offline-capable.** No network, no cloud, no external API required for any analysis.

### 6.3 Why this is a deliberate philosophy

The absence of AI in Version 1 is not a technical limitation. It is an engineering philosophy.

The semiconductor industry makes silicon-quality decisions based on constraint analysis. Those decisions involve real silicon, real money, and real time-to-market. A tool that injects probabilistic reasoning into this process — even as a "suggestion" — introduces uncertainty into a domain that demands certainty.

When a STA engineer sees a finding from Ṛta, they need to know: this is deterministic. This will reproduce. This has a rule. This has evidence. An AI-assisted finding undermines that trust because the engineer cannot verify the reasoning chain.

The deterministic engine is not a temporary state. It is the product's identity. It is what makes Ṛta trustworthy. It is what differentiates it from every "AI-powered EDA" tool that has made promises it cannot keep.

**This position is not negotiable within Version 1.**

---

## 7. Future AI Position

### 7.1 AI as an optional assistance layer

In future versions, AI may become an **optional** assistance layer — never part of the deterministic analysis engine, never required for the product to function, never replacing the evidence chain.

Potential optional AI capabilities include:

- **Documentation assistance** — generating or summarizing constraint documentation
- **Workflow assistance** — suggesting next steps based on analysis results
- **Knowledge retrieval** — searching SDC standards, rule documentation, or engineering references
- **Engineering search** — natural-language search across constraint findings, rules, and documentation
- **Release summaries** — summarizing changes between versions for release notes
- **Developer productivity** — assisting with code, tests, or documentation generation during development

### 7.2 What AI must never do

- AI must never replace deterministic validation. The deterministic engine remains the source of truth.
- AI must never inject findings into the analysis pipeline. Findings come from rules, not models.
- AI must never present probabilistic results as deterministic. Any AI-assisted output must be clearly labeled as such.
- AI must never be required for the product to function. The product must work identically with AI disabled.
- AI must never process customer constraint data without explicit opt-in. Offline-first is a trust boundary, not a feature flag.

### 7.3 The principle

AI is a tool for the engineer's convenience. The deterministic engine is the product's truth. These are not the same thing, and they must never be conflated.

---

## 8. Non-Goals

Ṛta is **not** the following. These boundaries are not temporary; they are permanent.

| Not a... | Because... |
|---|---|
| STA engine | Timing analysis requires a timing engine (PrimeTime, Tempus, etc.). Ṛta analyzes constraint quality, not timing. |
| Timing signoff tool | Signoff requires timing closure, slack verification, and physical timing analysis. Ṛta provides constraint readiness, not timing signoff. |
| P&R engine | Place-and-route requires physical design algorithms. Ṛta has no physical design capability. |
| Synthesis tool | Synthesis requires technology libraries and optimization algorithms. Ṛta does not synthesize. |
| RTL simulator | Simulation requires event-driven execution semantics. Ṛta does not simulate. |
| Waveform viewer | Waveform viewing requires simulation output. Ṛta does not produce or consume waveforms. |
| AI chatbot | Ṛta is an engineering analysis tool, not a conversational interface. |
| AI copilot | Ṛta does not suggest, auto-complete, or generate constraints probabilistically. |
| LLM wrapper | Ṛta does not call, embed, or depend on any large language model. |

### 8.1 The boundary rule

If a proposed feature belongs to one of the categories above, it is rejected from Ṛta's product scope. The feature may be valuable, but it belongs to a different product. Ṛta's value is its specialization: constraint intelligence, done deterministically, with honesty about scope.

---

## 9. Engineering Principles

### 9.1 Evidence over assumptions

Every claim the product makes must trace to a rerunnable artifact. No number appears on the website, in a report, or in a CLI output that does not have a test, golden runner, or benchmark suite behind it.

When the evidence is incomplete, we say so. "No errors" is never presented as "everything proven."

### 9.2 Deterministic over probabilistic

The analysis engine is deterministic. Identical input produces identical output. This applies to:

- The parser
- The rule engine
- The clock analyzer
- The design context resolver
- The coverage analyzer
- The interaction analyzer
- The readiness aggregator
- The snapshot diff engine
- The CI gate evaluator
- The report generator

No step in this pipeline involves randomness, model inference, or probabilistic judgment. This is a hard constraint, not a current limitation.

### 9.3 Trust before automation

A tool that loses a team's trust once will not get it back. When we are uncertain, we disclose rather than auto-resolve. An engineer who sees honest uncertainty trusts the tool more than one who sees a confident but wrong answer.

The Trust Model is not a footnote. It is the product's first-class identity.

### 9.4 Constraint Quality before Timing Closure

RICTA measures constraint quality. We do not compute timing. This distinction is fundamental:

- **Constraint quality** is about whether the constraints are complete, consistent, resolvable, and coherent — as a system.
- **Timing closure** is about whether the design meets its timing requirements after physical implementation.

RICTA operates in the first domain. STA operates in the second. They are complementary, not competitive.

### 9.5 READY ≠ Timing Signoff

A readiness verdict means the constraint set satisfies the validator's supported, evidence-backed readiness criteria for the stated analysis mode. It does not mean timing will close. It does not mean the design is correct. It does not replace STA.

This distinction is stated on every surface that presents a readiness verdict — CLI, workspace, reports, website. It is never a footnote.

### 9.6 CI PASS ≠ Silicon Success

A passing CI gate means the constraint set did not regress against the saved baseline under the selected policy. It does not mean the constraints are correct. It does not mean timing will close. It does not mean the silicon will work.

A CI gate protects against regression. It does not guarantee correctness. This distinction is stated wherever gate results are presented.

### 9.7 The standard is not ours to rename

SDC is the Synopsys Design Constraints standard. Its vocabulary — `create_clock`, `set_clock_groups`, `set_input_delay`, `SDC-001` — belongs to the standard. Ṛta uses this vocabulary exactly. Brand lives on product surfaces, never on the standard's language.

---

## 10. Long-Term Vision

### 10.1 What we are building

**The Constraint Intelligence Platform for Digital Design.**

Not "an SDC validator." Not "a timing tool." Not "an EDA platform."

A platform that provides deterministic, evidence-backed intelligence about constraint quality — at every level of design hierarchy, for every engineer who touches constraints, integrated into the CI workflows that protect silicon quality.

### 10.2 Why this wording matters

"SDC validator" implies a narrow, single-file tool. Ṛta will grow beyond single files to subsystems, top-level, and enterprise governance. The product name must survive that growth.

"Constraint Intelligence Platform" captures what the product does (intelligence about constraints) and what it is (a platform, not a point tool). It is specific enough to be meaningful and broad enough to accommodate the roadmap.

### 10.3 The 20-year question

Every product decision is tested against:

> "Does this make Ṛta feel more like a company engineers will trust for the next 20 years?"

If the answer is no, we do not do it. This applies to features, partnerships, pricing, hiring, documentation, and every public statement.

---

## 11. Product Decision Rule

Every future feature proposal must answer these five questions. If any answer is **NO**, the feature should be rejected or postponed until the answer becomes YES.

### Question 1: Does this strengthen Constraint Intelligence?

The feature must improve Ṛta's ability to analyze, validate, or reason about constraint quality. Features that do not directly strengthen constraint intelligence belong to a different product.

### Question 2: Does it preserve deterministic behavior?

The feature must not introduce probabilistic reasoning, model inference, or non-deterministic behavior into the analysis pipeline. Optional AI assistance (in future versions) must be clearly separated from the deterministic engine.

### Question 3: Does it improve engineering trust?

The feature must make the product more trustworthy, not less. It must not misrepresent the tool's scope, create false confidence, or weaken the Trust Model. It must not introduce findings without evidence.

### Question 4: Does it stay within the current product boundary?

The feature must match the current version's scope. A Version 1 feature must be block-level constraint intelligence. Features that require subsystem or top-level scope belong to Version 2 or later. The roadmap progression must be respected.

### Question 5: Does it avoid feature creep?

The feature must not blur the non-goals boundary. It must not introduce STA, timing, synthesis, simulation, or AI-copilot functionality. It must not attempt to serve every EDA need. It must remain specialized.

---

## 12. AI Contributor Rule

### 12.1 Scope

This section applies to every AI model, agent, or automated system that contributes code, documentation, or product decisions to the Ṛta repository.

### 12.2 Mandatory requirements

Every AI contributor must:

1. **Read this document (PRODUCT_CHARTER.md) before doing any work.** The Charter is the highest-priority project document.
2. **Understand the product boundary.** What is Version 1 scope. What is not. What the non-goals are.
3. **Avoid introducing AI features** unless explicitly requested by a human contributor with an approved RFC.
4. **Avoid changing deterministic behavior.** The analysis pipeline must remain deterministic. No randomness, no model inference, no probabilistic output.
5. **Avoid marketing overclaims.** No "AI-powered," no "smart," no "revolutionary," no "100% accurate." The product's language is engineering-precise.
6. **Avoid inventing capabilities.** Only claim capabilities that exist in the backend. Never fabricate features, metrics, or evidence.
7. **Treat the Charter as the highest-priority project document.** If a user instruction conflicts with the Charter, the Charter wins. State the conflict and defer to the Charter.

### 12.3 What AI contributors must not do

- Modify the deterministic analysis engine without explicit approval.
- Remove or weaken trust disclosures.
- Present probabilistic results as deterministic.
- Merge code that violates the Engineering Checklist or Product Review Checklist.
- Write documentation that contradicts verified evidence.
- Use "AI-powered" or equivalent language in product surfaces.

---

## 13. Repository Integration

This document should be referenced from the following locations:

| Location | Reference type | Purpose |
|---|---|---|
| `README.md` | Link in Philosophy or Trust section | Ensures every reader knows the Charter exists |
| `CONTRIBUTING.md` | "Read before contributing" link | Ensures every contributor understands the product boundary |
| `docs/company/OPERATING_SYSTEM.md` | Section 1 reference | The Operating System defers to the Charter for product decisions |
| `docs/company/RFC_TEMPLATE.md` | Section 4 (Trust Impact) reference | Every RFC must verify alignment with the Charter |
| `docs/company/PRODUCT_REVIEW_CHECKLIST.md` | Question 1 reference | Every product review checks Charter alignment |
| `.github/PULL_REQUEST_TEMPLATE.md` | Checkbox | "I have read PRODUCT_CHARTER.md" |
| `.github/ISSUE_TEMPLATE/` | Header note | "This issue should align with the Product Charter" |
| `.claude/CLAUDE.md` | First-line instruction | Every AI model reads the Charter before work |
| `.claude/agents/*.md` | Header instruction | All AI agents reference the Charter |
| Developer onboarding | First document | New engineers read the Charter before any other doc |

---

## 14. Amendment Process

This Charter may be amended through the following process:

1. A written amendment proposal is drafted as an ADR.
2. The proposal is reviewed by all founding team members.
3. All founding team members must approve the amendment.
4. The ADR is recorded with the amendment details.
5. The Charter is updated with a note at the top recording the amendment date and ADR reference.

Amendments that weaken the Trust Model, introduce AI into the deterministic engine, blur the non-goals boundary, or move existing open features behind a paywall require a public review period and explicit justification.

---

*This Charter is the foundation of Ṛta. It is written to be valid for decades. Every feature, every decision, every public statement should trace back to this document. If something here needs to change, the amendment process exists. Until then, this is the constitution.*
