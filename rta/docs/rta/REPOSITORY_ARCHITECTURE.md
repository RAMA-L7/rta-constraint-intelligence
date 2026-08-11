# Ṛta — Repository Architecture

> **Document kind:** architecture record — current state, target state, and the
> migration path. No large filesystem refactor is performed in this phase.
> **Date:** 2026-08-06

---

## 1. Current state (as of v1.3.0, Ṛta Foundation)

```
repo root  (sdc-tools / Ṛta)
├── checker.py  sdc_preprocess.py  tcl_resolver.py  wildcard_analyzer.py
│   clock_relations.py  rules_registry.py  support_boundary.py
│   design_context.py  design_coverage.py  coverage.py
│   constraint_interactions.py  constraint_readiness.py
│   readiness_diff.py  finding_identity.py  policy_engine.py
│   constraint_diff.py  custom_rules.py
├── generator.py  linter.py  converter.py  corner_manager.py  mmc.py
│   batch_runner.py  reporter.py
├── cli.py  api_server.py  app.py
├── webui/          # premium workspace (vanilla JS + stdlib API server)
├── ui/             # legacy Streamlit workspace
├── site/           # marketing website (static)
├── benchmarks/     # suites + phase reports
├── tests/          # pytest suite
├── docs/
│   ├── features/   # per-module reference docs
│   ├── product/    # historical product/design docs
│   └── rta/        # Ṛta foundation docs (this set)
├── samples/  policy_examples/  data/  .github/  .claude/
└── pyproject.toml  README.md  CHANGELOG.md  Dockerfile  sdc-tools.cmd  rta.cmd
```

### Characteristics

- **Flat module layout** — every backend module lives at the repo root; the
  wheel is built from an explicit `py-modules` list.
- **Two UIs** — the premium `webui/` workspace (current product surface,
  launched by `rta web` / `sdc-tools web` via `api_server.py`) and the legacy
  Streamlit `ui/` (still shipped, still functional).
- **One API server** — `api_server.py` exposes the frozen deterministic
  backend over HTTP to the static frontend; stdlib-only, offline.
- **CLI is the integration boundary** — `check`/`report`/`diff`/`coverage`/
  `analyze`/`corners`/`rules`/`lint`/`convert`/`generate`/`batch`/`web`, with
  `--baseline`/`--gate` for CI.

## 2. Target state (proposed — not implemented now)

```
rta/
├── engine/        # deterministic analysis (moved from root modules)
│   ├── parser/  preprocessing/  validation/  clocks/  context/
│   ├── coverage/  interactions/  readiness/  diff/  policy/  trust/
│   └── rules/
├── api/           # api_server + HTTP layer
├── frontend/      # webui (workspace) + site (marketing)
├── cli/           # entry points
├── benchmarks/  tests/  docs/  examples/
└── pyproject.toml
```

- Python package namespace becomes `rta` (`from rta import check_sdc`).
- Wheel name becomes `rta`; CLI `rta` becomes primary; `sdc-tools` alias kept.
- `ui/` (Streamlit) retired after feature-parity with `webui/` is confirmed.

## 3. Migration path (deferred, gated)

| Step | Trigger | Risk |
|---|---|---|
| 1. Package namespace `rta/` | next packaging phase; requires py-modules → package conversion + import shims | high (all imports/tests/packaging) |
| 2. `api/` + `frontend/` split | stable workspace feature set | medium |
| 3. Streamlit `ui/` retirement | webui parity confirmed by workspace UX benchmark | low |
| 4. Wheel rename `rta` | after 1; update docs/CI/Docker | high |

**This phase performs none of these** — the brand changes are surface-level
(visible identity + `rta` CLI alias). Moving modules now would invalidate
benchmark evidence and packaging guarantees without product benefit.

## 4. Identifiers (enforced)

| Identifier | Value | Where |
|---|---|---|
| Visible brand | `Ṛta` | website, workspace, reports, README |
| ASCII identifier | `rta` | CLI alias (`rta check`), `rta.cmd` |
| Legacy CLI | `sdc-tools` | kept as alias |
| Package/wheel | `sdc-tools` / `sdc_tools-*` | unchanged this phase |
| Version | `1.3.0` | `rules_registry.APP_VERSION`, `pyproject.toml` |
