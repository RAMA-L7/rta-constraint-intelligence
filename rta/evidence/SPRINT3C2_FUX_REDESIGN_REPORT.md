# Sprint 3C2 — First-User Experience Redesign (FUX 2)

> Ṛta · product-correction sprint · frontend-only (backend frozen, zero backend
> modules modified). This sprint followed the mandated written design review
> (10 questions) conducted from the perspective of a Physical Design engineer
> who has never seen Ṛta.

---

## The design review (summary of the 10 answers)

The full written review is in the sprint response; the decisions that drove the
rebuild:

1. The user thinks they are opening a **constraint checker** ("I'll give it my
   SDC and it tells me what's wrong before STA") — not a navigation workspace.
2. Within 10 seconds they must understand *what this is, what to do, that it
   works* — via behavior, not nav copy.
3. The single primary action is **Analyze the loaded SDC**.
4. Before analysis, all results and utility information is unnecessary.
5. All result and utility pages stay hidden until an analysis exists.
6. Advanced functionality is discovered through **progressive disclosure**
   (RESULTS → collapsed "More tools"), driven by the engineer's questions.
7. Readiness / Coverage / Clock Intelligence / Diff are translated into the
   engineer's own questions: **Health** ("Can I hand this off?"), **Coverage**
   ("Did I constrain every port?"), **Clocks**, **Changes**.
8. Ideal journey: input screen → Analyze → timeline → **Findings** → question
   paths (Clocks, Coverage, Health, Changes, Report).
9. Every post-analysis screen exists to answer exactly one engineer question.
10. **No screen except the input is visible at launch** — no sidebar at all.

## Before vs After

| Aspect | Before (Sprint 3C) | After (Sprint 3C2) |
|---|---|---|
| Launch | New Analysis page with sidebar visible (START group) | **No sidebar** — full-width landing "Check your SDC before STA" |
| Labels | Validation, Clock Intelligence, Readiness, Diff, Interactions | **Findings, Clocks, Health, Changes, Conflicts** (+ Summary, Coverage, Report) |
| Post-analysis landing | Overview | **Findings** ("what did Ṛta find?") |
| Nav | 6 groups with utilities mixed in | **RESULTS** (10 items, engineer's questions) + collapsed **"More tools"** disclosure |
| Page headers | Purpose line | Purpose asks the **engineer's question** + "Next" action |

## Screens implemented / verified (browser, live backend, zero console errors)

- **Landing**: no sidebar, headline "Check your SDC before STA", REQUIRED SDC
  pre-filled with the sample, OPTIONAL netlist with why-copy, Analyze button.
- **Analyze → Findings**: auto-lands on `#/validator`; RESULTS sidebar appears;
  heading, metrics (Errors/Warnings/Clocks) and findings table verified.
- **Sidebar**: RESULTS group (Summary · Findings · Clocks · Coverage · Design ·
  Conflicts · Health · Changes · Report · Export) + collapsed **More tools**
  (Generator · Linter · Converter · Corner Manager · MMC · Test Drive · Rules ·
  CI · Trust · Documentation · Feedback).

## Regression

| Suite | Result |
|---|---|
| pytest | **800/800** |
| UI/API | **35/35** |
| Workspace UX (WS-01b → RESULTS/TOOLS + "More tools", same capability) | **31/31** |
| State isolation | **12/12** |
| Motion | **14/14** |
| Release smoke | **10/10** |
| Evidence check | OK |

## Independent review → fixes applied

1. **`newSession()` could leave a stale sidebar** — when already on the landing
   (hash unchanged, no `hashchange` fires), the body class and nav were not
   re-evaluated after clearing the analysis. Now `newSession()` forces an
   explicit `route()` re-render.
2. **Brand mark routed to Overview** instead of the New Analysis landing —
   pre-analysis this showed the empty Summary page. Brand now returns to
   `#/new_analysis`.
3. Minor dead wiring (`data-action` branch, unused icon entries) noted as
   harmless; left in place.

## Remaining limitations

- Interactive click-through of some post-analysis pages (Health/Changes detail
  interactions) still hits the browser-agent tooling limitation on multi-step
  flows; the flows are verified structurally and by the API-level benchmarks.
- Sessions remain in-memory per tab (deliberate; baselines are the persistence
  path).

## Recommendation

The first-time experience now matches the design review: launch → understand →
one action → results. Next sprint: the signature **Health (readiness rail) and
Clocks (graph/inventory/matrix)** visual redesigns inside this results-led
shell, then the **Coverage bus visualization**, then a fresh interactive browser
pass.
