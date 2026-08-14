# Ṛta — Product Rebuild Plan (staged)

> **Status:** planning only. No implementation in this sprint.
> **Inputs:** `FUNCTIONAL_BASELINE.md` (frozen contract),
> `PRODUCT_WORKSPACE_ARCHITECTURE_V2.md` (target architecture),
> `FEATURE_WORKFLOW_MATRIX.md` (workflows), `FEATURE_TRACEABILITY.md`
> (feature coverage), `VLSI_ENGINEERING_ACCEPTANCE_REPORT.md` (P1 done, P2 open),
> `rta/docs/product/` design references (VISUAL_DESIGN_SYSTEM,
> PRODUCT_WEBSITE_DESIGN_DNA, HIGH_FIDELITY_PRODUCT_SPEC, PHASE17_*).

---

## Guiding constraints (all phases)

- The deterministic SDC engine is **frozen** (see FUNCTIONAL_BASELINE.md §2).
- No rule semantics, IDs, severities, parser, coverage/clock/readiness/diff/
  generator/converter behavior changes without a documented correctness
  regression.
- Trust disclosures are never weakened.
- Working deterministic functionality is reused, not rebuilt.
- Every phase ends with verification; the verification chain is:
  full pytest suite → smoke → comprehensive checks → parity harness → Test
  Drive → gen→lint→check pipeline → API integration tests.

---

## Phase A — Functional freeze

**Goal:** lock the contract and protect it.

- [ ] Keep `docs/product/FUNCTIONAL_BASELINE.md` as the single contract source.
- [ ] Confirm the parity-defect regression tests (23) + P1 regression tests
      (23) remain green on every future change.
- [ ] Add any missing regression pins for behavior the rebuild touches
      (API shape, webui state) so presentation changes can't silently alter
      engineering results.
- [ ] Record the exit-code contract and gate-policy matrix in one place
      (acceptance P2-10) as a **documentation** task — allowed now; it changes
      no behavior.
- **Exit criteria:** baseline re-verified end-to-end; no engine diff.

## Phase B — Architecture

**Goal:** finalize the target architecture (this package is its draft).

- [ ] Review PRODUCT_WORKSPACE_ARCHITECTURE_V2 with the founder/engineers;
      resolve open decisions (card set, grouping, naming).
- [ ] Confirm the two-surface boundary (business site vs workspace).
- [ ] Confirm the 17-card primary catalog and the supporting surfaces.
- [ ] Freeze the feature-first entry + implicit-session model.
- [ ] Design the input/output contract per card (from FEATURE_WORKFLOW_MATRIX).
- **Exit criteria:** signed-off architecture; no code changes.

## Phase C — Feature workflow implementation

**Goal:** every card leads to a working workflow on the frozen backend.

Order (each lands as a complete INPUT→RESULT→NEXT flow, verified per feature):

1. **Validator** — card → upload → findings (highest traffic; keep current
   `/api/analyze` contract, add the feature-first entry).
2. **Generator** — card → form → SDC → open in Validator.
3. **Linter / Converter** — cards → upload → result + download.
4. **Clocks / Coverage / Conflicts / Readiness / Design** — cards that open
   the session results (still individually reachable; their input is the
   session SDC or a fresh upload).
5. **Diff** — card → V1+V2 → changes (standalone).
6. **Corners / MMC** — cards → configure → per-corner SDCs + ZIP.
7. **Test Drive** — card → sample → unified dashboard.
8. **Rules / Trust / Documentation / Feedback** — cards / support pages.
9. **CI** — card → SDC + baseline + gate → verdict + export.

Implementation rules:
- Input is requested at the feature entry (no global upload screen).
- Every output keeps its trust disclosure.
- No dead buttons; every card's next-step is functional.
- API additions are additive and never contradict engine collections
  (stats-consistency is regression-guarded).
- **Exit criteria:** all 17 cards end-to-end green on CLI/API/webui; full
  verification chain passes.

## Phase D — Feature verification

**Goal:** prove each workflow as a real engineer would use it.

- [ ] Per-feature acceptance: reuse the WF1–WF14 methodology from
      VLSI_ENGINEERING_ACCEPTANCE_REPORT.md against the rebuilt surfaces.
- [ ] Regression: full suite + parity harness + Test Drive contract
      (`real_design_full.sdc`: 7 clocks / 21 pairs / 25 constraints / 82.1% /
      0 errors).
- [ ] API integration tests for every endpoint the rebuild uses.
- [ ] Webui state/UX evidence suites (state isolation, motion, smoke).
- **Exit criteria:** 14/14 workflows accepted on the new surface; 0 new P1.

## Phase E — Workspace UX

**Goal:** the workspace feels like a focused engineering product.

- [ ] Feature-first catalog landing (positioning line + cards).
- [ ] Implicit session: results-led navigation appears after analysis;
      tools always reachable.
- [ ] Clear input/processing/output/next-state visibility on every screen
      (Phase 7 questions answered visibly).
- [ ] Beginner and expert journeys walkthrough (from architecture §12).
- **Exit criteria:** first-time user can complete a workflow without docs;
      expert can reach any capability in ≤2 clicks.

## Phase F — Visual design system

**Goal:** premium engineering product look (Phase 8 direction in the
architecture doc): clean, high contrast, clear typography, subtle depth,
controlled glass/gloss, light base + hairline structure, near-black text.

- [ ] Derive tokens from `rta/docs/product/VISUAL_DESIGN_SYSTEM.md` +
      PRODUCT_WEBSITE_DESIGN_DNA + current Arcade light language.
- [ ] Apply consistently: cards, matrices, findings, disclosures.
- [ ] Never: cluttered, arcade, blurry, excessive gradients,
      dark-text-on-dark, info dumps, tiny nav items.
- **Exit criteria:** design passes engineering-readability review (findings
  readable at a glance; matrices scannable; disclosures always legible).

## Phase G — Business website integration

**Goal:** Surface A (business site) leads into Surface B (workspace).

- [ ] Keep the boundary: site explains, tool works.
- [ ] Feature pages on the site mirror the 17-card catalog; each links into
      the corresponding workspace capability (deep link).
- [ ] Trust/evidence/benchmarks sections link the verified baseline numbers
      (from FUNCTIONAL_BASELINE.md) — no inflated claims.
- [ ] Installation commands + "open the tool" CTA on every feature page.
- **Exit criteria:** every business-site feature page has a working deep link
  into a working workspace workflow.

## Phase H — End-to-end acceptance

**Goal:** the rebuilt product passes the same bar as the functional baseline.

- [ ] Full verification chain (see guiding constraints).
- [ ] Re-run the VLSI engineering acceptance workflows on the rebuilt product.
- [ ] Re-run the parity harness and Test Drive contract.
- [ ] Publishable state: docs, CHANGELOG, `whats-new`, version bump.
- [ ] Final acceptance report update (remediation-style section for the
      rebuild: before/after/test/result per workflow).
- **Exit criteria:** full suite green; 14/14 workflows accepted; no capability
  lost; parity intact; trust disclosures intact.

---

## Open P2 items (tracked, out of scope for Phase C unless they block a card)

From VLSI_ENGINEERING_ACCEPTANCE_REPORT.md (10 P2; the ones affecting the
rebuild):

- P2-3 exit code 2 collision (CI) — document in the one-place contract (A).
- P2-10 exit-code contract + gate matrix in one place — Phase A doc task.
- Corners CLI read-only / MMC CLI absence — decide in Phase C whether MMC gets
  a CLI subcommand (architecture decision; backend `mmc.py` exists).
- Diff-report description duplication — cosmetic, Phase F.
- Lint API `fix:false` empty formatted text — API polish, Phase C.
- Netlist-delta not stated on the input screen — fixed by the card anatomy in
  Phase C (input model shown per card).
- Small Test Drive samples — Phase C (expand sample set).
- No release notes in UI — Phase E (surface `whats-new`).
- No bundle export — Phase C/G decision.

---

## Risks / guardrails

- **Engine drift:** every phase re-runs the parity harness; any engine change
  requires a documented correctness regression first.
- **Capability hiding:** the rebuild must not move capabilities into collapsed
  menus — the 17 cards are primary and visible.
- **Scope creep:** this plan implements workspace architecture, not new
  engine features; new capability requests go through a separate feature
  sprint.
- **Mock data:** no surface ever shows non-backend results; Test Drive stays
  real.

*Planning only — no implementation performed in this sprint.*
