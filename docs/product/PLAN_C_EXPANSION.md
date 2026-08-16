# Ṛta — Plan C: Expansion Paths (Optional, Evidence-Gated)

> **Document kind:** strategy / Plan C (optional expansion) · **Status:**
> planning only — **every item in this document is FUTURE / GATED**: none of
> it is implemented or claimed to exist. Plan C becomes justified only after
> block-level adoption evidence (G5/G7 in `STRATEGIC_PRODUCT_PLAN.md`,
> canonical triggers in `STRATEGIC_DECISION_TREE.md` §2). Every expansion
> must respect the Product Charter: deterministic engine, offline trust,
> honest scope, no AI in the analysis pipeline, and the V1 block-level
> boundary until evidence proves the next level.
>
> **Hierarchy:** the Product Charter and Functional Baseline outrank this
> document; the Decision Tree's definitions outrank any number restated
> here.

---

## 0. Trigger discipline

Plan C is **not** a roadmap to start now. It is a menu of expansion
hypotheses, each with a specific evidence gate. The common precondition:

> **G5 evidence:** ≥3 teams with sustained (≥1 quarter) block-level usage;
> ≥1 real repo running the CI gate; a documented before/after from real
> usage; and a specific hypothesis about which adjacent problem users
> actually have.

Without that, Plan C items are deferred — building them early is the
single most likely way to waste the engine's credibility.

---

## 1. Candidate expansions (each: value · feasibility · data · cost · differentiation · risk · why after evidence)

### C1 — Constraint Regression / Health Intelligence (near-term, most aligned)

**What:** Turn the existing diff + baseline + readiness machinery into
*constraint health over time* — per-block baseline history, trend of
findings (new/resolved/changed), debt accumulation, and a "constraint
health report" a team reviews on a regular cadence. Deterministic
throughout.

- **Engineering value:** Answers "is this block getting healthier or
  drifting?" — the question diff answers for one change, at team scale.
- **Customer value:** A review artifact teams already need; regression
  intelligence is why they keep using Ṛta (Plan A's retention loop).
- **Technical feasibility:** High — built on verified diff/readiness/
  baseline/CI machinery; no new analysis engine.
- **Data requirements:** Per-block baseline snapshots over time (JSON
  schema v2 already exists); no netlist beyond current optional use.
- **Infrastructure cost:** Low — local/self-hosted files, no server.
- **Differentiation:** Strong — incumbents don't provide constraint
  *regression* intelligence for blocks.
- **Risk:** Low-medium — scope creep into dashboards; must stay
  deterministic and honest (health ≠ timing).
- **Why after evidence:** Only useful if teams actually maintain baselines;
  that behavior must be proven by real CI-gate usage first.

### C2 — Subsystem / Cross-Block Constraint Intelligence (charter V2)

**What:** Constraint relationships across adjacent blocks — clock-domain
crossings between blocks, interface consistency between a transmitter and
receiver, coherent constraint sets for a subsystem. This is the charter's
stated Version 2.

- **Engineering value:** Catches cross-block constraint incoherence that
  block-level analysis cannot see.
- **Customer value:** The next question every team asks after trusting
  block-level results.
- **Technical feasibility:** Medium-high — extends existing clock
  relations/interactions/diff machinery to multiple files; new trust-scope
  semantics required (the charter's scope model must extend honestly).
- **Data requirements:** Multiple SDCs + cross-block topology (netlists or
  a manifest); more complex inputs.
- **Infrastructure cost:** Low-medium (local), but analysis design cost is
  real (relationship model, scope disclosure).
- **Differentiation:** High if done with the same determinism/evidence
  discipline.
- **Risk:** Medium — the hardest part is the *honest scope model*, not the
  math; overclaiming cross-block coverage would damage trust.
- **Why after evidence:** Charter prerequisite — block-level must be
  trusted by real teams before subsystem reasoning is credible.

### C3 — Benchmark & Evidence Platform (credibility flywheel)

**What:** A public, rerunnable evidence surface: the corpus, the parity
audits, clean-room gates, and a "run the benchmark yourself" page —
presented as the proof posture.

- **Engineering value:** Forces the evidence system to stay honest and
  current (already the project rule).
- **Customer value:** Directly answers "prove it" objections (Plan B B10);
  converts determinism/no-LLM from a claim into a demonstration.
- **Technical feasibility:** High — the artifacts exist; work is
  packaging/presentation.
- **Data requirements:** None beyond the existing corpus.
- **Infrastructure cost:** Low — GitHub Pages static.
- **Differentiation:** High for a startup; rare to publish the full proof.
- **Risk:** Low — but it must never present benchmarks as timing/quality
  guarantees (frozen disclosures apply).
- **Why after evidence:** Do this *as soon as* real usage produces
  before/after stories — it can start before full Plan C.

### C4 — CI Constraint Governance for Organizations (later)

**What:** Policy catalogs, per-team gate tiers, audit trails, and
org-wide constraint-quality enforcement across many repos.

- **Engineering value:** Enforces "the same standard for everyone" at
  org scale.
- **Customer value:** The buying motion for PD/STA organizations; the
  enterprise wedge.
- **Technical feasibility:** Medium — policy engine exists; needs
  multi-repo orchestration, secret/config management, audit storage.
- **Data requirements:** Org-wide SDC/baseline/policy stores.
- **Infrastructure cost:** Medium-high (server, storage, auth).
- **Differentiation:** Strong but contested space.
- **Risk:** High for a small team — multi-user/auth/SSO/audit is a
  different engineering domain; slow sales cycles.
- **Why after evidence:** Only after ≥3 orgs demonstrate sustained
  block-level + CI usage and explicitly request governance.

### C5 — Optional AI Assistance Layer (charter §7, strictly bounded)

**What:** Optional, clearly-labeled assistance *outside* the deterministic
pipeline: documentation generation, finding summaries, next-step
suggestions, natural-language search over rules/docs. Never in the engine;
never required; opt-in; offline boundary preserved for constraint data.

- **Engineering value:** Lowers the barrier to acting on findings.
- **Customer value:** Convenience — but it is **not** the product's truth.
- **Technical feasibility:** High for a wrapper; the discipline is in the
  boundaries (charter §7.2).
- **Data requirements:** None for constraint data (must respect the
  no-processing-without-opt-in rule).
- **Infrastructure cost:** Medium (model hosting or API keys — breaks
  offline if used).
- **Differentiation:** None by itself; "AI" is table stakes elsewhere.
- **Risk:** High to the brand if it leaks into analysis or reads as
  probabilistic results; the charter makes this non-negotiable.
- **Why after evidence:** Only after core value is proven and users ask
  for assistance; and only if it can be delivered without touching the
  deterministic engine or the offline promise.

### C6 — Hosted Workspace / Enterprise Multi-Project SaaS (highest cost)

**What:** A hosted multi-user workspace with shared sessions, auth,
project stores, and team dashboards.

- **Engineering value:** Marginal to the engine; high to the business model.
- **Customer value:** Real for enterprises; **directly conflicts** with the
  current offline/no-upload trust story (risk B5).
- **Technical feasibility:** Low-medium today (Streamlit single-user, no
  auth; would need a real product build).
- **Data requirements:** Customer SDC on servers — the opposite of the
  current position.
- **Infrastructure cost:** High (hosting, auth, ops, security).
- **Differentiation:** Low; crowded.
- **Risk:** High — would likely destroy the trust position that makes the
  offline CLI valuable.
- **Why after evidence:** Only if revenue signals prove enterprises will
  pay enough to justify rebuilding the trust story; otherwise C6 is
  rejected on charter grounds.

---

## 2. Expansion ordering and dependencies

```
G5 evidence (real block-level + CI usage)
        │
        ├─► C3 (benchmark/evidence platform)      — cheapest, do first, even during Plan A
        ├─► C1 (regression/health intelligence)   — next, reuses verified machinery
        ├─► C2 (subsystem intelligence)           — charter V2, after block-level trust
        ├─► C4 (org governance)                   — after ≥3 orgs ask
        └─► C5 (optional AI assist) / C6 (SaaS)   — last, gated, risk-managed
```

Dependencies: C3 can start inside Plan A (it is evidence packaging). C1
requires baseline behavior that Plan A's CI-gate adoption creates. C2 is
the charter's V2 gate. C4/C5/C6 require G7-level justification.

## 3. What must NOT be expanded into (charter non-goals, permanent)

- STA engine, timing signoff, P&R, synthesis, simulation, waveform tools.
- AI copilot / LLM wrapper that touches the analysis pipeline.
- Anything that weakens the offline/no-upload/no-LLM position.
- Anything that claims subsystem/top-level scope before the evidence gate.

*Plan C is a menu, not a promise. Each item lists its evidence gate, and
none of it is built in this package or presented as existing.*
