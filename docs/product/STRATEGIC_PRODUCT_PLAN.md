# Ṛta — Strategic Product Plan (Umbrella)

> **Document kind:** strategy / decision planning · **Status:** planning only —
> no implementation. **Authority:** defers to `rta/docs/company/PRODUCT_CHARTER.md`
> and `docs/product/FUNCTIONAL_BASELINE.md`. Nothing in this package changes
> engine, API, UI, routes, features, tests, or architecture. No future feature
> described here is implemented or claimed to exist.
>
> **Read first:** `docs/product/PRODUCT_STRATEGY_INDEX.md`, then this document,
> then the plan you need (`PLAN_A_PRIMARY.md` / `PLAN_B_CONTINGENCY.md` /
> `PLAN_C_EXPANSION.md`), then `STRATEGIC_DECISION_TREE.md` and
> `12_MONTH_ROADMAP.md`.

---

## 1. Why this document exists

The functional product is complete and verified: 19/19 capabilities pass the
Phase C acceptance contract, the deterministic engine is frozen, and the
workspace UX is implemented. What is **not** proven is *adoption*: whether
real VLSI engineering teams will use Ṛta, keep using it, and eventually pay
for it. This package answers one question:

> If the first product strategy does not achieve adoption, value,
> differentiation, or traction — exactly what do we do next?

The answer is three staged plans (A → B → C) plus measurable triggers that
tell us when to switch. All three preserve the frozen engine and the working
product; none require rebuilding anything that works.

---

## 2. Current baseline (established from existing documents — not re-audited)

Source of truth: `docs/product/FUNCTIONAL_BASELINE.md` (v1.5.8),
`docs/product/PHASE_C_FINAL_ACCEPTANCE.md`, `docs/product/VLSI_ENGINEERING_ACCEPTANCE_REPORT.md`,
`rta/docs/company/PRODUCT_CHARTER.md`, `docs/product/PRODUCT_WORKSPACE_ARCHITECTURE_V2.md`.

| Dimension | Current state |
|---|---|
| Product | Block-level **Constraint Intelligence** — deterministic, offline, no-LLM analysis of SDC (optional structural Verilog netlist) before STA |
| Capabilities | **19/19 PASS** (Validate, Generator, Linter, Converter, Clock Intelligence, Coverage, Design Context, Conflicts, Readiness, Diff, Corner Manager, MMC, Test Drive, Rules, CI, Reports, Trust, Documentation, Feedback) |
| Engine | **Frozen** — 119 rules, deterministic; rule IDs/severities/parser/calculations change only on a documented correctness regression |
| Tests / evidence | **1,228 passed** (full pytest suite, `python -m pytest -q`) · **887** in the `rta/tests` manifest (the evidence-registry count quoted on product surfaces); 200-file parity harness intact; clean-room + smoke + comprehensive checks green. Test-count definition: the full suite is the total; the manifest count is the evidence number. `FUNCTIONAL_BASELINE.md` records 1,227/886 at its 2026-08-14 verification; the live truth is 1,228/887 (the evidence manifest regenerated 886→887 — live count, per project convention surfaces quote the manifest) |
| Trust model | Non-negotiable disclosures: *NOT an STA signoff · READY ≠ setup/hold passes · Coverage is NOT correctness · CI PASS ≠ timing pass · engine failure never becomes PASS* |
| Surfaces | **Business website** (GitHub Pages: `RAMA-L7.github.io/rta-constraint-intelligence`, per-feature pages, searchable Rules catalog, install commands) · **Engineering tool** (Streamlit workspace, `legacy/streamlit/app.py`, deployed to Streamlit Cloud, launched from the site) · **CLI** (`rta`, 13 subcommands) · **API** (stdlib `http.server`) |
| Distribution | PyPI (`pip install rta-constraint-intelligence`, `[web]` extra), Dockerfile, GitHub CI (tests) + Pages (business site) |
| Open P2 items | 10 tracked (P2-1…P2-10, see acceptance report §Known limitations) — none block any workflow |
| Known honest limitations | Corners/MMC CLI read-only (P2-1); no true READY fixture in corpus; coverage ≠ correctness; retired JS workspace (`rta/workspace/webui`) is no longer the product surface |
| **Adoption state** | **Unproven.** No validated external users; PyPI/Stars/usage signals exist but are small; the roadmap's next milestone is *first real engineering usage* — not more features |

### What is genuinely differentiated today

- **Determinism + evidence as identity**: every finding traces to a rule,
  source line, and rerunnable artifact; no probabilistic output anywhere.
  This is a defensible position against "AI-powered EDA" noise.
- **Regression intelligence built in**: semantic `diff`, baseline snapshots,
  readiness diff, and a real **CI gate with a deterministic exit-code
  contract** (0/1/2/3) — a team-level workflow, not a point check.
- **Breadth under one frozen engine**: checker + clocks + coverage +
  conflicts + readiness + generator + linter + converter + corners/MMC, all
  consistent, all testable, all offline.

### What is NOT yet differentiated

- **The web tool is a single-user local/demo surface** (Streamlit, no auth,
  no multi-user). As a "platform" surface it is currently undifferentiated.
- **The Validator alone** is not differentiated — "SDC lint" exists in
  incumbent flows. Differentiation lives in the *workflow* (check → diff →
  CI gate → report), not the checklist.
- **Generator/Converter/Linter** are convenient but not strategic;
  competitors and flows already do these.
- No published GitHub Action, no hosted evidence page, no real-design sample
  corpus with a netlist (P2-6) — the *proof* surfaces are thinner than the
  engine.

### What must NOT be rebuilt

Everything in `FUNCTIONAL_BASELINE.md` §2 (frozen scope) and the accepted
19 workflows. The engine, CLI contract, trust model, and the Streamlit tool
are assets. Do not rewrite them to chase a strategy.

---

## 3. The three plans at a glance

| Plan | Name | Trigger | One-line strategy |
|---|---|---|---|
| **A** | **The Constraint Regression Gate** (primary) | Start now | Lead with the loop engineers repeat: **validate → diff → CI gate → report**; CLI/CI-first distribution; web tool as demo + onboarding; prove adoption before expanding |
| **B** | **Wedge + CLI-first** (contingency) | Plan A underperforms (defined triggers, §6 / decision tree) | Stop platform messaging; sell **Validate + Diff + CI** as a narrow, installable engineering utility; web becomes demo only |
| **C** | **Constraint-health / expansion** (optional) | Block-level adoption evidence exists | Expand into regression-health intelligence, subsystem scope, evidence/benchmark platform, org governance — only on evidence (charter-compatible, deterministic-first) |

Plans are **cumulative and evidence-gated**, not "pick one". A failing branch
never discards the working product; it re-scopes the *story and investment*.

---

## 4. Business website vs engineering tool (roles and traffic flow)

### Business website — the *explain + convert* surface

- Positioning, credibility, benchmarks/evidence, engineering use cases,
  trust, documentation, install commands.
- Job: move a skeptical engineer from *"what is this?"* → *"I want to run
  it on my SDC"*.
- Keep it honest: every claim must trace to the evidence system
  (charter §9.1). Never add a claim the rerunnable artifacts do not back.

### Engineering tool — the *do* surface

- Immediate task completion: paste/upload SDC → findings → next action.
- Job: convert a first run into a *repeat* workflow (diff/CI/report), and a
  repeat workflow into a *team* workflow (CI gate).
- Today this is the Streamlit workspace. Its role in Plan A is demo +
  onboarding + report generation; the CLI/CI is the primary adoption path
  for working engineers.

### Traffic flow (the model every page and CTA should serve)

```
Business page → understand the problem → see evidence/benchmarks
→ understand Ṛta → Install (pip) or Launch App → complete a real task
→ useful result (findings/diff/gate/report) → return / reuse / share / export
```

Conversion is measured, not assumed: see the triggers in
`STRATEGIC_DECISION_TREE.md` (business→tool conversion, CLI installs,
repeat sessions).

---

## 5. What this package does NOT do

- **No implementation.** No engine/API/UI/routes/features/tests changes.
- **No new capabilities are claimed.** Every "future" item in Plan C is
  explicitly unbuilt and gated on evidence.
- **No feature is removed.** `PRODUCT_PRIORITIZATION.md` classifies
  investment priority only; the 19 capabilities stay.

---

## 6. Decision gates (the seven questions, each with measurable evidence)

Full trigger definitions and measurement sources: `STRATEGIC_DECISION_TREE.md`.
Cadence: review at each release (or quarterly), and whenever a trigger
threshold is crossed.

| Gate | Question | Evidence required | Default action |
|---|---|---|---|
| **G1** | Is the current product valuable enough to continue? | ≥5 distinct engineers outside the founding circle run a real workflow (CLI or tool) and report a genuine finding/diff/gate result; ≥2 say the finding was actionable | Continue Plan A |
| **G2** | Which capabilities actually matter? | Feature-usage distribution (tool + CLI) + feedback themes; which 3 capabilities drive ≥80% of repeat sessions | Double down on those; de-prioritize the rest |
| **G3** | Platform or focused tool? | G2 data + adoption pattern: do users engage 1–2 workflows (focused) or flow across 4+ (platform)? | If focused → shift messaging (Plan B direction) |
| **G4** | Web workspace or CLI/CI as primary path? | Where do repeat users run? (CLI runs vs tool sessions vs CI runs); CI adoption count | CLI/CI-first (Plan A default); web-first only if evidence says so |
| **G5** | Enough evidence to expand? | ≥3 teams with sustained (≥1 quarter) usage; CI gates running in ≥1 real repo; a documented before/after | Then consider Plan C candidates |
| **G6** | Is Plan B required? | Plan A triggers (below) — canonical definitions in `STRATEGIC_DECISION_TREE.md` §2; e.g. 2 consecutive quarters with <10 external users/quarter or <1 sustained CI team | Switch to Plan B |
| **G7** | Is Plan C justified? | G5 evidence + a specific expansion hypothesis + a paying/collaborating partner willing to pilot | Scope a Plan C pilot |

### Plan A trigger thresholds (used by G6 and the decision tree)

Canonical definitions and the full measurement sources live in
`STRATEGIC_DECISION_TREE.md` §2–§3; the thresholds restated here for quick
reference use exactly the same numbers:

- **Adoption (Plan B activation):** two consecutive quarters with <10
  external users/quarter, or <1 sustained CI team.
- **Usage depth:** median external session completes <1 workflow; repeat
  usage <20% (feeds G2/G3).
- **Distribution:** PyPI downloads flat or falling for 2 quarters (proxy
  signal); no external CI-gate repo once the GitHub Action ships (NEXT TO
  SHIP — not a current capability).
- **Feedback:** consistent themes from ≥5 distinct users that the platform
  is "too much" / "unclear what to use" / "just want the check".

---

## 7. Risk register (concise)

Full detail lives in each plan; this is the register the founder should
re-read quarterly. Probability/impact: L/M/H (relative to a small team).

| # | Risk | Prob | Impact | Early signal | Mitigation | Plan A resp. | Plan B resp. | Plan C resp. |
|---|---|---|---|---|---|---|---|---|
| R1 | No real adoption (product is engineering-complete, market-empty) | M | H | Zero external users; PyPI downloads flat | Ship distribution (Action, docs, samples); lead with the repeat loop; measure everything | Focus all effort on 1 loop + distribution; no new features | Wedge + CLI-first (Plan B) | n/a (no evidence) |
| R2 | Users want only the Validator / see a utility, not a platform | M | H | Usage concentrated in 1 workflow; feedback "just a linter" | Lead with diff/CI/regression value, not feature count | Position as regression gate; demote platform language | Sell Validator + Diff + CI wedge | — |
| R3 | Trust insufficient for adoption (proprietary SDC concerns; no signoff claims) | M | M | Enterprise asks blocked on security/evidence; feedback "needs certification" | Offline-first, no-upload guarantee, evidence pages, honest scope | Publish evidence + no-data-leaves-your-machine story | Keep trust posture (it is Plan B's core) | Evidence platform (C3) |
| R4 | Web tool drains engineering time without driving adoption (Streamlit, single-user, no auth) | M | M | Tool sessions high but no CLI/CI/team usage | Treat tool as demo; invest in CLI/CI instead | Cap web investment at maintenance + demo polish | Web = demo only; all investment to CLI/CI | Only hosted web if revenue asks |
| R5 | Incumbent flows / other tools already do "SDC lint" | M | M | Feedback "we already have X" | Differentiate on regression + determinism + evidence, not lint | Regression-gate positioning | Narrower wedge (check + diff) | Health/trend platform (C1) |
| R6 | Two web surfaces confusion (retired JS workspace + Streamlit) | L | M | Docs/tests still reference `rta/workspace/webui` | Keep JS workspace retired; remove stale refs on cleanup passes | Ignore; never resurrect | Ignore | Ignore |
| R7 | Maintenance cost exceeds capacity (1228 tests, 2 surfaces, docs) | M | M | PR velocity drops; test time grows; docs drift | Freeze engine (done); resist feature additions; automate evidence regen | No new engine features; only P2 + distribution | Reduce surface (web = demo; fewer docs pages) | — |
| R8 | Competition or "AI EDA" noise undermines differentiation | L | M | Prospects compare to AI tools; "no AI" reads as outdated | Make determinism/evidence the story; benchmarks prove it | Publish rerunnable benchmarks | Same | Benchmark platform (C3) |
| R9 | Enterprise sales cycle too slow for a small team | M | M | Only enterprise inquiries, no closed deals | Target individual engineers first (bottom-up) | Engineer-first adoption | CLI utility = zero sales cycle | — |
| R10 | Engines freeze blocks fixes (bug discovered post-freeze) | L | M | Genuine correctness regression reported | Freeze has a documented regression path (FUNCTIONAL_BASELINE §2) | Use the documented path | Same | Same |

---

## 8. Validation / market learning (before major development)

Everything below can be tested with the **current product** — no new engine
work required.

**Assumptions that must be tested (in priority order):**
1. An engineer will `pip install` and run Ṛta on a **real SDC** in <10
   minutes, and the findings are **actionable**.
2. **Diff + baseline + CI gate** is the workflow engineers want to keep
   using (the retention loop), not just a one-time check.
3. **Determinism / no-LLM / offline** is a *positive* for this audience
   (vs a curiosity).
4. Engineers prefer **CLI/CI** over the web tool for daily work.
5. Teams are unwilling to upload proprietary SDC to anything cloud-hosted.
6. The web tool's job is **demo + onboarding**, not daily work.

**How to test cheaply (current product only):**
- Publish the latest PyPI release and a **GitHub Action** for the CI gate;
  write a 5-minute "run on your SDC" guide (P2-10 gives us the one-place
  contract doc).
- Add one **realistic multi-clock sample + netlist** to Test Drive (P2-6) —
  the best demo asset we have.
- Add **whats-new / release notes** to the tool (P2-8) so users see
  progress.
- Collect usage: PyPI downloads, GitHub stars/issues, Streamlit Cloud
  sessions, `feedback.json`, and (once shipped) Action runs.
- Recruit 3–5 engineers outside the founding circle; ask them to run the
  CLI on one of their real SDCs and tell us what they'd use daily.

**What must NOT be built before validation:** subsystem/top-level scope,
enterprise governance, AI assistance, hosted/SaaS, multi-user auth, plugin
marketplaces, new rules, new engine features. (Charter V2+ and the roadmap
depend on block-level evidence first.)

---

## 9. Final recommendation (blunt)

1. **Do NOW:** Ship distribution and prove one loop. Publish the current
   release to PyPI; ship a GitHub Action wrapping `rta check + diff + gate`;
   write the 5-minute real-SDC guide (fixes P2-10); add the realistic Test
   Drive sample (P2-6). Then get 3–5 real engineers to run it on real SDCs.
   Everything else in the product is already built.
2. **Do NOT do NOW:** Build more capabilities, market the 19-feature
   platform, start subsystem/top-level work, add AI, build SaaS/auth, or
   invest further in the web tool beyond maintenance and demo polish. The
   product is ahead of its evidence.
3. **Test before spending more engineering time:** assumptions 1–6 in §8 —
   especially *actionable findings* and *diff/CI retention* — because the
   whole strategy rests on them.
4. **What keeps us on Plan A:** ≥10 distinct external users/quarter with
   ≥20% repeat, ≥1 sustained CI-gate team, and 2+ users reporting a
   workflow they'd miss if removed.
5. **What triggers Plan B:** two consecutive quarters below those numbers,
   or feedback that the platform is too broad ("I only want the check").
6. **What justifies Plan C:** 3+ sustained teams, ≥1 real CI-gate repo, and
   a specific expansion hypothesis with a partner willing to pilot.
7. **Single biggest strategic mistake to avoid:** treating the 19-capability
   platform as the product to market and adding features instead of proving
   one repeatable loop with real engineers. The engine is the asset; the
   feature list is not the story.
8. **Single highest-impact opportunity available now:** turn the already-
   built **diff + baseline + CI gate** into a one-command team workflow
   (GitHub Action + guide + real sample) and get real SDCs through it. It is
   the only workflow that turns a validator into something a team adopts
   permanently, and it requires almost no new engineering.

---

## 10. Current vs future — canonical classification

A planned item must never read as implemented. The classification below is
canonical for the whole package; every reference to these items elsewhere
uses these labels.

| Item | Classification | Where it lives |
|---|---|---|
| Deterministic engine, 119 rules, CLI (13 commands), API, Streamlit tool, business site, Dockerfile, GitHub CI (tests) + Pages | **EXISTS NOW** | `FUNCTIONAL_BASELINE.md` |
| PyPI release cadence (latest release publish) | **NEXT TO SHIP** | `PLAN_A_PRIMARY.md` §6 |
| GitHub Action for the CI gate | **EXISTS NOW** (in-repo, `.github/actions/rta-gate`; CI self-test green) — versioned release tag + external adoption still pending | `12_MONTH_ROADMAP.md` Phase 1 |
| Realistic Test Drive sample with netlist (P2-6) | **NEXT TO SHIP** (tracked P2) | `VLSI_ENGINEERING_ACCEPTANCE_REPORT.md` P2-6 |
| whats-new in the tool (P2-8) | **NEXT TO SHIP** (tracked P2) | acceptance report P2-8 |
| One-place exit-code contract (P2-10) | **DONE** — `docs/features/README-14-ci-gate.md` | `VLSI_ENGINEERING_ACCEPTANCE_REPORT.md` P2-10 |
| Benchmark/evidence platform (public rerunnable surface) | **FUTURE / GATED** (corpus exists; the platform surface does not) | `PLAN_C_EXPANSION.md` C3 |
| Constraint regression/health intelligence | **FUTURE / GATED** | `PLAN_C_EXPANSION.md` C1 |
| Subsystem / cross-block intelligence | **FUTURE / GATED** (charter V2) | `PLAN_C_EXPANSION.md` C2 |
| CI governance for organizations | **FUTURE / GATED** | `PLAN_C_EXPANSION.md` C4 |
| Optional AI assistance layer | **FUTURE / GATED** (charter §7 boundaries) | `PLAN_C_EXPANSION.md` C5 |
| Hosted/SaaS workspace | **FUTURE / GATED** (conflicts with offline trust today) | `PLAN_C_EXPANSION.md` C6 |

## 11. Source-of-truth hierarchy

No strategy document overrides the Product Charter or the Functional
Baseline. The authority order is:

```
rta/docs/company/PRODUCT_CHARTER.md          (constitution: scope, trust, determinism, non-goals)
        ↓
docs/product/FUNCTIONAL_BASELINE.md          (frozen functional contract, test counts, disclosures)
        ↓
docs/product/STRATEGIC_PRODUCT_PLAN.md       (this document: strategy umbrella, gates, risks)
        ↓
docs/product/STRATEGIC_DECISION_TREE.md      (canonical numerical triggers and metric definitions)
        ↓
docs/product/PLAN_A_PRIMARY.md · PLAN_B_CONTINGENCY.md · PLAN_C_EXPANSION.md
        ↓
docs/product/12_MONTH_ROADMAP.md             (execution phases; uses only the tree's gates)
```

Rules:

- If a strategy document conflicts with the Charter or the Functional
  Baseline, the Charter/Baseline wins and the strategy document is wrong.
- If a plan or the roadmap conflicts with the Decision Tree's numbers, the
  Decision Tree wins.
- `PRODUCT_PRIORITIZATION.md` is the canonical 19-capability inventory;
  `PRODUCT_STRATEGY_INDEX.md` is the navigation index.

## 12. Document map

| Document | Purpose | Read when |
|---|---|---|
| `PRODUCT_STRATEGY_INDEX.md` | Index + read order | First |
| `STRATEGIC_PRODUCT_PLAN.md` | This umbrella | Second |
| `PLAN_A_PRIMARY.md` | Primary strategy, detailed | Making investment decisions |
| `PLAN_B_CONTINGENCY.md` | Failure scenarios + contingency | Adoption signals weaken |
| `PLAN_C_EXPANSION.md` | Expansion paths + evidence gates | G5/G7 evidence appears |
| `STRATEGIC_DECISION_TREE.md` | Branches + measurable triggers | Every review cycle |
| `PRODUCT_PRIORITIZATION.md` | 19-capability priority matrix | Sprint planning |
| `12_MONTH_ROADMAP.md` | Phased execution plan | Planning cycles |

*Strategy planning only. No implementation. The functional baseline
(`FUNCTIONAL_BASELINE.md`) and the Product Charter remain the authority on
what the product is and does.*
