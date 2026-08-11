# Ṛta Phase 1 — Repository Migration Log

> Migration from the flat legacy layout to the product-first Ṛta startup structure.
> Executed per the approved `docs/architecture/MIGRATION_PLAN.md` and the
> `REPOSITORY_BLUEPRINT.md` product-first architecture.
>
> **Visible brand:** Ṛta · **Technical ASCII identifier:** `rta` (Python package
> namespace, CLI entry point, URLs).

---

## 1. Migration summary

The repository moved from a flat, technology-first layout (root modules +
`ui/` Streamlit package + `benchmarks/` + `site/`) to a product-first hierarchy
under `rta/` with a clearly separated `legacy/` archive. **Zero behavior
changes** were made to the deterministic backend: every analysis module was
moved as-is, and import compatibility is preserved by a **root-shim strategy**
(see §4). No file was deleted; every pre-migration file is either in its new
production home, its legacy home, or recreated as a shim.

## 2. Target structure (product-first)

```
rta/                         ← production product root (the startup)
  branding/tokens/           ← design tokens (theme)
  engine/
    preprocess/              ← SDC preprocessing, Tcl variable resolution
    rules/                   ← checker, rules registry
    analysis/                ← clock relations, coverage, interactions, readiness, wildcards
    context/                 ← design context
    diff/                    ← constraint diff, readiness diff, finding identity
    policy/                  ← policy engine, custom rules
    trust/                   ← support boundary
  tools/
    generate/ lint/ convert/ corners/ batch/ report/
  cli/                       ← rta CLI (entry points: rta, sdc-tools)
  api/                       ← local stdlib-only API server (workspace backend)
  workspace/
    webui/                   ← product workspace SPA (static)
    server/                  ← feedback service
    data/                    ← runtime data (feedback.json)
  website/                   ← business/marketing website (static)
  evidence/                  ← benchmark runners + suites + data trees
    manifest/                ← evidence.py + RELEASE_EVIDENCE.json (single source of truth)
  examples/                  ← sample SDC designs + policy examples
  tests/                     ← pytest suite
  docs/                      ← product/architecture/company docs
  knowledge/                 ← rules/trust/documentation surfaces
  infrastructure/scripts/    ← gen_shims.py, verify_*.sh (migration tooling)
legacy/                      ← preserved historical work (never packaged)
  streamlit/                 ← the old Streamlit app (app.py + ui/ + .streamlit/)
  assets/                    ← svg assets
  experiments/               ← graphify-out and other experiments
  working-copies/            ← scratch copies
```

## 3. Files moved (by phase)

| Phase | What | From → To |
|---|---|---|
| 2 | Branding | `ui/theme.py` → `rta/branding/tokens/theme.py` |
| 2 | Docs | `docs/**` → `rta/docs/**` (kept the same sub-structure) |
| 2 | Assets | `svg/` → `legacy/assets/svg/` |
| 3 | Engine | `sdc_preprocess.py`, `tcl_resolver.py` → `rta/engine/preprocess/` |
| 3 | Engine | `checker.py`, `rules_registry.py` → `rta/engine/rules/` |
| 3 | Engine | `clock_relations.py`, `coverage.py`, `design_coverage.py`, `constraint_interactions.py`, `constraint_readiness.py`, `wildcard_analyzer.py` → `rta/engine/analysis/` |
| 3 | Engine | `design_context.py` → `rta/engine/context/` |
| 3 | Engine | `constraint_diff.py`, `readiness_diff.py`, `finding_identity.py` → `rta/engine/diff/` |
| 3 | Engine | `policy_engine.py`, `custom_rules.py` → `rta/engine/policy/` |
| 3 | Engine | `support_boundary.py` → `rta/engine/trust/` |
| 3 | Evidence | `evidence.py` → `rta/evidence/manifest/evidence.py` |
| 4 | API | `api_server.py` → `rta/api/api_server.py` (WEBUI_DIR/DATA_DIR path updates) |
| 4 | CLI | `cli.py` → `rta/cli/cli.py` (cmd_web now resolves `rta/api/api_server.py`) |
| 4 | Workspace | `webui/` → `rta/workspace/webui/`, `data/` → `rta/workspace/data/`, `ui/feedback.py` → `rta/workspace/server/feedback.py` |
| 5 | Tools | `generator.py`, `linter.py`, `converter.py`, `corner_manager.py`, `mmc.py`, `batch_runner.py`, `reporter.py` → `rta/tools/**` |
| 6 | Website | `site/` → `rta/website/` (+ GitHub artifact link rewrites) |
| 7 | Evidence | `benchmarks/` → `rta/evidence/` (28 runners + suites + data trees) |
| 7 | Tests | `tests/` → `rta/tests/` |
| 7 | Examples | `samples/` → `rta/examples/samples/`, `policy_examples/` → `rta/examples/policies/`, `custom_rules_example.yaml` → `rta/examples/` |
| 8 | Legacy (planned) | `app.py`, `.streamlit/`, remaining `ui/**` (20 modules) → `legacy/streamlit/`; `svg/` → `legacy/assets/`; `graphify-out/` → `legacy/experiments/` |
| 9 | Legacy (executed 2026-08-12) | `git mv app.py` + `ui/` → `legacy/streamlit/` (whole package, **no root shims** — founder decision). Deviations: `svg/`, `graphify-out/`, `.streamlit/` were **already absent** from the tree — nothing to move (`graphify-out/` stays gitignored). `ui/theme` → `rta/branding/tokens/theme` (Phase 1) and `ui/feedback` → `rta/workspace/server/feedback` (Phase 4) were already moved; active importers (`api_server`, comprehensive tests) were updated to those production homes, and `api_server`'s dangling `from ui import theme` was fixed. `legacy/streamlit/ui/` uses relative internal imports; the preserved app bootstraps the repo root onto `sys.path`. |

**Files preserved in place:** `pyproject.toml`, `README.md`, `CHANGELOG.md`,
`CONTRIBUTING.md`, `CLAUDE.md`, `LICENSE`, `Dockerfile`, `.github/workflows/ci.yml`,
`.pre-commit-config.yaml`, `.pre-commit-hooks/`, `rta.cmd`, `sdc-tools.cmd`,
`.claude/`, requirements files, and the new root-level shim modules.

## 4. Import strategy — root shims (the approved "shim strategy")

All pre-migration imports (`from checker import ...`, `import ui.components`,
`from rules_registry import APP_VERSION`, `python cli.py`, `python -m api_server`,
`python -m pytest tests/`, benchmark runners, the evidence chain) keep working
**unchanged** because:

1. **Root shim modules** (`checker.py`, `rules_registry.py`, … 27 root modules)
   are thin files generated by `rta/infrastructure/scripts/gen_shims.py` that
   `sys.modules`-alias into the real `rta/…` module and re-execute under
   `__main__` via `runpy` when invoked directly (`python cli.py`, `python -m cli`).
2. **`ui/` package — moved wholesale, no root shims (Phase 9).** The old
   Streamlit UI now lives at `legacy/streamlit/ui/` (relative internal imports);
   its production modules (`theme`, `feedback`) live at
   `rta/branding/tokens/theme.py` and `rta/workspace/server/feedback.py`.
   Active code imports those production homes directly — no `ui.*` imports
   remain anywhere.
3. **Path-sensitive code** was updated once, at the new location (benchmark
   ROOT depths, `test_evidence.py`, `test_cli.py`, `test_branding.py`,
   `feedback.py` sample paths, `api_server` WEBUI_DIR, `cli.cmd_web`,
   `build_evidence.py`, `run_comprehensive_checks.py`).

### Path-depth convention (rta/evidence/)
Benchmark files sit at `rta/evidence/<file>.py`; the repository root is:
- `Path(__file__).resolve().parent.parent.parent` (Path-style), or
- `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
  (os.path-style).

## 5. Packaging changes (pyproject.toml)

- `[tool.setuptools.packages.find]` now ships `rta*` + `legacy*`. `legacy*` is
  included so the preserved Streamlit app (`legacy/streamlit/app.py` +
  `legacy/streamlit/ui/`) ships in the wheel — matching the clean-room
  expectation that the wheel contains the legacy app + `ui` package.
- `py-modules` keeps the 27 root shims + `cli`/`api_server`/`evidence` so a
  clean wheel install resolves `rta`-style and legacy-style imports alike.
- `package-data` ships `rta/workspace/webui/**` (SPA), `rta/evidence/manifest/*.json`,
  `rta/examples/*.yaml`.
- Entry points: `rta = cli:main` (modern) and `sdc-tools = cli:main` (alias).
- The business website (`rta/website/**`) is intentionally **not** shipped in
  the wheel — it is a marketing surface served from the repo/hosting, not part
  of the installed product.

## 6. Verification results (all green after migration + review fixes)

| Gate | Result |
|---|---|
| pytest (`rta/tests/`) | **800 passed** |
| Evidence check (`build_evidence.py --check`) | OK: 800 tests / 111 rules / 42 suites / v1.3.0 |
| Benchmark suites (28 files) | **42/42 pass** |
| Benchmark runners (12) | **12/12 pass** (incl. `run_benchmark.py` after path fix) |
| Release smoke | **10/10 pass** |
| Release clean-room | **17/17 pass** |
| Release CLI audit | **16/16 pass** |
| Release packaging probe | OK (shims, sdist/wheel, ui) |
| CLI contract | `Ṛta v1.3.0`; `check` runs against `rta/examples/samples/example.sdc` |
| API boot (repo) | health OK, SPA 200, `/api/rules` 111 rules |
| Clean wheel install (temp venv) | CLI + API + feedback endpoint + `/api/design` tokens all OK, **without** `PYTHONIOENCODING` (UTF-8 guard added) |
| Browser verification | Workspace: Ṛta brand, nav, controls, no console errors. Website: Ṛta brand, full nav, hero, no console errors. |
| Brand scan | 0 occurrences of "SDC Validator" in `rta/website` + `rta/workspace` |

## 7. Review fixes applied (independent reviewer)

1. **`run_benchmark.py` sys.path depth** — pointed one level too shallow
   (repo-root+1); fixed to `ROOT.parent.parent`, docstring paths updated.
2. **`rta/workspace/server/feedback.py` module-level Streamlit imports** —
   `api_server` lazily imports the data layer from it; moved `import streamlit`
   and `from ui.components import …` inside the widget functions so the data
   layer (FeedbackEntry / save_feedback) works in a clean install without the
   `web` extra.
3. **`api_server` UnicodeEncodeError on Windows** — the "Ṛta — serving on …"
   banner crashed under the default cp1252 console; added the same
   `sys.stdout/stderr.reconfigure(encoding="utf-8")` guard that `cli.py` has.

## 8. Remaining risks / notes

- Internal `rta/` modules import each other through the root shims (not via
  `rta.*` absolute paths). This is the sanctioned strategy and is fully green,
  but import *order* can matter — the shim chain is regenerated by
  `rta/infrastructure/scripts/gen_shims.py` if a module is ever renamed/moved.
- `streamlit` remains in `requirements.txt` / the `web` extra only for the
  legacy app path; the product workspace is a static SPA + stdlib API server.
- The 42 benchmark suites are not run inside CI (they were not before either);
  `build_evidence.py --check` guards the counts. A nightly full-suite job is a
  Phase 2 candidate.

## 9. Migration tooling (kept, documented)

- `rta/infrastructure/scripts/gen_shims.py` — regenerates all root + ui shims.
- `rta/infrastructure/scripts/verify_migration.sh` — full verification battery.
- `rta/infrastructure/scripts/verify_packaging.sh` — packaging/clean-room gates.
- `rta/infrastructure/scripts/verify_wheel.sh` / `verify_wheel2.sh` — wheel
  content + clean-install verification.
- `rta/infrastructure/scripts/start_servers.sh` — starts workspace API + website
  for browser verification.
