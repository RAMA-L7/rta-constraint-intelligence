# Ṛta — Plan B: Wedge + CLI-First (Contingency)

> **Document kind:** strategy / Plan B (contingency) · **Status:** planning
> only — not active. Plan B activates **only after measurable Plan A failure**
> (triggers in `STRATEGIC_PRODUCT_PLAN.md` §6 and, canonically, in
> `STRATEGIC_DECISION_TREE.md` §2/§4). No implementation. The frozen engine
> and the working product are preserved in every scenario.
>
> **Hierarchy:** the Product Charter and Functional Baseline outrank this
> document; all numerical triggers use the canonical definitions in
> `STRATEGIC_DECISION_TREE.md` §2.

---

## 1. What Plan B is (and is not)

Plan B is **not** "keep improving the same product." It is a deliberate
re-scoping of the product story and investment when the platform framing
fails to convert:

> **Stop selling the 19-capability platform. Sell the narrow, installable
> engineering utility that teams already want: Validate + Diff + CI gate,
> CLI-first, zero friction, zero data leaving the machine.**

The evidence in the repository supports this direction more strongly than
any other contingency option:

- The **CLI is the broadest, most self-contained surface** (13 subcommands,
  exit-code contract, JSON/JUnit/HTML/CSV/Markdown output, batch mode).
- **Diff + baseline + readiness-diff + CI gate** are the most mature
  *workflow* assets (CHG-* rule set, policy engine, regression semantics).
- The **web tool is a single-user demo surface** (Streamlit, no auth) — it
  is the weakest adoption surface and the most expensive to maintain as a
  platform.
- The **trust posture (offline, deterministic, no-LLM, no upload)** is
  exactly what a CLI utility needs and what enterprise prospects worry
  about — it is Plan B's core, not a footnote.

---

## 2. Failure scenarios (each with a measured response)

Trigger definitions are quantified in §3 and the decision tree. For every
scenario: **early warning → evidence required → decision threshold →
response → preserve / stop / change.**

| # | Scenario | Early warning signal | Evidence required | Decision threshold | Response | Preserve | Stop | Change |
|---|---|---|---|---|---|---|---|---|
| B1 | Engineers like the tech but don't adopt the full platform | Site/tool sessions high; CLI installs low; sessions touch 1 capability | Feature-usage distribution; session depth; feedback themes | >80% of repeat sessions use 1–2 capabilities; "too much" feedback ≥5 distinct users | Shift to wedge story; single-entry "check" flow | Engine, CLI, trust, tests | Platform messaging; catalog investment | Homepage + tool entry lead with Validate only |
| B2 | Users only want the Validator | Usage concentrated in `check`; diff/CI untouched; feedback "just want a linter" | Usage distribution + interviews | Check >70% of all runs for 2 quarters | Make Validator the product; diff/CI become upsell paths | Validator + linter + rules registry | Diff/CI/MMC marketing; web-only features | Lead story = "SDC check that fits your flow" |
| B3 | Users don't understand the broader Ṛta platform | Drop-off after catalog; "what do I use?" feedback; empty sessions | Session funnel from business site → tool → completion | Conversion business→tool <5% or first-run completion <40% | One-primary-path UX (validate only); move the rest to "more tools" | All 19 remain available | Catalog as the lead surface | Single CTA home; rest discoverable but secondary |
| B4 | Technically strong but differentiation weak | "We already have X" feedback; competitors cited; no named differentiator | Competitive interviews; why-choose-Ṛta answers | ≥3 distinct users name an incumbent as sufficient | Lead with regression + determinism; demote lint framing | Diff/CI/baseline assets | "Validator/linter" as the headline | "The constraint regression gate" positioning |
| B5 | Organizations won't upload proprietary SDC/netlists | Enterprise inquiries stall on security; "can it run offline?" questions | Sales/interview log; security objections count | ≥3 orgs cite upload/cloud as the blocker | CLI + offline-first story; no-upload guarantee; local-only tool | Offline architecture, trust disclosures | Cloud/upload messaging | "Runs entirely on your machine" as lead line |
| B6 | Engineers prefer CLI over web UI | CLI runs >> tool sessions; tool sessions shallow; feedback "I don't need the app" | Run-count split (CLI vs tool) | CLI ≥80% of runs for 2 quarters | CLI-first distribution; web = docs + demo | CLI surface, exit codes, batch | Web tool feature investment | Web reduced to maintenance + demo |
| B7 | Users only need 1–2 workflows | Single-workflow repeat usage dominates | G2 data (decision tree) | 1–2 workflows drive ≥80% of repeat sessions | Product = those workflows; others hidden-but-present | Chosen workflows + engine | Unused workflow investment | Simplify catalog to the chosen set |
| B8 | Enterprise adoption too slow | Pipeline all enterprise, no closes; long cycles | Sales cycle data | No closed deal in 2 quarters | Abandon top-down; engineer-first; free CLI wedge | Open-source posture | Enterprise sales motion | Community/individual adoption only |
| B9 | Seen as a utility rather than a platform | Word-of-mouth describes it as "an SDC linter I use sometimes" | Positioning feedback | Consistent utility framing from ≥5 users | Accept utility; win the utility category with best-in-class depth | Depth of rules/evidence | Platform claims | "The SDC utility engineers trust" |
| B10 | Insufficient evidence/trust prevents adoption | "Can you prove it?" stalls; benchmarks disbelieved | Evidence requests; audit feedback | ≥3 prospects demand proof we can't show | Publish corpus + audits + clean-room; make evidence rerunnable | Evidence system | Unsupported claims | Benchmark/evidence as marketing surface |
| B11 | Maintenance cost too high | PR velocity drops; test time grows; docs drift | Velocity + test-time trend | 2 quarters of declining velocity | Reduce surface: web = demo; docs consolidated; no new features | Engine, tests, CLI | Second surfaces, doc sprawl | One CLI + one site + one demo tool |
| B12 | Competitors provide overlapping functionality | "Tool X does this" recurring | Competitive analysis | ≥3 users choose alternatives for the same job | Differentiate on regression/determinism; otherwise shrink to the gap | Diff/CI/baseline | Me-too features | Focus only where we're measurably better |

---

## 3. Plan B definition (the actual contingency)

**Name:** *Ṛta — the Constraint Regression Gate* (wedge positioning).

**Product shape (unchanged engine, changed story):**

- **Lead capability:** `rta check` (Validate) — the 5-minute-to-value entry.
- **Retention capabilities:** `rta diff` + baseline snapshots + `rta
  analyze gate` (CI) — the reason a team keeps it.
- **Proof capabilities:** `rta report`, `rta rules`, `rta batch` — the
  evidence and shareability.
- **Supporting (present, de-emphasized):** generator, linter, converter,
  corners/MMC, clock/coverage/context/conflicts/readiness (all remain,
  discoverable, not the lead).

**Execution steps:**

1. **Reposition** the business site lead: one loop (check → diff → gate),
   "runs entirely on your machine", pip + GitHub Action up front.
2. **One primary path in the tool:** catalog leads with Validate; the rest
   stay reachable but secondary (reverses the Phase E "all equal" surface
   *only as a positioning change*, not a feature removal).
3. **Distribution:** PyPI cadence, GitHub Action, Docker, batch for
   regression runs across a design directory.
4. **CLI-first docs:** every workflow documented as a command first; web
   becomes demo/onboarding.
5. **Stop:** web-tool feature investment, platform messaging, enterprise
   sales motion, corners/MMC UI work beyond maintenance.

**Definition of success (Plan B):** ≥20 external users per quarter running
`rta check` on real SDCs (canonical window: trailing quarter); ≥2 sustained
CI teams (canonical §2); ≥1 public "we run Ṛta on every SDC change"
reference; PyPI downloads growing quarter-over-quarter (proxy signal). If
Plan B also fails to hit these within two quarters, the honest conclusion
is unproven demand — not a framing problem — see `STRATEGIC_PRODUCT_PLAN.md`
§6 G1 and the final recommendation.

## 4. Alternative directions evaluated (and why not chosen)

| Direction | Verdict | Reason |
|---|---|---|
| **SDC Validator as the wedge** | **Chosen** (part of Plan B) | Strongest single capability; CLI-complete; 5-minute value |
| **CLI-first engineering tool** | **Chosen** (Plan B's distribution) | CLI is the broadest surface; engineers' daily work is terminal + CI |
| **Focused pre-STA constraint quality platform** | Absorbed into Plan A/B positioning | The framing, not a separate plan |
| **CI/CD constraint-quality product** | **Chosen as the retention half** | Diff + baseline + gate are the mature assets; the differentiator |
| **Enterprise engineering workflow product** | Rejected for now | No multi-user/auth/SSO; sales cycle too long for a small team (B8) |
| **Verification/evidence/reporting product** | Partial (proof surface, not the product) | Reports/evidence are trust assets, not the lead product |
| **API/platform model** | Rejected for now | stdlib API is a power-user surface; no auth/hosting → not a platform yet |

*Plan B is not a rebuild. It re-scopes the story, distribution, and
investment around the capabilities the repository shows are strongest
(CLI, diff/CI, offline trust), and it preserves the entire working
product.*
