# Ṛta — Strategic Decision Tree

> **Document kind:** strategy / decision framework · **Status:** planning
> only. Companion to `STRATEGIC_PRODUCT_PLAN.md` (gates + risk register) and
> `PLAN_A/B/C`. Every branch has a **measurable trigger** — no "if users
> don't like it" language. Measurement sources are defined in §3; cadence:
> review at each release or quarterly, plus on any crossed threshold.
>
> **This document is the canonical source for every numerical trigger and
> metric definition in the strategy package.** If `PLAN_A/B/C`, the umbrella,
> or the roadmap disagree with §2, this document wins.

---

## 1. The tree

```
                            CURRENT ṚTA (block-level, engine frozen)
                                        │
        ┌───────────────────────────────┼────────────────────────────────┐
        │                               │                                │
  PLAN A runs                    G1 fails (no external               Org/complexity
  (validate→diff→CI→report)      value signal)                       pressure
        │                               │                                │
   ┌────┴────────────────┐              │                          re-scope/focus
   │                     │              │                              (B11)
   G1 passes          G2: which         │
   (≥10 users/qtr,      capabilities    │
   ≥20% repeat,         matter?         │
   ≥1 CI team)          │               │
   │                focused (1-2)   broad (4+)        PLAN A fails adoption (2 qtrs)
   ▼                │               │                 <10 users/qtr or <1 team
 ┌─────────┐    ┌────┴─────┐   ┌────┴─────┐                      │
 │ G4:      │    │ G3:      │   │ G3:      │                      ▼
 │ web vs   │    │ utility  │   │ platform │              ┌─────────────────┐
 │ CLI/CI   │    │ → Plan B │   │ → keep A │              │ PLAN B (wedge + │
 └────┬─────┘    └──────────┘   └──────────┘              │ CLI-first)      │
      │                                                   └────────┬────────┘
  CLI/CI-first (keep A)  ·  web-first (rebalance A)                │
                                                          B succeeds? (≥20 external
                                                          users/qtr, ≥2 sustained CI
                                                          teams, ≥1 public ref)
                                                          │          │
                                                     yes │          │ no → honest
                                                         ▼          │   demand problem;
                                                     G5: expand    │   re-evaluate G1
                                                     evidence?     │   (not more build)
                                                         │          │
                                             3+ teams, 1+ CI repo,│
                                             before/after story ──┘
                                                     │
                                                     ▼
                                              PLAN C (menu, gated):
                                              C3 evidence platform → C1 health →
                                              C2 subsystem (charter V2) → C4/C5/C6
```

---

## 2. Canonical metric definitions (authority)

The definitions below are canonical for the entire strategy package (Plan A,
Plan B, Plan C, umbrella, roadmap). All triggers use **quarterly** windows
unless stated otherwise.

| Metric | Canonical definition |
|---|---|
| **External user** | A distinct engineer **outside the founding circle** who runs a real workflow (CLI, CI gate, or web tool) in the measurement window |
| **Measurement window** | Trailing quarter (3 months) |
| **External users / quarter** | Count of distinct external users in the trailing quarter |
| **Repeat usage** | ≥20% of external users return within 30 days of their first run |
| **Actionable finding** | A finding the user says they used or would act on (interview or feedback; not inferred) |
| **Sustained CI team** | A team running the CI gate on a real repository for ≥1 continuous month |
| **G1 — value signal** | ≥5 distinct external users run a real workflow in the quarter; ≥2 report an actionable finding |
| **Plan A continuation** | ≥10 external users/quarter **and** ≥20% repeat usage **and** engine green (1,228 full-suite tests, parity intact) |
| **Plan A success (v2.0 review)** | ≥10 external users/quarter · ≥20% repeat usage · ≥1 sustained CI team · ≥2 users name a workflow they would miss (Diff or CI named in ≥1 case) |
| **Plan B activation** | **Two consecutive quarters** with any of: <10 external users/quarter · <1 sustained CI team · platform-confusion feedback from ≥5 distinct users |
| **Plan B success** | ≥20 external users/quarter · ≥2 sustained CI teams · ≥1 public "we run Ṛta on every SDC change" reference |
| **Plan C activation (G5)** | ≥3 teams with sustained (≥1 quarter) block-level usage **and** ≥1 real repo running the CI gate **and** a documented before/after **and** a specific expansion hypothesis |
| **G7 — Plan C pilot** | G5 evidence **plus** a collaborating partner willing to pilot a specific expansion |

Notes:

- **PyPI downloads are a proxy, not the user metric.** Installs indicate
  reach; only distinct external users who run a workflow count toward the
  thresholds above.
- Feature-usage distribution and feedback themes feed G2/G3 but do not, by
  themselves, trigger a plan change.

---

## 3. Measurement sources (what the triggers read)

| Signal | Source (current product) | Notes |
|---|---|---|
| Active users (distinct, external) | PyPI downloads (proxy — quarterly cadence), GitHub stars/issues, Streamlit Cloud sessions, direct outreach logs | Count only distinct external users who run a workflow (canonical §2) |
| Repeat usage | Streamlit Cloud returning sessions; CI-gate repo activity; feedback.json timestamps | Return within 30 days |
| Workflow completion | Tool session funnel (catalog → input → result); CLI run counts per subcommand | Add lightweight counters if needed |
| Validation runs | CLI `check`/`batch` runs; tool Validate executions | Volumes tell us demand |
| Exported reports / downloads | Report downloads; `rta report` usage; `feedback.json` | Proof-sharing behavior |
| CLI adoption | PyPI installs, `rta --version` telemetry (opt-in), issue reports | The Plan B signal |
| CI adoption | GitHub Action installs (measure once the Action ships — NEXT TO SHIP); gate runs; exit-code results in the wild | The retention signal |
| Business→tool conversion | Site analytics → "Launch the App" / pip clicks → first run | Funnel for the site |
| Feature usage distribution | Tool sessions per capability; CLI subcommand mix | Feeds G2/G3 |
| Feedback themes | `feedback.json` + issues; ≥5 distinct users for a theme | Qualitative but counted |
| Enterprise requests | Inbound inquiries; security/evidence questions (B5/B10) | Tracked in outreach log |

---

## 4. Branch triggers (canonical — §2 definitions apply)

### A. Plan A continues (default)

Continue Plan A while **all** hold:

- ≥10 distinct external users run a real workflow in the trailing quarter
  (CLI or tool), **and**
- ≥20% of them return within 30 days, **and**
- the engine stays green (1,228 full-suite tests; 887 in the `rta/tests` manifest; parity intact).

### B. G2 — capability relevance

- Compute feature-usage distribution each quarter.
- If **1–2 capabilities drive ≥80%** of repeat sessions → the product is
  effectively a focused tool → run **G3 utility** branch (Plan B direction).
- If **4+ capabilities** are used across the user base → platform framing is
  defensible → keep Plan A's breadth story.

### C. G3 — platform vs tool

- **Utility signal:** ≥5 distinct users describe Ṛta as "a linter/checker I
  use sometimes", or adoption is single-workflow → shift to Plan B framing.
- **Platform signal:** users flow across 4+ capabilities and ask for
  "more of the same" (cross-links, sessions) → keep Plan A.

### D. G4 — web vs CLI/CI as the primary adoption path

- **CLI/CI-first (expected):** ≥80% of runs are CLI or CI-gate for 2
  quarters → keep Plan A's CLI/CI-first distribution; web stays demo.
- **Web-first:** tool sessions dominate and CLI installs stagnate → rebalance
  Plan A toward the web tool (maintenance + demo) and measure why.

### E. Plan A fails adoption → Plan B (activation)

Activate Plan B when **either** holds for **two consecutive quarters**:

- <10 distinct external users per quarter, **or**
- <1 sustained team (CI gate running ≥1 month), **or**
- consistent platform-confusion feedback (≥5 distinct users: "too much",
  "unclear what to use", "I only want the check").

Activation is a **re-scoping decision** (see `PLAN_B_CONTINGENCY.md`), not a
rewrite: the engine, CLI, tests, and trust model are untouched.

### F. Plan B outcome

- **B succeeds:** ≥20 external users per quarter running `rta check`, ≥2
  sustained CI teams, ≥1 public "we run Ṛta on every SDC change" reference
  (canonical §2) → continue Plan B, then evaluate G5 for expansion.
- **B fails:** <those numbers after two quarters → the honest conclusion is
  unproven demand, not a framing problem. Stop adding product surface; keep
  the asset maintainable; re-evaluate G1 with fresh distribution channels
  before any further build.

### G. G5 — expansion evidence (Plan C gate)

Plan C becomes justified only when:

- ≥3 teams with sustained (≥1 quarter) block-level usage, **and**
- ≥1 real repo running the CI gate, **and**
- a documented before/after from real usage, **and**
- a specific expansion hypothesis (which adjacent problem users have).

Then pick from the `PLAN_C_EXPANSION.md` menu in dependency order
(C3 → C1 → C2 → C4 → C5/C6).

### H. Failure of differentiation (not adoption)

- **Signal:** ≥3 distinct users choose an incumbent for the same job, or
  competitors repeatedly cited.
- **Response:** reposition on regression + determinism (Plan B B4); if the
  gap is real, shrink the story to what we measurably do better.

### I. Technical/product complexity too high

- **Signal:** 2 quarters of declining PR velocity or rising test time with
  no offsetting adoption.
- **Response:** reduce surface (web = demo, docs consolidated, no new
  features — Plan B B11). Never touch the frozen engine.

### J. Strong demand in an adjacent workflow

- **Signal:** G5 evidence + users already asking for trend/health,
  cross-block, or governance capabilities.
- **Response:** scope a Plan C pilot with a collaborating partner
  (G7), starting with the cheapest credible item (C3/C1).

---

## 4. Cadence and ownership

- **Review:** at each release and every quarter; the founder owns the log
  of signals (a single `strategy-signals.md` or spreadsheet is enough).
- **Triggered reviews:** any crossed threshold above triggers a focused
  1-page decision memo within 2 weeks.
- **No trigger is optional:** if a signal can't be measured yet (e.g. no
  telemetry for CLI runs), the first task is to make it measurable — not to
  assume it is fine.

*Every branch ends in a concrete action with a named owner and a measured
threshold. No branch says "see how it goes."*
