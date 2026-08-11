# Ṛta — Brand Foundation

> **Document kind:** startup identity · source of truth for product naming, positioning, language and trust principles.
> **Date:** 2026-08-06 · **Version:** v1.3.0

---

## 1. Name

**Ṛta** — pronounced **“Ri-ta”**.

The visible, user-facing name of the product is always the Unicode form **Ṛta**.
The technical ASCII identifier used in code, packaging and URLs is **`rta`**
(e.g. the `rta` CLI entry point). This split is documented in
[REPOSITORY_ARCHITECTURE.md](REPOSITORY_ARCHITECTURE.md) and enforced by
`BRAND_MIGRATION_AUDIT.md`.

## 2. Pronunciation

“Ri-ta” — two syllables, stress on the first. The leading character is a
lowercase **r with a dot below** (U+1E5A), which is what makes the wordmark
distinctive. Keep the dot in all brand copy: **Ṛta**, never “Rta”.

## 3. Origin

The name is inspired by the ancient concept of *Ṛta*: order, coherence, rule —
the idea of many individual elements fitting together into an ordered whole.

## 4. Meaning

For us, the meaning is structural, not decorative:

> Clocks, delays, exceptions, design objects, modes and relationships may each
> appear valid independently while the complete constraint system remains
> incomplete, contradictory or ambiguous. Ṛta brings structure, evidence and
> clarity to that system — before STA.

We make **no exaggerated historical, religious, linguistic or philosophical
claims**. The cultural inspiration lives in the philosophy, never as visual
decoration. No temples, no religious iconography, no epic characters, no
ornamental clichés.

## 5. Product philosophy

**“Order in timing intent.”**

A constraint set is not a list of commands — it is a coherent statement of
intent about how a design is meant to run. Ṛta treats it that way: it checks
individual constraints, then checks how constraints relate to each other, to
the design, and to the engineer's own regression baseline.

## 6. Problem statement

Before STA, constraint problems are expensive to find:

- a delay that exceeds its own clock period,
- a generated clock whose ancestor cannot be resolved,
- two `set_case_analysis` commands contradicting each other,
- an input bus that is never constrained at all,
- a small change that silently breaks a previously passing gate.

Each of these is individually detectable. Most are only visible when the
constraints are viewed as a system. Ṛta performs that system-level analysis
deterministically, locally, and with an explicit trust boundary.

## 7. Category

**Constraint Intelligence for Digital Design.**

Ṛta is a **constraint-quality / Pre-STA engineering product** — not an STA
replacement and not a generic EDA platform. Its specialization is its
strength.

## 8. Target users

Initial:

1. Physical Design engineers
2. STA engineers
3. Synthesis engineers working with constraints
4. Implementation engineers
5. Small VLSI teams

Later:

6. Semiconductor design teams
7. CAD / methodology teams
8. Enterprise implementation organizations
9. CI-driven semiconductor workflows

## 9. Core value proposition

Move constraint verification left. Engineers find constraint-quality problems
**before** STA tooling consumes the constraint set — with deterministic,
evidence-backed analysis that is reproducible from a CLI, a browser, or a CI
pipeline.

## 10. Positioning

**Working positioning:** *Bring order to timing intent before STA.*

Ṛta sits between constraint authoring and STA:

```
Design / SDC authoring
        ↓
       Ṛta
        ↓
Constraint understanding · validation · design awareness ·
coverage · interactions · readiness · regression protection
        ↓
       STA
```

**What Ṛta is:** a deterministic, evidence-backed, local-first constraint
intelligence layer with explicit support boundaries.

**What Ṛta is NOT:**

- not an STA engine,
- not a timing signoff tool,
- not “AI-powered” (no LLMs, no model inference — analysis is deterministic),
- not a cloud service (it runs locally; no data leaves the machine),
- not a generic EDA platform.

## 11. Brand principles

1. **Precision over hype** — we say exactly what we analyze and what we do not.
2. **Deterministic by design** — identical input, identical output, every time.
3. **Evidence-backed** — every claim in the product maps to a finding, a rule,
   or a benchmark artifact.
4. **Honest boundaries** — READY ≠ STA signoff; coverage ≠ correctness; CI pass
   ≠ timing closure.
5. **Engineering density** — the interface respects the engineer's attention.
6. **Restraint** — no magic, no revolution, no guaranteed closure.

## 12. Product principles

1. Move constraint verification left.
2. Analyze constraints as a system, not as isolated commands.
3. Design context upgrades analysis — and its absence is disclosed, never hidden.
4. Findings must trace to source (line, and line₂ where two lines matter).
5. Regression protection is a first-class capability, not an afterthought.
6. Every status is communicated with more than color (icon + label + semantics).

## 13. Trust principles

1. Show what was validated, what was partially validated, and what was skipped.
2. Distinguish *trust limitation* from *constraint warning*.
3. Never fabricate progress, percentages or confidence.
4. When context is missing (no netlist, Tcl execution constructs), say so.
5. An engine failure must never read as a passing result.

## 14. Open-source philosophy

Ṛta Community is open source (MIT). The deterministic analysis engine, the
parser, the rule registry, the CLI and local reports are open. See
[OPEN_CORE_STRATEGY.md](OPEN_CORE_STRATEGY.md) for the planned boundary —
nothing that exists today is moved behind a paywall.

## 15. Future commercial philosophy

Any future commercial offering must extend capability (policies, shared
baselines, team workflows, enterprise CI, governance) — it must never degrade
what is already open. No licensing or paywalls are implemented in this phase.

## 16. Tone of voice

Serious semiconductor infrastructure. Calm, precise, engineering-first.
Prefer the vocabulary of constraint intelligence (see §18). Never market-speak
like “magic”, “revolutionary”, “AI-powered”, “100% accurate”, “guaranteed
timing closure”.

## 17. Terminology

Keep the SDC standard's terminology intact:

- **SDC file / SDC command / SDC rule / SDC-046** — always SDC, never “Ṛta file”.
- **check_sdc()**, **sdc_preprocess.py** — technical identifiers unchanged.
- Product surfaces use Ṛta: **Ṛta Validate**, **Ṛta Clocks**, **Ṛta Readiness**, …

Bad: *RTA-046*, *Ṛta clock constraint language*. Good: *SDC-046*, *Ṛta Validate*.

## 18. Naming architecture

| Layer | Identifier | Example |
|---|---|---|
| Visible brand | `Ṛta` | website, app, reports, README |
| Product modules | `Ṛta Validate`, `Ṛta Clocks`, `Ṛta Context`, `Ṛta Coverage`, `Ṛta Interactions`, `Ṛta Readiness`, `Ṛta Diff`, `Ṛta CI` | workspace pages |
| Technical ASCII | `rta` | `rta check design.sdc` |
| Backward-compatible CLI | `sdc-tools` | `sdc-tools check design.sdc` |
| Package / wheel | `sdc-tools` / `sdc_tools-*` | pip install (unchanged this phase) |
| Rule codes | `SDC-001…`, `CHG-*` | unchanged |
| Release | `v1.3.0` | unchanged |

## 19. What Ṛta validates (short form)

The full trust disclosure lives in [TRUST_MODEL.md](TRUST_MODEL.md). In brief:
structurally-valid SDC semantics, clock relationships, object references,
coverage and readiness — with design-aware upgrades when a netlist is
supplied, and honest “not analyzed” states otherwise.
