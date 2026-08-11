# Ṛta Phase 1 — Repository Migration & Foundation: Final Report

**Status: COMPLETE** · Baseline and post-migration results identical.

---

## 1. Migration summary

The repository was transformed into the approved product-first Ṛta startup
structure. Production code now lives under `rta/` (branding, engine, tools,
cli, api, workspace, website, evidence, examples, tests, docs, knowledge,
infrastructure); historical Streamlit UI and experiments were archived under
`legacy/` (never packaged). **No file was deleted and no backend behavior
changed.** Import compatibility is preserved via a root-shim strategy so
every existing consumer — tests, benchmarks, CLI, API, legacy UI — works
unchanged.

## 2. Files moved

- **Engine (17 modules)** → `rta/engine/{preprocess,rules,analysis,context,diff,policy,trust}/`
- **Tools (7)** → `rta/tools/{generate,lint,convert,corners,batch,report}/`
- **CLI + API** → `rta/cli/cli.py`, `rta/api/api_server.py`
- **Workspace** → `rta/workspace/{webui,server,data}/`
- **Website** → `rta/website/`
- **Evidence** → `rta/evidence/` (28 benchmark files + data trees) with `rta/evidence/manifest/evidence.py`
- **Tests** → `rta/tests/` · **Examples** → `rta/examples/{samples,policies}/`
- **Docs** → `rta/docs/` · **Legacy** → `legacy/{streamlit,assets,experiments,working-copies}/`

## 3. Files preserved

Root-level config/entry files (`pyproject.toml`, `README.md`, `CHANGELOG.md`,
`CONTRIBUTING.md`, `LICENSE`, `Dockerfile`, CI workflow, pre-commit, launchers,
`.claude/`) and **27 root shim modules + the `ui/` shim package** that alias
into `rta/` (and `legacy/` for the old Streamlit UI).

## 4. Import changes

Zero import edits in consumer code. The shim layer (`gen_shims.py`) injects
`sys.modules` aliases and re-executes real modules under `__main__` via
`runpy`, so `python cli.py`, `python -m cli`, `python -m api_server`,
`pytest rta/tests/`, and every benchmark runner behave exactly as before.
Path-sensitive modules were updated once at their new location.

## 5. Verification results

| Gate | Result |
|---|---|
| pytest | **800/800** |
| Benchmark suites | **42/42** |
| Benchmark runners | **12/12** |
| Release smoke / clean-room / CLI audit | **10/10 · 17/17 · 16/16** |
| Evidence manifest check | OK (800 / 111 rules / 42 suites / v1.3.0) |
| CLI contract | Ṛta v1.3.0, `check` works |
| API boot (repo + clean wheel) | health, SPA, rules, feedback, design tokens all OK |
| Clean wheel install | CLI + API work **without** PYTHONIOENCODING (UTF-8 guard added) |
| Browser (workspace + website) | Ṛta branding, nav, hero, zero console errors |
| Brand scan | 0 stray "SDC Validator" in product surfaces |

## 6. Remaining migration risks

- Internal `rta/` imports route through root shims; import order can matter
  (regenerate with `gen_shims.py` after any module move/rename).
- `streamlit` is a legacy-path-only dependency now (`web` extra).
- The 42 benchmark suites aren't in CI (pre-existing); `--check` guards counts.
- Business website intentionally ships only from repo/hosting, not the wheel.

## 7. Recommended Phase 2

1. Migrate internal `rta/` imports to absolute `rta.*` paths (remove shim
   ordering sensitivity) and delete the root shims once legacy consumers are
   retired.
2. Move the 42 benchmark suites + 12 runners into CI (nightly or on-tag job).
3. Rename the package/repo to `rta` proper (currently `sdc-tools` wheel with
   `rta` entry point) once external consumers are confirmed.
4. Product Experience sprint: build the Ṛta workspace UI on the new shell
   (the API + SPA structure from Phase 17 is already in place).
