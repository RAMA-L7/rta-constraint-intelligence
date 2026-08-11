# Sprint 3 — Ṛta Internal Alpha: Vertical Slice Verification

> Priority change per founder directive: **ship a working product milestone**, not
> implementation completeness. One complete vertical slice, real backend only,
> repository left runnable via `rta web` / `sdc-tools web`.

---

## What is fully complete (verified live)

The Sprint 3B shell plus the full founder manual checklist were verified in a
real browser against the live server (`python api_server.py <port>` — the exact
server `rta web` launches). Every item on the founder checklist passes:

| # | Checklist item | Status |
|---|---|---|
| 1 | Application launches | ✅ `200` on `/` and `/api/health`; page renders |
| 2 | Branding | ✅ dark Ṛta workspace; title `Ṛta — Constraint Intelligence for Digital Design` |
| 3 | Workspace shell | ✅ command bar, session header strip, grouped nav, main canvas |
| 4 | Navigation | ✅ START/ANALYZE/DECIDE/OUTPUT/KNOWLEDGE/TOOLS; hash routes + active state |
| 5 | Session flow | ✅ session header reflects analysis (name, status, file, mode, badges); fresh tab = honest EMPTY state |
| 6 | Import SDC | ✅ command-bar Import reads a local file into Validation; Load sample verified |
| 7 | Optional netlist | ✅ netlist field populated by Load sample; coverage then shows real port data |
| 8 | Validation | ✅ Analyze runs the deterministic backend; metrics + findings table appear |
| 9 | Findings | ✅ severity/rule/search filters, accordions, inspector, source viewer with highlights |
| 10 | Readiness | ✅ overall badge, 7-dimension rail, Blockers (4), Review items (6), Recommended actions |
| 11 | Clocks | ✅ inventory table (name/period/frequency), hierarchy tree, relationship matrix |
| 12 | Coverage | ✅ coverage summary + port detail (real netlist evidence) |
| 13 | Reports | ✅ HTML report + JSON result artifact rows with Download buttons |
| 14 | Diff | ✅ V1/V2 input areas + Compare button |
| — | Command bar | ✅ Quick Actions menu (5 real actions), Open Session menu |
| — | Console | ✅ zero console errors on every verified page |

## What is intentionally deferred

- **Signature page redesigns** (Clock Intelligence / Coverage / Readiness / Diff
  as bespoke visual experiences) — the pages are *complete and functional* with
  real backend evidence; deeper visual redesign is the next product slice, not
  a prerequisite for the alpha.
- **Session persistence** — sessions are in-memory per tab by design; a session
  store is a product decision, not an alpha blocker.
- **Website motion pass** — out of scope for this milestone (site content is
  already Ṛta-branded with evidence-backed messaging).

## What should be evaluated manually

1. `rta web` (or `python -m cli web`) from the repo root → opens the workspace.
2. Load sample → Analyze; click through Readiness, Clock Intelligence, Coverage.
3. Command-bar Import with a real `.sdc` file; add a Verilog netlist and re-run
   to see design-aware coverage.
4. Reports → download the JSON and HTML artifacts.
5. Diff → paste two SDC variants and Compare.

## Regression proof (all green)

| Suite | Result |
|---|---|
| pytest | **800/800** |
| UI/API benchmark | **35/35** |
| Workspace UX | **31/31** |
| State isolation | **12/12** |
| Motion | **14/14** |
| Release smoke | **10/10** |
| Evidence manifest check | OK (800 tests / 111 rules / 42 suites / v1.3.0) |
| CLI `web` subcommand | resolves and serves the workspace |

## Recommended next implementation slice

**Readiness + Clock Intelligence signature redesigns** inside the completed
shell — dimension-rail experience and clock-graph/inventory/matrix as bespoke
visuals — followed by the Coverage bus visualization. The alpha is stable and
runnable today; the next slice should enhance, not repair.
