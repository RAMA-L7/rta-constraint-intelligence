# Ṛta — Visual Identity Direction

> **Document kind:** visual identity foundation (direction only — the full
> design system and motion system belong to the next product-experience phase).
> **Date:** 2026-08-06

---

## 1. Concept

The visual identity of Ṛta expresses one idea:

> **ORDER EMERGING FROM COMPLEXITY.**

Individual constraints, clocks, objects and relationships are chaotic in
isolation; Ṛta resolves them into a coherent, readable structure. Every visual
choice should serve that idea — never decoration.

**Forbidden motifs:** mythology, temples, religious iconography, epic
characters, ornamental cultural clichés, AI sparkles, brains, robots, magic
stars, neural-network blobs, generic chip/bolt logos.

## 2. Wordmark direction

`Ṛ` is the distinctive glyph (r with dot below, U+1E5A). Directional options:

- **A — Ordered Arc:** timing arcs progressively aligning into one coherent
  structure; the arc motif doubles as the analysis pipeline.
- **B — Constraint Node:** multiple constraint paths resolving into a single
  ordered node — literally “many inputs, one ordered whole”.
- **C — Ṛ Glyph System:** a restrained geometric interpretation of the `Ṛ`
  glyph; a dot-node anchored on a stem reads as a resolved clock node.

The working wordmark is **Ṛta** in a geometric sans (e.g. Inter 700) with a
monospace lockup for technical contexts. The glyph lockup must survive 16 px.

## 3. Typography philosophy

- **Display / product:** a premium geometric sans (Inter family is the current
  foundation; evaluate a display face for the marketing site in the next phase).
- **Technical data:** JetBrains Mono — SDC commands, rule IDs, object names,
  line numbers, metrics.
- **Rule:** monospace is used *selectively* for technical identifiers, never
  for the whole interface. Metrics need tabular numerals.

## 4. Technical visual language — primitives

Recurring primitives drawn from the domain (do not use generic dashboard
charts):

- **Clock edges** — vertical ticks / edge marks representing clock events.
- **Clock trees** — primary node branching into generated-clock children.
- **Timing arcs** — curved links between constrained objects.
- **Netlist nodes** — ports, pins, cells as distinct node glyphs.
- **Buses** — bit-range strips showing covered/uncovered slices.
- **Constraint links** — directed connectors with explicit semantics
  (override, conflict, legal multiple).
- **Analysis pulses** — slow traveling dots along edges (explanatory motion,
  never simulation accuracy).
- **Boundaries** — the trust boundary as a visual edge between “analyzed” and
  “not analyzed” regions.

## 5. Motion philosophy

Four levels (defined, not yet fully implemented):

1. **Ambient** — background topology: sparse nodes, slow pulses. Nearly
   imperceptible but alive. Respects `prefers-reduced-motion`.
2. **Explanatory** — analysis resolution, clock hierarchy formation, coverage
   bit-resolution, readiness dimension activation.
3. **Interaction** — hover, focus, navigation, inspector transitions. Fast and
   restrained (≈150–250 ms).
4. **Page/section** — workspace navigation transitions (180–300 ms), marketing
   hero sequence.

Performance: CSS transforms/opacity and canvas/SVG only; pause animation when
the tab is hidden; 60 fps target; reduced motion disables levels 1–2 and 4.

## 6. Background-animation philosophy

A single canonical background grammar: **silicon topology** — sparse netlist
nodes, routing-like arcs, occasional clock-edge pulses. Not particles, not
stars, not Matrix rain, not floating orbs. The background must be *visible
when observed* but must never compete with technical data. The Phase 17
visibility gap (background too faint to be visible when observed) is fixed in
`rta/workspace/webui/` — see `assets/css/app.css` (`#bg` layers) and
`assets/js/viz.js` (canvas draw); the broader motion system stays per §5.
The fix targets the current light surface; the dark-first workspace (§8)
remains future work and must re-derive these background values from the
color tokens.

## 7. Icon philosophy

Line icons, 1.5px stroke, geometric, consistent optical weight. Icons are
functional (severity, status, navigation) — never illustrative mascots.

## 8. Dark/light strategy

Dark-first. The engineering workspace is permanently dark (like STA tooling).
The marketing site is dark too, with strict AA contrast. A light theme is a
future option, not a phase-requirement.

## 9. Engineering density

The workspace is dense by design: compact tables, rails and inspectors instead
of floating cards. Hierarchy comes from spacing, surface contrast, borders and
typography — not shadows, glassmorphism or glow.

## 10. Status language (must never rely on color alone)

Every status = **icon + label + semantic treatment**:

- Severity: ERROR / WARNING / INFO
- Trust: VALIDATED / PARTIALLY_VALIDATED / NETLIST_REQUIRED /
  TCL_EXECUTION_REQUIRED / UNSUPPORTED / NOT_VALIDATED
- Readiness: READY / READY_WITH_ADVISORIES / REVIEW_REQUIRED / BLOCKED /
  INSUFFICIENT_CONTEXT

## 11. Brand-mark concepts (deliverable of this phase — concept only)

Three conceptual directions (see §2). Final selection deferred to the product
experience phase; no logo production work is done in this phase beyond the
wordmark lockup already present in the website/workspace brand mark.
