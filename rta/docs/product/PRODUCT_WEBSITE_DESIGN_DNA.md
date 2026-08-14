# Ṛta — Product Website Design DNA

> **Mandatory pre-implementation output** for the product-website stage.
> Reference study → synthesis → ONE design language. This document is the
> contract the website implementation must follow.
>
> References studied: **A** Synterium (semiconductor startup), **B** Muzli
> dark-mode collection, **C** Dribbble compliance dashboards, **D** Nucleus
> Cloud dark UI, **E** Ant Design application structure.
>
> Identity is ours: **Constraint Quality Intelligence and Pre-STA
> Validation** — silicon-graph / clock-edge / netlist-node grammar on a
> premium dark technical surface. Never STA, never AI, never generic SaaS.

---

## 1. Reference analysis

### REFERENCE A — Synterium (semiconductor product / startup structure)

| Dimension | What is useful | Where it appears in Ṛta |
|---|---|---|
| Structure | Hero → customers → features grid → stats band → solutions list → platform bullets → use-cases → CTA. One idea per section, full-width rhythm, generous vertical pacing | Home page section order; Platform page; Release page |
| Typography | Eyebrow micro-label above a large multi-line headline; tight tracking; short subhead; CTA pair (primary + secondary) | All marketing heroes (eyebrow "SDC VALIDATOR" / headline / subhead / Launch + Docs) |
| Formatting | Stats band with big tabular numerals ("2.5M+ / 15B / 99.8%") | Benchmarks release-evidence header (887 / 9 / 42 / 17 / 16 / 10) |
| Formatting | Feature grids → alternating full-width solution rows → platform bullet lists (rhythm variety, no repeated 3-card blocks) | Capabilities overview + platform pipeline |
| Credibility | Specs-style bullets, CTA near the end | Trust Center + release verification |
| **Reject** | Customer logos/testimonials, manufacturing claims (2.5M chips etc.), "revolutionize" language, AI-powered claims, exact copy/colors | — |

### REFERENCE B — Muzli dark-mode collection (premium dark visual language)

| Dimension | What is useful | Where it appears |
|---|---|---|
| Surfaces | Layered dark *ladder* (base `#0f172a`-class → elevated panels → highest flyouts) instead of pure black; depth via lightness steps, not shadows | Global product site + workspace surfaces (already the Phase 15/16 ladder) |
| Typography | Off-white primary text, medium/semibold optical bump, muted secondary tier; monospace reserved for identifiers/data | Display/body tokens + `JetBrains Mono` for SDC, rule IDs, metrics |
| Background | Matte base; very low-opacity tonal wash (≤3–5%) to anchor heroes; never particle fields or neon blobs | Home/Platform/Benchmarks hero backgrounds |
| Borders | Low-contrast structural borders (`border 1px rgba(148,163,184,.14)`); borders carry state (amber/rose tint for warnings) | Panels, tables, status surfaces |
| Accent | One restrained cool accent (steel/sky `#38bdf8`-family) + semantic emerald/amber/rose only for states | Already the Phase 15 accent system — extend to site |
| Motion | 100–150 ms, cubic-bezier, luminance-shift hovers — tool-like, not bouncy | All interactive elements |
| **Reject** | Gaming/crypto neon, generic AI particles, pure black, heavy shadows | — |

### REFERENCE C — Compliance / validation dashboards (workspace + data hierarchy)

| Dimension | What is useful | Where it appears |
|---|---|---|
| Status hierarchy | Validation status summaries, severity ladders, readiness/progress rails | Workspace Overview, Readiness rail, Findings explorer (already built) |
| Findings UX | Filter rows → dense table → detail inspector (drawer) without losing context | Findings explorer + inspector (Phase 15), reused as the pattern for Benchmarks drill-downs |
| Evidence | "What caused this" / audit-trail presentation | Finding detail provenance, Trust Center |
| **Translate** | Compliance finding→SDC finding · risk→readiness · evidence→provenance · control coverage→constraint coverage · audit compare→readiness diff | Everywhere |
| **Reject** | Financial branding, gauge dials, meaningless percentage rings | — |

### REFERENCE D — Nucleus Cloud dark UI (hero / atmospheric depth)

| Dimension | What is useful | Where it appears |
|---|---|---|
| Hero | Large atmospheric composition with clear foreground/background separation; restrained glow around one focal point | Home hero (SDC→clock→readiness animation), Platform hero, Benchmark hero, Trust hero |
| Depth | Background layers at different opacities; local illumination near interactive regions | Hero canvases; capability heroes |
| Balance | Typography-to-visual balance: strong headline, one visual moment, nothing competing | All marketing heroes |
| **Reject** | Illustration-heavy interfaces, animated everything | Workspace stays calm (Levels 2–3 motion only) |

### REFERENCE E — Ant Design (professional application structure)

| Dimension | What is useful | Where it appears |
|---|---|---|
| Navigation | Multi-level sidebar, breadcrumbs, keyboard-first discipline | Workspace sidebar (Phase 16) + Docs layout (left nav + TOC) |
| Data | Dense tables: sticky headers, fixed columns, compact rows, right-aligned tabular numbers | Clock inventory, matrix, findings, benchmarks tables |
| Master-detail | Stats → filterable list → detail panel (drawer) | Findings explorer, capability pages, benchmark detail |
| States | Default/hover/active/loading/disabled/error discipline; predictable interaction | Components on site + workspace |
| **Reject** | Stock admin-template look (blue buttons, generic layout), component soup | — |

---

## 2. Synthesized design DNA

**Formula:** Synterium storytelling + Nucleus/Muzli dark depth + compliance
information hierarchy + Ant structural discipline + **our original
SILICON GRAPH identity** = Ṛta. The references are not visually
identifiable in the final product.

### 2.1 STRUCTURE
- **Marketing surfaces:** hero → trust strip → problem/workflow → pillars →
  how-it-works (pipeline) → capability spotlights (alternating rows) →
  benchmark evidence → deterministic architecture → trust boundary → CTA →
  footer. Each section one idea, full-bleed, generous vertical rhythm.
- **Section rhythm discipline:** eyebrow + headline + evidence, never
  "title / subtitle / 3 cards" repeated. Alternate 2-column, full-width
  technical, and stat-band sections.
- **Workspace:** unchanged Phase 16 shell (grouped sidebar + context header +
  page-title system). Marketing density ≠ workspace density.

### 2.2 TYPOGRAPHY
- **DISPLAY:** a premium modern sans with real display weight — **"Space
  Grotesk"** for headlines (technical, slightly engineered, free/OFL) — with
  Inter fallback. Used at 44–96 px marketing scale, 600/700 weight, tight
  tracking (−0.02em), strong line breaks (2 lines max in hero).
- **BODY:** Inter 400/500 (15–17 px, 1.6 line-height). Uppercase micro-labels
  (11 px, +0.12em, muted) for eyebrows/section labels.
- **TECHNICAL:** JetBrains Mono for SDC commands, rule IDs, object names,
  line numbers, metrics, benchmark numbers. Right-aligned tabular numerals in
  data columns.
- No monospace-everywhere; mono is a *signal* that content is technical.

### 2.3 COLOR (dark-first, from the approved Phase 15 tokens)
| Token | Value |
|---|---|
| Background base | `#0B0F17` (graphite-navy, not black) |
| Surface 1 / 2 | `#111827` / `#151D2B` |
| Surface elevated | `#1A2436` |
| Border | `rgba(148,163,184,0.14)`; active `rgba(56,189,248,0.5)` |
| Text primary / secondary / muted | `#E6EDF6` / `#94A3B8` / `#64748B` |
| Accent primary | `#38BDF8` (sky — restrained, interactive only) |
| Accent secondary | `#818CF8` (indigo, subtle) |
| Success / Warning / Error / Info | `#34D399` / `#FBBF24` / `#F87171` / `#60A5FA` |
| Unknown / N/A | `#94A3B8` / `#475569` |
| Diff new / resolved / changed | `#34D399` / `#60A5FA` / `#FBBF24` |
| Focus | `#38BDF8` 2px ring |

Rules: one accent family; semantic colors only for status; **status never by
color alone** (icon + label + shape). No gradients > 5% opacity washes; no
glow except a single restrained halo in heroes.

### 2.4 SPACING
Base unit 4 px. Marketing sections 96–140 px padding (desktop), 56–64 px
tablet, 40 px mobile. Content max-width 1200 px (hero 1320 px). Two-column
gutters 56–80 px. Workspace density unchanged (compact tables, 6–8 px row
padding).

### 2.5 COMPONENTS
Buttons (primary accent / secondary outline / ghost), status badges
(Phase 15 system), eyebrow labels, stat-band numerals, evidence scorecards,
expandable methodology panels, trust callouts, pipeline diagram steps,
capability-row tiles, spec tables, footer. Component states: default/hover/
active/focus/disabled always defined.

### 2.6 BACKGROUND
Graphite base + faint 1px technical grid (radial-faded) + very low-opacity
netlist-topology arcs in heroes + occasional slow clock-edge pulse
(Level-1 ambient, `prefers-reduced-motion` respected). Depth via opacity
layering, never particles/starfields/glowing blobs.

### 2.7 MOTION (four levels)
- **L1 Ambient:** hero topology drift + clock-edge pulse; ≤ 20 s loops, 3–6%
  opacity elements.
- **L2 Explanatory:** SDC→pipeline→readiness hero sequence; clock-hierarchy
  branch expansion; coverage bit-resolution. Purposeful, 600–1200 ms.
- **L3 Interaction:** hover/focus/selection/expanders; 100–150 ms
  cubic-bezier(0.2,0,0,1); luminance shifts, no bounce.
- **L4 Page/section:** scroll reveals (fade+8px rise), hero transitions,
  capability exploration; short, never cinematic.
- Reduced motion: all L1/L4 suppressed; L2 shows final state instantly.

### 2.8 TRANSITIONS (relationship-specific)
pipeline→horizontal progression · clock hierarchy→branch expansion ·
coverage→bit-range resolution · readiness→dimension activation ·
diff→baseline→current sweep. Not one generic fade for everything.

### 2.9 TECHNICAL VISUALIZATION
Reuse Phase 16 primitives (node/arc/clock-edge/bus/constraint-link) and the
actual rendered visualizations (clock SVG, bus strips, readiness rail,
matrix, diff flow) inside capability and platform sections — the product
demonstrates itself with its real outputs, never generic dashboard charts.

### 2.10 WORKSPACE
Unchanged shell and density (Phase 16). Website launches the workspace
(`/` app) — the site is the product story, the app is the work surface.

### 2.11 MARKETING SURFACES
Home, Platform, Capabilities, Benchmarks, Trust, Docs entry, Release. All
dark-first, same tokens, own identity, high credibility density, honest
claims only (verified benchmark numbers; explicit non-claims; READY ≠
signoff).

---

## 3. Where each reference lands (responsibility matrix)

| Surface | Primary | Secondary |
|---|---|---|
| Home | A + D + B | Silicon Graph |
| Platform | A storytelling + D depth | technical pipeline diagram |
| Capabilities | A section hierarchy + B technical layouts | real visualizations |
| Benchmarks | C evidence presentation + B dark tech | E structural discipline |
| Trust Center | C info hierarchy + premium dark | SDC trust-status system |
| Docs entry | E structural discipline | B developer dark |
| Workspace | C IA + E discipline | Silicon Graph (unchanged) |
| Clock Intelligence | our own netlist grammar | — |
| Readiness / Diff | C risk hierarchy / change-review | deterministic semantics |

## 4. Final identity test (must all pass)
Compared side-by-side with old Ṛta, Synterium, Nucleus, a compliance
dashboard, and an Ant template, the product must be **recognizably its own**:
a premium semiconductor-engineering product whose language reflects clocks,
timing relationships, design context, evidence and readiness. It must never
look like any single reference copied, nor like the old Streamlit app with
animations.
