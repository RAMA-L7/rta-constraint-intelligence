# Ṛta — Founder Review Package (Revised)

> **Document kind:** review package · **Status:** REVISED — awaiting founder approval
> **Date:** 2026-08-07 · **Sprint:** Ṛta Startup Foundation — Founder Review
> Corrections (documentation only — no files moved, no UI implemented, no
> features changed, no packages renamed).
> **Corrections applied:** product-first architecture (C1), workspace IA (C2),
> website/workspace separation (C3), tool-first philosophy (C4), permanent
> feature catalog (C5), legacy strategy (C6), naming standards (C7), migration
> readiness (C8).

---

## Contents

| # | Item | Location |
|---|---|---|
| 1 | Repository Audit | `docs/architecture/REPOSITORY_AUDIT.md` |
| 2 | Repository Blueprint (product-first revision) | `docs/architecture/REPOSITORY_BLUEPRINT.md` |
| 3 | Workspace Information Architecture | `docs/architecture/WORKSPACE_INFORMATION_ARCHITECTURE.md` |
| 4 | Feature Mapping | `docs/architecture/FEATURE_MAPPING.md` |
| 5 | Naming Recommendations | `docs/architecture/NAMING_RECOMMENDATIONS.md` |
| 6 | Legacy Strategy | `docs/architecture/LEGACY_STRATEGY.md` |
| 7 | Migration Plan | `docs/architecture/MIGRATION_PLAN.md` |
| 8 | Migration Readiness | `docs/architecture/MIGRATION_READINESS.md` |
| 9 | Business Website vs Workspace | `REPOSITORY_BLUEPRINT.md` §5 + `WORKSPACE_INFORMATION_ARCHITECTURE.md` |
| 10 | Open Questions | §5 below |

---

## 1. Corrections record (founder feedback → what changed)

| # | Founder correction | What changed | Where |
|---|---|---|---|
| C1 | Technology-first → product-first | Blueprint rewritten: every folder is one product responsibility; `frontend/backend/shared` rejected | `REPOSITORY_BLUEPRINT.md` |
| C2 | Workspace IA blueprint | New document: first screen, first action, engineer's journey, tool availability classes, session model | `WORKSPACE_INFORMATION_ARCHITECTURE.md` |
| C3 | Website vs workspace separation | Explicit two-surface contract; only `branding/` shared | Blueprint §5 |
| C4 | Tools are the product | All 18 tools first-class; session vs standalone vs always-visible classes; nothing under "More tools" | Blueprint §6 + IA §4 + Feature Mapping §2 |
| C5 | Feature catalog permanent home | `reference-features-for-startup.md` → `docs/product/PRODUCT_CAPABILITY_CATALOG.md` (canonical); working copy archived to `legacy/` | Blueprint §7 + Feature Mapping header |
| C6 | Legacy strategy | New `legacy/` policy: what belongs, what never moves, decision procedure, lifecycle | `LEGACY_STRATEGY.md` |
| C7 | Naming standards | Per-folder name review vs 6 criteria; rejected names; 10× scale test | `NAMING_RECOMMENDATIONS.md` |
| C8 | Migration readiness | 5-year stability assessment + 3 pre-migration conditions | `MIGRATION_READINESS.md` |

## 2. Legacy inventory (preserved, never deleted)

| Item | Count | Why legacy | Proposed home |
|---|---|---|---|
| `app.py` + `ui/` (Streamlit) | 23 files | Superseded by `api_server.py` + `webui/` (premium workspace) | `legacy/streamlit/` |
| `.streamlit/config.toml` | 1 | Stale "SDC Validator" branding + old dark palette for retired UI | `legacy/streamlit/config/` |
| `svg/` (`gemini-svg (N).svg`) | 40 | Unreferenced AI-generated icons — no HTML/JS/CSS reference them | `legacy/assets/` (curated reference) |
| `graphify-out/` | 54 | Gitignored knowledge-graph experiment output | `legacy/experiments/` |
| `reference-features-for-startup.md` | 1 | Working inventory, superseded by the canonical catalog | `legacy/working-copies/` |
| `build/`, `dist/`, `sdc_tools.egg-info/` | 66 | Build artifacts, gitignored, regenerable | regenerate; no move needed |
| `__pycache__/`, `.pytest_cache/`, `.benchmarks/` | 30+ | Runtime caches, gitignored | leave |
| `docs/product/PHASE17_*` | 3 | Historical phase audits (superseded by product docs) | keep in `docs/` (history) |

## 3. Duplicate inventory

| Duplicate pair | Nature | Resolution |
|---|---|---|
| `app.py`+`ui/` vs `api_server.py`+`webui/` | Two UI generations | Keep both; legacy → `legacy/streamlit/`; current → `rta/workspace/` |
| `ui/theme.py` vs `webui/assets/js/theme.js` | Token source of truth + JS fallback (by design) | Keep pairing; move both to `rta/branding/tokens/` |
| `build/lib/*.py` vs root `*.py` | Build output mirroring source | Regenerate; never edit `build/` |
| `reference-features-for-startup.md` vs catalog | Working copy vs canonical | Catalog is canonical; working copy → `legacy/working-copies/` |
| `docs/company/REPOSITORY_MAP.md` vs `docs/architecture/` series | Company-level map vs deep architecture series | Keep both; architecture series is the deep-dive |

## 4. Business website structure (current → target)

**Current:** `site/` — index, platform, capabilities (+8 per-capability pages),
benchmarks, trust, docs, release + `assets/css/site.css` + `assets/js/site.js`.
**Target:** `rta/website/` (unchanged content, new home).
**Boundary:** marketing/company/evidence/trust/release only. No engineering app
content mixes in. Pricing/blog are future pages under the same folder.

## 5. Open questions for the founder (revised)

Resolved by these corrections:
- ✅ Feature inventory home → `docs/product/PRODUCT_CAPABILITY_CATALOG.md` (C5).
- ✅ Legacy home → `legacy/` at repo root, committed (C6).
- ✅ Naming → product-first table (C7).
- ✅ Tool visibility → session/standalone/always-visible classes (C4).

Still open — the three pre-migration conditions (`MIGRATION_READINESS.md` §5):
1. **Initial commit:** only 93 files are git-tracked; most Ṛta work is
   uncommitted. Approve a full `git add -A` commit (or a fresh branch) **before**
   any move?
2. **Package identity:** keep PyPI wheel `sdc-tools` (recommended — avoids a
   breaking rename) and open a packaging ADR for a future `rta` wheel? Or rename
   now?
3. **Imports during migration:** thin `__init__.py` shim layer (zero-import-
   change, staged) vs mechanical rewrite per phase (cleaner end state, more
   churn)? Recommendation: shim layer for Phases 1–9, removed in Phase 10.
4. **`docs/` location:** move `docs/` into `rta/docs/` (single docs home) vs
   keep `docs/` at repo root (less link churn)? (Recommendation: move — one
   product home.)
5. **`svg/` assets:** keep the 40 generated icons in `legacy/assets/` (curated
   later) vs drop from tracking entirely? (Recommendation: keep in `legacy/`.)

## 6. What happens next

- Founder reviews this package + the revised architecture series.
- Founder answers §5 open questions (or delegates).
- On approval, migration executes per `MIGRATION_PLAN.md` phase order, after the
  three conditions in `MIGRATION_READINESS.md` §5 are satisfied.
- Until then: **no files are moved, no UI is implemented, no features change.**

---

*Revised review package complete. Awaiting founder approval. Stop point reached.*
