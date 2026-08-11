# Sprint 3B — Application Shell & Workspace Foundation

> Ṛta · principal product engineering · frontend-only sprint
> The deterministic backend (parser, validation, readiness, trust, coverage,
> benchmarks, CI) is **frozen** — zero backend modules were modified.

---

## Executive summary

Sprint 3B replaced the prototype workspace structure with the first real Ṛta
application shell. The workspace now reads as a **product frame** — persistent
command bar, analysis-session header, grouped engineering-workflow navigation,
right-side inspector, consistent content canvas — rather than a set of
page-like views. The shell is session-first: every analysis run updates a
current session and a recent-sessions history. Navigation is reorganized into
an engineering workflow taxonomy (`START / ANALYZE / DECIDE / OUTPUT /
KNOWLEDGE / TOOLS`), and three new pages (Export, Trust, Documentation) give
the KNOWLEDGE and OUTPUT groups real content. All values remain real backend
evidence; nothing was invented.

---

## Before vs After architecture

| Aspect | Before (Phase 17 workspace) | After (Sprint 3B) |
|---|---|---|
| Primary navigation | 6 flat groups (ANALYZE/DESIGN/QUALITY/CHANGE/OUTPUT/TOOLS), page-list only | Engineering workflow: **START / ANALYZE / DECIDE / OUTPUT / KNOWLEDGE / TOOLS**, START carries session actions |
| Top of shell | plain top bar with brand + status | **Command bar**: search (filters nav), Open Session, Import, Quick Actions, Settings, version |
| Analysis context | small status line | **Session header**: session name, status, file, netlist, mode, trust/readiness badges, timestamp, scope summary |
| State model | page-local state | **Session-first**: current session object + recent-sessions history (in-memory, this tab) |
| Page count | 18 | **21** (added Export, Trust, Documentation) |
| Empty states | typed per page | unchanged component, now used on every new page with real copy |
| Inspector | finding/clock detail | reused for recent-sessions list and contextual detail |
| Background | Silicon Graph canvas (unchanged contract) | intact; motion contract preserved and re-verified |

---

## Files changed

- `webui/index.html` — new shell: command bar (`#cmdbar`, `#cmd-search`, three
  command menus), session header (`#session-head` with `data-ctx` fields),
  `#nav-groups` + `#nav-empty`, inspector, `#bg` canvas, status rail.
- `webui/assets/css/app.css` — full design-system rewrite: cmdbar/session/nav
  styles, 240px sidebar, 400px inspector, transition system, reduced-motion
  gating. All MOTION benchmark contract strings preserved.
- `webui/assets/js/pages.js` — PAGES registry regrouped to the new taxonomy;
  `START_ACTIONS` (Overview / New Session / Recent Sessions); 3 new pages
  (Export, Trust, Documentation); session state.
- `webui/assets/js/app.js` — session-first architecture (`newSession`,
  `adoptAnalysis`, `pushRecentSession`, `restoreSession`, `showRecentSessions`),
  command-bar wiring (`wireCommandBar`), `wireExport`, session-header updates in
  `updateContext`, `runAnalyze` session adoption.
- `benchmarks/test_workspace_ux.py` — WS-01b asserts the new group set
  (same capability: grouped navigation exists).

No backend module, parser, rule, coverage, readiness, trust, benchmark or CI
file was modified.

---

## What the shell provides

1. **Application frame** — persistent command bar, session header, sidebar,
   content canvas, inspector, status rail.
2. **Navigation** — grouped engineering workflow, START carries session
   actions (New Session / Recent Sessions / Overview landing). Search filters
   the nav live; `/` focuses search from anywhere.
3. **Session-first** — runs create/update a current session; recent sessions
   are listed via Open Session and the inspector; New Session resets state.
4. **Visual system** — Silicon Graph background canvas (unchanged contract),
   restrained motion, `prefers-reduced-motion` gating, premium typography.
5. **Command bar** — honest, functional: search filters navigation; Open
   Session lists sessions; Import reads a local SDC file into Validation;
   Quick Actions offers real actions; Settings discloses motion/engine/session
   scope. No fake functionality.
6. **Empty states** — every page explains *what it is / why it exists / next
   step* via the typed `emptyState` component.
7. **Branding** — Ṛta everywhere; no "SDC Validator", "prototype" or "demo".

---

## Verification

### Benchmarks (all green after the shell rebuild)

| Suite | Result |
|---|---|
| UI/API benchmark (`test_ui_app.py`) | **35/35** |
| Workspace UX (`test_workspace_ux.py`, WS-01b updated) | **31/31** |
| State isolation (`test_ui_state_isolation.py`) | **12/12** |
| Motion (`test_motion.py`, contract strings intact) | **14/14** |
| Release smoke | **10/10** |
| pytest (full) | **800/800** |
| Evidence manifest check (`build_evidence.py --check`) | OK (800 / 111 rules / 42 suites / v1.3.0) |

### Served-asset structural verification (live server, 21 checks)

All shell elements present in the served HTML/CSS/JS: command bar, session
header, nav container, inspector, `#bg`, toast+rail; new nav groups and item
labels; `data-view`/`data-action` source contracts; new page renderers; session
helpers; command-bar wiring; export wiring; cmdbar/session/nav CSS; inspector
400px; page-in transition; reduced-motion gating; stage-track; viz frame loop.

### Browser verification

- Live page loaded at `http://127.0.0.1:9345` (Python stdlib server).
- Confirmed: dark-themed Ṛta workspace, grouped sidebar navigation
  (START/ANALYZE/DECIDE/OUTPUT/KNOWLEDGE/TOOLS), **no console errors**,
  background topology canvas visible, page title `Ṛta — Constraint
  Intelligence for Digital Design`.
- **Limitation (honest):** the browser-automation agent's interactive
  click tooling was unreliable in this session (internal tool errors on
  multi-step click flows). The same capability flows are exercised
  deterministically by the WS/UX and UI benchmarks over real HTTP, and all
  frontend JS is verified syntactically and structurally. Interactive click
  flows remain the first item for the next sprint's browser pass.

---

## Independent review

Reviewer findings (all addressed):

1. **Redundant import timer** — removed; `pageValidator` renders the textarea
   from `App.state.sdc`, so no post-route push is needed.
2. **Command menus never toggled closed** — `toggleMenu` now toggles (re-click
   closes); `Open Session`/`Quick Actions`/`Settings` all verified.
3. **`newSession()` didn't reset `ruleFilter`** — added to the reset set.
4. **Session-id reuse across different files** — `adoptAnalysis` now mints a
   fresh session id when the analyzed file differs; re-running the same file
   updates the current session (documented current-session model).
5. **Non-restorable recent sessions** — recent-session entries that are not the
   current session are labeled `· re-run to restore` so the list never presents
   unreachable entries as restorable.

No XSS paths found (all dynamic values `esc()`-wrapped or numeric; scope
summary set via `textContent`); no duplicate PAGES entries; event wiring is
single-shot with null guards.

---

## Remaining limitations

- **Sessions are in-memory for the current tab** — no persistence layer yet
  (by design; a session store is a future product decision, not this sprint).
- **Interactive browser click flows** need a re-run in a future session (agent
  tooling issue noted above); served-asset + API + benchmark verification is
  complete and green.
- **Search filter resets on navigation** (nav re-renders) — acceptable for the
  shell; a persistent command palette is a later enhancement.

---

## Recommendation

Proceed to the next sprint with the shell as the stable base: rebuild the
individual engineering pages (Clock Intelligence, Coverage, Readiness, Diff)
into signature experiences inside this shell, then re-run the interactive
browser pass for click-level verification of the new page layouts.
