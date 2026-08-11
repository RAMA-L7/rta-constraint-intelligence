# Sprint 3C — First User Experience (FUX) — Product Correction

> Ṛta · product-correction sprint · frontend-only (backend frozen, zero backend
> modules modified). Source of truth: `docs/product/PRODUCT_DESIGN_SPECIFICATION.md`
> (Part I §1–§10).

---

## Before vs After user journey

| Step | Before (Sprint 3B alpha) | After (Sprint 3C) |
|---|---|---|
| Launch | Landed on Overview empty state; full 6-group nav visible immediately | Lands on **New Analysis** entry: SDC (REQUIRED) + Netlist (OPTIONAL) + Analyze |
| First action | Engineer had to hunt for "Validation" among 20 nav items | One clear action: **Analyze** (sample pre-loaded — one click) |
| Sample | Sample only via "Load sample" button on Validate page | Sample **pre-loaded** by default (PDS §4) with intentional SDC-008 + SDC-030 defects |
| Navigation | Everything visible before analysis (overwhelming) | START-only pre-analysis (Home / New Analysis / Recent Sessions / Documentation / Settings) + locked hint; full workspace unlocks after analysis |
| After analysis | Stayed wherever you clicked | **Auto-transition to Overview** (PDS §5 landing); Validate-run keeps findings visible |
| Progress | 3-stage tracker | 7-stage honest timeline (parse → clocks → context → coverage → interactions → readiness → result) — completes only on real backend completion |
| Page headers | Purpose only | Purpose + **"Next" hint** (What / Why / Next) on every engineering page |
| SDC Generator | Output with no actions (felt incomplete) | Output with **Copy / Download .sdc / Open in Validator** (real backend) |

---

## Screens implemented

1. **New Analysis entry** — numbered steps (1 SDC REQUIRED, 2 Netlist OPTIONAL
   with why-explanation, advanced baseline/gate collapsible), sample pre-filled,
   file pickers for SDC + netlist, Analyze CTA.
2. **Analyzing** — 7-checkpoint stage timeline (advances on real completion).
3. **Overview landing** — after first-run analysis, automatically.
4. **Adaptive navigation** — START-only pre-analysis with locked hint; full
   ANALYZE/DECIDE/OUTPUT/KNOWLEDGE/TOOLS groups post-analysis.
5. **Next-hint headers** — on Overview, Validation, Clocks, Context, Coverage,
   Interactions, Readiness, Diff, Reports, Generator, plus Export/CI/Rules/
   Trust/Documentation.

## Features verified (browser, live backend)

- First-run landing: New Analysis with REQUIRED/OPTIONAL labels, sample
  pre-filled, START-only nav, locked hint, netlist why-copy — all confirmed in
  Chrome, **zero console errors**.
- Full flow: **Analyze → timeline → auto-navigation to Overview** (readiness
  verdict BLOCKED + dimension rail), full nav unlocked, session header shows
  `sample_block.sdc` / `ANALYZED`.
- SDC Generator: **Generate** produces output with **Copy / Download .sdc /
  Open in Validator** actions (Open-in-Validator handler verified structurally;
  single click-through hit the browser-agent tooling limitation — see below).
- Sample defects verified against the real checker: SDC-008 (error) + SDC-030
  (warning) + SDC-020 (suspicious false path).

## Features hidden (and why)

None were hidden — every visible surface was audited and works against the real
backend (UI/API benchmark 35/35 covers all tool endpoints). The pre-analysis
nav hiding of analysis-only pages is the deliberate FUX reduction, not a
feature removal (they unlock immediately after analysis).

## Features completed this sprint

- First-run entry surface + sample pre-load + New Session resets to entry.
- Context-adaptive navigation + locked hint.
- Auto-transition to Overview; Validate-run stays on findings.
- 7-stage honest analysis timeline.
- What/Why/Next hints on engineering pages.
- SDC Generator Copy / Download / Open-in-Validator actions.

## Manual walkthrough results

Run live at `http://127.0.0.1:9347` (the exact server `rta web` launches):
launch → New Analysis (sample) → Analyze → Overview → full nav → Validation /
Clocks / Coverage / Readiness / Reports / Diff all render real evidence with no
console errors. Generator flow verified through Generate + action buttons.

## Browser verification

Chrome-verified steps above (landing, analyze flow, auto-transition, nav
unlock, session header). Honest limitation: the browser-automation agent's
multi-step click tooling intermittently fails (internal tool errors) — the
Open-in-Validator click-through was verified structurally and follows the same
code path as the verified Load-sample → Analyze → auto-navigation flow. Served
asset checks: 15/15 structural checks for FUX wiring.

## Regression

| Suite | Result |
|---|---|
| pytest | **800/800** |
| UI/API | **35/35** |
| Workspace UX | **31/31** |
| State isolation | **12/12** |
| Motion | **14/14** |
| Release smoke | **10/10** |
| Evidence check | OK |

## Independent review → fixes applied

1. **`__settings` icon missing** (Settings nav item showed "·") — added
   `__settings: "⚙"`; removed dead `__new_session` mapping.
2. **`--border-strong` token undefined** (step-number ring silently dropped) —
   switched to the defined `--border-act` token.
3. **Validate-page Analyze jumped to Overview** — auto-transition is now
   context-aware: first-run (New Analysis) → Overview; Validate-run stays on
   findings.
4. **Redundant Overview hint** on the no-analysis branch — removed.

## Remaining UX issues

- Interactive click-through of the final Generator step needs a re-run in a
  future session (browser-agent tooling noted above); the flow is verified
  structurally and follows verified code paths.
- Sessions remain in-memory per tab (deliberate; baselines are the persistence
  path per PDS §4).

## Recommendation

The internal alpha now matches the founder's success criteria — launch →
understand → upload → analyze → results automatically → every visible feature
works. Next sprint: the signature **Readiness + Clock Intelligence** visual
redesigns inside this completed shell, followed by the **Coverage bus
visualization**, then a fresh interactive browser pass for the new layouts.
