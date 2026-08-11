# PHASE15 — Frontend Foundation & P0 Validator Vertical Slice (internal engineering report)

**Engineering report identifier:** PHASE15 (internal only — not a public product milestone)
**Date:** 2026-08-06 · **Product:** SDC Validator v1.3.0
**Sources of truth:** `docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md`,
`docs/product/VISUAL_DESIGN_SYSTEM.md`, `docs/product/HIGH_FIDELITY_PRODUCT_SPEC.md`

> **Scope:** the first production-quality vertical slice of the approved
> premium redesign — design foundation, global workspace styling, and the
> **Validator / Findings experience** driven by real `check_sdc()` results.
> The deterministic backend is **frozen**: no validation semantics changed.

---

## 1. Baseline (recorded before implementation)

| Suite | Result |
|---|---|
| pytest | **691/691** |
| Release smoke (`benchmarks/test_release_smoke.py`) | **10/10** |
| UI benchmark (`benchmarks/test_ui_app.py`) | **35/35** |
| UI state isolation (`benchmarks/test_ui_state_isolation.py`) | **6/6** |

Environment: Python 3.10 · Windows · `SDC Tools v1.3.0` · branch `main`.

## 2. Files inspected

`app.py` · `ui/components.py` · `ui/__init__.py` · `ui/feedback.py` ·
`ui/tab_linter.py` · `ui/tab_converter.py` · `ui/tab_rules.py` ·
`ui/tab_test_drive.py` · `checker.py` (Issue/InfoItem/CheckResult shapes) ·
`finding_identity.py` (identity fields) · `cli.py` (readiness/gate data) ·
`benchmarks/test_ui_app.py` · `benchmarks/test_ui_state_isolation.py` ·
`pyproject.toml` (package config) · the three approved design documents.

## 3. UI architecture before

- 10 emoji-labeled Streamlit tabs (Checker, Generator, Linter, Converter,
  Corner Mgr, MMC SDC, Diff, Clock, Coverage, Rules) + sidebar views
  (Test Drive, Feedback).
- Light-first theme with a `[data-theme="dark"]` CSS override; gradient
  header, rounded cards, emoji icons, expander-based findings.
- The Checker tab inlined a ~600-line implementation: upload/paste, optional
  netlist + baseline + custom rules, `check_sdc` results as emoji metric
  cards + issue-card expanders, plus scope/coverage/interactions/readiness/
  baseline-diff/rule-reference panels.

## 4. Design-system implementation

Implemented the approved **SILICON GRAPH + PRECISION INFRASTRUCTURE** system
in the live app:

- **Dark-only P0 graphite theme** (`.streamlit/config.toml` `base="dark"` +
  token colors; CSS forces dark containers regardless of Streamlit theme).
- Hairline borders + surface hierarchy (`#0B0E14` bg, `#141926` surfaces,
  `#1A2130` elevated) — hierarchy via contrast/borders, not shadows/glow.
- One restrained accent (`#38BDF8`), no glassmorphism, no neon.
- **Universal status system** (icon + label + color + shape) for severity,
  trust, readiness, diff and pass/fail — never color alone.
- Global focus ring (`:focus-visible`), reduced-motion media query, styled
  scrollbars, compact technical metric rail, restyled tabs/buttons/inputs.

## 5. Token implementation

`ui/theme.py` — single source of truth (no scattered hex values):

- `COLORS` (21 tokens incl. semantic + diff + code-gutter colors)
- `FONT_UI` / `FONT_MONO` (Inter + JetBrains Mono with fallbacks)
- `SPACING` (4px base), `RADIUS`, `MOTION`
- `SEVERITY` / `TRUST` / `READINESS` / `DIFF` / `PASS_FAIL` metadata maps
  (label + icon + color + shape)
- `ICONS` — stroke-based inline SVG set (16px grid, 1.5px stroke), no emoji
- `esc()` — Phase 14 stored-XSS escaper

`tests/test_ui_design.py` asserts token validity (hex parse, icon-name
resolution, every backend status string covered).

## 6. Workspace shell

- Compact engineering header: brand mark (CONSTRAINT BRACKET SVG) + "SDC
  Validator" + tagline + `v1.3.0` / `deterministic` / `offline-capable` chips
  (no gradient, no emoji).
- Sidebar: brand card + Test Drive / Feedback actions (keys preserved) +
  accurate changelog + GitHub/Docs links.
- 10-tab workspace retained **as the migration-safe navigation contract**
  (the UI benchmark asserts 10 tabs; see §23 deviation D1).

## 7. Navigation migration

The 10 tabs remain the primary navigation (restyled). The grouped
`ANALYZE / DESIGN / QUALITY / CHANGE / OUTPUT` sidebar from the HF spec is a
**later-slice** migration target (deviation D1). The first tab is now the
premium Validator.

## 8. Existing-feature preservation

Nothing was removed:

| Capability | Status |
|---|---|
| Generator · Linter · Converter · Corner Mgr · MMC SDC · Diff · Clock · Coverage · Rules | Preserved, restyled via global theme + legacy CSS compat block |
| Test Drive · Feedback | Preserved (sidebar, keys unchanged) |
| Checker: netlist (design context) | Preserved (optional, in the new Validator) |
| Checker: baseline + CI gate | Preserved (optional expander) |
| Checker: custom rules YAML | Preserved (all results rendered with details) |
| Checker: scope/coverage/interactions/readiness panels | Preserved |
| Checker: rule reference | Preserved |
| Info-level advisories (`result.info`) | **Restored** after review finding (was dropped in the first draft) |
| Baseline-diff identity-version + coverage/trust regressions | **Restored** after review finding |

## 9. Validator redesign

`ui/validator.py` replaces the old Checker body:

1. Input surface (upload/paste + optional netlist/baseline/custom-rules).
2. `Run Check` → `check_sdc()` (with context) — backend untouched.
3. Summary rail (Errors/Warnings/Info/Clocks metrics) + trust chip +
   readiness chip (premium status badges).
4. Verdict callout (typed; always carries the "not an STA signoff" note).
5. Filters (severity / rule / search) — **presentation only**; the stored
   result is never mutated; filters reset on each run.
6. **Findings Explorer** — dense HTML table (Severity · Rule · Finding ·
   Object · Clock · Loc), sticky header, left-rule severity tinting,
   horizontal scroll.
7. **Finding details** — expander per finding with severity badge, full
   message, rule "why it matters", object/clock (from structured identity),
   dual-line provenance (`Lx ↔ Ly`), **STA/path-analysis marker** for
   SDC-070 / overlap findings, and a mini source excerpt with highlights.
8. **Source viewer** — full SDC with line numbers, per-line finding
   highlights, dual-line connector markers, escaped content.
9. **Advisories** section for `result.info` (restored).
10. Scope / coverage / interactions / readiness / baseline-diff / custom-rules
    panels (styled, preserved).

## 10. Findings explorer

Real `check_sdc()` findings only. Columns: severity badge (icon+label),
mono rule code, message (escaped, ellipsized via CSS), object, clock,
location. Row hover highlights; severity encoded by icon+label+badge color
+ left rule (never color alone). Filtering never alters the analysis.

## 11. Finding inspector

Each finding expands to: severity badge, full message, mono metadata
(rule / object / clock / `Lx ↔ Ly`), "Why it matters" (from
`rules_registry`), an explicit `REQUIRES STA / PATH ANALYSIS` callout where
the finding's structured evidence indicates overlap (SDC-070 or
`interaction_type` containing `overlap`+`sta`), and a highlighted source
excerpt with the `↕` dual-line connector.

## 12. Source/provenance viewer

Line-numbered mono viewer (escaped). Error lines get a red left rule + tint;
warning lines amber; dual-line findings get the `↕` connector on both lines.
Provenance is reachable from every finding (mini excerpt) and globally
(full viewer).

## 13. Status system

`theme.SEVERITY/TRUST/READINESS/DIFF` cover every backend status:
- Severity: FATAL/ERROR/WARNING/INFO
- Trust: VALIDATED/PARTIAL/NETLIST/TCL EXEC/UNSUPPORTED/NOT CHECKED
- Readiness: READY/READY+/REVIEW/BLOCKED/LIMITED
All rendered as icon + label + color + shape. Unknown statuses fall back to a
neutral badge (never a misleading color).

## 14. Empty states

- **No SDC loaded** → designed empty state ("Upload or paste SDC …",
  "SDC-only analysis works offline") + the benchmark-contract info line.
- **Ready to analyze** (text present, not run yet).
- **No findings** → "No issues found within scope" + scope pointer.
- **No matching findings** (after filters) → clear-filters guidance.

## 15. Error states

Typed, never generic red alerts: `INVALID INPUT`, `UNSUPPORTED`,
`INSUFFICIENT CONTEXT` (netlist rejected), `INCOMPATIBLE BASELINE`,
`ANALYSIS FAILED` (engine failure — explicitly "not a PASS"), `POLICY
ERROR`. No tracebacks in the UI.

## 16. Loading states

Honest `st.spinner("Analyzing constraints…")` — **no fake percentages**
(the backend exposes no stage progress). A stage list was intentionally not
faked (§23 D3).

## 17. Accessibility

- Visible 2px focus ring everywhere; logical tab order.
- Every status = icon + label + shape (never color-only).
- Reduced-motion media query kills all animation/transition.
- Source highlights carry left-rule + tint + connector symbols (not color
  alone); tables use real `<th>` semantics.
- Touch targets ≥ 40px for interactive elements.

## 18. Responsive behavior

Desktop-first. Findings table scrolls horizontally (sticky header, no
squish); header wraps; layout verified at 1920/1440/1280/1024 via
`AppTest` + live browser. Mobile summary mode is a later slice.

## 19. Security review

- **Phase 14 stored-XSS rule preserved and extended:** every user-controlled
  value rendered through custom HTML is escaped via `theme.esc()` — including
  the legacy helpers (`status_banner`, `issue_card`, `section_header`,
  `metric_cards_row`, `progress_bar`, `badge`) that previously interpolated
  user content raw.
- Adversarial probe (`<script>`, `<img onerror>`, quotes, ampersands in SDC
  object names/messages): rendered escaped, no raw injection, no exception.
- `tests/test_ui_design.py` locks this in (10+ escaping assertions).
- No `eval`/`exec`/unsafe YAML; report generation unchanged.

## 20. State isolation

`validator_run` holds one atomic analysis; filters live in session keys that
reset on every run. Verified: A → B → A deterministic results, repeated
Run Check stable, no stale findings/filters between analyses
(`test_ui_state_isolation.py` 6/6 + custom probes).

## 21. Performance

- Analysis cost unchanged (same `check_sdc` call; no added engine work).
- Findings table is a single HTML table (no per-row Python re-analysis).
- Details capped at 400 expanders with an honest "all findings in the
  table" note for very large inputs.
- Edge probes (empty, comments-only, scientific notation, long object
  names, `warning_heavy`, `buggy_no_clocks`, `real_design_full`,
  `clock_relations`) all complete with no exceptions.

## 22. Streamlit constraints encountered

- Tabs render all bodies eagerly → the generator tab's metrics coexist with
  the validator's; order is preserved so benchmark lookups hit the right
  widgets first.
- No JS: row-click-to-inspector is not possible natively → detail
  expanders + mini excerpts serve as the inspector (deviation D2).
- Widgets with global keys persist across reruns → filters are reset
  explicitly on each run.
- `.streamlit/config.toml` forces native dark widgets; custom CSS forces
  dark containers regardless.

## 23. Spec deviations

| # | SPEC | CONSTRAINT / DECISION | RATIONALE |
|---|---|---|---|
| D1 | HF spec §5–6: grouped sidebar nav | 10 restyled tabs retained | The UI benchmark contract asserts 10 tabs; grouped sidebar lands with the workspace rebuild slice |
| D2 | HF spec §21–22: row-click inspector rail | Expander-based detail (benchmark also requires code-labeled expanders) | Streamlit has no native row-click; expanders preserve the approved progressive-disclosure pattern |
| D3 | VDS §38: stage list | Single honest spinner | Backend exposes no stage progress; fake stages would violate the honesty principle |
| D4 | VDS §8: dark-only | Dark-only shipped; light tokens documented but unused | Approved dark-only P0 |
| D5 | HF spec §20: no emoji in product UI | `st.metric` labels `❌ Errors` / `⚠️ Warnings` / `🕐 Clocks` retain emoji | Required verbatim by the UI-benchmark contract (CHK-01/ISO); removed everywhere else in new UI |
| D6 | VDS §25: full 44-component library | ~24 components implemented | P0 subset per approved §45 |

## 24. Interactive testing

- **Live browser (Chrome):** dark background confirmed, header + version +
  `deterministic`/`offline-capable` chips confirmed, **zero console errors**.
  (The automation agent could not reliably type into Streamlit's dynamic
  textarea — full interaction verified headlessly via `AppTest` instead.)
- **Rendered-markup verification (AppTest):** all 11 premium artifacts
  present in the rendered DOM (`.sdc-header`, `.sdc-table`, `.sdc-status`,
  `.sdc-source`, `.sdc-empty`, trust/readiness chips, dark tokens, no emoji
  in the header).

## 25. Edge cases

Empty file · comments-only · scientific notation · very long object names ·
HTML-like object names (escaped) · many findings (`warning_heavy`) ·
dual-line interaction findings · unsupported constructs · missing netlist ·
invalid netlist · repeated Analyze · filter combinations — all handled with
no exceptions and honest typed states.

## 26. Independent reviewer findings

| Sev | Finding | Resolution |
|---|---|---|
| HIGH | Legacy Tools tabs lost all custom CSS (`.metric-card`, `.status-banner`, `.issue-card`, `.badge`, `.code-block`, `.progress-*`) → unstyled preserved features | Added a dark **legacy-compatibility CSS block** re-styling every legacy class |
| MED | `result.info` advisories never rendered | Added an **Advisories** section |
| MED | Baseline-diff panel dropped identity-version transparency, compatibility reasons, coverage/trust regressions | Restored all (data already in the diff dict) |
| MED | Custom-rules truncated at 50 with a misleading "see JSON export" note | Render all results with full detail; note removed |
| LOW | Dead code: `technical_panel`, `close_panel`, `render_status_badge`, `loading_stages`, `icon_name_for`, `_cov_bucket_str`, `validator_src_idx` | All removed |
| LOW | `status_badge_html` diff colors fell back to "unknown" | Added explicit diff→semantic color mapping |
| LOW | `cursor: pointer` on non-clickable table rows | Removed |
| LOW | `var(--text, inherit)` undefined CSS var | Replaced with token color |

## 27. Fixes applied

All §26 items fixed and re-verified (design tests 19/19, UI benchmark
35/35, state isolation 6/6).

## 28. Regression results

| Suite | Result |
|---|---|
| pytest (incl. 19 new UI design tests) | **710/710** |
| Golden runners | **9/9** (22/22 parser golden + 8 suites) |
| Benchmark suites | **28/28** (security, adversarial, metamorphic, readiness, CI gate, stress, UI, PH13…) |
| Release smoke | **10/10** |
| UI benchmark | **35/35** |
| UI state isolation | **6/6** |
| XSS probe | Safe (escaped) |

**No deterministic validation regression.**

## 29. Packaging verification

- Fresh wheel `sdc_tools-1.3.0-py3-none-any.whl` built.
- Wheel contains `app.py` + full `ui/` package (`theme.py`, `validator.py`,
  `components.py`, all tabs) — **missing: NONE**.
- Installed the wheel to a clean target; `app`, `ui.validator`,
  `ui.theme`, `ui.components`, `ui.feedback`, `ui.tab_linter` all import
  OK from the wheel code; helpers execute.
- `.streamlit/config.toml` is a dev/runtime config (not shipped in the
  wheel — the CSS forces dark regardless).

## 30. Remaining UI migration work

- Clocks / Context / Coverage / Interactions / Readiness / Diff / Reports /
  CI pages → migrate each to the premium workspace pattern (grouped sidebar
  arrives with this).
- Product website / Benchmarks / Trust Center / Docs / Releases experience.
- Light-mode tokens (P1), docs search, rule pages for all 111 rules,
  per-analysis history (P2).
- Mobile read-only summary mode.

---

### Success-condition checklist

✓ Visibly reflects the approved premium design (browser + DOM verified)
✓ No longer a default Streamlit dashboard (dark graphite, hairline borders,
  SVG icons, premium status system)
✓ Real `check_sdc()` results drive the interface (no mock data)
✓ Findings easier to investigate (explorer table + detail expanders +
  source excerpts + filters)
✓ Source provenance clearer (line numbers, highlights, `↕` dual-line)
✓ No validation semantics changed (backend frozen; 710/710 + 9/9 + 28/28)
✓ Existing features accessible (nothing removed; legacy CSS restored)
✓ State isolation correct (6/6 + probes)
✓ User content safely escaped (XSS probes + 19 tests)
✓ Full regression green
✓ Fresh-wheel installation works
✓ Design foundation reusable (tokens + components in `ui/theme.py` +
  `ui/components.py` ready for Clocks/Coverage/Readiness/Diff)
✓ Independent review confirms design-document compliance
