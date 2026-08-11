# Ṛta — Migration Readiness Assessment

> **Document kind:** final architecture review · **Status:** proposed — awaits founder approval
> **Date:** 2026-08-07 · **Applies to:** the product-first blueprint
> (`REPOSITORY_BLUEPRINT.md`) before Phase 1 migration begins.
> **Founder requirement (Correction 8):** is the repository architecture stable
> enough to remain valid for the next five years? If not, recommend changes now.
> After migration, major restructuring should never be necessary again.

---

## 1. Verdict

**READY — with three conditions.** The product-first structure is stable for a
five-year horizon. The three conditions (§5) are inexpensive to satisfy now and
expensive to retrofit later; they are folded into the migration plan.

## 2. Stability criteria — assessed

| Criterion | Assessment | Verdict |
|---|---|---|
| **Product-first naming** | Every folder = one product responsibility; no framework names (Correction 1) | ✅ stable |
| **Workspace IA** | Workflow-first (Import → Analyze → Understand → Export); tools classified as session/standalone/always-visible | ✅ stable |
| **Website/workspace separation** | Business vs engineering never mixed; only `branding/` shared (Correction 3) | ✅ stable |
| **Tool-first product** | 18 tools are first-class; none hidden (Correction 4) | ✅ stable |
| **Feature inventory** | Canonical `docs/product/PRODUCT_CAPABILITY_CATALOG.md`; mapping table as contract | ✅ stable |
| **Legacy preservation** | `legacy/` at root; never deleted, never imported; indexed (Correction 6) | ✅ stable |
| **Engine hermeticity** | Frozen engine depends on stdlib only; one-direction dependency graph | ✅ stable |
| **Naming standards** | All names pass the 6 criteria; judged at 10× scale (Correction 7) | ✅ stable |
| **SDC vocabulary** | Never renamed — technical terminology intact | ✅ stable |
| **Packaging identity** | ASCII `rta` technical identifier vs Unicode Ṛta visible brand — documented split | ✅ stable |

## 3. What the five-year horizon adds — and why the structure survives it

| Future | Where it lands | Structural change needed? |
|---|---|---|
| V2 subsystem intelligence (more analysis) | `engine/analysis/` + workspace routes | none |
| V3 top-level (more clocks/coverage depth) | same pattern | none |
| Team product (shared baselines, policies, history) | `api/` integration surface + `workspace/` session modules + `knowledge/policy` | none |
| Enterprise (governance, audit, support) | `api/`, `infrastructure/`, `website/` (pricing) | none |
| Public SDK / integrations | `api/` documented surface | none |
| 10× benchmark suites | `evidence/{manifest,runners,data,reports}/` | none |
| 10× docs | `docs/` + `knowledge/docs-as-product/` split already exists | none |

The architecture is sized for the roadmap in `docs/rta/PRODUCT_ROADMAP.md`
without structural rework. **That is the definition of a five-year-stable tree.**

## 4. Risks if migration happens as-is (mitigated in plan)

| Risk | Mitigation |
|---|---|
| Engine import churn (highest touch) | Mechanical rewrite + full golden/semantic regression per group (MIGRATION_PLAN Phase 2) |
| `api_server.py` imports `ui.theme` | Phase 1 moves tokens to `branding/` before Phase 5 (server updates once) |
| Test rootdir/conftest paths | Phase 7 includes pytest config update + full regression |
| Benchmark data paths in runners | Paths updated mechanically; expected values never edited |
| Docs cross-links | Phase 8 includes a link-rewrite + link-check step |

## 5. Three conditions before green light

1. **Initial full commit.** Only 93 files are git-tracked. Phase 0 (`git add -A`
   full commit or branch) must happen first so every move is visible in history
   and revertible. *(Founder open question 1 — approval required.)*
2. **Canonical catalog first.** `docs/product/PRODUCT_CAPABILITY_CATALOG.md`
   must be created (or confirmed) before migration so the mapping contract has
   its permanent anchor. The root working copy then archives to `legacy/`.
3. **Packaging ADR decision.** Whether the PyPI wheel stays `sdc-tools` or
   becomes `rta` must be decided *before* Phase 4 (entry points) — changing it
   later is the one genuinely breaking move. *(Founder open question 2 —
   recommendation: keep `sdc-tools` wheel identity for compatibility; open a
   packaging ADR for a future rename.)*

## 6. What would make this review fail — and why it doesn't

- "Folder names will mean something different in 2 years" → all names are
  product responsibilities, which are stable; frameworks are not.
- "We'll need frontend/backend splits later" → surfaces are already separate
  product folders (`workspace/`, `website/`, `api/`, `cli/`); a technology
  split adds nothing.
- "Evidence will outgrow benchmarks/" → `evidence/` is named for the system,
  not the current content.
- "Legacy will rot" → `legacy/` is indexed and policy-governed, not abandoned.

## 7. Post-migration guarantee

After the 10-phase migration, **major restructuring should never be necessary
again** — the blueprint, workspace IA, naming, legacy, and evidence contracts
are all in place, and any new work has a documented home.

---

*Assessment complete. RECOMMENDATION: approve the product-first blueprint and
begin Phase 0 → Phase 1 of `MIGRATION_PLAN.md` after the three conditions in §5
are satisfied.*
