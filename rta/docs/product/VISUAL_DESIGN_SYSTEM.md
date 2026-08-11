# Ṛta — Visual Design System

**Premium Visual Design System · v1.0 (design specification only — no implementation)**
**Date:** 2026-08-06 · **Baseline:** Ṛta v1.3.0 · **Source of truth:** `docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md`

> This document defines the visual language of the Ṛta product
> experience. It is a **design specification**: no CSS, Streamlit, backend,
> validation, or benchmark code is changed by this document. A frontend
> engineer must be able to implement the P0 experience from this document +
> `HIGH_FIDELITY_PRODUCT_SPEC.md` without inventing hierarchy, color,
> typography, spacing, components, or states.

---

## 1. Design Vision

The Ṛta looks like a **precision engineering instrument for
constraint quality** — the product an EDA methodology team builds internally
and then decides is good enough to ship to the industry.

Three reference cultures, in priority order:

1. **Semiconductor engineering** — netlist topology, clock trees, timing edges, silicon grid geometry.
2. **Developer infrastructure** — static analysis tooling, observability platforms, technical observability (Grafana/Sentry/Vercel-caliber restraint).
3. **Premium technical product design** — precise typography, controlled motion, credible evidence presentation.

The product must feel **deterministic**: structured, grid-based, reproducible.
Nothing in the interface suggests randomness, particles, gradients-for-its-own-sake, or "AI magic."

**One sentence:** *An engineering instrument, not a marketing dashboard.*

---

## 2. Design Principles

1. **ENGINEERING FIRST** — Every visual element must improve comprehension or product identity. If it does neither, remove it.
2. **EVIDENCE OVER HYPE** — Verified engineering evidence receives stronger visual weight than adjectives. A benchmark count outranks a hero slogan.
3. **PROGRESSIVE TECHNICAL DEPTH** — Summary → evidence → source/provenance. Three levels, always one click apart.
4. **DETERMINISTIC VISUAL LANGUAGE** — Structure is grid-based, alignment is strict, repetition is a feature. The interface must look reproducible.
5. **STATUS NEVER DEPENDS ONLY ON COLOR** — Every state carries icon + label (+ shape/pattern). Color is a reinforcement, never the sole carrier.
6. **DENSE DOES NOT MEAN CLUTTERED** — Engineering data is dense by nature; density is managed with hierarchy, alignment, and whitespace rhythm — not by thinning the data.
7. **MOTION EXPLAINS SYSTEM BEHAVIOR** — Animation shows pipeline flow, hierarchy resolution, state transitions. It never decorates.
8. **TRUST BOUNDARIES ARE PRODUCT FEATURES** — "What we did not check" is presented as prominently as "what we found."
9. **WORKSPACE AND MARKETING SURFACES HAVE DIFFERENT DENSITIES** — The workspace is dense and task-focused; the product site breathes. Same language, different density.
10. **SOURCE PROVENANCE IS ALWAYS ONE CLICK AWAY** — Every finding, benchmark, and status links to its evidence/provenance.

---

## 3. Current UI Audit (from repository inspection)

| Area | Current state | Verdict |
|---|---|---|
| Navigation | 10 horizontal tabs (Checker, Generator, Linter, Converter, Corner Mgr, MMC SDC, Diff, Clock, Coverage, Rules) + sidebar views (Test Drive, Feedback) | **Overloaded.** 10 tabs at once; no grouping; readiness/diff buried inside Checker |
| Theme | Inter via Google Fonts import; light-first with `[data-theme="dark"]` override block; gradient header (slate→blue), rounded cards, emoji icons | **Functionally strong, visually generic.** Gradients + emoji + shadow lifts read as a starter dashboard |
| Cards | `.metric-card` with gradient accent strips, hover lift, emoji icons | **Keep the metric concept; restyle.** Too much gradient; emoji in metrics |
| Tables | Native Streamlit tables / expander lists | **Rebuild as dense technical tables** with sticky headers and mono data cells |
| Findings | `.issue-card` expanders with left severity border, emoji icon, mono code | **Good base; elevate.** Border-left + emoji → formal status system with shape + icon |
| Readiness | Metric columns inside Checker expander; overall badge | **Under-visible for a flagship capability.** Needs dedicated workspace page |
| Coverage | Metric columns + port list | **Under-visible.** Needs bus visualization |
| Clock relations | Report has a matrix; workspace tab shows expander summary | **Matrix is strong; bring it into the workspace** |
| Diff | CLI/report have readiness diff; workspace has baseline expander inside Checker | **Needs dedicated diff workspace** |
| Empty states | `st.info("Upload a file...")` | **Basic.** Need designed technical empty states |
| Error states | `st.error` / `st.warning` native | **Functional, generic.** Need typed error states (input vs unsupported vs engine) |
| Dark mode | CSS override block via `data-theme` selector | **Solid mechanism; incomplete coverage.** Some components lack dark variants |
| Typography | Inter UI + Fira Code/Cascadia mono | **Good direction; formalize.** Mono used inconsistently |
| Density | Wide layout, expander-heavy | **Good for scanning; weak for professional density** |

**Preserve (working UX):** metric cards concept, severity color semantics, expander-driven progressive disclosure, dual-line provenance (Lx ↔ Ly), download flows, rule-reference search, test-drive "expect this sample to fail" transparency, feedback widget.

**Fix:** 10-tab overload, emoji-as-icon, gradient-overuse, missing status shapes, hidden flagship capabilities, generic empty/error states.

---

## 4. Three Visual Directions

### Direction A — SILICON GRAPH
- **Philosophy:** The interface is a netlist. Content is nodes; structure is routing; transitions are paths.
- **Visual characteristics:** hairline grid backgrounds; node/edge primitives (ports, cells, constraint links); orthogonal routing aesthetics; precise corners; technical mono accents.
- **Typography:** Inter tight tracking for UI; JetBrains Mono for code/identifiers/metrics.
- **Background:** subtle routing-grid; slow constraint-path movement in hero only.
- **Geometry:** square-ish (radius 2–6px), orthogonal lines, bus-style connector bars.
- **Motion:** path-flow reveals, node resolution, clock-edge pulses.
- **Strengths:** unmistakably EDA; highly original; supports clock tree + coverage + diff visualizations naturally.
- **Risks:** can feel cold; easy to overcomplicate with graph decoration.
- **Suitability:** Excellent for identity + data viz; needs restraint discipline.

### Direction B — TIMING INTELLIGENCE
- **Philosophy:** The interface is an oscilloscope/analyzer. Waveform edges, clock edges, constraint relationships, analysis states.
- **Visual characteristics:** edge lines, rise/fall markers, waveform bands, time-axis metaphors; status as signal states.
- **Typography:** technical sans + mono; waveform annotations.
- **Background:** faint timing-grid; edge-pulse accents.
- **Geometry:** rounded-but-controlled; waveform curves used sparingly.
- **Motion:** edge transitions, hold/setup-style pulses.
- **Strengths:** strong semantic link to clock/constraint analysis; distinctive.
- **Risks:** waveform motifs can become decorative; risk of implying timing analysis we do not perform.
- **Suitability:** Good for clock intelligence + diff; weaker as the whole-product identity.

### Direction C — PRECISION INFRASTRUCTURE
- **Philosophy:** The interface is a first-class developer/static-analysis tool (Grafana/Sentry/Vercel discipline). Neutral graphite, one restrained accent, world-class typography and tables.
- **Visual characteristics:** graphite surfaces; cyan/blue accent used sparingly; border-based hierarchy; dense data tables; quiet motion.
- **Typography:** Inter + JetBrains Mono; strict type scale.
- **Background:** flat or near-flat; very subtle grid.
- **Geometry:** mixed radii (2–8px), restrained.
- **Motion:** micro-interactions only.
- **Strengths:** premium feel guaranteed; fast to build; safe.
- **Risks:** less EDA-specific; could be mistaken for generic developer tooling.
- **Suitability:** Excellent execution baseline; lacks EDA identity on its own.

### Comparison

| Criterion | A SILICON GRAPH | B TIMING INTELLIGENCE | C PRECISION INFRASTRUCTURE |
|---|---|---|---|
| EDA identity | ★★★ | ★★☆ | ★☆☆ |
| Premium feel | ★★☆ | ★★☆ | ★★★ |
| Data-viz support | ★★★ | ★★☆ | ★★☆ |
| Implementation risk | Medium | Medium | Low |
| Differentiation | ★★★ | ★★☆ | ★☆☆ |

---

## 5. Selected Direction

**Primary: SILICON GRAPH**, executed with **PRECISION INFRASTRUCTURE restraint**.

- The **node–edge–bus visual grammar** (Direction A) is the identity layer: used in hero, platform diagram, clock hierarchy, coverage, diff, empty states, logo.
- The **execution discipline** (Direction C) is the engineering layer: graphite surfaces, one restrained accent, border-based hierarchy, dense tables, quiet motion.
- Direction B's **status/signal language** is absorbed as a *secondary* motif for clock and readiness states (edge markers), never implying timing propagation.

This is a genuinely different philosophy (not a color swap): the product *is* a graph of constraints, design objects, and evidence — and the UI renders that graph literally.

---

## 6. Brand Character

- **Descriptors:** precise · restrained · technical · credible · instrument-like · EDA-native · deterministic.
- **Non-descriptors:** playful · futuristic · glowing · fluffy · magical.
- **Voice:** the product speaks like a senior methodology engineer writing a design note — short, factual, confident, honest about limits.
- **Signature elements:** node/edge primitives, hairline borders, mono data, structured status markers, the constraint-pipeline motif (SDC → analysis → evidence → readiness → CI).

---

## 7. Color System

### Foundations (dark-first; see §8)

| Token | Value (dark) | Role |
|---|---|---|
| `BACKGROUND_PRIMARY` | `#0B0E14` | App/site background (near-black graphite) |
| `BACKGROUND_SECONDARY` | `#10141D` | Alternating bands, footer |
| `SURFACE` | `#141926` | Content surface (level 1) |
| `SURFACE_ELEVATED` | `#1A2130` | Panels, inspectors (level 2) |
| `SURFACE_OVERLAY` | `#202A3C` | Hover/selected, modal (level 3+) |
| `BORDER_SUBTLE` | `#232C3E` | Default hairlines |
| `BORDER_ACTIVE` | `#3B4A66` | Focus, active states |
| `TEXT_PRIMARY` | `#E6EAF2` | Primary text |
| `TEXT_SECONDARY` | `#A7B0C0` | Secondary text |
| `TEXT_MUTED` | `#68738A` | Captions, metadata |
| `ACCENT_PRIMARY` | `#38BDF8` (sky-400) | Primary interactive + brand accent |
| `ACCENT_SECONDARY` | `#60A5FA` (blue-400) | Secondary accent, links |
| `FOCUS` | `#38BDF8` | Focus ring (2px, 1 offset) |
| `SUCCESS` | `#34D399` | Verified/pass/resolved |
| `WARNING` | `#FBBF24` | Advisory/review |
| `ERROR` | `#F87171` | Definite problem |
| `INFO` | `#60A5FA` | Informational |
| `UNKNOWN` | `#94A3B8` | Unresolved/unknown |
| `NOT_APPLICABLE` | `#475569` | N/A (lowest emphasis) |
| `DIFF_NEW` | `#34D399` (emerald) | New finding/object |
| `DIFF_RESOLVED` | `#38BDF8` (sky) | Resolved finding |
| `DIFF_CHANGED` | `#FBBF24` (amber) | Changed finding |
| `DIFF_UNCHANGED` | `#64748B` (slate) | Unchanged (neutral) |

### Usage rules
- **Accent discipline:** `ACCENT_PRIMARY` is used for interactive elements, focus, and the brand mark — **not** for decoration. Never paint a full panel accent.
- **Semantic colors are data, not decoration:** success/warning/error/info appear only where a real status exists.
- **Text hierarchy:** primary > secondary > muted by weight and size, not just color.
- **Neon ban:** no pure `#00FFxx`-class colors. All accents are desaturated enough to be readable on graphite.
- **Glow:** reserved for focus ring and one hero element; everywhere else, borders + background contrast carry hierarchy.

### Light mode (P1+, deferred)
Documented but not built in P0: same hue families, elevated lightness — `BACKGROUND_PRIMARY #FAFBFC`, `SURFACE #FFFFFF`, `TEXT_PRIMARY #0F172A`, borders `#E2E8F0`, accent unchanged. Dark is the P0 identity (see §8).

---

## 8. Light / Dark Strategy

**Recommendation: dark-only for v1.3.0 beta (P0), light as a P1 option.**

Evidence:
- The product's identity (engineering instrument, EDA heritage, deterministic feel) reads strongest in dark.
- The current Streamlit app already has a dark-mode foundation (`[data-theme="dark"]` block) — dark-only removes the maintenance burden of dual themes in P0.
- Light mode doubles token/contrast testing and risks inconsistency across the two surfaces.
- Most serious EDA/technical tools default to dark.

**Decision:** P0 ships a **single, carefully tuned dark theme** on both the product site and the workspace. The design system defines light tokens (§7) so light mode can be added in P1 without rework, but it is explicitly **not** in P0 scope.

---

## 9. Typography System

| Role | Font | Size | Weight | Line height | Letter spacing | Usage |
|---|---|---|---|---|---|---|
| DISPLAY | Inter | 44–56px | 700–800 | 1.05 | −0.03em | Hero headline (product site) |
| H1 | Inter | 32–36px | 700 | 1.15 | −0.02em | Page title |
| H2 | Inter | 24–26px | 650 | 1.25 | −0.01em | Section title |
| H3 | Inter | 18–20px | 600 | 1.3 | 0 | Subsection |
| BODY | Inter | 15–16px | 400–500 | 1.55 | 0 | Paragraphs, workspace text |
| BODY_SMALL | Inter | 13–14px | 400–500 | 1.5 | 0 | Secondary copy |
| LABEL | Inter | 12px | 600 | 1.3 | +0.05em | Uppercase section labels |
| METRIC | JetBrains Mono | 24–32px | 700 | 1.1 | 0 | Big numbers (tab figures) |
| MONOSPACE | JetBrains Mono | 13px | 400–500 | 1.6 | 0 | SDC, identifiers, paths |
| CODE | JetBrains Mono | 13px | 400 | 1.6 | 0 | Code blocks |
| TABLE | Inter | 13px | 400–500 | 1.4 | 0 | Data tables |
| TABLE_MONO | JetBrains Mono | 12.5px | 400 | 1.4 | 0 | Rule IDs, line numbers, values in tables |
| CAPTION | Inter | 11–12px | 400–500 | 1.4 | +0.01em | Metadata, provenance |
| STATUS | Inter | 11–12px | 650 | 1.2 | +0.03em | Status badges (uppercase) |

**Fonts:** `Inter` (UI, variable, Google Fonts — already used) and `JetBrains Mono` (code/data, OFL — practical, technical, tabular figures). Both are web-available and license-practical.

**Usage rules:**
- Mono is used **selectively**: rule IDs (`SDC-069`), line numbers, object/clock names, SDC commands, metric values, baseline/current version labels. The interface is not a terminal — body text stays Inter.
- Numeric alignment: all tables and metrics use **tabular figures** (JetBrains Mono default; enable `font-variant-numeric: tabular-nums` for Inter numerals).
- Uppercase labels are limited to section labels and status badges.

---

## 10. Grid & Spacing System

- **Base unit:** 4px. All spacing is a multiple of 4.
- **Page margins (product site):** 24px mobile · 48px tablet · 80px desktop (1440 max content width 1200px).
- **Content max widths:** site prose 720px; site section grids 1200px; workspace fluid with 24px gutters.
- **Workspace gutters:** 24px between panels; 16px inside panels.
- **Card padding:** 16px (dense) / 20px (standard) / 24px (elevated).
- **Table density:** compact 28–32px row height (workspace), standard 40px (product site tables).
- **Section spacing:** 32px between sections (workspace), 64–96px (product site).
- **Navigation:** product header 64px; workspace sidebar 240px (collapsible to 64px icon rail); drawer 360px; finding inspector 400px.
- **Breakpoints:** 640px (mobile) · 1024px (tablet) · 1280px (laptop) · 1440px (desktop) · 1920px (large desktop).

---

## 11. Spacing Scale (tokens)

`SP-1 = 4` · `SP-2 = 8` · `SP-3 = 12` · `SP-4 = 16` · `SP-5 = 20` · `SP-6 = 24` · `SP-8 = 32` · `SP-10 = 40` · `SP-12 = 48` · `SP-16 = 64` · `SP-24 = 96` · `SP-32 = 128`.

Rules: 4/8 for intra-component gaps · 16/24 for component padding · 32/48/64 for section rhythm · 96/128 for hero/sectional spacing on the product site.

---

## 12. Surface System

| Level | Token | Use |
|---|---|---|
| 0 | `BACKGROUND_PRIMARY` | Page/app background |
| 1 | `SURFACE` | Standard content blocks, tables, cards |
| 2 | `SURFACE_ELEVATED` | Analysis panels, inspectors, drawers |
| 3 | `SURFACE_OVERLAY` | Hover, selected rows, floating menus |
| 4 | `SURFACE_OVERLAY` + border + shadow | Modal/command surface |

**Rule:** not everything is a floating card. Background contrast + hairline borders define most structure. Cards are used for grouped evidence; panels for analysis; tables sit directly on level-1.

---

## 13. Border & Depth System

- **Borders are the primary depth tool.** Default hairline `1px BORDER_SUBTLE`; active `1px BORDER_ACTIVE`; status borders use semantic color only on the leading edge (4px left rule for findings) — never a full colored border.
- **Shadows:** three levels only — `SHADOW_SM` (elevated controls), `SHADOW_MD` (drawers/inspectors), `SHADOW_LG` (modal). Shadows are 1–2 layers, low opacity, tight blur (see tokens §48).
- **Glow:** `GLOW_ACCENT` reserved for focus rings and a single hero element. Never on data.
- **Depth rules:** hierarchy comes from background contrast + borders first, shadow second, glow last.

---

## 14. Radius Strategy

Avoid the "everything is a giant rounded rectangle" AI-product look.

| Level | Value | Use |
|---|---|---|
| `RAD_SM` | 4px | Buttons, inputs, badges, table cells, chips |
| `RAD_MD` | 8px | Panels, cards, tables, code blocks |
| `RAD_LG` | 12px | Drawers, inspectors, modals, hero feature |
| `RAD_FULL` | 999px | Pills (status badges, tags) only |

Rules: controls 4px; panels 8px; hero feature may use 12px; nothing above 12px except pills.

---

## 15. Iconography

**Strategy: one stroke-based line-icon family, 1.5px stroke, 16/20/24px grid.** Product UI uses **no emoji**. (Emoji may remain in casual docs/samples only; the shipped UI and product site are emoji-free.)

Icon set (semantic, consistent):
- Capabilities: `validate` (check-shield), `clock` (clock-edge), `design` (hierarchy/node), `coverage` (bus/target), `interaction` (link), `readiness` (gauge-bars), `diff` (split/arrow), `report` (document), `ci` (pipeline), `trust` (boundary/shield), `benchmark` (measure/bars), `security` (lock), `performance` (timer).
- Severity/status: `error` (octagon + ✕), `warning` (triangle + !), `info` (circle + i), `success` (circle-check), `unsupported` (circle-slash), `netlist-required` (net-node), `tcl-exec` (terminal), `unknown` (question), `not-applicable` (dash).
- Diff: `new` (plus), `resolved` (check), `changed` (swap), `unchanged` (minus/equals).
- Actions: `run`, `download`, `copy`, `search`, `filter`, `expand`, `collapse`, `close`, `back`, `external`.

Every icon must exist in a **filled** variant for active states and an **outline** variant for default states. Icon + label pairs are used for all statuses (see §22–25).

---

## 16. Semiconductor Visual Language

Original primitives derived from EDA geometry — **not** circuit-board stock imagery:

| Primitive | Definition | Used in |
|---|---|---|
| NODE | Small square (4px) or circle with hairline ring; represents a clock/port/cell/finding | Clock tree, coverage, diff, findings, logo |
| ARC | Orthogonal connector (right-angle routed) linking nodes | Platform pipeline, hierarchy, hero |
| CLOCK EDGE | Vertical tick with rise/fall marker | Clock hierarchy, status markers, hero |
| BUS | Parallel hairline bundle (3–4 lines) representing a bus | Coverage visualization, hero |
| PORT | Open square on a node boundary | Design context, coverage |
| CELL | Rounded-square node with label | Hierarchy, coverage |
| CONSTRAINT LINK | Dashed orthogonal connector with direction arrow | Interactions, diff |
| ANALYSIS PULSE | Short bright dot traveling along an arc | Hero, pipeline, loading |
| STATUS MARKER | Small filled shape (square/triangle/circle/octagon) with icon | Every status badge |

**Rules:** primitives are hairline (1px), mono-labeled, orthogonal. They appear in hero animation, platform diagram, section separators, empty states, benchmark visuals, loading states. They never animate in data-dense surfaces.

---

## 17. Background System

- **Default:** flat `BACKGROUND_PRIMARY` with a **very subtle** grid (SVG pattern, 24px cells, 1px lines at 3–4% opacity).
- **Hero (product site only):** the SILICON GRAPH motif — a slow-moving constraint path (nodes + arcs) with occasional clock-edge pulses and a single analysis pulse traveling. Depth via opacity layers, not particles. 8–14 fps max, GPU-friendly (CSS transforms/opacity only).
- **Allowed animated backgrounds:** HOME hero · PLATFORM hero · (optionally) BENCHMARKS hero.
- **Prohibited animated backgrounds:** findings tables, coverage, readiness, diff, source viewers, all workspace analysis surfaces, docs.
- **Reduced motion:** grid stays, all movement stops (see §19).
- **Performance:** background must not animate the main thread; no canvas/WebGL in P0.

---

## 18. Motion System

| Category | Purpose | Duration | Easing | Prohibited when | Reduced-motion fallback |
|---|---|---|---|---|---|
| MICRO | Hover, focus, select, expand/collapse | 120–180ms | ease-out | — | Instant state change |
| NAVIGATION | Page/panel transition | 180–240ms | ease-out | — | Instant swap |
| DATA | Chart update, readiness transition, diff change | 240–400ms | cubic-bezier(0.2,0,0,1) | When data changes faster than 400ms (batch updates are instant) | Instant final state |
| EXPLANATORY | Pipeline flow, clock hierarchy reveal, constraint flow | 400–900ms staged | ease-in-out | Data surfaces | Static diagram, labels |
| AMBIENT | Hero background only | 6–20s loops | linear | Everything except hero | Static hero art |

**Philosophy:** motion communicates *what happened* (a node resolved, a status changed, a path flowed). It never delays comprehension. All transitions are < 1s; no cinematic sequences anywhere in the workspace. `prefers-reduced-motion` → all animations become instant state swaps.

---

## 19. Navigation System

### Product navigation (top header)
`Platform · Capabilities · Benchmarks · Trust · Docs · Releases` + `Launch Validator` (primary CTA). Compact on scroll (64→48px). Active state = accent underline + label weight.

### Workspace navigation (left sidebar, grouped)
Derived from the approved architecture (§40 of the architecture doc):

```
ANALYZE     Overview · Validator · Clocks
DESIGN      Context · Coverage
QUALITY     Interactions · Readiness
CHANGE      Diff
OUTPUT      Reports · CI / Policies
```

Collapsible to a 64px icon rail. Section headers are uppercase 11px labels. Active item = `SURFACE_OVERLAY` + accent left rule + icon fill. A footer shows version + trust status chip.

---

## 20. Workspace Shell

```
┌──────────────────────────────────────────────────────────────┐
│ SIDEBAR (240px) │ ANALYSIS HEADER (context)                  │
│ ANALYZE         ├────────────────────────────────────────────┤
│  ▸ Overview     │ MAIN WORKSPACE                             │
│  ▸ Validator    │                                            │
│  ▸ Clocks       │                          ┌───────────────┐ │
│ DESIGN          │                          │ INSPECTOR     │ │
│  ▸ Context      │                          │ (contextual,  │ │
│  ▸ Coverage     │                          │ 400px)        │ │
│ QUALITY         │                          │               │ │
│  ▸ Interactions │                          │               │ │
│  ▸ Readiness    │                          └───────────────┘ │
│ CHANGE          │                                            │
│  ▸ Diff         │                                            │
│ OUTPUT          │                                            │
│  ▸ Reports      │                                            │
│  ▸ CI / Policies│                                            │
│ ─────────────── │                                            │
│ v1.3.0 · Trust  │                                            │
└─────────────────┴────────────────────────────────────────────┘
```

Elements:
- **Sidebar:** grouped nav (above), version + trust chip footer.
- **Analysis header:** design/top, SDC filename, netlist status, analysis mode, trust, readiness chip, timestamp (see spec §20).
- **Center:** primary surface (dense).
- **Right inspector:** contextual finding/clock/object detail; opens on selection, closes with ✕ or Esc; 400px.
- **Status area:** only when an analysis is running (stage list) — otherwise no persistent footer bar.

---

## 21. Status System (universal)

Every status = **icon + label + color + shape**. No color-only signaling.

| Status | Icon | Label | Color | Shape |
|---|---|---|---|---|
| ERROR | octagon ✕ | ERROR | `ERROR` | filled octagon |
| WARNING | triangle ! | WARNING | `WARNING` | filled triangle |
| INFO | circle i | INFO | `INFO` | filled circle |
| SUCCESS / PASS | circle check | PASS | `SUCCESS` | filled circle-check |
| FAIL | octagon ✕ | FAIL | `ERROR` | filled octagon |
| UNKNOWN | question | UNKNOWN | `UNKNOWN` | hollow circle |
| NOT_APPLICABLE | dash | N/A | `NOT_APPLICABLE` | hollow square |
| READY | shield check | READY | `SUCCESS` | shield |
| READY_WITH_ADVISORIES | shield + dot | READY+ | `SUCCESS` | shield + small dot |
| REVIEW_REQUIRED | triangle ! | REVIEW | `WARNING` | triangle |
| BLOCKED | octagon ✕ | BLOCKED | `ERROR` | octagon |
| INSUFFICIENT_CONTEXT | question shield | LIMITED | `UNKNOWN` | hollow shield |
| VALIDATED | solid node | VALIDATED | `SUCCESS` | filled square |
| PARTIALLY_VALIDATED | half node | PARTIAL | `WARNING` | half-filled square |
| NETLIST_REQUIRED | net node | NETLIST | `INFO` | square + net tick |
| TCL_EXECUTION_REQUIRED | terminal | TCL | `UNKNOWN` | square + terminal |
| UNSUPPORTED | circle slash | UNSUPPORTED | `ERROR` | slash circle |
| NOT_VALIDATED | hollow node | NOT CHECKED | `UNKNOWN` | hollow square |
| NEW | plus | NEW | `DIFF_NEW` | plus-in-diamond |
| RESOLVED | check | RESOLVED | `DIFF_RESOLVED` | check-in-circle |
| CHANGED | swap | CHANGED | `DIFF_CHANGED` | swap arrows |
| UNCHANGED | equals | UNCHANGED | `DIFF_UNCHANGED` | equals |

---

## 22. Severity System

Severity is a **status** (above): `FATAL > ERROR > WARNING > INFO`.
- FATAL: filled double-octagon + "FATAL" (used by CHG-* content-diff findings).
- ERROR: octagon ✕.
- WARNING: triangle !.
- INFO: circle i.
- Rendered in tables as: icon + short label; color reinforces only. Row tinting uses a **left rule** (4px), never a full colored row background (except a very subtle tint ≤8% for ERROR).

---

## 23. Trust Status System

Trust statuses use the universal system: `VALIDATED` (filled square) · `PARTIALLY_VALIDATED` (half square) · `NETLIST_REQUIRED` (square + net tick) · `TCL_EXECUTION_REQUIRED` (square + terminal) · `UNSUPPORTED` (slash circle) · `NOT_VALIDATED` (hollow square). Presented as a compact **trust strip** in the analysis header and a full trust panel in the Trust Center. Each maps to `support_boundary.py` semantics exactly (see architecture §33).

---

## 24. Diff Status System

Diff statuses use the universal system: `NEW` (plus-diamond, emerald) · `RESOLVED` (check-circle, sky) · `CHANGED` (swap, amber) · `UNCHANGED` (equals, slate). In tables these appear as leading chips + row markers; never red/green alone. Debt panel uses the same markers (existing/new/resolved debt).

---

## 25. Component Library

Implementation-ready inventory (density + states + a11y per component are specified in the component spec file; here: purpose, variants, where used):

| Component | Purpose | Variants | Used in |
|---|---|---|---|
| Button | Primary action | Primary / Secondary / Ghost / Danger / Icon | Everywhere |
| Icon Button | Compact action | Ghost / Filled | Tables, headers, inspectors |
| Navigation Item | Sidebar/header nav | Default / Active / Disabled | Sidebar, header |
| Breadcrumb | Location | — | Docs, workspace pages |
| Tabs | Coarse view switch | Underline / Segmented | Workspace pages |
| Segmented Filter | Mutual-exclusive filter | — | Findings, diff |
| Search Field | Text search | — | Findings, rules |
| File Upload | SDC/Verilog/baseline/policy | Dropzone / click | Validator |
| Select | Single choice | — | Filters, top module |
| Checkbox | Toggle option | — | Filters |
| Badge | Short metadata | Neutral / Accent | Tables, headers |
| Status Badge | Status (universal system) | 20+ states | Everywhere |
| Metric | Big number | Plain / Colored | Overview, summary |
| Evidence Metric | Metric + source link + methodology | — | Benchmarks, readiness |
| Card | Grouped content | Default / Clickable | Product site, overview |
| Technical Panel | Analysis block | — | Workspace |
| Callout | Inline note | Info / Warning / Error / Success | Workspace, docs |
| Trust Callout | "We did NOT check X" | — | Every analysis surface |
| Table | Data table | Default / Dense | Everywhere |
| Dense Data Table | Compact, sticky header | — | Findings, coverage, clocks |
| Tree | Hierarchy | — | Clock hierarchy, design context |
| Relationship Matrix | Pairwise matrix | — | Clock relations |
| Source Viewer | SDC with line numbers | — | Validator, findings |
| Finding Row | Table row for a finding | Default / Selected | Findings explorer |
| Finding Inspector | Right-panel detail | — | Findings, clocks |
| Readiness Dimension | Dimension status block | — | Readiness page |
| Coverage Bar | Status proportions | — | Coverage |
| Bus Coverage | Per-bit bus visualization | — | Coverage |
| Clock Node | Node primitive | Primary / Generated / Virtual | Clock hierarchy |
| Clock Edge | Edge connector | — | Clock hierarchy |
| Benchmark Card | Evidence summary | — | Benchmarks |
| Benchmark Methodology Drawer | Expandable methodology | — | Benchmarks |
| Diff Marker | Change chip | NEW/RESOLVED/CHANGED/UNCHANGED | Diff |
| Policy Card | Gate/policy explainer | — | CI / Policies |
| Empty State | No-content guidance | Per-type | All |
| Error State | Typed failure | Per-type | All |
| Loading State | Analysis stages | Indeterminate | Validator, analysis |
| Tooltip | Short help | — | Labels, icons |
| Drawer | Context panel | — | Methodology, settings |
| Modal | Focused confirm | — | Only when justified (e.g., baseline overwrite confirm) |
| Toast | Transient confirmation | — | Actions (download, copy) |
| Code Block | SDC/JSON display | — | Source, reports |
| Command Block | CLI snippet + copy | — | CI / Policies, docs |
| Report Artifact | Download card | HTML / JSON / Snapshot / Baseline | Reports |

---

## 26. Component States

Every interactive component defines: **default · hover · focus · active/selected · disabled · loading (where applicable) · error (inputs)**.
- **Focus:** 2px `FOCUS` ring with 2px offset — always visible (keyboard + mouse).
- **Hover:** `SURFACE_OVERLAY` background + 1px border lighten; never a full re-layout (no size jumps).
- **Selected:** accent left rule (nav), accent border (tabs/filters), filled icon + label weight change.
- **Disabled:** 40% opacity, no pointer events, no hover.
- **Error (input):** 1px `ERROR` border + icon + message; never red text only.

---

## 27. Data Table System

- **Structure:** sticky header; column alignment — text left, numbers/mono right, statuses left with fixed width; row hover `SURFACE_OVERLAY`; selected row accent left rule; zebra off (borders do the work); column resizing P1+.
- **Density:** workspace compact 28–32px rows; product site 40px rows.
- **Sorting:** clickable headers with arrow indicator; stable secondary sort by rule ID.
- **Overflow:** horizontal scroll for wide tables (matrix, coverage) with sticky first column where meaningful.
- **Empty table:** designed empty state (see spec §36), not a bare "no data."
- **Semantics:** proper `<th>` scope, caption, and summary for screen readers.

---

## 28. Source / Code System

- **Code blocks:** `CODE` mono 13px, `SURFACE` background, `BORDER_SUBTLE`, 8px radius, horizontal scroll, line numbers in `TEXT_MUTED` 40px gutter.
- **SDC syntax awareness (P1):** comments muted, commands accent-2, options `TEXT_SECONDARY`, values mono default. Implemented as lightweight token styling, not a full language server.
- **Finding highlight:** error findings get left rule + subtle red tint on the source line; dual-line provenance draws a dashed connector between Lx and Ly with both rows tinted.
- **Copy:** a copy icon button in the code block header; toast "Copied."
- **Jump:** next/previous finding buttons in source viewer header.

---

## 29. Data Visualization System

Principles: data-ink first; no 3D; no pie charts for engineering data; axes labeled with units; mono numeric ticks; every chart has a textual equivalent (table or description) for a11y.

Chart types allowed:
- **Bar** (coverage proportions, benchmark counts)
- **Line** (performance scaling — input size vs runtime)
- **Matrix heatmap** (clock relationships) — but with **non-color encoding**: cells carry symbols (✓ / ✗ / ? / ~) + tooltip; color is reinforcement.
- **Node-edge graph** (clock hierarchy, constraint interactions)
- **Bus strip** (coverage per-bit)
- **Dimension rail** (readiness)

Chart rules: no glowing gradients; gridlines at 4% opacity; mono labels; title + source + environment caption on every benchmark chart.

---

## 30. Clock Graph Language

- **Primary clock node:** filled square, `ACCENT_SECONDARY`.
- **Generated clock node:** square outline with inner tick, `TEXT_SECONDARY`.
- **Virtual clock node:** circle outline.
- **Derived edge:** solid orthogonal arc (parent → generated).
- **Declared relationship:** solid labeled arc (e.g., `asynchronous`).
- **Inferred relationship:** dashed arc.
- **Unknown relationship:** dotted arc + `?`.
- **Warning/advisory marker:** amber triangle on the node.
- Node label: name (mono) + period underneath (mono, muted). Tooltip: full ClockDef fields.
- **Never implies propagation:** edges are labeled "derived/inferred," and a static caption reads "Structural relationships only — no timing propagation."

---

## 31. Coverage Visualization

- **Bus strip:** `data_in[31:0]` rendered as a horizontal strip of per-bit cells. Constrained bits filled `SUCCESS`; partial/unconstrained `WARNING`; unconstrained `ERROR`; exempt hatched; unknown stippled; N/A muted. Hover/click a bit → the covering constraint evidence (line, rule).
- **Summary:** direction bars (inputs/outputs) with constrained/partial/unconstrained/exempt/unknown segments, plus legend. Percentage only as a *secondary* annotation, with the caption "Coverage is not correctness."
- **Never a single ring gauge.** No "100% ready" implication.

---

## 32. Readiness Visualization

The **signature** component — a structured **dimension rail** (not a gauge):

```
READINESS  ┌────────────────────────────────────────┐
REVIEW_REQUIRED │  R E V I E W   R E Q U I R E D     │  (status badge)
               └────────────────────────────────────────┘
 DIMENSION STACK (7 rows, each clickable)
 CLOCKS          [▮▮▮▮▮▮▯▯▯▯]  READY
 I/O             [▮▮▮▯▯▯▯▯▯▯]  REVIEW_REQUIRED   ← selected
 EXCEPTIONS      [▮▮▮▮▮▮▮▮▯▯]  READY_WITH_ADVISORIES
 COVERAGE        [▮▮▮▮▮▮▮▮▮▯]  READY
 CONSISTENCY     [▯▯▯▯▯▯▯▯▯▯]  BLOCKED
 ANALYSIS_TRUST  [▮▮▮▮▯▯▯▯▯▯]  REVIEW_REQUIRED
 DESIGN_CONTEXT  [▮▮▮▮▮▯▯▯▯▯]  LIMITED
```

- Overall status = badge + label (universal system), with mode disclosure ("SDC only" / "Design-aware") beside it.
- Each dimension row: status marker + label + mini rail + status; click → evidence panel (which findings caused it).
- Below: BLOCKERS / REVIEW / ADVISORIES sections, then recommended actions (P0–P3), then the trust callout: **"This is a constraint-readiness review, not STA signoff."**
- No numeric score (none exists). No speedometer.

---

## 33. Diff Visualization

- **Header:** `BASELINE [READY] → CURRENT [BLOCKED]` with a large transition marker (arrow) and classification badge (`BLOCKING_REGRESSION` etc.) + gate result.
- **Change markers:** NEW (emerald plus-diamond) / RESOLVED (sky check-circle) / CHANGED (amber swap) / UNCHANGED (slate equals) — as leading chips.
- **Debt panel:** three columns — existing / new / resolved — each with blocker·review·advisory counts and the same markers.
- **Coverage delta:** list of newly unconstrained objects with bus strips.
- **Trust delta:** VALIDATED → PARTIAL transitions rendered as small status chips with arrows.
- **Rows:** finding code (mono), change marker, object/clock (mono), message, line provenance.
- **Non-color encoding:** every row also carries the shape icon; filters via segmented control (All / New / Resolved / Changed / Unchanged).

---

## 34. Benchmark Visualization

- **Scorecard** (not a ring): 
```
┌────────────────────────────────────────────┐
│ PARSER GOLDEN          [ PASS ]  (badge)   │
│  22 / 22  cases match expected behavior    │
│  Scope: SDC/Tcl parsing semantics          │
│  Version: v1.3.0 · Python 3.10 · Windows   │
│  [ Methodology ]  [ Artifact ]             │
└────────────────────────────────────────────┘
```
- **Rules:** no accuracy-percentages unless the benchmark semantics justify them; pass counts are shown as `n / n` not as misleading percentages; environment always shown for performance; internal suites labeled "Verified Test Evidence / Internal Release Benchmark" — never "industry benchmark."
- **Performance charts:** only from measured data (`test_readiness_diff_perf.py` etc.); axes labeled (findings count, ms); environment caption mandatory.

---

## 35. Tooltip / Help System

Three explanation levels, never cluttering the main UI:
1. **SHORT TOOLTIP** (150ms delay, 250ms max display): one line — label definitions, icon meanings.
2. **CONTEXT HELP** (clickable ⓘ in panel headers): 2–4 lines explaining the panel + link to docs.
3. **FULL DOCUMENTATION** (docs link): deep explanation, rules, examples.

Rules: tooltips never block interaction; all keyboard-triggerable; no tooltip-only meaning (every critical state has a visible label).

---

## 36. Empty States

Designed technical empty states (primitive-based illustration, mono caption, one clear next action). Each answers *what this means* + *what to do next*:

- **No analysis:** NODE diagram with "No analysis yet — load an SDC to begin." + [Load SDC] + sample links.
- **No SDC:** PORT primitive + "Upload or paste an SDC file." + [Choose file] [Use sample].
- **No netlist:** NET node + "Design context not supplied — object references will be marked netlist-required. Optional." + [Add netlist] [Continue SDC-only].
- **No findings:** shield check + "No issues found within scope. See Analysis Scope for what was verified." + [View scope].
- **No coverage:** bus strip empty + "Coverage requires design context (netlist)." + [Add netlist].
- **No interactions:** CONSTRAINT LINK dashed + "No duplicates, overrides, or conflicts detected."
- **No baseline:** SNAPSHOT node + "Save a baseline to enable regression diff and CI gates." + [Save baseline].
- **No diff:** split arrow + "Load a baseline snapshot to compare." + [Load baseline].
- **No policy:** CI node + "Choose a built-in gate or define a CUSTOM policy." + [Choose policy].

---

## 37. Error States

Typed, not generic red alerts:

| Type | Visual | Message pattern |
|---|---|---|
| INVALID INPUT | ERROR badge + field-level ring | "design.sdc could not be parsed: line 12 — unexpected token" |
| UNSUPPORTED ANALYSIS | UNSUPPORTED badge | "Construct 'create_generated_clock -edge_shift' is outside the supported scope — see support matrix" |
| INSUFFICIENT CONTEXT | NETLIST badge | "get_ports refs cannot be verified without a netlist" |
| INCOMPATIBLE BASELINE | UNKNOWN badge | "Baseline schema v0 is not comparable — baseline review required" |
| ENGINE FAILURE | ERROR badge + run-id | "Analysis failed (SDC-140) — results are not a PASS" |
| FILE FAILURE | ERROR badge | "Cannot read file: ..." |
| POLICY ERROR | ERROR badge | "Policy invalid: unknown field 'fail_on_nothing'" |

Never tracebacks in the UI. Every error state links to relevant docs/help.

---

## 38. Loading / Analysis State

The validator is deterministic — progress is **stage-based, honest**:

```
Analyzing design.sdc
  ✓ Parsing constraints          (instant)
  ✓ Analyzing clocks
  ⟳ Resolving design context     (only when netlist supplied)
  → Evaluating coverage
  → Analyzing interactions
  → Assessing readiness
  → Preparing result
```
- Stages are labeled and shown in order; completed stages get check icons; current stage gets a pulse (CLOCK EDGE primitive). **No fake percentages** — backend does not provide progress numbers.
- If a stage is skipped (e.g., no netlist → no design context), it is shown struck-through with "skipped."
- Reduced motion: pulse becomes a static highlight.

---

## 39. Documentation Visual System

- **Layout:** left nav (240px) · main content (max 720px prose, up to 1200px for tables) · right TOC on wide screens.
- **Same visual family:** graphite background, hairline borders, mono for code/rule IDs, status callouts reuse the universal system.
- **Trust callouts:** a distinct callout style with the boundary icon — used wherever a doc makes a claim the validator cannot fully prove.
- **Code blocks:** copy button, mono, dark surface.
- **Rule references:** inline rule chips (mono, clickable to rule page).
- **Prev/next navigation** at page bottom; search (P1).

---

## 40. Copy Style

**Tone:** technical · confident · precise · restrained · transparent.

- **Good headline:** "Deterministic SDC validation before STA."
- **Bad headline:** "Revolutionize your timing workflows with AI-powered constraint intelligence."
- **Good benchmark claim:** "Parser golden: 22/22 cases match expected behavior (v1.3.0, Python 3.10)."
- **Bad benchmark claim:** "Industry-leading 100% parsing accuracy."
- **Good trust disclosure:** "This result is not an STA timing signoff — the validator does not compute slack or propagate timing."
- **Bad trust disclosure:** "Signoff-ready SDC verification."

**Banned words:** revolutionary · game-changing · AI-powered · industry-leading · unmatched · perfect · 100% accurate · signoff-ready · magic · blazing.

---

## 41. Logo Direction

Three conceptual directions (final logo is a later stage):

1. **CONSTRAINT BRACKET** — two opposing brackets forming a node: `[ ]` enclosing a small clock edge. Suggests SDC syntax + constraints.
2. **CLOCK EDGE / TIMING ARC** — a single rising clock edge with a node at the corner; suggests determinism and analysis.
3. **SILICON TOPOLOGY** — a 3-node orthogonal graph (ports → cell → constraint link) in a square. Suggests netlist/design context.

**Recommendation: direction 1 (CONSTRAINT BRACKET)** — the most distinctive, echoes the SDC grammar, works at small sizes, and avoids generic chip/robot/bolt clichés. Wordmark: "Ṛta" in Inter 700 with a mono "SDC" lockup option.

---

## 42. Accessibility

- **Contrast:** all text ≥ WCAG AA on their surfaces (verify: TEXT_MUTED on BACKGROUND at 4.5:1; body 7:1 target). Semantic colors checked against both backgrounds they appear on.
- **Keyboard:** full tab order, visible 2px focus ring everywhere, Esc closes drawers/modals, arrow keys in tables/matrices, `/` focuses search.
- **Semantics:** real headings (`h1`→`h6` order), `<th scope>`, table captions, `aria-label` on icon buttons, `role="status"` for toasts.
- **Non-color status:** universal icon+label+shape system (§21).
- **Reduced motion:** `prefers-reduced-motion` honored everywhere.
- **Touch targets:** ≥ 40px for interactive elements.
- **Text scaling:** layout must survive 200% zoom without data loss.

---

## 43. Responsive Rules

- **Product site:** fluid — mobile (stack, hamburger nav), tablet (2-col grids), desktop (full). Polished at all three.
- **Workspace:** desktop-first. Tablet (1024px): sidebar collapses to icon rail; inspector becomes an overlay drawer; matrices scroll horizontally. Mobile (<640px): read-only summary mode — analysis summary, readiness status, findings list (no matrices, no inspector); a "open on desktop for full analysis" note.
- **Matrix/tree fallback on small screens:** horizontal scroll with sticky first column; never squish.

---

## 44. Performance Design Budget

| Asset/behavior | Budget |
|---|---|
| Initial load (product site) | < 1.5s on 4G; no render-blocking JS beyond fonts |
| Initial load (workspace) | Streamlit baseline + ≤ 50KB CSS |
| Fonts | Inter variable + JetBrains Mono (subset to used glyphs) |
| Hero animation | ≤ 2 animated layers, CSS transforms/opacity only, ≤ 14fps, pause on `document.hidden` |
| Charts | SVG (not WebGL) in P0; ≤ 1000 DOM nodes per chart |
| Page transitions | No full-page animation; content swap + 200ms fade |
| Background grid | Single SVG data-URI pattern, GPU-cached |
| Data tables | Virtualized beyond 500 rows (P1) |

**Rule:** premium must never cost responsiveness. If an effect costs frames in the workspace, it is removed.

---

## 45. Streamlit Constraints

What the workspace can/can't do in Streamlit (per approved architecture §63 — Streamlit stays for the workspace):

| Requirement | Streamlit capability | Plan |
|---|---|---|
| CSS theme | `unsafe_allow_html` + `<style>` | Full token-driven CSS injected once |
| Layout | `st.columns`, `st.container`, sidebar | Shell via columns + containers |
| Navigation | view state (`st.session_state`) + sidebar buttons/radio | Grouped sidebar nav mapping to view states |
| Dense tables | `st.dataframe` / HTML tables | Custom HTML dense tables (styling control) |
| Status badges/markers | HTML/CSS | Custom HTML components |
| Relationship matrix | HTML table | Custom HTML matrix (existing report pattern) |
| Clock tree / node-edge | Not native | Custom SVG via `st.markdown` (inline SVG) — feasible for ≤100 nodes |
| Bus coverage strip | Not native | Custom HTML/CSS strip |
| Inspector drawer | Not native | `st.container` + columns simulating a right rail; or `st.popover`/expander |
| Source viewer | Not native | Custom HTML with line numbers + highlights |
| Animation | Not native | CSS transitions only; no JS |
| Modal | `st.dialog` (recent versions) | Use for confirmations |

**Feasibility verdict:** the P0 workspace (Overview, Validator, Clocks, Coverage, Readiness, Diff) is **fully achievable in Streamlit** with custom HTML/CSS components, provided we accept: no JS-driven animation, no true virtualization, inspector as an in-page rail rather than a floating panel. Anything requiring JS interactivity (drag-graph, smooth animations) is deferred or belongs to the product frontend.

---

## 46. Product Frontend Constraints

- The **product site** (Home, Platform, Capabilities, Benchmarks, Trust, Docs, Release) is a separate lightweight frontend (static/SSG recommended — e.g., plain HTML/CSS + markdown content, or a minimal static generator; **no framework mandated**).
- It must: be fast, SEO-friendly, responsive, and read content from the same sources (rules registry, support matrix, release manifest — see architecture §65). No app server for marketing pages.
- Animation allowed only in the 3 hero contexts (§17). Charts as static SVG generated from benchmark data.

---

## 47. Design Tokens (proposed)

```yaml
# Color — dark (P0)
color:
  background_primary: "#0B0E14"
  background_secondary: "#10141D"
  surface: "#141926"
  surface_elevated: "#1A2130"
  surface_overlay: "#202A3C"
  border_subtle: "#232C3E"
  border_active: "#3B4A66"
  text_primary: "#E6EAF2"
  text_secondary: "#A7B0C0"
  text_muted: "#68738A"
  accent_primary: "#38BDF8"
  accent_secondary: "#60A5FA"
  success: "#34D399"
  warning: "#FBBF24"
  error: "#F87171"
  info: "#60A5FA"
  unknown: "#94A3B8"
  not_applicable: "#475569"
  focus: "#38BDF8"
  diff_new: "#34D399"
  diff_resolved: "#38BDF8"
  diff_changed: "#FBBF24"
  diff_unchanged: "#64748B"

# Typography
type:
  ui: "Inter"
  mono: "JetBrains Mono"
  scale: { display: 48, h1: 34, h2: 25, h3: 19, body: 15.5, body_small: 13.5,
           label: 12, metric: 28, mono: 13, code: 13, table: 13, table_mono: 12.5,
           caption: 11.5, status: 11.5 }

# Spacing (4px base)
spacing: { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48, 16: 64, 24: 96, 32: 128 }

# Radius
radius: { sm: 4, md: 8, lg: 12, full: 999 }

# Borders
border: { hairline: "1px solid #232C3E", active: "1px solid #3B4A66", status: "4px left rule" }

# Shadow
shadow:
  sm: "0 1px 2px rgba(0,0,0,.35)"
  md: "0 8px 24px rgba(0,0,0,.4)"
  lg: "0 16px 48px rgba(0,0,0,.5)"

# Motion
motion: { micro: 150ms, nav: 220ms, data: 300ms, explanatory: 600ms, ambient: "6-20s" }
easing: { standard: "cubic-bezier(.2,0,0,1)", out: "ease-out" }

# Z-index
z: { base: 0, sticky: 10, header: 20, drawer: 30, modal: 40, toast: 50 }

# Breakpoints
breakpoint: { sm: 640, md: 1024, lg: 1280, xl: 1440, xxl: 1920 }

# Table density
table: { compact_row: 30px, standard_row: 40px, gutter: 12px }

# Code
code: { bg: "#141926", fg: "#E6EAF2", gutter: "#68738A", radius: 8 }
```

---

## 48. Anti-Patterns

- Generic AI aesthetics: purple gradient backgrounds, glassmorphism panels, glow-on-everything, sparkle icons.
- Emoji as product icons in the UI (keep for sample labels only, replace everywhere else).
- Speedometer gauges, progress rings with fake precision, single-percentage readiness.
- Color-only status (every status needs icon + label + shape).
- Long cinematic transitions in the workspace.
- Full colored rows everywhere (use left rules + subtle tints).
- Anything implying timing propagation/signoff.
- Cards-for-everything layouts.
- Wall of benchmark numbers without methodology/artifacts.

---

## 49. Performance Design Budget (summary)

See §44. The hard rules: CSS/SVG only in P0; no WebGL; hero animation GPU-cheap and auto-pausing; charts < 1000 nodes; initial loads fast; reduced-motion honored.

---

## 50. Independent Review Findings

Independent design review executed after drafting. Findings and resolutions:

| Sev | Finding | Resolution |
|---|---|---|
| MEDIUM | The full-feature hero (animated constraint path) is described in the VDS; ensure it stays product-site-only and is static in the workspace | Confirmed: §17 restricts animated backgrounds to 3 hero contexts; workspace is flat |
| MEDIUM | Dark-only decision could alienate light-mode users and conflicts with the existing dual-theme Streamlit CSS | Kept dark-only for P0 with explicit light-token spec (§7) so P1 light is additive, not a redesign; documented tradeoff |
| LOW | JetBrains Mono adds a font dependency vs reusing Fira Code already in the repo | Adopted JetBrains Mono for the design system (better tabular figures + technical feel); Fira Code remains an acceptable fallback for the workspace in P0 to avoid double font loading |
| LOW | Matrix "heatmap" naming could imply color-only encoding | Renamed to "matrix" with mandatory non-color cell symbols (§29) |
| INFO | Component count (44) is large; risk of over-building | P0 uses a subset (~24 components); the rest are defined for P1+ and the product site |
| INFO | Streamlit SVG feasibility for clock trees needs an explicit node cap | Added ≤100-node cap with HTML-table fallback (§45) |

Reviewer also confirmed: no generic-AI aesthetics; no glassmorphism; restrained radius; motion is explanatory; benchmark language is honest; statuses are never color-only; dense tables are specified; the identity is recognizably EDA.

---

*End of Visual Design System. Design specification only — no production code was modified.*
