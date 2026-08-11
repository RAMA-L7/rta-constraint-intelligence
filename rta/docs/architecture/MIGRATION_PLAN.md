# Ṛta — Migration Plan (product-first targets)

> **Document kind:** execution plan · **Status:** Phases 0–8 complete · **Phase 9
> (legacy/) executed 2026-08-12** with founder sign-off (see
> `MIGRATION_LOG.md` row 9 for the executed scope and deviations).
> **Date:** 2026-08-07 · **Revision:** targets updated to the product-first
> blueprint (founder corrections).
> **Hard rule:** nothing is deleted. Every legacy item lands in `legacy/`.

---

## 1. Principles

1. **Behavior-preserving moves only.** Imports are updated mechanically and
   verified by the full regression (pytest 800 + benchmarks + smoke + clean-room).
2. **Frozen engine untouched in behavior.** Moves are renames + import updates; no
   logic changes.
3. **One commit per surface.** Each migration step is reviewable and revertible.
4. **Evidence stays intact.** `benchmarks/` data and expected outputs move with
   their runners; expected values are never edited during a move.
5. **Do it after a full initial commit.** Only 93 files are git-tracked today;
   commit the working tree first so moves are visible in git history
   (readiness condition 1).
6. **Product-first targets.** Every target folder is a product responsibility
   (see `REPOSITORY_BLUEPRINT.md`); no `frontend/backend/shared` folders.

## 2. Migration order (phased)

| Phase | Scope | Moves | Regression gates |
|---|---|---|---|
| 0 | **Pre-flight** | `git add -A` full commit (or branch) of current working tree; create canonical `docs/product/PRODUCT_CAPABILITY_CATALOG.md` | none |
| 1 | **branding/** | `ui/theme.py` → `rta/branding/tokens/`; `webui theme.js` pairing follows | pytest + UI benchmark + smoke |
| 2 | **engine/** | 17 frozen modules → `rta/engine/**` (grouped per blueprint §2; `evidence.py` is the 18th engine-adjacent module but targets `rta/evidence/manifest/` in Phase 7) | pytest + golden + semantic + netlist + readiness runners |
| 3 | **tools/** | generator, linter, converter, corner_manager, mmc, batch_runner, reporter → `rta/tools/**` | pytest tools + CLI audit |
| 4 | **cli/** + **api/** | `cli.py` → `rta/cli/` (entry points updated in pyproject); `api_server.py` → `rta/api/` | CLI contract audit + smoke + API contract |
| 5 | **workspace/** | `webui/` → `rta/workspace/webui/`; `data/feedback.json` → `rta/workspace/data/` | UI benchmark + UX + state + motion + browser pass |
| 6 | **website/** | `site/` → `rta/website/` | website integrity check |
| 7 | **tests + evidence** | `tests/` → `rta/tests/`; `benchmarks/` → `rta/evidence/` (runners/data/reports); `evidence.py` + `RELEASE_EVIDENCE.json` → `rta/evidence/manifest/` | full regression |
| 8 | **examples + docs + knowledge** | samples/, policy_examples/, custom_rules_example.yaml → `rta/examples/`; docs/ → `rta/docs/` *(contingent on open question 4)*; rules/trust reference docs → `rta/knowledge/` | evidence check |
| 9 | **legacy/** | `app.py`, `ui/`, `.streamlit/`, `svg/`, `graphify-out/`, working-copy inventory → `legacy/**`; write `LEGACY_README.md` | full regression + smoke + clean-room |
| 10 | **root cleanup** | remove now-empty stubs; keep pyproject, README, LICENSE, shims, .github, .gitignore, .dockerignore, .pre-commit-config | release checklist |

## 3. Per-surface move table (current → future → why → deps → risk)

### 3.1 Engine modules (frozen)

| Current | Future | Why | Deps | Risk |
|---|---|---|---|---|
| `sdc_preprocess.py`, `tcl_resolver.py` | `rta/engine/preprocess/` | preprocess domain | checker, cli | import path updates |
| `checker.py`, `rules_registry.py` | `rta/engine/rules/` | rule domain | all | highest-touch |
| `clock_relations.py`, `coverage.py`, `design_coverage.py`, `constraint_interactions.py`, `constraint_readiness.py`, `wildcard_analyzer.py` | `rta/engine/analysis/` | analysis domain | checker | many imports |
| `design_context.py` | `rta/engine/context/` | netlist domain | coverage | import updates |
| `constraint_diff.py`, `readiness_diff.py`, `finding_identity.py` | `rta/engine/diff/` | change domain | tcl_resolver, wildcard | many imports |
| `policy_engine.py`, `custom_rules.py` | `rta/engine/policy/` | policy domain | checker | import updates |
| `support_boundary.py` | `rta/engine/trust/` | trust domain | all surfaces | import updates |

### 3.2 Surfaces

| Current | Future | Why | Deps | Risk |
|---|---|---|---|---|
| `cli.py` | `rta/cli/` | terminal surface | engine+tools | entry point in pyproject |
| `api_server.py` | `rta/api/` | programmatic HTTP surface | engine+branding | static path resolution |
| `webui/` (8 files) | `rta/workspace/webui/` | engineering application | api, branding | asset paths, hash routes |
| `site/` (17 files) | `rta/website/` | business website | evidence, branding | absolute links |
| `app.py` + `ui/` + `.streamlit/` | `legacy/streamlit/` | preserved legacy | none (retired) | none |

### 3.3 Branding / evidence / data

| Current | Future | Why | Deps | Risk |
|---|---|---|---|---|
| `ui/theme.py` | `rta/branding/tokens/theme.py` | token source of truth | api_server | import update (critical: server imports it) |
| `evidence.py` | `rta/evidence/manifest/` | evidence manifest | build_evidence | import updates |
| `RELEASE_EVIDENCE.json` | `rta/evidence/manifest/` | release artifact | release tooling | path in scripts |
| `data/feedback.json` | `rta/workspace/data/` | feedback store (workspace runtime data) | API + Feedback page | path resolution |

### 3.4 Tools (each first-class, per correction C4)

| Current | Future | Why | Deps | Risk |
|---|---|---|---|---|
| `generator.py` | `rta/tools/generate/` | first-class tool | engine | imports (cli, workspace) |
| `linter.py` | `rta/tools/lint/` | first-class tool | engine | imports |
| `converter.py` | `rta/tools/convert/` | first-class tool | engine | imports |
| `corner_manager.py`, `mmc.py` | `rta/tools/corners/` | first-class tool | engine | imports |
| `batch_runner.py` | `rta/tools/batch/` | first-class tool | engine | imports |
| `reporter.py` | `rta/tools/report/` | first-class tool | engine | imports |

### 3.5 Tests & evidence

| Current | Future | Why | Deps | Risk |
|---|---|---|---|---|
| `tests/` (27 files + conftest + runner) | `rta/tests/` | suite beside engine | pytest config, CI | pytest rootdir/conftest |
| `benchmarks/` (runners + 28 suites + 18 data dirs + reports) | `rta/evidence/` | verification system | engine, CI | data paths in runners |

### 3.6 Examples, docs, knowledge

| Current | Future | Why | Deps | Risk |
|---|---|---|---|---|
| `samples/` (19) | `rta/examples/samples/` | demo corpus | tests, docs | sample paths |
| `policy_examples/` (3) | `rta/examples/policies/` | policy demos | docs | — |
| `custom_rules_example.yaml` | `rta/examples/` | custom-rules demo | docs | — |
| `docs/` (company, rta, product, features, architecture) | `rta/docs/` | docs lifecycle | README links | link rewriting *(contingent — open question 4)* |
| rule/trust reference docs (rules_registry-driven, support_boundary) | `rta/knowledge/` | product knowledge base | engine | — |
| `reference-features-for-startup.md` | canonical copy → `docs/product/PRODUCT_CAPABILITY_CATALOG.md`; working copy → `legacy/working-copies/` | permanent feature inventory (correction C5) | sprint audits | links |

### 3.7 Root packaging & CI (stay)

`pyproject.toml`, `requirements.txt`, `Dockerfile`, `.dockerignore`, `.gitignore`,
`.pre-commit-config.yaml`, `.github/`, `rta.cmd`, `sdc-tools.cmd`, `README.md`,
`CHANGELOG.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `LICENSE`.

### 3.8 Regenerable / legacy-only

| Path | Action | Why |
|---|---|---|
| `build/`, `dist/`, `sdc_tools.egg-info/`, `__pycache__/`, `.pytest_cache/`, `.benchmarks/` | leave; gitignored, regenerated | build artifacts |
| `svg/` (40 unreferenced icons) | → `legacy/assets/` | preserved, unreferenced |
| `graphify-out/` | → `legacy/experiments/` | gitignored experiment |
| `reference-features-for-startup.md` (after catalog is canonical) | → `legacy/working-copies/` | provenance |

## 4. Dependency & risk notes

- **Highest risk:** Phase 2 (engine imports are the most referenced). Mitigation:
  mechanical import rewrite + full golden/semantic regression per group.
- **Critical dependency:** `api_server.py` imports `ui.theme` (tokens). Phase 1
  moves tokens to `branding/` **before** Phase 4, so the server import updates once.
- **Entry points:** `pyproject.toml` `[project.scripts]` (`rta = cli:main`) must
  change in Phase 4; wheel identity stays `sdc-tools` until a separate packaging
  ADR (readiness condition 3).
- **CI:** `.github/workflows/ci.yml` paths update after Phases 7–9.
- **Docs links:** every `docs/**` cross-link and README references must be
  rewritten in Phase 8 (link checker step).

## 5. Rollback

Each phase is a separate commit. Rollback = revert that commit; no cross-phase
coupling is introduced.

## 6. What is NOT in this plan

- No deletion of any file.
- No change to CLI exit-code contract.
- No change to engine behavior.
- No new dependencies.
- No rename of SDC vocabulary.
- No execution before founder approval.

---

*Plan complete (product-first targets). Phase 9 executed 2026-08-12; Phases 1–8
were completed in prior sprints (see `MIGRATION_LOG.md`). Deviations recorded in
`MIGRATION_LOG.md` row 9 and `legacy/LEGACY_README.md`: `svg/`, `graphify-out/`,
`.streamlit/` were already absent from the tree when Phase 9 ran.*
