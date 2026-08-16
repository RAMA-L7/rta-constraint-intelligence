# Ṛta — 12-Month Strategic Roadmap

> **Document kind:** strategy / planning · **Status:** planning only — no
> implementation in this package. Assumes a **small team (1–3 engineers)**.
> The engine is frozen; this roadmap spends capacity on distribution,
> evidence, and adoption, not new analysis features. All phases are
> evidence-gated via `STRATEGIC_DECISION_TREE.md`, and this roadmap uses
> **only the gates defined there** (G1, G2/G3/G4, G5, G6, G7) — it
> introduces no new thresholds.
>
> **Hierarchy:** the Product Charter and Functional Baseline outrank this
> document; the Decision Tree's definitions are canonical for all numbers.

---

## Phase structure

| Phase | Months | Objective | Gate out |
|---|---|---|---|
| **1 — Stabilize** | 1–2 | Ship the current product cleanly; make adoption friction-free | CLI usable by an external engineer in <10 min |
| **2 — Prove** | 3–5 | First real external usage; validate the loop assumptions | G1 evidence (≥5 external users, actionable findings) |
| **3 — Adopt** | 6–9 | Repeat usage + first CI-gate teams; measure what matters | G2/G3/G4 readouts |
| **4 — Differentiate** | 9–12 | Prove the regression-gate story with real evidence | G5 review (Plan C gate) or Plan B activation |

---

## Phase 1 — Stabilize (Months 1–2)

**Objective:** the working product is *reachable and usable* — install,
docs, demo, and the CI contract are solid before any outreach.

**Key deliverables**
- Publish current release to PyPI (v1.5.8+); verify `pip install
  rta-constraint-intelligence` end-to-end (fresh env, no `[web]` needed for
  CLI).
- One-place **exit-code + gate-policy contract** doc — **DONE**
  (`docs/features/README-14-ci-gate.md`, P2-10); fix exit-code 2 collision
  (P2-3).
- **GitHub Action** for the CI gate with JSON + JUnit output — **DONE in-repo**
  (`.github/actions/rta-gate`, CI self-test green); publish a versioned
  release tag for external adoption.
- **Test Drive realistic sample** with netlist (P2-6); **whats-new** in the
  tool (P2-8).
- "Run on your SDC in 5 minutes" guide; README/site install path verified.
- Make usage measurable: PyPI downloads, site→tool→CLI funnel, feedback
  themes (decision-tree sources).

**Success criteria:** an external engineer can install, run, and interpret
a real result unaided; all adoption friction items closed.

**Major risks:** PyPI publish credentials/cadence (R1); time spent on
polish instead of outreach.

**Decision gate:** G1 precondition (checkpoint feeding G1 — **not a
numbered gate**, no new threshold): does the 5-minute path work for one
non-founder engineer? If not, fix the funnel before outreach.

---

## Phase 2 — Prove (Months 3–5)

**Objective:** validate the two load-bearing assumptions: (1) findings are
**actionable**, (2) **diff/CI** is the retention loop.

**Key deliverables**
- 3–5 external engineers run the CLI on real SDCs; collect findings,
  actions taken, and "what would you use daily" feedback (interviews).
- Ship a documented **before/after** asset (one real SDC: findings → diff →
  gate → report).
- Measure feature-usage distribution and session depth (G2/G3 inputs).
- Publish the evidence/benchmark surface (Plan C C3 — cheapest, can start
  now): corpus + audits rerunnable, site proof page.

**Success criteria:** ≥5 distinct external users run a real workflow;
≥2 report an actionable finding; the diff/CI loop is named by ≥1 user as
something they'd miss.

**Major risks:** no external access (R1) — outreach is the deliverable;
sample corpus too small (P2-6).

**Decision gate:** **G1** — is the product valuable enough to continue?
Thresholds in `STRATEGIC_PRODUCT_PLAN.md` §6.

---

## Phase 3 — Adopt (Months 6–9)

**Objective:** convert one-off runs into repeat usage and the first
**CI-gate teams**.

**Key deliverables**
- GitHub Action + baseline workflow refined from real usage; ≥1 external
  repo running the gate.
- Repeat-usage mechanics: diff/report/review guidance front and center;
  regression-intelligence messaging (Plan A §1).
- Performance pass on large real SDCs (the working engineer's first
  complaint).
- Release cadence with visible whats-new; quarterly decision-tree readout.

**Success criteria:** ≥10 distinct external users/quarter; ≥20% return
within 30 days; ≥1 sustained CI-gate team; G2/G3/G4 signals measured.

**Major risks:** web-tool time drain (R4); utility framing winning over
loop framing (R2/B3).

**Decision gate:** **G4** (web vs CLI/CI primary path) and **G3**
(platform vs focused) — the data decides whether Plan A continues or
shifts toward Plan B framing.

---

## Phase 4 — Differentiate (Months 9–12)

**Objective:** prove the regression-gate story with real, published
evidence — or honestly re-scope (Plan B).

**Key deliverables**
- Documented before/after from ≥1 real team; benchmarks page reflecting
  real usage.
- If evidence supports: begin **Plan C C1** (constraint health/trends over
  time) as a scoped pilot with a collaborating team (G7).
- If triggers hit: execute **Plan B** re-scoping (story + distribution)
  instead — no engine changes either way.

**Success criteria:** G5 evidence (3+ sustained teams, 1+ CI-gate repo,
before/after) → Plan C justified; otherwise a documented, evidence-based
decision to stay focused (Plan A/B).

**Major risks:** differentiation weakness (R5/B4); expansion pulled too
early (R7).

**Decision gate:** **G5** (expand?) / **G6** (Plan B?) — the two
explicit exits from Plan A.

---

## Cross-phase rules

- **No engine changes** unless a documented correctness regression exists
  (frozen scope, `FUNCTIONAL_BASELINE.md` §2).
- **No new capabilities** in phases 1–3; Plan C items are pilots only in
  phase 4 and only on G5/G7 evidence.
- **Trust disclosures never weakened.**
- **Every phase ends with a measured gate** — the decision tree defines the
  numbers; no phase rolls into the next on enthusiasm.

*This roadmap spends capacity on distribution, evidence, and adoption of
the already-built loop. If the evidence says the loop isn't the product,
the roadmap's own gates switch us to Plan B — that is the point of having
them.*
