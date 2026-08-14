# Ṛta — Phase E Workspace UX Specification

> **Status: implemented and verified.** This document specified the workspace
> UX architecture around the frozen Phase C product; the approved architecture
> was then implemented in the Streamlit tool (`legacy/streamlit/`) — tool home,
> capability catalog, per-feature entry points, back navigation — and the
> visual foundation applied in Phase F (see `PHASE_E_IMPLEMENTATION_STATUS.md`
> and `PHASE_F_IMPLEMENTATION_STATUS.md`). §23 records what was built, the
> verification evidence, and the deltas adopted during implementation.
>
> Engine, API result semantics, rule semantics, and validated feature behavior
> were unchanged by this work (`FUNCTIONAL_BASELINE.md`); the deterministic
> engine stayed frozen.

---

## 1. Tool home (first screen)

The engineering tool opens on a **Ṛta tool home**, not on results.

**Goal within seconds:** the user answers "What is Ṛta?", "What can I use it
for?", "Which tool do I need?".

**Structure (top → bottom):**

1. **Welcome / positioning** — one line, engineering tone:
   *"Ṛta is a deterministic constraint-intelligence workspace for block-level
   digital design — validate, generate, and review SDC before STA."*
2. **Entry helpers** (beginner path) — two primary calls to action, always
   visible, never buried:
   - *"Start with Test Drive"* — run a real sample through the real backend
   - *"Validate an SDC"* — jump straight to the Validate tool
3. **Capability catalog** — the four groups (Core / Analyze / Advanced /
   Output & Knowledge) as scannable card grids (§2, §4).
4. **Standing trust line** — the frozen disclosures, one line under the grid:
   *"Deterministic · offline · no LLM. Readiness is a constraint-quality
   review, not an STA timing signoff."*

**Explicitly NOT on the home:** findings, clocks, coverage, readiness,
reports, or any analysis dashboard. The home is a **choice surface**, not a
result surface.

---

## 2. Capability catalog

The 19 capabilities are the product. They are the primary navigation.

**Groups (canonical — `PRODUCT_CAPABILITY_CATALOG.md` / `FEATURE_TRACEABILITY.md`):**

| Group | Capabilities |
|---|---|
| **Core** | Validate · SDC Generator · SDC Linter · SDC Converter |
| **Analyze** | Clock Intelligence · Coverage · Design Context · Constraint Conflicts · Readiness · SDC Diff |
| **Advanced** | Corner Manager · MMC · Test Drive · Rules · CI |
| **Output & Knowledge** | Reports · Trust · Documentation · Feedback |

**Adopted presentation order (implementation):** the home catalog presents the
same 19 capabilities in the business-site order — **Analysis capabilities**
(SDC Validation · Clock Intelligence · Design Context · Constraint Coverage ·
Constraint Interactions · Readiness · CI Quality Gates), **Engineering tools**
(Generator · Linter · Converter · Diff · Corners / MMC · Rules Reference ·
Test Drive), **Output & Knowledge** (Reports · Trust · Documentation ·
Feedback). The canonical capability set is unchanged; only the grouping labels
and order were aligned with the business site (§23).

**Rules:**

- No capability is labeled "More Tools", "Utilities", "Extras", "Optional",
  or "Secondary". Every one of the 19 has a card or an always-visible entry.
- Reports / Trust / Documentation / Feedback are **capabilities with cards**,
  not buried settings.
- The catalog is the *only* pre-analysis navigation. RESULTS pages appear
  only after an analysis exists (session model, §8–9).

---

## 3. Navigation architecture

**Principle:** the simplest hierarchy that supports the real workflows.
Every item must have a reason to exist.

```
PRIMARY      Capabilities (the catalog = the tool home)
             + per-feature results, contextual (only when relevant)

SECONDARY    Session strip (current file / netlist / mode / status)
             Recent work (only if genuinely useful — see §21)

SUPPORT      Documentation · Trust · Feedback
             Settings (thin — see §21)

REMOVED      Quick Actions · global Import · "More Tools" · global Settings menu
```

**Concrete nav model:**

- **Left rail (desktop / wide):** "CAPABILITIES" group (catalog card +
  the four group headings as fast-links, or the catalog itself), then a
  **contextual RESULTS group** that appears only after an analysis.
- **Top command bar (all sizes):** product mark → tool home · context strip
  (session name, file, netlist, mode, status) · a single "New / Start over"
  action · Support links (Docs · Trust · Feedback).
- **No duplicate routes to the same surface.** Each capability has exactly
  one home route; cross-links are contextual next-actions (§10), not nav
  duplicates.

---

## 4. Feature card anatomy

Every card answers five questions, in this order (consistent pattern):

```
┌────────────────────────────────────────────┐
│ [icon]  TITLE                    GROUP tag │
│ WHAT IS IT?  one sentence, plain language  │
│ INPUT  SDC required · netlist optional     │
│ DOES   one line: what Ṛta computes         │
│ GET    one line: what you receive          │
│ NEXT   one line: suggested next action     │
│                    [ Open the tool → ]     │
└────────────────────────────────────────────┘
```

Example — Validate:

> **Validate** — *Check an SDC for structural and constraint issues before STA.*
> Input: SDC required · netlist optional.
> Does: runs the deterministic rule engine (parse, TCL resolve, all rules,
> clock/interaction/readiness fold).
> Get: findings with rule codes, severity, source lines, engineering context.
> Next: review clocks / coverage / conflicts / readiness.

Every card's "Open" leads to that feature's own workspace (§5). No card
opens a universal dashboard.

---

## 5. Feature workspace anatomy

Selecting a feature enters **that tool**. It owns its INPUT, PROCESS, RESULT,
and NEXT ACTION. Standard anatomy:

```
┌──────────────────────────────────────────────┐
│ [group]  FEATURE TITLE                        │
│ what this is · what you provide               │
│ ──────────────────────────────────────────────│
│ INPUT SURFACE  (feature-specific, §6)         │
│   [ Run ]  (one primary action per feature)   │
│ ──────────────────────────────────────────────│
│ PRIMARY RESULT  (§7)                          │
│ ──────────────────────────────────────────────│
│ RELATED RESULTS  (contextual next actions §10)│
└──────────────────────────────────────────────┘
```

- One primary action per feature ("Validate", "Generate", "Lint",
  "Convert", "Compare", "Run gate", "Analyze sample"…).
- Related results are **labeled links** under the primary result — e.g.
  Validator's primary result is Findings; related are Clock Intelligence,
  Coverage, Conflicts, Readiness.
- The user is never trapped: each feature works standalone (§8); session
  links are optional (§9).

---

## 6. Input architecture

**Inputs belong to the feature that needs them.** There is no global upload.

| Feature | Inputs (where the user provides them) |
|---|---|
| Validate | SDC (required) · netlist (optional) · top (optional) · baseline/gate/custom-rules (advanced, collapsed) |
| Generator | generation parameters only — no SDC |
| Linter | SDC (required) |
| Converter | SDC (required) · target format |
| Clock Intelligence | SDC (required) — netlist not needed for relation inference |
| Coverage | SDC (required) · netlist (optional, design-aware mode) |
| Design Context | SDC (required) · netlist (required for object resolution — honest limit stated) |
| Conflicts | SDC (required) |
| Readiness | SDC (required) · netlist (optional) |
| Diff | Version A SDC (required) · Version B SDC (required) |
| Corner Manager | corner preset (no SDC) |
| MMC | corner set · design · clock |
| Test Drive | sample choice (no upload needed) |
| Rules | browse: none · execute: SDC + custom-rules YAML |
| CI | SDC (required) · baseline (optional) · gate policy (required) |
| Reports | an analysis (from Validate etc.) |
| Trust / Documentation / Feedback | none / feedback comment (required) |

Every input surface states required vs optional **at the feature**, with an
explanation of what the input is used for. The user never navigates back to a
global upload screen to satisfy another feature.

---

## 7. Result architecture

**No one giant results dashboard.** The current tool owns the primary result;
related results become clearly labeled next actions.

- **Primary result:** what the user asked for (Findings for Validate,
  generated SDC for Generator, matrix for Clocks, diff summary for Diff…).
- **Key numbers first:** severity/status, most important metrics, immediate
  actions — then progressive disclosure for details, source, evidence,
  technical explanation, advanced data (§11).
- **Per-result structure:** result headline → metric strip → primary list →
  expandable detail → related actions.

**Density rule:** engineering information is not removed; it is disclosed
progressively. Dense matrices (e.g. Clock Relationships) get a scannable
summary (counts, status chips) above the full matrix, with the full matrix
available to experts.

---

## 8. Standalone workflow

Every feature completes its task without a session:

```
Open Validator → provide SDC → Validate → findings → done.
Open Generator → parameters → Generate → SDC → download/done.
Open Diff → V1 + V2 → Compare → changes → done.
```

Standalone is the **default mental model**. Nothing forces a session.

---

## 9. Session workflow

Sessions are useful but optional and never dominate:

```
Validate → Findings → Clocks → Coverage → Conflicts → Readiness → Report
```

- An analysis run in any analysis feature **adopts** the run into the current
  session (as today), so related results are one click away.
- The session strip (file / netlist / mode / status) makes the shared context
  visible and understandable — the related tools are seen as **related
  tools**, not mysterious pages.
- **New / Start over** is always one click; the user is never trapped.

---

## 10. Cross-feature navigation

Contextual, placed next to the result that motivates it — **not** a global
Quick Actions menu:

| From | Contextual next action |
|---|---|
| Generator | Open in Validator · Lint · Download |
| Validator | Inspect Clocks · Check Coverage · Review Conflicts · Check Readiness |
| Clock Intelligence | Review Coverage · Review Conflicts · Readiness |
| Coverage | Review missing constraints · Validate |
| Design Context | Open Coverage (design-aware) · All findings |
| Conflicts | All findings · Readiness |
| Readiness | Review blockers · Report |
| Diff | Open V2 in Validate · Review changed constraints |
| CI | Download gate JSON · Review findings |
| Test Drive | Open findings · Open clocks · Open coverage |
| MMC | Open a corner in Validate |
| Corner Manager | Open MMC |
| Reports | Download · Share · Archive |
| Rules | Validate with rules · Download registry |

Every action performs something real; no dead links.

---

## 11. Progressive disclosure

Three levels, consistent across features:

1. **Summary** — status chip, key numbers, primary action. Fits in one screen
   without scrolling for a typical result.
2. **Details** — findings list, source lines, categories, filters
   (severity/rule/search), download/export.
3. **Deep evidence** — raw JSON, full matrices, structural details, CLI
   equivalents — behind explicit "Show full …" controls.

Experts reach level 3 in one click; beginners never have to see it.

---

## 12. Beginner path

1. Tool home → "Start with Test Drive" (real sample through the real backend).
2. Test Drive explains: what is this, what input, what Ṛta does, what you get,
   what next (the card contract in action).
3. From Test Drive results → "Open findings/clocks/coverage" teaches the
   session model by doing.
4. Every feature page carries the same five-question header — a beginner can
   read any page and know what to do.

No onboarding wizard required; the card contract *is* the onboarding.

---

## 13. Expert path

- Fast access: catalog → tool → input → run (keyboard reachable, `/` search
  across capability names and rule codes stays).
- Filters (severity / rule / search), downloads (JSON / HTML / JUnit /
  snapshot), CLI equivalents shown on result and export surfaces.
- Progressive disclosure gives experts the full technical detail without
  clutter.

One application serves both paths.

---

## 14. Empty states

Every feature has a first-visit empty state that teaches:

- **Validate / Linter / Converter / Coverage / Conflicts / Readiness /
  Clocks / Context:** "No result yet — paste an SDC and press [Run]" +
  one-click sample loader.
- **Diff:** "Enter Version A and Version B, then Compare."
- **Generator:** parameter form is its own empty state (defaults shown).
- **Reports / Export:** "No analysis to report — run Validate first."
- **CI:** "SDC + baseline + policy — explained before running."
- **Rules / Trust / Documentation / Feedback:** always meaningful.

Empty states never show fake data or fake progress.

---

## 15. Error states

- **Input errors:** inline, at the field — required missing, empty,
  whitespace-only (mirrors the API's HTTP 400 contract).
- **Backend errors:** typed error surface with the honest message; **engine
  failure never becomes PASS** (exit-3 contract preserved).
- **Validation rejections:** CI baseline invalid, custom-rules YAML invalid,
  feedback empty/overlong — each returns the actual reason.
- **Network/API failure:** explicit failure state, retry available; no stale
  result from another feature is ever shown.

---

## 16. Loading states

- Skeleton/progress only for real in-flight requests.
- No fake loading completion, no fake progress bars, no pre-filled success.
- On completion the result is rendered from the actual response.

---

## 17. Trust presentation

The frozen disclosures are **surfaced, not hidden**:

- Tool home: one-line trust statement (deterministic · offline · no LLM ·
  readiness ≠ STA signoff).
- Coverage result: "Coverage is NOT correctness" inline.
- Readiness result: "READY does not mean setup/hold passes" inline.
- CI result: "CI PASS ≠ timing pass" inline.
- Everywhere: "NOT an STA timing signoff."
- Trust page: evidence-backed facts (from `/api/evidence`) + full boundary
  statements + what requires design context/STA.

**Wording is not marketing-rewritten.** Exact phrases preserved
(§ trust disclosures in `PHASE_C_UX_HANDOFF.md`).

---

## 18. Responsive behavior

Priority order: **1. task → 2. result → 3. action → 4. detail.**

- **Wide desktop:** left rail + content + optional inspector; grids at full
  width.
- **Laptop:** same hierarchy; grids breathe, no horizontal overflow.
- **Small viewport:** the left rail collapses to the catalog (single scroll);
  the command bar keeps brand + context + New; capability cards stack 1-up
  with the full card contract intact; results use progressive disclosure so
  the primary result stays first.
- Never solve responsiveness by shrinking text below readable size — collapse
  structure, not legibility.

---

## 19. Accessibility

- Semantic landmarks (`nav`, `main`, `aside`, `header`, `footer`).
- Keyboard reachable: catalog navigation, all primary actions, filters,
  downloads, cross-links; visible focus states.
- ARIA labels on icon-only controls; `role="status"`/`aria-live` on toasts and
  session strip (current pattern preserved).
- Color is never the only signal: severity also uses text labels / icons
  (existing status chips pattern).
- `prefers-reduced-motion` respected (existing behavior preserved); no
  motion is added in this phase anyway.
- Contrast maintained for engineering readability.

---

## 20. Removed / replaced concepts

| Concept today | Decision | Reason |
|---|---|---|
| **Quick Actions** (top-bar menu) | **Remove from primary workspace** | Every action already has a home at the feature or as a contextual next-action; a generic menu duplicates routes and adds a concept. |
| **Import** (global top-bar upload) | **Remove; replace with per-feature input** | Inputs belong to features (§6). Validate's own file picker is the home for SDC import. |
| **Settings** (top-bar menu) | **Thin or remove** | Current settings are informational (motion/engine/sessions/about) — move "About / engine facts" to Trust or Documentation; keep only genuinely functional settings, if any, at the feature level. |
| **Open Session / Recent sessions** (top-bar) | **Keep as a thin secondary concept, or remove** | Evaluate in implementation: if the session strip + New covers the need, drop the menu; if recent work is genuinely useful for returning engineers, keep one simple "Recent" surface. Do not preserve merely because it exists. |
| **More Tools** | **Already removed in Phase C** | Never reintroduce; all capabilities visible. |
| **Universal results dashboard** | **Replace with per-tool primary result + contextual links** | §7. |

**Rule:** no concept survives because it exists; each must serve the
engineer's primary job or be removed.

---

## 21. Migration from current workspace

The migration described here is **done** (see §23) — it was implemented in
`legacy/streamlit/` after this architecture was approved: Quick Actions and
global Import/Settings menus removed, catalog home kept, per-feature input
surfaces kept, contextual next-actions kept. The rows below remain as the
historical specification of the migration.

The current workspace already implements much of this (Phase C): feature-first
catalog, own input panels, contextual links, no "More Tools". Migration is
therefore **subtractive and re-organizing**, not greenfield:

1. **Keep:** catalog home, 19 capability entries, per-feature input panels,
   real-backend results, trust disclosures, contextual next-actions, empty/
   error/loading state rules, session strip.
2. **Remove:** Quick Actions menu, global Import button, top-bar Settings
   menu (relocate informational content), duplicate routes, any remaining
   "More Tools"-style grouping.
3. **Re-organize:** results become per-tool primary + related (§7, §10);
   session UI is simplified to strip + New + (optionally) Recent.
4. **Behavior unchanged:** all backend calls, result rendering, exit codes,
   and state rules stay exactly as verified in Phase C (WS-01..35 +
   1,227 pytest must remain green after the rebuild).

---

## 22. Before / after information architecture

| Aspect | Before (post-Phase-C baseline) | After (Phase E spec) |
|---|---|---|
| First screen | Catalog with cards (good) but command bar still carries Quick Actions / Import / Settings / Open Session | Tool home = catalog + positioning + beginner CTAs; command bar = brand, context strip, New, Support links |
| Global actions | 4 top-bar menus (Session / Import / Quick Actions / Settings) | 0 generic menus; actions live at features or as contextual next-actions |
| Results | RESULTS group with 10 competing entries once analyzed | Current tool owns primary result; related results are labeled links |
| Navigation | CAPABILITIES + RESULTS groups | CAPABILITIES (primary) + contextual per-tool results + thin Support |
| Sessions | Menu + strip | Strip + New (+ optional Recent); never dominant |
| Input | Already per-feature (keep) | Confirmed as the single model; global upload removed |
| Density | Results can feel overloaded | Progressive disclosure: summary → details → deep evidence |
| Beginner | "Start with Test Drive" exists | Same CTA elevated on the home; card contract everywhere |
| Trust | Inline disclosures present | Preserved verbatim + surfaced on home |

---

## Self-review (users A–G)

| User | Find the tool? | Understand input? | Complete without unrelated pages? | Understand result? | Find next action? |
|---|---|---|---|---|---|
| **A — validate an SDC** | ✓ "Validate an SDC" CTA on home + Core card | ✓ card states SDC required · netlist optional | ✓ Validate owns its input; standalone | ✓ findings first, severity + lines | ✓ Inspect Clocks / Coverage / Conflicts / Readiness |
| **B — generate an SDC** | ✓ Core card "SDC Generator" | ✓ parameters form (no SDC) | ✓ generator standalone | ✓ generated SDC shown | ✓ Open in Validator · Lint · Download |
| **C — check clock relationships** | ✓ Analyze card "Clock Intelligence" | ✓ SDC required (own panel) | ✓ standalone | ✓ inventory + matrix (scannable summary above) | ✓ Review Coverage / Conflicts / Readiness |
| **D — coverage** | ✓ Analyze card "Coverage" | ✓ SDC · netlist optional | ✓ standalone | ✓ score/present/total + NOT-correctness | ✓ Review missing constraints · Validate |
| **E — compare two SDCs** | ✓ Analyze card "SDC Diff" | ✓ V1 + V2 on the page | ✓ fully standalone | ✓ changes summary + detail | ✓ Open V2 in Validate · Review changes |
| **F — run CI** | ✓ Advanced card "CI" | ✓ SDC + baseline + policy on the page | ✓ standalone automation | ✓ gate result + exit code + reasons | ✓ Download gate JSON |
| **G — understand Ṛta first** | ✓ home explains it | ✓ Test Drive = real sample | ✓ no upload needed | ✓ real result summary | ✓ Open findings / clocks / coverage |

All seven complete their task with the feature owning input/process/result/
next-action; no user is routed through unrelated pages. **No revision
required.**

---

## STOP condition

*Historical:* this document was the Phase E UX architecture; at the time it
was written, no implementation had occurred. The architecture was subsequently
approved and implemented (§23), and the visual foundation followed in Phase F.
Phase C remains frozen — the deterministic engine is unchanged.

---

## 23. Implementation status & deltas (post-implementation record)

The approved architecture was implemented in the Streamlit tool
(`legacy/streamlit/`) and verified in a real browser. This section is the
living record of what was built and where implementation deliberately
adapted the specification.

### 23.1 What was built

- **Tool home** — first screen is the capability home (not a results
dashboard): eyebrow, positioning line, two beginner CTAs (**🧪 Start with
Test Drive**, **🛡 Validate an SDC**), the 19-card catalog, and the standing
trust line (deterministic · offline · no LLM · readiness ≠ STA signoff).
- **Capability catalog** — all 19 capabilities as cards, each answering
what / input / does / get / next, with a real "Open … →" control. Tab and
view targets navigate in-app; URL targets (CI · Reports · Trust ·
Documentation) render as `st.link_button` buttons opening the target in a new
tab. No capability is hidden under "More Tools".
- **Catalog grid** — true row-major 3-per-row grid (cards chunked in rows, not
cycled into fixed columns); scoped `:has(.home-card)` flex rules (with
`min-height: 0`) give every card in a row equal height and bottom-aligned
"Open" buttons (≤2px, measured).
- **Sidebar** — minimal: Home · Test Drive · Feedback · **Dark mode toggle** ·
What's New · GitHub/Docs footer. Features live once, in the catalog; the
sidebar intentionally does not duplicate them. Auto-collapses on page load
(one-shot script, `window.__rtaSidebarOnce` guard); expands on demand.
- **Header command bar** — brand block (eyebrow + Ṛta + version badge) on the
left, business-site navigation (Features · Why Ṛta · Rules · Install · Docs)
right-aligned, tagline on its own line. No Quick Actions / Import / Settings
menus.
- **Back navigation** — a visible "← Back to Home" button on every non-home
view, so users can always return even with the sidebar collapsed.
- **Dark mode** — sidebar toggle flips `data-theme="dark"` on the main
document; the full dark palette (background, cards, inputs, tables, buttons,
sidebar) applies app-wide, and toggling off reliably returns to light.

### 23.2 Implementation deltas vs this spec

| Spec (sections) | Implemented as | Why |
|---|---|---|
| §1–2 group labels Core / Analyze / Advanced / Output & Knowledge | **Analysis capabilities / Engineering tools / Output & Knowledge**, in business-site order | Align the tool's catalog with the business website's feature order (per founder direction); canonical capability set unchanged |
| §3 left rail = CAPABILITIES + contextual RESULTS group | Minimal sidebar (Home · Test Drive · Feedback · Dark · What's New) — no capability rail, no RESULTS group | Features live once in the catalog (dedupe); results stay in-tool with contextual next-actions; a rail duplicated every feature |
| §3 command bar context strip + New/Start-over | Brand + business nav + tagline; back button on non-home views; no context strip | Session strip not required by the current tab-based feature workspaces |
| §4 card "GROUP tag" | Not rendered on cards | Group heading above each grid section already labels the group |
| §5–10 per-feature workspaces | Kept from Phase C (own input, real backend, primary result, contextual next-actions); URL links opened via `st.link_button` | Verified unchanged; only entry/nav surfaces rebuilt |
| §18 responsive | Grid collapses to stacked cards on narrow viewports; tab rail scrolls horizontally | Streamlit constraints; no text-shrink |

### 23.3 Verification evidence

- Browser (Selenium + computed styles + screenshots): whole-app dark
(`rgb(12,12,13)`) and light restore (`rgb(255,255,255)`); sidebar
auto-collapsed on load; all card rows equal-height and bottom-aligned
(≤2px); 19 catalog cards with real buttons (4 URL cards open new tabs);
back navigation; **0 console errors**.
- Test suite: **1228 pytest passed** (`rta/tests/` = 887; evidence manifest
regenerated to 887 — the stable truth — and all doc surfaces quoting the
count synced).
- Deterministic engine untouched: rule IDs, severities, parser, coverage,
clock, readiness and diff semantics unchanged (functional baseline frozen).
