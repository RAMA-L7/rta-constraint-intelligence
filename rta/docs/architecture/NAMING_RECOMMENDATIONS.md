# Ṛta — Repository Naming Recommendations

> **Document kind:** architecture review · **Status:** proposed — awaits founder approval
> **Date:** 2026-08-07 · **Applies to:** `docs/architecture/REPOSITORY_BLUEPRINT.md` §2
> **Criteria (founder Correction 7):** every name must be immediately
> understandable · startup quality · professional · scalable · no abbreviations ·
> no temporary names · no duplicates. A new engineer understands the repository
> in under 10 minutes.

---

## 1. Naming principles

1. **Product responsibility, not framework.** A folder is named for what the
   product does in it, never for the technology used there.
2. **One word, lowercase** — matching Python package conventions and the ASCII
   technical identifier `rta`.
3. **No abbreviations** except universal industry terms (`api`, `cli`), which are
   unambiguous in engineering contexts and documented as such.
4. **No temporary words:** no `new`, `old`, `final`, `temp`, `v2` in folder
   names. Versioning lives in releases, not paths.
5. **No duplicates:** every name must have exactly one meaning across the tree.
6. **Scalable:** a name must still make sense when its folder has 10× the
   content.

---

## 2. Per-folder review

| Folder (proposed) | Meaning | Meets criteria? | Rejected alternatives |
|---|---|---|---|
| `rta/branding/` | The product's visual identity — tokens, type, mark. Consumed by every surface. | ✅ one clear meaning | `design/` (ambiguous with design work), `theme/` (too narrow — tokens only), `styles/` (framework-y) |
| `rta/engine/` | The deterministic analysis core. The "brain". | ✅ industry-standard | `core/` (vague), `analysis/` (too narrow — also holds preprocess/diff/policy/trust), `backend/` (❌ technology-first) |
| `rta/api/` | Programmatic HTTP surface. | ✅ universal term, documented | `server/` (narrow — also future public API), `http/` (technology) |
| `rta/cli/` | Terminal surface. | ✅ universal term, documented | `terminal/` (verbose), `cmd/` (ambiguous with Windows cmd) |
| `rta/workspace/` | The engineering application engineers use daily. | ✅ product-first, memorable | `app/` (too generic), `frontend/` (❌ technology-first), `ui/` (framework-y, collides with legacy `ui/` name) |
| `rta/website/` | Business/marketing site. | ✅ | `marketing/` (narrow — also hosts docs/release), `site/` (generic) |
| `rta/tools/` | First-class engineering tools (generate/lint/convert/corners/mmc/batch/report). | ✅ | `utilities/` (diminishes them — they ARE the product), `bin/` (framework-y) |
| `rta/knowledge/` | Rules reference, trust model, in-app docs. | ✅ | `content/` (vague), `rules/` (too narrow — also trust + docs) |
| `rta/evidence/` | Benchmarks, runners, manifest, reports — everything that verifies claims. | ✅ distinct | `benchmarks/` (too narrow — also manifest + evidence module), `verification/` (clashes with tests' role) |
| `rta/examples/` | Sample corpus for demos + tests. | ✅ | `samples/` (fine, but `examples/` is the broader, standard name) |
| `rta/assets/` | Shared static material (curated icons, fonts). | ✅ standard | `static/` (web-framework term), `media/` (too broad) |
| `rta/infrastructure/` | CI, Docker, packaging, hooks, release tooling. | ✅ | `devops/` (jargon), `ci/` (too narrow — also docker/packaging), `build/` (❌ collides with the gitignored `build/` artifact) |
| `rta/tests/` | Pytest suite. | ✅ | `test/` (singular, nonstandard) |
| `rta/docs/` | Company + foundation + product + architecture docs. | ✅ | `documentation/` (verbose) |
| `legacy/` (repo root) | Preserved history — superseded generations, experiments. | ✅ honest, permanent | `archive/` (implies dead/removed; `legacy/` signals "old but preserved on purpose"), `old/` (❌ temporary-sounding), `history/` (ambiguous) |

---

## 3. Explicitly rejected names

| Rejected | Why |
|---|---|
| `frontend/` · `backend/` | Technology-first, not product-first (founder Correction 1) |
| `shared/` | No product meaning — "shared between what?" (founder Correction 1) |
| `ui/` | Framework-era name; collides with the legacy Streamlit `ui/` package |
| `more/` · `misc/` · `other/` | Catch-alls — the product has no "everything else" bucket |
| `build/` as a source folder | Already a gitignored artifact dir; would be a duplicate meaning |
| `temp/` · `tmp/` · `new/` · `final/` | Violate the no-temporary-names rule |
| `src/` | Works for libraries; a product repository reads better with named responsibilities |

---

## 4. Why these names hold at 10× scale

| Future growth | Still fits |
|---|---|
| 50 engine modules | `engine/{preprocess,rules,analysis,context,diff,policy,trust}/` — domain split already present |
| 30 workspace pages | grouped by workflow (START/ANALYZE/DECIDE/OUTPUT/KNOWLEDGE/TOOLS) |
| Public API for team products | `api/` becomes the documented integration surface |
| 100 benchmark suites | `evidence/runners/` + `evidence/data/` + `evidence/reports/` |
| Pricing + blog | pages under `website/` — no new top-level folder needed |
| Enterprise auth/governance | modules under `workspace/` (session/auth) and `api/` (integration) |

---

## 5. Naming-consistency contract

1. **Visible brand:** Ṛta (Unicode) — website, app, docs, reports.
2. **Technical ASCII identifier:** `rta` — CLI, package, env vars (`RTA_*`),
   URLs, imports. (Established in the foundation sprint; unchanged.)
3. **SDC vocabulary:** never renamed — SDC, SDC file, SDC-046, `check_sdc()`
   remain exact.
4. **Folder names:** the table in §2 is the single source; any new top-level
   folder must pass the same six criteria and be added here before creation.

---

## 6. Summary

The proposed tree passes every criterion in founder Correction 7. The two
judgment calls — `legacy/` over `archive/`, and `evidence/` over
`benchmarks/` — are deliberate: `legacy/` signals intent to preserve,
`evidence/` names the *system* (benchmarks are one part of it).

---

*Naming review complete. Consistent with `REPOSITORY_BLUEPRINT.md` §9 and
`LEGACY_STRATEGY.md`.*
