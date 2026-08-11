# AI Contributor Guide

> **Document kind:** mandatory pre-read for every AI model, agent, or automated system working on the Ṛta repository.
> **Authority:** implements PRODUCT_CHARTER.md §12. If this guide conflicts with the Product Charter, the Charter wins.
> **Last updated:** 2026-08-07

---

## Read Before Every Task

Before writing any code, documentation, or product decision, verify:

- [ ] I have read `docs/company/PRODUCT_CHARTER.md`.
- [ ] I understand what Ṛta is (Constraint Intelligence Platform).
- [ ] I understand what Ṛta is NOT (not STA, not signoff, not AI, not an LLM wrapper).
- [ ] I understand the current version scope (Version 1: Block-Level Constraint Intelligence).
- [ ] I understand the Trust Model and its six statuses.
- [ ] I understand that the analysis engine is deterministic — no randomness, no inference, no probabilistic output.
- [ ] I understand the five Product Decision Questions (Charter §11).
- [ ] I understand the non-goals (Charter §8).
- [ ] I will not introduce "AI-powered," "smart," or "revolutionary" language.
- [ ] I will not invent capabilities the backend does not have.
- [ ] I will not present probabilistic results as deterministic.

---

## 1. What Ṛta Is

Ṛta is a semiconductor software startup building a **Constraint Intelligence Platform** for digital design.

The first product validates SDC (Synopsys Design Constraints) files deterministically — checking constraint quality, clock relationships, coverage, interactions, and readiness before STA consumes the constraint set.

The analysis engine is Python. It is deterministic. It runs offline. It makes no network calls. It contains no LLM, no model inference, and no probabilistic reasoning.

The product's credibility is built on evidence: every claim traces to a rerunnable benchmark artifact. Stale claims are trust failures.

---

## 2. Product Charter Hierarchy

The Product Charter is the constitution. All other documents implement it.

```
PRODUCT_CHARTER.md           ← constitution (highest authority)
    ↓
OPERATING_SYSTEM.md          ← how we work
    ↓
RFC_TEMPLATE.md              ← how we propose
ADR_TEMPLATE.md              ← how we decide
ENGINEERING_CHECKLIST.md     ← how we verify
PRODUCT_REVIEW_CHECKLIST.md  ← how we review
STARTUP_BACKLOG.md           ← what we do next
    ↓
AI_CONTRIBUTOR_GUIDE.md      ← this document
NEW_ENGINEER_ONBOARDING.md   ← human onboarding
REPOSITORY_MAP.md            ← where things are
GLOSSARY.md                  ← what things mean
```

If any document conflicts with the Product Charter, the Charter wins. State the conflict and defer to the Charter.

---

## 3. Which Documents Must Be Read First

| Order | Document | Why |
|---|---|---|
| 1 | `PRODUCT_CHARTER.md` | Defines what the product is, what it is not, and what must never change |
| 2 | `REPOSITORY_MAP.md` | Explains the repository structure and where work belongs |
| 3 | `GLOSSARY.md` | Defines the vocabulary — using the wrong term is a product error |
| 4 | This document (AI_CONTRIBUTOR_GUIDE.md) | Defines how you must behave |
| 5 | `OPERATING_SYSTEM.md` | Defines the processes and standards |

Documents 1–3 are mandatory. Document 4 defines your behavior. Document 5 defines the team's processes. If your task is a code change, also read `ENGINEERING_CHECKLIST.md`. If your task is a product surface change, also read `PRODUCT_REVIEW_CHECKLIST.md`.

---

## 4. Product Boundaries

### 4.1 What Version 1 does

- Deterministic SDC validation (111 rules)
- Clock intelligence (inventory, hierarchy, relations)
- Constraint coverage (object-level, bus-level, bit-range)
- Constraint interactions (duplicates, overrides, contradictions, overlaps)
- Design-aware validation (netlist object resolution)
- Readiness analysis (seven dimensions)
- Trust transparency (per-result scope disclosure)
- Readiness diff (semantic baseline comparison)
- CI gate (declarative policies, deterministic exit codes)
- Reports (HTML, JSON, JUnit)
- Benchmarks (golden runners, adversarial suites, release verification)

### 4.2 What Version 1 does NOT do

- Timing propagation, slack calculation, or physical timing analysis
- Clock latency or skew computation
- Path-level analysis
- Subsystem, top-level, or multi-block constraint intelligence
- Enterprise governance, collaboration, or dashboards
- Cloud processing or SaaS deployment
- AI-assisted analysis, prediction, or suggestion

### 4.3 The boundary rule

If you are unsure whether a proposed change falls within Version 1's scope, apply the five Product Decision Questions (Charter §11). If any answer is NO, stop and state the concern.

---

## 5. What NOT to Change

### 5.1 Never modify without explicit approval

- The deterministic analysis pipeline (parser, rules, clock_relations, design_context, design_coverage, constraint_interactions, constraint_readiness, readiness_diff, finding_identity, policy_engine, support_boundary, rules_registry, sdc_preprocess, tcl_resolver, wildcard_analyzer, constraint_diff, custom_rules)
- The Trust Model's status vocabulary (VALIDATED, PARTIALLY_VALIDATED, NETLIST_REQUIRED, TCL_EXECUTION_REQUIRED, UNSUPPORTED, NOT_VALIDATED)
- The exit-code contract (0 pass, 1 gate failed, 2 invalid invocation, 3 engine failure)
- The readiness verdict vocabulary (READY, READY_WITH_ADVISORIES, REVIEW_REQUIRED, BLOCKED, INSUFFICIENT_CONTEXT)

### 5.2 Never do

- Remove or weaken trust disclosures
- Present probabilistic results as deterministic
- Use "AI-powered," "smart," "revolutionary," or similar language
- Invent capabilities the backend does not have
- Fabricate test counts, rule counts, or benchmark numbers
- Add external runtime dependencies to the core engine without an ADR
- Change the CLI exit-code contract
- Rename SDC standard vocabulary

---

## 6. How to Work

### 6.1 Before starting

1. Read the documents in §3 order.
2. Understand the task. What is the problem? Who is affected?
3. Check: does this task conflict with any item in §5? If yes, stop.

### 6.2 While working

1. **Preserve determinism.** The analysis pipeline must remain deterministic. No randomness, no model inference, no probabilistic output.
2. **Preserve evidence.** Every claim the product makes must trace to a rerunnable artifact. If you change a number, re-run the artifact that produced it.
3. **Preserve trust.** Every surface must carry its trust disclosure. Do not remove, weaken, or bury trust status.
4. **Write code that reads like the surrounding code.** Match comment density, naming conventions, and idiom. The codebase is Python (backend), vanilla JavaScript (workspace), and static HTML/CSS (website).
5. **Write documentation that states what exists, not what should exist.** Present tense for current behavior. Past tense for what was implemented. Never describe unimplemented features as current.

### 6.3 After finishing

1. Run `python -m pytest tests/ -q` — all tests must pass.
2. Verify the relevant golden suite passes (if the change touches the analysis pipeline).
3. Verify evidence numbers are current (if the change affects any claimed number).
4. Update documentation (README, CHANGELOG, feature docs) if the change is user-facing.
5. Record the decision as an ADR (if the change is architectural).

---

## 7. Coding Philosophy

- **Deterministic.** Same input → same output. No exceptions.
- **Evidence-backed.** Every product claim has a test or benchmark.
- **Bounded.** The tool has a clear scope. Do not expand scope without a Charter-aligned decision.
- **Honest.** When the tool does not know, it says so. When a check is partial, it says so. When context is missing, it says so.
- **Defensive.** An engine failure can never produce a passing result. This discipline extends to every function.
- **Simple.** No clever code that is hard to verify. No magic. No hidden behavior.

---

## 8. Documentation Philosophy

- **Technical, not marketing.** Engineering documentation does not use hype words.
- **Present tense for what exists.** "The validator checks" not "the validator will check."
- **Numbers have sources.** Every claim of "780 tests" must be verifiable by running the suite.
- **Trust boundaries are prominent.** Every capability page carries its trust disclosure as a first-class section.
- **One canonical product name.** The product is "Ṛta" (with the dot below, U+1E5A). The CLI is `rta`. The standard's vocabulary is never renamed.

---

## 9. Trust Philosophy

Trust is the product's most valuable asset. It is earned by:

1. Telling the truth about what was checked and what was not.
2. Never presenting "no errors" as "everything proven."
3. Never presenting coverage as correctness.
4. Never presenting readiness as signoff.
5. Never presenting CI pass as silicon success.
6. Never fabricating or approximating evidence numbers.

It is destroyed by:

1. Stale evidence numbers on any user-facing surface.
2. Omitting trust disclosures from surfaces that compute them.
3. Using marketing language that implies capabilities the product does not have.
4. Introducing probabilistic reasoning into the deterministic analysis path.

---

## 10. Review Expectations

Every change will be reviewed against:

1. **The Engineering Checklist** (`ENGINEERING_CHECKLIST.md`) — for code changes.
2. **The Product Review Checklist** (`PRODUCT_REVIEW_CHECKLIST.md`) — for user-facing changes.
3. **The Product Charter** — for alignment with the product's identity, boundary, and principles.
4. **The Trust Model** — for impact on what the tool discloses.

If your change cannot satisfy these reviews, it should not be merged. State the concern and propose an RFC or ADR.

---

## 11. Common Mistakes

| Mistake | Why it is wrong | Correct behavior |
|---|---|---|
| Saying "100+ rules" when the count is 111 | Stale or approximate numbers violate the evidence principle | State the exact verified number |
| Calling the product "an SDC validator" | Undersells the product; the Charter calls it a Constraint Intelligence Platform | Use the Charter's language |
| Using `sdc-tools check` as the primary CLI | `rta` is the primary CLI; `sdc-tools` is the alias | Lead with `rta check` |
| Describing the Trust Model as a "limitation" | The Trust Model is a feature — it is the product's credibility mechanism | Describe it as a transparency feature |
| Saying "AI-powered" anywhere | The product contains no AI in Version 1; this language violates the Charter | Never use AI-related marketing language |
| Presenting coverage percentage as quality | Coverage ≠ correctness; this is a first-class trust principle | Always state "coverage ≠ correctness" |
| Changing the parser without re-running golden suites | Parser changes can silently break determinism | Always re-run `run_golden.py` after parser changes |
| Adding external dependencies without an ADR | Dependencies affect the offline-capable, clean-room, and single-wheel guarantees | Open an ADR before adding any dependency |
| Describing features as "coming soon" in docs | Unimplemented features should not appear in current-state documentation | Document only what exists |
| Removing a trust disclosure to "clean up" the UI | Trust disclosures are first-class content, not clutter | Trust disclosures are mandatory on every relevant surface |

---

## 12. Forbidden Assumptions

Do not assume:

1. **That "no errors" means "correct."** A clean result means no rule fired, not that the constraints are correct.
2. **That the product does timing analysis.** It does not. It does constraint quality analysis.
3. **That the product is an AI tool.** It is not. It is a deterministic analysis engine.
4. **That benchmark numbers are approximate.** They are exact, verified, and current as of the stated date.
5. **That the Trust Model is optional.** It is mandatory on every surface that presents analysis results.
6. **That the product competes with STA tools.** It complements them. It is not a replacement.
7. **That the open-core boundary is negotiable.** It is defined in the Charter and requires amendment to change.
8. **That the deterministic engine can be made probabilistic "for now."** It cannot. The engine is deterministic. Period.
9. **That the product serves top-level or enterprise scope.** Version 1 is block-level. Future versions are not yet implemented.
10. **That documentation can describe unimplemented features as current.** Only implemented, tested, and verified capabilities are documented.

---

## 13. AI Behavior Rules

### 13.1 Before every task

- Read the Product Charter.
- Read this guide.
- Verify the task does not conflict with §5 (What NOT to Change).

### 13.2 During every task

- Do not introduce probabilistic reasoning.
- Do not invent capabilities.
- Do not use marketing language.
- Do not remove trust disclosures.
- Do not change the analysis pipeline without explicit approval.
- Do not present unverified numbers.
- Do not assume the product does more than it does.

### 13.3 After every task

- Verify tests pass.
- Verify evidence numbers are current.
- Verify documentation is accurate.
- Verify trust disclosures are present on affected surfaces.

### 13.4 When uncertain

- State the uncertainty explicitly.
- Do not guess. Do not approximate. Do not fabricate.
- If the task requires a decision that conflicts with the Charter, defer to the Charter.
- If the task requires a decision outside your authority, state what decision is needed and who should make it.

---

*This guide is the operational implementation of PRODUCT_CHARTER.md §12. It exists because AI models can produce confident, plausible, and wrong output — and this repository serves engineers who trust their tools with silicon-quality decisions. The bar is high. This guide enforces it.*
