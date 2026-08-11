# PHASE 17 — Current UI Failure Audit

> Phase 17 corrective audit. Documents why the Phase 15/16 Streamlit workspace
> still reads as "the old application with a dark theme", and what must change.
> This is an internal engineering document — not a public milestone.

Audit date: 2026-08-06 · Baseline recorded before any Phase 17 change:
**pytest 710/710 · release smoke 10/10**.

---

## 1. Method

The audit combined three evidence sources:

1. **Source-level inspection** of `app.py`, `ui/workspace.py`, `ui/components.py`,
   `ui/theme.py`, and every page module (`ui/overview.py` … `ui/reports.py`).
2. **Live server inspection** — the app was launched with
   `python -m streamlit run app.py` and observed in a real browser; the server
   log was checked for exceptions and the rendered DOM/console for framework
   artifacts.
3. **Benchmark evidence** — `benchmarks/test_ui_app.py` (35 checks),
   `benchmarks/test_workspace_ux.py` (21 checks) and
   `benchmarks/test_ui_state_isolation.py` (6 checks) drive the app through
   `streamlit.testing.v1.AppTest`; they verify *capabilities* (real data, real
   navigation) but not *visual identity*.

## 2. What the current application actually is

```
app.py                        # st.set_page_config + inject_css + sidebar + dispatch
ui/workspace.py               # st.sidebar radios (grouped) = navigation
ui/theme.py                   # design tokens + status metadata (good, reusable)
ui/components.py              # inject_css / status_badge_html / empty_state / nav_group
ui/validator.py, overview.py, clocks.py, context.py, coverage.py,
ui/interactions.py, readiness.py, diff.py, ci.py, reports.py   # page renderers
ui/tab_generator.py … feedback.py                               # tools
```

The Phase 15/16 work layered **CSS + custom HTML helpers** over the standard
Streamlit widget tree. The result is a Streamlit app wearing a theme.

## 3. Failure inventory — why it still feels like "old Streamlit + dark theme"

### F1 — Framework chrome is visible
- The app runs inside Streamlit's shell: browser tab chrome, the collapsed
  "Deploy/MainMenu" affordance, the default page frame and rerun flash on every
  interaction. Even with the header hidden by CSS, the interaction model
  (full-page rerun, spinner, DOM replacement) is recognizably Streamlit.
- **Verdict: STILL LEGACY** — framework presentation was restyled, not removed.

### F2 — Navigation is a column of radio buttons
- `ui/workspace.py` renders each group as `st.radio` with a `"—"` sentinel.
  Visually this is a radio list; structurally it is Streamlit's radio widget.
  There is no indicator-rail, no keyboard-first nav, no transition between pages.
- **Verdict: ONLY RESTYLED** — the mental model "click radio → page swaps" is
  identical to the 10-tab app, just grouped.

### F3 — No page transitions
- View dispatch replaces the main area instantly (`dispatch()` in `app.py`).
  Streamlit reruns rebuild the DOM; there is no exit/enter animation, no
  continuity. Navigation feels like clicking tabs, not moving through a product.
- **Verdict: MISSING**.

### F4 — Background animation absent or imperceptible
- `inject_css()` defines static styles. No animated topology, no pulse, no
  grid. The workspace background is a flat `#0B0E14`. The product website has a
  canvas, but the workspace has none, and the website canvas was reported as
  imperceptible in manual review.
- **Verdict: MISSING** (workspace) / **IMPERCEPTIBLE** (website).

### F5 — Widget surfaces are Streamlit widgets
- The Validator input is `st.text_area` + `st.file_uploader` + `st.button`;
  findings are `st.expander` rows; summary is `st.metric`; filters are
  `st.radio`/`st.selectbox`/`st.text_input`. Each carries Streamlit's default
  DOM, focus rings, borders and padding even when recolored.
- **Verdict: STILL LEGACY** — the user experiences "our CSS on their widgets".

### F6 — Layout is the Streamlit block model
- `st.columns([1,2])`, `st.expander`, `st.sidebar` structure page geometry.
  Content width, gutters and density are constrained by Streamlit's
  `stAppViewContainer`/block-container rules, not by a product grid.
- **Verdict: STILL LEGACY**.

### F7 — No microinteractions / hover / focus system
- Custom HTML helpers add hover colors on a few elements, but there is no
  consistent REST/HOVER/FOCUS/ACTIVE/SELECTED system, no copy feedback, no
  indicator movement, no focus-visible discipline beyond browser default.
- **Verdict: MISSING**.

### F8 — Typography is a patch
- Inter + JetBrains Mono are loaded via Google Fonts `<style>` injection, but
  headings/body/metrics/labels reuse default sizes with a few overrides. There
  is no display scale, no tabular-numeral metrics treatment, no consistent
  uppercase micro-label system.
- **Verdict: PARTIALLY IMPLEMENTED**.

### F9 — Real-data integrity is strong (preserve)
- All engineering values come from `check_sdc()` / clock_relations /
  design_* / constraint_* / readiness_diff via the frozen backend; the
  workspace-UX benchmark proves UI numbers match backend numbers exactly.
- **Verdict: IMPLEMENTED — this is the backbone to keep.**

### F10 — Empty/error/loading states are functional but Streamlit-styled
- `empty_state()` and `typed_error()` render styled HTML, and loading is a
  `st.spinner`. States exist; their presentation is widget-bound.
- **Verdict: PARTIALLY IMPLEMENTED**.

## 4. Capability-by-capability audit matrix

| Area | Phase 15/16 status | What still reads as "old UI" |
|---|---|---|
| Workspace shell | PARTIALLY | Streamlit sidebar + block model |
| Navigation | ONLY RESTYLED | radio column, no transitions |
| Analysis header | PARTIALLY | markdown caption, not a product bar |
| Validator input | STILL LEGACY | st.text_area + st.file_uploader |
| Findings explorer | PARTIALLY | styled table (good) + expander details |
| Finding inspector | ONLY RESTYLED | expander, not a persistent inspector |
| Clock intelligence | PARTIALLY | good data; graph/matrix are HTML/SVG helpers |
| Coverage | PARTIALLY | bus strips exist; wrapped in expanders |
| Interactions | PARTIALLY | list rows, not constraint↔constraint visuals |
| Readiness | PARTIALLY | dimension rail exists; no animated resolution |
| Diff | PARTIALLY | change-review data; table/expander presentation |
| Reports / CI | PARTIALLY | forms + captions |
| Tools | STILL LEGACY | original widget-based tabs |
| Empty states | PARTIALLY | exist, widget-bound |
| Error states | PARTIALLY | typed HTML, widget-bound |
| Loading | STILL LEGACY | st.spinner |
| Background motion | MISSING | flat background |
| Page transitions | MISSING | instant DOM swap |
| Microinteractions | MISSING | inconsistent |
| Responsive | PARTIALLY | Streamlit breakpoints, not product breakpoints |

## 5. Root-cause summary

The Phase 15/16 result is **a themed Streamlit application**, not a new
product, because the *interaction and layout substrate* was never replaced:
Streamlit widgets, the block model, the rerun lifecycle and the instant page
swap are all still the product surface. CSS cannot remove those; only a
different presentation substrate can.

Phase 17 therefore replaces the presentation substrate:

- **A static product frontend** (HTML/CSS/JS) is the only surface the user sees.
- **A stdlib-only local API server** (`api_server.py`) exposes the frozen
  deterministic backend over HTTP — no new dependencies, offline-capable, CI
  and clean-room safe.
- The old Streamlit UI (`app.py` + `ui/`) is retired from the launch path
  (`sdc-tools web` starts the new server). Its data-proven HTML helpers are
  preserved as the design contract where still useful.

## 6. What is preserved (non-negotiable)

1. **Deterministic backend** — checker, sdc_preprocess, clock_relations,
   design_context, design_coverage, constraint_interactions,
   constraint_readiness, readiness_diff, finding_identity, policy_engine,
   support_boundary, rules_registry: untouched.
2. **Real data only** — every value rendered in the new UI originates from the
   backend; no mock findings, no invented counts.
3. **Security** — every user-controlled value (SDC text, object names, clock
   names, netlist identifiers, baseline content) is escaped before any HTML/SVG
   interpolation.
4. **Every existing capability stays reachable** — Generator, Linter,
   Converter, Corner Manager, MMC SDC, Rules, Test Drive, Feedback remain
   functional through the new shell.
