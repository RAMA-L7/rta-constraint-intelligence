# Ṛta — Phase C → UX Transition Checkpoint

> Lightweight transition audit. Phase C is **accepted** (19/19 capabilities
> PASS · 0 P0 · 0 P1 · 0 semantic parity regressions · 1,227 tests passing).
> This document confirms the functional layer is frozen and safe for the UX
> phase — nothing was modified during this audit.

## 1. Functional baseline (frozen)

- **Engine**: deterministic, frozen behavior (`FUNCTIONAL_BASELINE.md`). No
  rule semantics, IDs, severities, parser, coverage/clock/readiness/diff
  mathematics changed during Phase C — only entry points, input surfaces,
  presentation and next actions.
- **Verification**: 1,227 pytest · 58/58 workspace UX · 37/37 UI/API ·
  12/12 state isolation · 10/10 smoke · 17/17 cleanroom · 16/16 CLI audit ·
  200-file parity harness with **0 semantic diffs** across all 9 batteries.
- **Version**: v1.5.8 · release status `RC_READY_WITH_KNOWN_LIMITATIONS`.

## 2. The 19 capabilities (all visible, all individually usable)

| Group | Capabilities |
|---|---|
| Core | Validate · SDC Generator · SDC Linter · SDC Converter |
| Analysis | Clock Intelligence · Coverage · Design Context · Constraint Conflicts · Readiness · SDC Diff |
| Advanced | Corner Manager · MMC · Test Drive · Rules · CI |
| Output/Support | Reports · Trust · Documentation · Feedback |

- **All visible from the catalog**: 17 capability cards on the feature-first
  landing (`#/catalog`) grouped Core / Analysis / Advanced; Documentation and
  Feedback sit in the always-visible **CAPABILITIES** nav group.
- **No "More Tools"**, no overflow disclosure, no hidden primary capability —
  verified absent from the webui source.
- **Each capability has its own entry + input surface** (own panel/textareas,
  own required/optional inputs) — verified end-to-end per capability in
  `PHASE_C_FINAL_ACCEPTANCE.md`.

## 3. Known limitations (pre-existing, not UX-blocking)

1. **P2-1** — corner creation/editing and MMC generation have no CLI (API/webui
   only); Corner Manager page honestly discloses read-only inspection.
2. **No true READY fixture** in the corpus — Readiness verified at BLOCKED and
   REVIEW_REQUIRED tiers; a READY fixture was not manufactured.
3. **Coverage ≠ correctness** — surfaced on every coverage surface.
4. **P2 (10)** from the acceptance report remain tracked in
   `PRODUCT_REBUILD_PLAN.md`; none block any of the 19 workflows.

## 4. UX problems the redesign must address

These are design-surface observations carried from the acceptance report —
none block the functional layer:

- **P2-1 / P2-10** — CLI-only engineers lack corner editing / MMC generation;
  the UX phase should keep the honest "read-only inspection" wording rather
  than implying edit capability.
- **P2-9** — clock-relation pair detail is verbose-only; the Clocks page's
  relationship matrix is dense — a redesign should prioritize scannability.
- **First-run clarity** — the catalog is already feature-first; the UX phase
  should preserve "what is this / what input / what will Ṛta do / what do I
  get / what next" on every surface (the current contract).
- **Trust disclosures must survive the redesign verbatim** — "NOT an STA
  timing signoff", "READY does not mean setup/hold passes", "Coverage is NOT
  correctness", "CI PASS ≠ timing pass", "Engine failure never becomes PASS".
- **No fake states** — empty, error, loading and success states must continue
  to render real backend evidence only.

## 5. UX blockers

**None.** No P0, no P1, no semantic parity regression, no hidden capability,
no dead workflow exists that would make a UX redesign unsafe. The functional
baseline is byte-identical across Groups 1–4.

---

## PHASE C FUNCTIONALLY FROZEN — SAFE TO BEGIN UX DESIGN.
