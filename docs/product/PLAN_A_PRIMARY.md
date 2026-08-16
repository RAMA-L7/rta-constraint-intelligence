# Ṛta — Plan A: The Constraint Regression Gate (Primary Strategy)

> **Document kind:** strategy / Plan A · **Status:** planning only — no
> implementation. Builds on `STRATEGIC_PRODUCT_PLAN.md`, `FUNCTIONAL_BASELINE.md`,
> `PHASE_C_FINAL_ACCEPTANCE.md`, and `rta/docs/company/PRODUCT_CHARTER.md`.
> Nothing here changes engine, API, UI, routes, features, tests, or
> architecture. The frozen engine is untouched; every action below is
> distribution, presentation, evidence, or adoption work.
>
> **Hierarchy:** the Product Charter and Functional Baseline outrank this
> document; all numerical triggers use the canonical definitions in
> `STRATEGIC_DECISION_TREE.md` §2.

---

## 1. Product positioning

**One line:** *Ṛta is the deterministic constraint-quality gate between
constraint authoring and STA — validate, diff, and gate your SDC before
timing analysis.*

**The frame:** not "a validator with 19 features". The product is the
**repeatable loop** an engineering team runs on every SDC change:

```
check → review findings → diff vs baseline → CI gate → report
```

Positioning must answer the engineer's daily question: *"Is this constraint
set complete, consistent, regression-free, and ready to hand to STA — and
what changed since last week?"* The platform story is real but is **not the
lead**; the loop is the lead.

## 2. Primary target user

**The constraint owner / block owner / STA triage engineer** in a block-level
digital design team (PD, STA, synthesis, or constraint-authoring role) at an
ASIC/SoC company — the person who receives, authors, and is responsible for
an SDC before it goes to timing analysis.

Secondary but important: the **PD/STA team lead** who wants a consistent,
enforced quality bar for the whole team (they are the CI-gate buyer).

## 3. Primary engineering problem

Constraint quality is verified by hand and by intuition, and regressions are
found late by downstream tools. Concretely:

- Missing, duplicate, or contradictory constraints slip in silently between
  revisions (no one diffs SDC semantically by hand).
- There is no cheap, deterministic, pre-STA check a team can run in CI.
- When a change breaks a constraint set, the team finds out after synthesis
  or STA, costing iteration cycles.

## 4. Core product promise

> **"Know in seconds whether your SDC is complete, consistent, and
> regression-free — before STA — with deterministic, explainable evidence."**

The promise has three parts that map to existing verified capabilities:
- **Complete & consistent** → `check` (119 rules), clock intelligence,
  coverage, conflicts, readiness.
- **Regression-free** → semantic `diff` + baseline snapshots + CI gate
  (exit-code contract 0/1/2/3).
- **Evidence, not opinion** → deterministic engine, source-line findings,
  rerunnable benchmarks, honest scope disclosures (never weakened).

## 5. Most important workflows

From the accepted Phase C matrix — the ones that drive retention:

1. **Validate** (card → SDC → findings → next actions) — the entry loop.
2. **Diff** (V1 vs V2 → what changed / why it matters / what to review) —
   the repeat-usage loop.
3. **CI gate** (SDC + baseline + policy → PASS/FAIL + exit code) — the
   team-level loop and the differentiator.
4. **Readiness** (BLOCKED / REVIEW_REQUIRED / READY with reasons) — the
   handoff artifact.
5. **Report** (HTML/JSON from real analysis) — the shareable evidence.

Generator, Linter, Converter, Corners/MMC, Rules, Trust, Documentation,
Feedback are **supporting** in Plan A (see `PRODUCT_PRIORITIZATION.md`).

## 6. What should be completed next (prioritized)

All are distribution/evidence/polish — **no engine changes**.

| # | Item | Why it matters | Effort |
|---|---|---|---|
| 1 | **Publish current release to PyPI** (v1.5.8+) | `pip install rta-constraint-intelligence` must deliver the newest engine; PyPI is the adoption front door | Small |
| 2 | **GitHub Action for the CI gate** | Turns the strongest engine asset into a one-line team workflow; the differentiator becomes usable | Medium |
| 3 | **One-place exit-code + gate-policy contract (P2-10)** | Trust + usability; CI users need the contract in one place | Small |
| 4 | **Realistic Test Drive sample + netlist (P2-6)** | Best demo asset; shows the design-aware tier honestly | Small |
| 5 | **whats-new in the tool (P2-8)** | Users see progress; release cadence becomes visible | Small |
| 6 | **Fix exit-code 2 collision (P2-3)** | CI scripts must distinguish "invalid invocation" from "gate blocked" | Small |
| 7 | **Real-SDC onboarding guide ("run on your SDC in 5 minutes")** | The adoption funnel; converts site visitors into CLI users | Small |
| 8 | **Samples/realistic corpus with netlist for Test Drive + evidence** | Proof surface; enables credible benchmarks and demos | Medium |

Deferred within Plan A: P2-1 (corners/MMC CLI) and P2-7 (single download
bundle) — convenience, not adoption drivers. P2-2/P2-4/P2-5/P2-9 are polish
items folded into release cycles when convenient.

## 7. What should explicitly NOT be built yet

- Subsystem / top-level / multi-block scope (charter V2+).
- Enterprise governance, auth, SSO, multi-user collaboration.
- Any AI assistance layer (charter §7 — future, optional, evidence-gated).
- Hosted/SaaS processing of customer SDC (breaks the offline trust story;
  violates the no-data-leaves-your-machine position).
- New rules, new engine features, new analysis dimensions.
- A second web tool (the retired JS workspace stays retired).
- Plugin marketplaces, integrations marketplace, pricing/entitlements.

Rule of thumb: if it is not (a) distribution, (b) evidence, (c) the
validate→diff→CI→report loop, or (d) a P2 fix that blocks a workflow — it
does not belong in Plan A.

## 8. UX/product priorities

1. **Validate loop under 30 seconds** for a returning user (paste →
   findings → next action; already true — protect it).
2. **Diff + CI as the visible "why you keep using Ṛta"** — make the
   before/after, why-it-matters, review-guidance content front and center.
3. **Web tool = demo + onboarding**, not the daily-work surface. Keep the
   catalog and per-feature workflows (Phase E/F) as-is; invest only in
   maintenance and the demo assets above.
4. **Empty/error states stay honest** (already verified) — never trade
   engineering truth for a fake success state.
5. Progressive disclosure stays (summary → details → evidence) so dense
   engineering data remains available without overwhelming first views.

## 9. Engineering priorities

1. **Distribution engineering:** release pipeline (PyPI), the GitHub
   Action, Docker image refresh.
2. **CI-gate completeness:** P2-3 exit-code semantics, P2-10 contract doc,
   JUnit/JSON consumability already verified.
3. **Evidence surface:** real-sample corpus with netlist (P2-6), rerunnable
   benchmark packaging for the website.
4. **Performance on real designs:** profile `check`/`diff` on large real
   SDCs (a working engineer's first complaint is speed).
5. **Stability:** keep the frozen engine green (1,228 full-suite tests;
   887 in the `rta/tests` manifest), keep the parity harness intact; no new
   features.

## 10. Business/website priorities

1. **Lead with the loop, not the feature list:** rework the homepage story
   around validate → diff → CI gate → report and the "before STA" moment.
2. **Evidence/benchmarks that a skeptic can rerun:** point to the corpus,
   the parity audits, the clean-room gates; add the realistic sample demo.
3. **Install + 5-minute guide front and center:** pip command, the GitHub
   Action snippet, "run on your SDC" path.
4. **Trust pages stay exact:** no overclaim; determinism/no-LLM/offline is
   the differentiator — say it precisely.
5. **Conversion instrumentation:** business→tool→CLI path measurable (see
   `STRATEGIC_DECISION_TREE.md`).

## 11. Evidence/benchmark strategy

- Keep the existing rule: **every public number traces to a rerunnable
  artifact** (charter §9.1); stale numbers are trust failures.
- Publish the benchmark corpus and the parity/acceptance audits as proof of
  engineering rigor — rare for a startup and genuinely differentiating.
- Add a **before/after** evidence asset: one realistic SDC, findings shown,
  diff shown, gate result shown — all real backend output.
- Never present coverage/readiness/CI results as timing results (trust
  disclosures are frozen).

## 12. Adoption strategy

**Bottom-up, engineer-first** (a small team cannot sell top-down to
enterprises first):

1. **Land:** an engineer `pip install`s, runs the CLI on a real SDC, gets a
   finding/diff they immediately value (<10 minutes to value).
2. **Spread:** the engineer adds the **CI gate to their repo** (the team
   now has a shared quality bar — "the same standard for everyone").
3. **Deepen:** diff + baseline gives the team regression intelligence;
   reports/readiness become the handoff artifact.
4. **Grow:** 2–3 teams → references → the first design win story.

Channels: GitHub (README, issues, Action), PyPI, technical content that
shows *real* rule outcomes (deterministic, credible — e.g. "SDC regressions
that slip past code review"), and the business site as the explain surface.

## 13. Trust/credibility strategy

- Keep the frozen trust disclosures verbatim everywhere.
- Publish evidence (corpus, audits, clean-room) as the proof posture.
- Publish the **119-rule catalog** (already searchable on the site) — depth
  of documented engineering is a credibility asset.
- Never claim signoff, STA, timing, or AI capabilities.
- "No data leaves your machine / no upload required" is a trust feature —
  make it explicit in adoption material (addresses proprietary-SDC concern
  head-on).

## 14. Release milestones

| Milestone | Contents | Gate to next |
|---|---|---|
| v1.6 | PyPI publish; P2-10 contract; P2-3 exit-code; P2-8 whats-new | CLI usable by external engineer in <10 min |
| v1.7 | GitHub Action; P2-6 realistic sample; 5-minute guide | ≥1 external CI-gate repo (pilot) |
| v1.8 | Evidence/benchmark packaging; performance pass on real SDCs | ≥10 external users/quarter, ≥20% repeat |
| v2.0 | First validated team workflow + documented before/after; decision-gate review | G1–G4 review; Plan B if triggers hit |

## 15. Definition of success

Measurable, at v2.0 review:

- **≥10 distinct external users** (non-founder-circle) running a real
  workflow in the trailing quarter; **≥20%** return within 30 days.
- **≥1 sustained team** running the CI gate in a real repo for ≥1 month.
- **≥2 users** report a workflow they would miss if removed (diff or CI
  gate named in ≥1 case).
- Business→tool conversion measurable and improving; CLI installs growing
  quarter over quarter.
- Engine untouched: 1,228 full-suite tests green (887 manifest), parity
  intact, trust disclosures verbatim.

## 16. Kill / adjust criteria

Adjust (stay on Plan A, change tactic) if: adoption is growing but the web
tool is the only surface used (→ push CLI/CI harder); users love the check
but ignore diff/CI (→ re-position the loop, measure why); feedback shows the
findings are not actionable (→ improve message quality, not breadth).

**Switch to Plan B** if: two consecutive quarters with <10 external users,
or <1 sustained team, or consistent feedback that the platform is "too
much" / "I only want the check" — see `PLAN_B_CONTINGENCY.md` and the
decision tree.

*Plan A is distribution + evidence + adoption of the already-built loop. It
requires no engine changes and preserves the working product exactly.*
