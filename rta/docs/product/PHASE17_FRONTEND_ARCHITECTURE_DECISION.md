# PHASE 17 — Frontend Architecture Decision Record

> Decision: **Separate static frontend + stdlib-only Python API server**,
> replacing Streamlit as the presentation substrate.
> Internal engineering document — not a public milestone.

Date: 2026-08-06 · Baseline: pytest 710/710 · smoke 10/10.

---

## 1. Context

The audit (PHASE17_CURRENT_UI_FAILURE_AUDIT.md) found that Phase 15/16 produced
*a themed Streamlit application*: the interaction and layout substrate
(Streamlit widgets, block model, rerun lifecycle, instant page swap) was never
replaced. The product cannot reach "a specialized semiconductor
constraint-analysis environment" while Streamlit remains the surface the user
interacts with.

The deterministic backend is frozen. Every capability (check, clocks, context,
coverage, interactions, readiness, diff, reports, CI, generator, linter,
converter, corners, MMC, rules, test drive, feedback) must remain reachable.

## 2. Options evaluated

### A. Streamlit with aggressive custom components
- **Visual freedom**: low-medium. Streamlit's DOM, rerun lifecycle and widget
  semantics survive any CSS; page transitions and persistent canvas
  backgrounds are effectively impossible inside the rerun model.
- **Animation/transitions**: CSS keyframes survive reruns only if injected per
  run; JS is not persistent (scripts are sanitised in `st.markdown`).
- **Interactive visualization**: bounded to HTML/SVG helpers; no canvas.
- **Maintainability**: low — every feature fights the framework.
- **Packaging/offline**: unchanged (good).
- **Security**: existing escaping helpers reusable.
- **Decision**: rejected as the *primary* substrate. It was already proven (F1–F10)
  not to deliver the required visual identity.

### B. Separate frontend + Python backend/API
- **Visual freedom**: full. The product defines its own DOM, grid, transitions,
  canvas, components, hover/focus system.
- **Animation/transitions**: full (canvas background, route transitions, motion
  levels).
- **Interactive visualization**: full (SVG/canvas clock trees, matrices, bus
  strips, readiness rail).
- **Maintainability**: high if the frontend stays dependency-free (no build
  step, no framework).
- **Packaging/offline**: good if the server is stdlib-only and ships in the
  wheel; single `pip install` keeps working.
- **Security**: must re-apply escaping discipline in the frontend (and the API
  should return structured data so the UI can escape at render time).
- **Cost**: new server + new frontend; UI benchmarks must be rewritten to the
  API while preserving behavioral coverage.
- **Decision**: **chosen**.

### C. Hybrid (Streamlit shell + custom HTML islands)
- Same substrate limitations as A for everything outside the islands; two
  presentation systems to maintain; rejected.

### D. Other lightweight architectures
- A pre-built SPA with a build step (Vite/React) was rejected: it adds a Node
  build to a pure-Python, offline-capable, single-wheel product and breaks the
  clean-room journey.
- A full async web framework (FastAPI/uvicorn) was rejected: `uvicorn` is not a
  declared dependency and CI installs only `pytest + pyyaml`. The stdlib
  `http.server` module is sufficient for a local, deterministic, single-user
  analysis tool and adds **zero** dependencies.

## 3. Decision

**Adopt: static frontend (`webui/`) + stdlib-only local API server
(`api_server.py`) + `sdc-tools web` launches the new server.**

- The frontend is plain HTML/CSS/JS served by the same process; **no build
  step, no framework, no package.json**.
- The API server uses only the Python standard library
  (`http.server.ThreadingHTTPServer`) so the wheel gains **no new runtime
  dependency**; CI (`pip install pytest pyyaml`) and the clean-room journey
  keep working unchanged.
- The backend remains the authority: the server imports the frozen modules and
  serializes their results to JSON; it never re-implements semantics.
- `sdc-tools web` now resolves and launches `api_server.py`; the Streamlit app
  (`app.py`) is retired from the launch path but kept in the repository for
  reference and for the design-contract tests that still import `ui.theme`.

## 4. Why this fits the product positioning

- **Deterministic / reproducible**: same input → same JSON; the frontend is a
  pure renderer of backend evidence.
- **Offline-capable**: everything is localhost; no CDN fonts are required at
  runtime (fonts fall back to system stacks when offline).
- **Single wheel**: `pip install -e ".[web]"` → `sdc-tools web` → works from any
  cwd; static assets ship inside the package.
- **Engineering-focused**: dense tables, technical visualizations and keyboard
  workflows are owned by the product, not borrowed from a dashboard framework.

## 5. API surface (all JSON; backend-frozen)

| Endpoint | Backend consumed | Returns |
|---|---|---|
| `POST /api/analyze` | `check_sdc` + `analyze_clock_relations` + `analyze_scope` (+ `parse_verilog`, `analyze_coverage`, `analyze_interactions`, `analyze_readiness`, custom rules, baseline diff) | full evidence: issues, info, stats, scope, coverage, interactions, readiness, clocks, context, baseline diff, gate |
| `GET /api/design` | `ui.theme` | tokens + status metadata (single source of truth) |
| `GET /api/rules` | `rules_registry` | rule catalog |
| `POST /api/lint` | `lint_sdc` | lint result |
| `POST /api/convert` | `parse_sdc` + `sdc_to_json`/`sdc_to_yaml` | conversion result |
| `POST /api/generate` | `generate_sdc` | generated SDC |
| `POST /api/corners` | `corner_manager` | corner validation / matrix |
| `POST /api/mmc` | `mmc` | multi-corner SDCs / diff / check |
| `POST /api/feedback` | `ui.feedback` | feedback write result |
| `GET /api/health` | — | version + status |

## 6. Migration of the UI test surface (behavioral coverage preserved)

| Benchmark | Before | After |
|---|---|---|
| `test_ui_app.py` (35) | AppTest drives app.py | API-level: analyze fixtures, assert counts/statuses equal backend |
| `test_workspace_ux.py` (21) | AppTest widget tree | API + static-frontend contract: every capability reachable via `/api/*`, backend numbers match, XSS probes escaped, no-context states honest |
| `test_ui_state_isolation.py` (6) | AppTest A→B→A | API-level A→B→A determinism |
| `tests/test_ui_design.py` (19) | ui.theme/components/validator helpers | keep + extend: tokens/status contract + new frontend escaping helpers |

## 7. Risks and mitigations

- **Frontend must escape everything** → `ui/theme.esc` logic ported to a tested
  JS `esc()`; API returns structured data (severity/code/msg separated) so the
  UI renders, not interpolates, user content.
- **UI benchmarks rewritten** → same fixtures, same assertions, new transport;
  no behavioral coverage removed (verified by the Phase 17 report).
- **Packaging** → `api_server` added to `py-modules`; `webui/` ships as package
  data; clean-room + packaging probe re-run.
- **Performance** → static assets are small; canvas animation is paused when
  the tab is hidden and disabled under `prefers-reduced-motion`.

## 8. Conclusion

Streamlit cannot present this product at the required quality bar. The separate
frontend + stdlib API server delivers full visual ownership with zero new
dependencies, keeps the frozen backend authoritative, and preserves every
existing capability and the verified regression surface.
