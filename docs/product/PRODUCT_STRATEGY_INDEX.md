# Ṛta — Product Strategy Index

> **Document kind:** index · **Status:** planning only. One page that tells
> an engineer or founder where the strategy lives, which plan applies when,
> and what to read first.

---

## Where the strategy is right now

**Plan A — The Constraint Regression Gate** (see `PLAN_A_PRIMARY.md`).

The product is functionally complete (19 capabilities across 18 catalog
cards — see `PRODUCT_PRIORITIZATION.md` §0; frozen engine; 1,228 full-suite
tests / 887 in the `rta/tests` manifest) but **adoption is unproven**. Plan
A spends the next cycle on
**distribution + evidence + adoption of one loop** — `validate → diff →
CI gate → report` — with the CLI/CI as the primary adoption path and the
web tool as demo/onboarding. No new engine features.

## When to use each plan

| Situation | Plan | Read |
|---|---|---|
| Default — proving and growing the current product | **Plan A** | `PLAN_A_PRIMARY.md` |
| Adoption stalls (2 quarters <10 external users/qtr, <1 CI team, or "too much/just want the check" feedback ≥5 users) | **Plan B** | `PLAN_B_CONTINGENCY.md` |
| Adoption proven (3+ sustained teams, 1+ real CI-gate repo, before/after story) and you want to expand | **Plan C** | `PLAN_C_EXPANSION.md` |
| Any review cycle / when a threshold is crossed | — | `STRATEGIC_DECISION_TREE.md` |
| Deciding what to fund next | — | `PRODUCT_PRIORITIZATION.md` |
| Planning the quarter / year | — | `12_MONTH_ROADMAP.md` |

## Read order

1. **This index.**
2. `STRATEGIC_PRODUCT_PLAN.md` — baseline, the three plans at a glance,
   surfaces, validation, risk register, gates G1–G7, and the blunt final
   recommendation (do this before any investment decision).
3. `PLAN_A_PRIMARY.md` — the active strategy in detail.
4. `STRATEGIC_DECISION_TREE.md` — the measurable triggers that tell you
   when to switch; review at every release/quarter.
5. `12_MONTH_ROADMAP.md` — the phased execution of Plan A.
6. `PRODUCT_PRIORITIZATION.md` — capability investment classes.
7. `PLAN_B_CONTINGENCY.md` / `PLAN_C_EXPANSION.md` — only when their
   triggers fire.

## Source-of-truth hierarchy

```
rta/docs/company/PRODUCT_CHARTER.md      →  constitution (scope, trust, determinism, non-goals)
docs/product/FUNCTIONAL_BASELINE.md      →  frozen functional contract, test counts, disclosures
docs/product/STRATEGIC_PRODUCT_PLAN.md   →  strategy umbrella, gates G1–G7, risks, recommendation
docs/product/STRATEGIC_DECISION_TREE.md  →  CANONICAL numerical triggers + metric definitions
PLAN_A / PLAN_B / PLAN_C                →  the three plans (evidence-gated)
12_MONTH_ROADMAP.md                     →  execution phases (uses only the tree's gates)
```

**No strategy document may override the Product Charter or the Functional
Baseline.** If a plan conflicts with the Decision Tree's numbers, the
Decision Tree wins.

## Ground rules (apply to everything in this package)

- **No implementation** — the engine, API, UI, routes, features, and tests
  are untouched by these documents.
- **Frozen engine** — `FUNCTIONAL_BASELINE.md` is the authority; rule
  semantics, IDs, severities, and calculations change only on a documented
  correctness regression.
- **Charter wins** — `rta/docs/company/PRODUCT_CHARTER.md` governs scope,
  trust, determinism/no-AI, and the V1 block-level boundary.
- **No feature is removed** — `PRODUCT_PRIORITIZATION.md` is an investment
  classification, not a removal list; it is also the canonical capability
  inventory (19 capabilities / 18 catalog cards).
- **Decision Tree is the canonical metrics source** — all user/CI/adoption
  numbers across Plan A/B/C and the roadmap use `STRATEGIC_DECISION_TREE.md`
  §2 definitions.
- **Nothing in Plan C is built or claimed** — every expansion is gated on
  adoption evidence (G5/G7).

## One-line summary

> The engine is done and trustworthy; the strategy is now about proving the
> **validate → diff → CI gate → report** loop with real engineers, keeping
> the web tool as the demo, and switching plans only when the measured
> triggers say so.
