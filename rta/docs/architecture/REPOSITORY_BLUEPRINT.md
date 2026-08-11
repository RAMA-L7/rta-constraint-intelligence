# Ṛta — Repository Blueprint (Product-First)

> **Document kind:** architectural blueprint (approved direction, not yet executed)
> **Status:** REVISED per founder review — awaits final approval · **Date:** 2026-08-07
> **Predecessor:** `docs/architecture/REPOSITORY_AUDIT.md` (classification of the
> current tree) · **Execution plan:** `docs/architecture/MIGRATION_PLAN.md`
> **Correction record:** this revision replaces the technology-first draft
> (frontend/backend/shared) with a **product-first** architecture — every folder
> is one product responsibility, not one framework.
> **Constraint:** no file is deleted; the legacy tree remains recoverable in
> `legacy/`.

---

## 1. Design principle — product-first, not technology-first

Ṛta is a product, not a Python project. The repository is organized around
**what the product does and how engineers use it**, never around what framework
a surface happens to use.

| Technology-first (rejected) | Product-first (this blueprint) |
|---|---|
| `frontend/` · `backend/` · `shared/` | `workspace/` · `website/` · `engine/` · `api/` · `cli/` |
| Folders named by framework | Folders named by product responsibility |
| "Where does the UI code go?" | "Where does an engineer do this work?" |

Each top-level folder answers one question a new engineer would ask:

| Folder | It answers |
|---|---|
| `branding/` | What is Ṛta's identity? |
| `engine/` | How does Ṛta analyze constraints? |
| `api/` · `cli/` | How do I drive Ṛta programmatically? |
| `workspace/` | Where do I do engineering work? |
| `website/` | What do I show the world? |
| `tools/` | Which discrete jobs can I run? |
| `knowledge/` | What does Ṛta know — rules, trust, support boundaries? |
| `evidence/` | How is every claim verified? |
| `examples/` | What can I try it on? |
| `assets/` | Shared static material |
| `infrastructure/` | How is it built, tested, shipped? |
| `tests/` · `docs/` | How is it verified and understood? |

---

## 2. Target architecture

```
sdc-tools/                     ← repo root (existing git repository, unchanged)
├── rta/                       ← FUTURE PRODUCTION ROOT
│   ├── branding/              ← Ṛta visual identity (tokens, type, mark)
│   │   └── tokens/            ← ui/theme.py (source of truth) + webui theme.js fallback
│   ├── engine/                ← deterministic analysis core (FROZEN — the "brain")
│   │   ├── preprocess/        ← sdc_preprocess.py, tcl_resolver.py
│   │   ├── rules/             ← checker.py, rules_registry.py
│   │   ├── analysis/          ← clock_relations.py, coverage.py, design_coverage.py,
│   │   │                         constraint_interactions.py, constraint_readiness.py,
│   │   │                         wildcard_analyzer.py
│   │   ├── context/           ← design_context.py
│   │   ├── diff/              ← constraint_diff.py, readiness_diff.py, finding_identity.py
│   │   ├── policy/            ← policy_engine.py, custom_rules.py
│   │   └── trust/             ← support_boundary.py
│   ├── api/                   ← HTTP surface (api_server.py + /api/* routes)
│   ├── cli/                   ← terminal surface (cli.py + command modules)
│   ├── workspace/             ← ENGINEERING APPLICATION (the product engineers use)
│   │   └── webui/             ← SPA (index.html + assets/js + css) — premium workspace
│   ├── website/               ← BUSINESS WEBSITE (marketing · company · benchmarks ·
│   │   │                         trust · docs · release — never engineering content)
│   │   └── (site/ content moves here)
│   ├── tools/                 ← FIRST-CLASS tools (each is the product, never hidden)
│   │   ├── generate/          ← generator.py
│   │   ├── lint/              ← linter.py
│   │   ├── convert/           ← converter.py
│   │   ├── corners/           ← corner_manager.py, mmc.py
│   │   ├── batch/             ← batch_runner.py
│   │   └── report/            ← reporter.py
│   ├── knowledge/             ← product knowledge base
│   │   ├── rules/             ← rule reference (rules_registry-driven docs)
│   │   ├── trust/             ← trust model, support boundaries (support_boundary.py docs)
│   │   └── docs-as-product/   ← in-app Documentation content
│   ├── evidence/              ← verification system (benchmarks + manifest)
│   │   ├── manifest/          ← evidence.py, RELEASE_EVIDENCE.json
│   │   ├── runners/           ← benchmark runners + 28 suites
│   │   ├── data/              ← benchmark input data
│   │   └── reports/           ← benchmark reports
│   ├── examples/              ← sample SDC, policies, custom rules
│   ├── assets/                ← shared static material (svg/ icons, fonts)
│   ├── infrastructure/        ← CI, Docker, packaging, hooks, release tooling
│   │   ├── ci/                ← .github/workflows
│   │   ├── docker/            ← Dockerfile, .dockerignore
│   │   ├── packaging/         ← pyproject.toml fragments, entry points
│   │   └── scripts/           ← .pre-commit-hooks/, release automation
│   ├── tests/                 ← pytest suite (mirrors engine/tools)
│   └── docs/                  ← company + foundation + product + architecture
│
├── legacy/                    ← PRESERVED history (never deleted, never imported)
│   ├── streamlit/             ← app.py + ui/ (superseded UI generation)
│   ├── experiments/           ← graphify-out/, svg/ (unreferenced generated icons)
│   └── LEGACY_README.md       ← index: what each item is and why it is preserved
│
├── pyproject.toml             ← packaging (remains at repo root)
├── requirements.txt
├── Dockerfile
├── README.md, CHANGELOG.md, CONTRIBUTING.md, CLAUDE.md, LICENSE
├── rta.cmd, sdc-tools.cmd     ← Windows shims (stay at root)
├── .github/                   ← CI workflows (stay)
├── .pre-commit-config.yaml    ← stays
├── docs/product/PRODUCT_CAPABILITY_CATALOG.md ← feature inventory (permanent home)
├── reference-features-for-startup.md ← working copy → archived after catalog is canonical
└── build/ dist/ *.egg-info/ __pycache__/ .pytest_cache/ .benchmarks/  ← gitignored, regenerate
```

---

## 3. Every folder — one product responsibility

| Folder | Product responsibility | Current home → target | Depends on | Scales to |
|---|---|---|---|---|
| `branding/` | The identity: tokens, type, mark. One visual system for every surface. | `ui/theme.py` + `theme.js` | — | new surfaces consume tokens |
| `engine/` | The analysis core. Deterministic, frozen, hermetic. | 18 root modules | stdlib only | V2/V3 analysis modules |
| `api/` | Programmatic HTTP access. Workspace + integration consume it. | `api_server.py` | engine, branding | public API growth |
| `cli/` | Terminal access. CI + scripting. **No analysis logic.** | `cli.py` | engine, tools | new commands |
| `workspace/` | The engineering application — sessions, analysis, reports, tools. | `webui/` | api, branding | new pages, session model |
| `website/` | Business/marketing site. Company, product story, evidence, trust, release. | `site/` | evidence, branding | pricing, blog |
| `tools/` | Discrete engineering jobs — all first-class, none hidden. | generator/linter/converter/corners/mmc/batch/report | engine | new tools |
| `knowledge/` | What Ṛta knows: rules reference, trust model, docs-as-product. | rules_registry-driven docs + support_boundary docs | engine | rule catalog growth |
| `evidence/` | Verification: benchmark runners, suites, data, reports, release manifest. | `benchmarks/`, `evidence.py`, `RELEASE_EVIDENCE.json` | engine, tools | new suites |
| `examples/` | Demo + test corpus: sample SDC, policies, custom rules. | `samples/`, `policy_examples/`, `custom_rules_example.yaml` | — | more examples |
| `assets/` | Shared static material (icons, fonts, images). | `svg/` (curated, referenced only) | branding | design asset growth |
| `infrastructure/` | Build, test, ship: CI, Docker, packaging, hooks, release scripts. | `.github/`, Dockerfile, pyproject, hooks | engine, evidence, tests | release pipelines |
| `tests/` | Pytest suite mirroring engine + tools. | `tests/` | engine, tools | more tests |
| `docs/` | Company, foundation, product, features, architecture documentation. | `docs/` | — | docs lifecycle |

## 4. Dependencies (one direction)

```
rta/tools        → rta/engine
rta/cli          → rta/engine + rta/tools
rta/api          → rta/engine + rta/branding
rta/workspace    → rta/api + rta/branding + rta/evidence
rta/website      → rta/evidence + rta/branding
rta/tests        → rta/engine + rta/tools
rta/evidence     → rta/engine + rta/tools
rta/knowledge    → rta/engine (generated references)
rta/infrastructure → everything (build/test/ship)
```

The engine never imports cli, api, workspace, website, tests, evidence, or
infrastructure. The frozen pipeline stays hermetic and clean-room installable.

## 5. Business website vs workspace — completely separate

Per founder Correction 3, **nothing is mixed**. Only branding is shared.

| | `rta/workspace/` | `rta/website/` |
|---|---|---|
| Audience | Working PD/STA/synthesis engineers | Prospective users, evaluators, public |
| Purpose | Engineering work: import → analyze → understand → export | Company · product story · benchmarks · trust · docs · release · (future) pricing/blog |
| Content | Sessions, findings, clocks, coverage, readiness, diff, reports, tools | Marketing, evidence cards, methodology, trust center |
| Interaction | SPA with the API; session-driven | Static pages; links back to workspace |
| Shared | Branding only: `rta/branding/` tokens, type, mark, motion grammar | Same `rta/branding/` |
| No mixing | ✅ no marketing pages | ✅ no engineering app |

## 6. Tool-first product architecture

Per the Product Charter, `reference-features-for-startup.md` and founder
Correction 4, every capability is a **first-class tool** — the product, never a
hidden catch-all. Each tool owns one workspace route and one engine entry point
(full mapping in `FEATURE_MAPPING.md`):

Validate · Generate · Linter · Converter · Corner Manager · MMC · Clock
Intelligence · Coverage · Design Context · Constraint Conflicts · Readiness ·
Regression Diff · CI · Rules · Trust · Documentation · Test Drive · Feedback.

> **Note — `rta/tools/` vs the 18-tool catalog:** the 18 capabilities are a
> product taxonomy. `rta/tools/` hosts only the *standalone module-based* tools
> (generate, lint, convert, corners, mmc, batch, report). Session tools
> (Validate, Clock Intelligence, Coverage, Design Context, Conflicts, Readiness,
> Diff, CI) live in `rta/engine/analysis/` + workspace routes; knowledge surfaces
> (Rules, Trust, Documentation) live in `rta/knowledge/`. The folder layout
> follows product responsibility, not the catalog count.

## 7. Feature inventory — permanent home

Per founder Correction 5, `reference-features-for-startup.md` becomes a
permanent product document at:

**`docs/product/PRODUCT_CAPABILITY_CATALOG.md`**

- This is the canonical, versioned feature inventory.
- The working copy at the repo root is archived into `legacy/` once the catalog
  is canonical (after migration).
- Every sprint audit and the `FEATURE_MAPPING.md` contract cite the catalog.

## 8. Legacy strategy

Per founder Correction 6 — nothing is lost. `legacy/` at repo root holds every
superseded generation and experiment, indexed by `LEGACY_README.md`. Details in
`LEGACY_STRATEGY.md`. The hard rules:

1. `legacy/` is **never imported** by any runtime surface.
2. `legacy/` is **never deleted**; removal requires founder sign-off and a git
   history reference.
3. The frozen engine, workspace, website, tests, benchmarks, and evidence
   **never move into `legacy/`** — only superseded/experimental work does.

## 9. Naming standards

Per founder Correction 7 — every folder name satisfies: immediately
understandable · startup quality · professional · scalable · no abbreviations ·
no temporary names · no duplicates. The full per-name review is in
`NAMING_RECOMMENDATIONS.md`.

## 10. Scalability

- **V2 (Subsystem Intelligence):** new modules under `rta/engine/analysis/` +
  workspace routes. No structural change.
- **V3 (Top-Level):** same. Domain split already exists.
- **Enterprise (V5):** `rta/workspace/` gains auth/session modules; engine stays
  pure; `rta/api/` becomes the public integration surface.
- **New surfaces:** any new surface consumes `rta/branding/` tokens + evidence
  and lives in its own `rta/<surface>/` folder.

## 11. What this blueprint does NOT do

- Does not rename SDC vocabulary.
- Does not touch the frozen engine's behavior.
- Does not delete any file (superseded work → `legacy/`).
- Does not change the CLI contract or packaging entry points at this stage.
- Does not rewire imports until the migration plan is approved.

## 12. Adoption criteria

A new engineer can, within 10 minutes:
1. Read this blueprint + `REPOSITORY_AUDIT.md` + `FEATURE_MAPPING.md`.
2. Find where any capability lives (engine → api → workspace route).
3. Know where new work belongs (Section 3 table).
4. Know what is frozen and what may change (blueprint + Charter).
5. Distinguish product (rta/) from preserved history (legacy/).

---

*Blueprint complete (product-first revision). Execution is deferred to
`MIGRATION_PLAN.md` and requires final founder approval.*
