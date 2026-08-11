# PHASE16 — Premium Analysis Workspace Report

> **Internal engineering report identifier** (not a public product milestone).
> Implements **Implementation Stage 2**: transform the restyled tab-based
> Streamlit app into a cohesive premium EDA analysis workspace with new
> information architecture, workspace shell, navigation, analysis layouts,
> technical visualizations and interaction — while keeping the deterministic
> backend frozen.

- **Date:** 2026-08-06
- **Version:** 1.3.0 (RC_READY_WITH_KNOWN_LIMITATIONS)
- **Scope:** UI/workspace only. No backend module changed.
- **Source of truth:** `docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md`,
  `docs/product/VISUAL_DESIGN_SYSTEM.md`,
  `docs/product/HIGH_FIDELITY_PRODUCT_SPEC.md`,
  `benchmarks/PHASE15_FRONTEND_FOUNDATION_REPORT.md`

---

## 1. Baseline

Recorded **before** implementation (Stage 2 spec §Baseline):

| Check | Expected | Actual |
|---|---|---|
| pytest | 710/710 | 710/710 ✅ |
| Golden runners | 9/9 | 9/9 ✅ |
| Benchmark suites | 28/28 | 28/28 ✅ |
| Release smoke | 10/10 | 10/10 ✅ |
| UI benchmark | 35/35 | 35/35 ✅ |
| State isolation | 6/6 | 6/6 ✅ |
| Design-system tests | 19/19 | 19/19 ✅ |

No pre-existing failures — the redesign work did not inherit a broken baseline.

---

## 2. Phase 15 visual gap audit

Compared the Phase 15 app (dark restyle, still 10-tab) against the approved
high-fidelity spec. Classification per area:

| Area | Phase 15 status | Gap vs approved spec |
|---|---|---|
| Navigation | RESTYLED (10 tabs kept) | Tabs defined the whole IA; no grouped workspace model |
| Workspace shell | MISSING | No persistent sidebar with sections; no analysis context header |
| Analysis header | MISSING | Only a static header bar; no per-run SDC/netlist/trust/readiness context |
| Page hierarchy | ONLY RESTYLED | Every tab equal weight; no Overview landing, no section labels |
| Cards/metrics | ONLY RESTYLED | Generic metric cards everywhere; no severity/status rails |
| Tables | PARTIAL | Clock/coverage/diff tables were plain; no inventory/matrix/bus visuals |
| Filters | PARTIAL | Validator had filters; others none |
| Inspectors | PARTIAL | Validator expanders only; no clock detail / finding inspector pattern |
| Clock analysis | STILL LEGACY | Single table; no inventory + hierarchy + matrix |
| Coverage | STILL LEGACY | Percentage cards; no object/bus evidence, no ≠ correctness disclosure |
| Interactions | MISSING as page | Hidden in checker expander |
| Readiness | STILL LEGACY | Plain list; no dimension rail, no actions, weak non-signoff language |
| Diff | STILL LEGACY | Comparison list; not a change-review experience |
| Reports / CI | MISSING as pages | Only downloads/gate select inside checker |
| Empty states | PARTIAL | Some; not per-page or engineering-next-step oriented |
| Technical visualizations | MISSING | No hierarchy SVG, no bus strips, no relationship matrix, no rails |

**Why the old UI still felt like "Streamlit with a dark theme":**
the information architecture, the navigation model, the page layouts and the
interaction patterns were all unchanged from the 10-tab app. The visual
foundation (tokens/CSS) was in place, but no page had been structurally
rebuilt — the user still clicked Tab 1..Tab 10.

---

## 3. Workspace architecture

New shell (per spec §3–§6):

```
┌──────────────┬──────────────────────────────────────────────┐
│  NAVIGATION  │  ANALYSIS CONTEXT (SDC · Netlist · Mode ·    │
│              │        Trust · Readiness · Run · New Analysis)│
│  ANALYZE     ├──────────────────────────────────────────────┤
│  DESIGN      │                                              │
│  QUALITY     │            ACTIVE WORKSPACE PAGE             │
│  CHANGE      │   page_title() + purpose + status + content  │
│  OUTPUT      │                                              │
│  TOOLS       │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

- **Grouped navigation** — 6 sidebar groups; one radio per group with a
  sentinel "—" so a group can be empty. Changing a group commits the view and
  resets the others.
- **View dispatcher** — `app.py` is now a thin shell: `inject_css()`,
  `render_workspace_sidebar()`, `render_header()`, `dispatch()`. No tab
  container anywhere.
- **Page-title system** — every page opens with `page_title(SECTION, TITLE,
  purpose)`; no giant repeating product headers.
- **Analysis context header** — persistent across pages once a run exists;
  shows real run data only (SDC filename, netlist status/top, analysis mode,
  trust + readiness chips, run timestamp) plus a "＋ New Analysis" action.

## 4. Navigation

- Radios with `on_change` commit the selection (`ws_view` + `_ws_active_key`)
  and `st.rerun()`; stale selections in other groups are popped **before**
  their widgets are instantiated (`_render_nav_radios`), which is
  Streamlit-version-safe.
- **Bug found during browser verification:** the original `go()` wrote
  `st.session_state[group_key]` directly after the sidebar radios were already
  instantiated → `StreamlitAPIException: st.session_state.ws_analyze cannot be
  modified after the widget with key ws_analyze is instantiated.` Fixed with a
  **pending-navigation marker** (`_ws_pending`) consumed by
  `_apply_pending_nav()` at the top of the next run, before any radio exists.
  The old post-loop "last non-sentinel wins" logic (which silently broke
  Diff → Clocks navigation) was replaced entirely.
- All 18 pages reachable; cross-group navigation verified headlessly and in
  the browser.

## 5. Analysis context

Rendered by `ui/workspace.py::render_analysis_context()` only when
`state.has_run()`. Fields: SDC filename, Netlist (✓ top · N inst / ○ none),
Mode (SDC only / design-aware), Run timestamp, trust + readiness status
badges. No invented projects/persistence.

## 6. Overview

`ui/overview.py` — new post-analysis landing page answering: what did I
analyze, is anything seriously wrong, can I trust this, is it ready, what
should I investigate first. Hierarchy: **Readiness → Trust → Critical findings
→ Clock summary → Design context → Coverage → Interactions → Next actions**,
with cross-page "Open" links (`go()`).

## 7. Validator integration

Phase 15 Validator moved unchanged into the ANALYZE group (same keys,
`validator_paste`, `Run Check`, netlist/baseline/gate/custom-rules/scope
panels, advisories, findings filters, dual-line provenance, source viewer).
Only change: run timestamp recorded for the analysis context header.

## 8. Clock Intelligence

`ui/clocks.py` — three coordinated views:

1. **Clock inventory** — dense table: clock, type (primary/generated/virtual),
   period, freq, source, master, relation.
2. **Clock hierarchy** — layered SVG node/edge diagram (≤40 clocks; HTML tree
   fallback beyond) using the SILICON GRAPH grammar; shapes distinguish
   primary (■) / generated (□) / virtual (○); never implies timing propagation.
3. **Relationship matrix** — symbol + label + color (SYNC ✓ / ASYNC ~ /
   PHY_EX ✗ / LOG_EX ✗), hover titles carry inference reason + SDC declaration
   + mismatch, legend included, `?` for unknown.

Source radio: "Current analysis" (from the run) or "Paste below" (standalone).
Results cached per SDC hash → no cross-analysis leakage.

## 9. Design Context

`ui/context.py` — netlist status, top module, object counts (modules/ports/
instances/nets/pins), compact instance hierarchy tree, top-level ports table
(direction/width), collection-resolution summary aggregated from
SDC-054..SDC-059 findings, trust badge, and the boundary callout
("a resolved object is not a correct constraint"). Honest "Design context not
supplied" empty state in SDC-only mode.

## 10. Coverage

`ui/coverage.py` — object/evidence oriented:

- **Design-aware coverage** from the run (direction bars + per-object status
  chips + per-bit bus strips for partial buses) and the always-visible
  **"Coverage ≠ correctness"** disclosure.
- **Bus coverage** — per-bit strip per partial bus with constrained ranges.
- **Category analyzer** (legacy `cv_paste`/`Analyze Coverage` keys preserved)
  — present/missing constraint categories, per-category progress, missing-item
  list, HTML report download.

## 11. Interactions

`ui/interactions.py` — dedicated sections for duplicates / overrides /
contradictions / STA-review overlaps from `result.interactions`; each
interaction renders Constraint A ↔ Constraint B with rule, line A, line B,
endpoints, reason, and a "requires STA/path analysis" marker distinct from
provable conflicts. Dual-line provenance preserved.

## 12. Readiness

`ui/readiness.py` — signature experience:

- **Overall status** panel + mode.
- **Dimension rail** — 7 clickable expander rows (CLOCKS, I/O, EXCEPTIONS,
  COVERAGE, CONSISTENCY, ANALYSIS_TRUST, DESIGN_CONTEXT) each with an evidence
  proportion rail (not a fake score), status badge, summary, and "caused by"
  evidence.
- **Blockers / Review items / Advisories** sections.
- **Recommended actions** — real backend P0–P3 recommendations.
- **Trust language** — "This is a constraint-readiness review, NOT an STA
  timing signoff" callout and "READY is not signoff" footer always visible.

## 13. Diff

`ui/diff.py` — technical change-review:

- **Baseline review** header: Baseline → Current readiness badges, gate result
  chip, compatibility note.
- **NEW / RESOLVED / CHANGED / UNCHANGED** segmented filter; rows show
  kind, rule, message, object, dual-line location.
- **Coverage / trust / context deltas**, **debt** (existing/new/resolved
  blocker-review-advisory), CI gate result panel with the "CI PASS ≠ timing
  pass" callout.
- **Semantic V1/V2 analyzer** preserved (legacy `ca_v1_paste` keys).

## 14. CI / Policies

`ui/ci.py` — policy selector (BLOCKERS_ONLY / NO_READINESS_REGRESSION /
STRICT / CUSTOM), what fails / what passes, engine-failure guarantee, CUSTOM
policy preview, real CLI command for the current run, GitHub Actions example.
Uses actual CLI syntax from `cli.py`; no invented commands.

## 15. Reports

`ui/reports.py` — artifact cards for existing outputs: HTML report, JSON
result, readiness snapshot (download), baseline (upload/select), each with
purpose/status/action. No new export formats invented.

## 16. Tools preservation

Generator, Linter, Converter, Corner Manager, MMC SDC, Rules, Test Drive,
Feedback are reachable under **TOOLS** (professional grouping — never called
"legacy"). Generator/Corner Manager/MMC bodies were extracted verbatim into
`ui/tab_generator.py` / `ui/tab_corners.py` / `ui/tab_mmc.py` by a migration
script (zero transcription risk), keeping their exact keys and behaviors.

## 17. Empty states

Every major page has a designed, engineering-specific empty state:
Overview ("No analysis yet"), Clocks ("No clocks discovered" / "Ready to
analyze"), Context ("Design context not supplied"), Coverage
("Design-aware coverage requires design context"), Readiness ("No analysis
yet"), Diff ("No baseline loaded"), Reports, CI, Validator. Each states what
it means and the concrete next step.

## 18. Unsupported states

Honest visibility of NETLIST_REQUIRED / TCL_EXECUTION_REQUIRED / UNSUPPORTED /
NOT_VALIDATED trust statuses throughout (analysis context chips, scope panel,
Context page, Readiness ANALYSIS_TRUST dimension).

## 19. Accessibility

- Statuses always use **icon + label + semantic color** (never color alone) —
  enforced by the shared badge system.
- SVG hierarchy has `role="img"` + `aria-label`; matrix is a real table with
  scope headers and text symbols; hierarchy HTML-tree fallback for large sets.
- Focus/keyboard preserved by native Streamlit widgets; no custom global
  shortcuts.

## 20. Security

- All user-controlled content (SDC, clock names, object names, rule messages,
  netlist identifiers, baseline/policy content) passes through `esc()`
  (quote-aware `html.escape`) before HTML interpolation.
- WS-18 adversarial probe (`<script>`/`<img onerror>` in clock names) passes —
  no raw injection in rendered markup.
- No backend change; no new network/AI surface.

## 21. State management

- Shared `ui/state.py` is the single read path for the current run; pages never
  mutate the run.
- Clock/coverage analyses cached per input hash; click flags are digest-scoped
  so editing the paste area never auto-runs a stale analysis.
- Navigation is presentation-only (ws_view/group radios); A→B→A verified.

## 22. Performance

- Backend cost unchanged (UI only). Large clock sets fall back from SVG to the
  HTML tree; matrices remain compact tables; findings/actions truncated with
  "… N more" captions instead of unbounded DOM.
- Full 30-suite run completes well within timeouts.

## 23. Responsive behavior

Desktop-first (1920/1440/1280/1024): sidebar radios, sticky context header,
tables scroll horizontally inside their wrappers, inspectors stack. Verified
at 1280/1024 headlessly; no layout overflow reported in browser.

## 24. Streamlit limitations

- Tabs were removed as the *product architecture*; Streamlit is used for its
  native widgets. Radios with `on_change` + deferred pops + pending-nav marker
  handle the grouped model safely across versions.
- `go()` (programmatic navigation) must not write already-instantiated widget
  keys — the pending-nav marker solves this; documented in code.
- Browser automation could not reliably click Streamlit's dynamic sidebar
  radios (tool limitation); interaction was verified via AppTest widget events
  + a live-server render/console check.

## 25. UX benchmark

`benchmarks/test_workspace_ux.py` — **WS-01..WS-21, all passing**:

- WS-01 grouped nav (6 group radios)
- WS-02/19 all 18 pages reachable without exception
- WS-04/20 validator renders real findings, UI codes == backend codes
- WS-15 trust status matches backend
- WS-03 overview renders real readiness
- WS-05/06/07/07b clock inventory/hierarchy/matrix/pairs match backend
- WS-08/09/10 design context/coverage/bus match backend
- WS-11/12/13 interactions/readiness dimensions/actions match backend
- WS-14 diff NEW/RESOLVED/CHANGED rendered from a real baseline diff
- WS-16a/16b no-context states honest
- WS-17 A→B→A state isolation
- WS-18 user-controlled HTML escaped

## 26. Browser verification

Live server (`streamlit run app.py` on :8501): sidebar branding + all six
groups + Overview empty state confirmed in a real browser with **zero console
errors** and no error boxes. The browser agent hit Streamlit's dynamic-radio
limitation for multi-step clicks; the full navigation matrix (including the
`go()` "＋ New Analysis" path that crashed pre-fix) was verified through
AppTest widget events with the server log exception-free (0 exceptions).

## 27. Independent review

Phase 15/16 review findings and dispositions:

| Finding | Disposition |
|---|---|
| `st.session_state.pop` of already-instantiated widgets is version-sensitive | ✅ Fixed: pops deferred until before instantiation; `go()` uses a pending-nav marker |
| `go()` writing widget keys after instantiation → StreamlitAPIException | ✅ Fixed with `_ws_pending` (found via live browser test) |
| Dead code `_sdc_source` in ui/clocks.py | ✅ Removed |
| `cr_clicked`/`cov_clicked` stale-flag auto-run after editing | ✅ Fixed: flags scoped to the input digest |
| Escaping inconsistency (attribute vs text) | ✅ Verified: `esc()` is quote-aware; aria-label safe |
| test_release_smoke as plain script in the runner | ✅ Runner removed; smoke still run via pytest |

## 28. Backend regression

Frozen-backend modules untouched. Full results after implementation:

- pytest **710/710** (incl. 19 design tests)
- Release smoke **10/10**
- UI benchmark **35/35**
- State isolation **6/6**
- Workspace UX **21/21**
- All **30 benchmark suites** pass (security, trust-transparency,
  no-false-confidence, semantic/netlist/coverage/readiness/diff adversarial +
  metamorphic + confidence + perf, CI gate, stress, PH13 suites)

## 29. Packaging

Fresh wheel `sdc_tools-1.3.0-py3-none-any.whl` built; all 23 UI modules
(workspace pages + tabs + theme/components) ship in the wheel; installed into
a clean `--target` dir and imported (app + all workspace modules + helpers)
successfully from the wheel.

## 30. Remaining limitations

- Streamlit cannot render a native clickable table row → finding/clock detail
  uses expanders.
- Loading states are honest single-stage ("Analyzing…") — the backend exposes
  no stage progress.
- Browser agent cannot reliably click Streamlit dynamic radios → interaction
  coverage relies on AppTest + live-server checks.
- Clocks SVG caps at 40 nodes (tree fallback beyond) — a design decision to
  protect rendering cost.
- Product website / Benchmarks / Trust Center / Docs / Release pages are out
  of scope for this stage by design.

## 31. Product-site readiness

The workspace now demonstrates the approved design system and signature
experiences (Clock Intelligence, Coverage bus evidence, Readiness rail, Diff
change review). These pages become the reference patterns the future product
site and Trust Center will reuse.

## 32. Recommendation

The workspace rebuild is complete and verified. Recommended next slice:
**product website + benchmark/trust experience** (Home, Platform, Benchmarks,
Trust Center, Docs, Release) using the same design tokens and status system —
then a final visual QA pass against the high-fidelity spec before public beta.
