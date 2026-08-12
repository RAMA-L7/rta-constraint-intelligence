# Ṛta — High-Fidelity Product Specification

**Premium Product Experience · High-Fidelity Wireframe & Interaction Specification · v1.0 (design specification only — no implementation)**
**Date:** 2026-08-06 · **Baseline:** Ṛta v1.3.0 · **Sources of truth:** `docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md` + `docs/product/VISUAL_DESIGN_SYSTEM.md`

> This document specifies *where everything goes, how it behaves, and how the
> user moves through it* — at wireframe fidelity. It is a **design
> specification**: no production frontend, Streamlit, CSS, backend, or
> validation code is changed by this document. A frontend engineer must be
> able to implement the P0 experience from this document + the Visual Design
> System without inventing layout, behavior, states, or boundaries.

---

## 1. Experience Overview

Two surfaces, one product, one visual language (dark graphite + hairline
borders + SILICON GRAPH primitives, per the Visual Design System):

- **PRODUCT SITE** — a fast, static, public frontend that explains, evidences,
  and documents: Home · Platform · Capabilities · Benchmarks · Trust · Docs ·
  Releases. Marketing *with evidence*: every claim links to a verified artifact.
- **ENGINEERING WORKSPACE** — the deterministic analysis environment (Streamlit
  in P0): Overview · Validator · Clocks · Context · Coverage · Interactions ·
  Readiness · Diff · Reports · CI / Policies.

The experience contract, enforced on both surfaces:

1. Within ~10 seconds a visitor knows: *what this is* (SDC constraint quality
   intelligence), *who it is for* (PD/STA/constraints engineers), *what it
   does* (validates, analyzes, and readiness-gates SDC before STA), and *why it
   is different* (deterministic, offline, evidence-driven, honest about scope).
2. Every status, finding, and benchmark is one click from its evidence.
3. "READY ≠ STA signoff" and "CI PASS ≠ timing closure" are always visible
   where those concepts appear.

---

## 2. Product vs Workspace Relationship

| | PRODUCT SITE | ENGINEERING WORKSPACE |
|---|---|---|
| Purpose | Understand, trust, evaluate, learn | Analyze, investigate, decide, integrate |
| User | Evaluator, technical lead, new engineer, docs reader | Working engineer running analysis |
| Density | Low–medium; prose + evidence | High; dense tables, panels, inspectors |
| Entry | Public URL (conceptual, e.g. sdcvalidator.dev) | "Launch Validator" CTA / app subdomain |
| Auth | None (public) | None (local tool in P0 — no accounts, no telemetry) |
| State | None; static content | In-memory analysis state only (no persistence beyond user-exported files) |
| Motion | Hero-only ambient (§8) | Micro + explanatory only; no ambient |
| Relationship | Workspace is *always one click away* from any product page ("Launch Validator") | Workspace links back to relevant docs/trust pages ("View rule docs", "Trust center") |

**Boundary rule:** the workspace never hosts marketing; the product site never
hosts live analysis. They share tokens, components, and terminology.

---

## 3. Global Navigation

**Product site (top header, 64px, compacts to 48px on scroll):**

```
[logo] Ṛta    Platform · Capabilities · Benchmarks · Trust · Docs · Releases   [Launch Validator ▸]
```

- Active state: accent underline + weight. `Launch Validator` = primary button.
- Mobile (<1024px): logo + hamburger → full-screen overlay nav with grouped links.

**Workspace (left sidebar, 240px → 64px icon rail):**

```
ANALYZE    Overview · Validator · Clocks
DESIGN     Context · Coverage
QUALITY    Interactions · Readiness
CHANGE     Diff
OUTPUT     Reports · CI / Policies
─────────────────────────────
v1.3.0 · [Trust chip]         (sidebar footer)
```

- Group headers are 11px uppercase muted labels; items 13px with icon + label.
- Icon-rail mode shows icons only; tooltips give labels.

**Consistency:** both surfaces use the same icon set, the same active-state
language, and the same logo. The workspace "Launch" equivalent is the *New
Analysis* action.

---

## 4. Product Header

| Element | Spec |
|---|---|
| Logo area | CONSTRAINT BRACKET mark (VDS §41, direction 1) + wordmark "Ṛta" (Inter 700). Mono "SDC" lockup option for small sizes. |
| Nav | Platform · Capabilities · Benchmarks · Trust · Docs · Releases (order fixed). |
| Version | Small mono chip in header right: `v1.3.0` (links to Release page). |
| CTA | `Launch Validator` — primary button, right-aligned, sticky. |
| Scroll | 64px → 48px; background gains `SURFACE` + hairline bottom border (no blur/glass). |
| Responsive | <1024px hamburger; CTA stays visible on mobile (icon + "Launch"). |

---

## 5. Workspace Navigation

Grouped sidebar per §3. Behavior:

- Selecting an item switches the workspace view (Streamlit view-state mapping).
- The item under "current analysis" shows the readiness/trust mini-chip next to
  it (e.g., `Readiness · REVIEW`).
- `Overview` is the post-analysis landing view; `Validator` is the input+run
  view. "New Analysis" primary action lives in the analysis header.
- Keyboard: `[` `]` cycle sections; `1`–`9` jump to items (documented in §42).

---

## 6. Workspace Shell

```
┌──────────────┬──────────────────────────────────────────────────────────────┐
│ SIDEBAR 240  │ ANALYSIS HEADER (64px)                                      │
│ (nav groups) ├──────────────────────────────────────────────────────────────┤
│              │ MAIN WORKSPACE                                              │
│              │                                            ┌──────────────┐ │
│              │                                            │ INSPECTOR    │ │
│              │                                            │ 400px,       │ │
│              │                                            │ contextual   │ │
│              │                                            │ (opens on    │ │
│              │                                            │  selection)  │ │
│              │                                            └──────────────┘ │
├──────────────┴──────────────────────────────────────────────────────────────┤
│ (status/stage strip only while an analysis is running — else absent)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

Rules: sidebar fixed; analysis header sticky; inspector opens on selection,
closes with ✕ or Esc; on <1024px the inspector becomes an overlay drawer; on
<640px it is unavailable (mobile = summary mode). No persistent footer bar.

---

## 7. Home High-Fidelity Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                    │
│ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ HERO (110vh, animated background allowed)                             │ │
│ │ eyebrow:  CONSTRAINT QUALITY INTELLIGENCE · PRE-STA VALIDATION        │ │
│ │ H1:       Deterministic SDC validation                                │ │
│ │           before STA.                                                 │ │
│ │ support:  Validate, analyze, and readiness-gate your SDC constraints  │ │
│ │           — offline, reproducible, with explicit trust boundaries.    │ │
│ │ [Launch Validator ▸]  [Read the docs]                                 │ │
│ │ trust strip:  ◈ Deterministic  ◈ Offline-capable  ◈ No AI/LLM runtime  │ │
│ │              ◈ Open evidence  ◈ Python ≥3.10                          │ │
│ │ [ HERO VISUAL: constraint path → clock tree → readiness ]  (§8)       │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ PROBLEM / WORKFLOW ───────────────────────────────────────────────────┐ │
│ │ "Where constraint quality fits" — pipeline strip:                     │ │
│ │  Constraint Development → [ Ṛta ] → STA / Signoff           │ │
│ │  caption: "The validator does not replace STA. It makes what goes     │ │
│ │  into STA trustworthy and reviewable."                                │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ PRODUCT PILLARS ─────────────────────────────────────────────────────┐ │
│ │  VALIDATE  UNDERSTAND  ASSESS  PROTECT  PROVE                         │ │
│ │  (each pillar = icon + one-line + link to capability page)            │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ HOW IT WORKS ────────────────────────────────────────────────────────┐ │
│ │  SDC [+ optional Verilog] → Deterministic analysis → Evidence →       │ │
│ │  Readiness → Regression/CI   (orthogonal node-arc diagram, static)    │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ CAPABILITY SPOTLIGHT ────────────────────────────────────────────────┐ │
│ │  3 selected: Clock Intelligence · Constraint Readiness · Regression   │ │
│ │  Diff (each: problem / evidence / link)                               │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ READINESS STORY ─────────────────────────────────────────────────────┐ │
│ │  Mini dimension rail (7 rows, static) + quote:                       │ │
│ │  "Readiness is a structured review, not a score — and never a        │ │
│ │  timing signoff."                                                    │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ BENCHMARK EVIDENCE ──────────────────────────────────────────────────┐ │
│ │  767 pytest · 9/9 golden · 42/42 suites · 17/17 clean-room ·          │ │
│ │  16/16 CLI · 10/10 smoke   (Evidence Metric cards → Benchmarks page)  │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ DETERMINISTIC ARCHITECTURE ──────────────────────────────────────────┐ │
│ │  No LLM · No cloud · No external API · Offline analysis ·             │ │
│ │  Reproducible results · Versioned snapshots → Engineering page        │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ TRUST BOUNDARY ──────────────────────────────────────────────────────┐ │
│ │  "What we validate / what we do not claim" two-column, both equally   │ │
│ │  prominent. (No STA signoff, no slack, no .lib timing.) → Trust       │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ ┌─ CTA ─────────────────────────────────────────────────────────────────┐ │
│ │  [Launch Validator ▸]  [Read the docs]  [Explore benchmarks]          │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│ FOOTER: product nav · version v1.3.0 · "RC_READY_WITH_KNOWN_LIMITATIONS" │
│         · license · privacy note ("Runs entirely locally — no data leaves │
│         your machine")                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

**10-second rule:** eyebrow + H1 + support + trust strip + CTA are all above
the fold; the hero visual communicates "constraint graph → readiness" without
text.

---

## 8. Hero Visualization Specification

**Concept — "Analysis Pulse" (engineering visualization, not marketing motion):**

| Stage | Visual | Timing |
|---|---|---|
| 0 | Empty: faint grid + an SDC command line slides in from the left (mono, e.g. `create_clock -name clk_core -period 10.0 [get_ports clk_core]`) | 0–1.2s |
| 1 | Tokens decompose into constraint NODEs (squares) that snap to a horizontal spine | 1.2–2.4s |
| 2 | A CLOCK HIERARCHY grows upward from the primary node: generated clocks as child squares, solid orthogonal arcs | 2.4–3.8s |
| 3 | DESIGN OBJECTS (PORT open squares, CELL rounded squares) appear below the spine as a sparse netlist fragment | 3.8–5.0s |
| 4 | ANALYSIS PULSE (bright dot) travels the spine; arcs gain subtle edge pulses | 5.0–6.5s |
| 5 | All paths converge: a READINESS node resolves with the shield-check mark; loop resets after a 2s hold | 6.5s–∞ loop |

Spec: ≤2 animated layers, CSS transforms/opacity only, ≤14fps, pause on
`document.hidden`; labels are static mono text (never animated). Interaction:
hovering any node pauses the loop and shows its label. Mobile fallback: static
final-state diagram (stages 0/5 only). Reduced-motion: static diagram, no loop.

**Never in the hero:** waveforms that imply timing propagation, clocks "running,"
slack numbers, percentages.

---

## 9. Platform Wireframe

Interactive architecture diagram — a vertical/horizontal pipeline of 12
modules, each a node (square) with an arc to the next:

```
INPUT (SDC [+ Verilog])
  → PREPROCESS (Tcl vars · comments · collections)
  → VALIDATE (111 rules · semantic checks)
  → CLOCK ANALYSIS (primary · generated · relations)
  → DESIGN CONTEXT (structural resolution)
  → COVERAGE (inputs/outputs/buses)
  → INTERACTIONS (duplicates · overrides · conflicts)
  → TRUST (support boundary)
  → READINESS (7 dimensions)
  → SNAPSHOT (schema v2 · v1 compatible)
  → DIFF (semantic regression)
  → CI GATE (BLOCKERS_ONLY · NO_READINESS_REGRESSION · STRICT · CUSTOM)
```

Behavior: click a module → side panel reveals *purpose · inputs · outputs ·
evidence (benchmark/tests) · trust boundary · related capability page* + a
"Launch in workspace" deep link where the module exists in the workspace
(e.g., Readiness → workspace Readiness page). The diagram is static SVG on the
product site; hover highlights the path; one module can be "selected" at a
time. Caption at the end: *"The gate never produces PASS on engine failure."*

---

## 10. Capabilities Overview

One page, nine capabilities, uniform cards (icon · one-line problem · what it
produces · trust chip · link). Grid: 3×3 desktop, 2-col tablet, 1-col mobile.
Capabilities: SDC Validation · Clock Intelligence · Design Context ·
Constraint Coverage · Constraint Interactions · Constraint Readiness ·
Regression Intelligence · CI Quality Gates · Tcl & Wildcard Intelligence.
Each card links to its capability page (§11). No capability is presented
without its trust boundary note.

---

## 11. Capability Page Template

Reusable hierarchy (every capability page uses it):

```
HERO (H1 + one-line + trust chip + [Launch ▸])
ENGINEERING PROBLEM   (3 short bullet pains)
HOW IT WORKS          (input → analysis model → output, node-arc diagram)
TECHNICAL VISUALIZATION (the capability's signature visual — static)
INPUTS                (table: what it consumes, optional/required)
ANALYSIS MODEL        (what the analysis deterministically computes)
EXAMPLE RESULT        (small honest sample — e.g. a real finding block)
EVIDENCE / PROVENANCE (tests + benchmark + sample corpus links)
TRUST BOUNDARY        ("What this capability does NOT prove" callout)
BENCHMARK EVIDENCE    (scorecards relevant to this capability)
RELATED DOCS          (docs links, rule links)
[Launch capability ▸]
```

Rule: the TRUST BOUNDARY callout is mandatory and styled distinctly (boundary
icon). No page ships without it.

---

## 12. Benchmarks Wireframe

```
RELEASE EVIDENCE HEADER
  v1.3.0 · verified 2026-08-06 · RC_READY_WITH_KNOWN_LIMITATIONS
KEY VERIFIED RESULTS (6 Evidence Metric cards)
  767 pytest  |  9/9 golden runners  |  42/42 benchmark suites
  17/17 clean-room wheel journey  |  16/16 CLI contract  |  10/10 release smoke
CATEGORY TABS
  CORRECTNESS · DESIGN-AWARE · ROBUSTNESS · SECURITY · PERFORMANCE · RELEASE QUALITY
BENCHMARK CARDS (grid, each = scorecard §13)
METHODOLOGY FOOTER
  "All results are internal verified test evidence produced by the release
  pipeline (benchmarks/). They are not independent industry certification."
```

Every number on this page maps to a repository artifact (pytest output, runner
exit codes, `RELEASE_MANIFEST.md`, Phase 14 report). The header always shows
version + date + environment context.

---

## 13. Benchmark Detail

Scorecard (reused everywhere):

```
┌────────────────────────────────────────────────────────────┐
│ GOLDEN RUNNERS                   [ PASS ]  (status badge)  │
│   9 / 9  suites match expected behavior                    │
│   Scope: parsing + semantics + readiness + CI gates       │
│   Version: v1.3.0 · Python 3.10 · Windows                  │
│   [ Methodology ▸ ]  [ Artifact ]  [ Limitations ▸ ]       │
└────────────────────────────────────────────────────────────┘
```

Detail view (methodology drawer) fields: NAME · PURPOSE · WHAT IT TESTS ·
METHODOLOGY · CORPUS SIZE · EXPECTED-BEHAVIOR SOURCE · RESULT · VERSION ·
ENVIRONMENT · LIMITATIONS · ARTIFACT/MANIFEST REFERENCE. The drawer is 360px,
opens on click, closes with Esc. "Artifact" links to the actual runner file or
report in the repo.

**Placeholder rule:** any scorecard used as a *template* in designs or mockups
must display `[n] / [n]` with an explicit "populate from runner output"
annotation — never a hard-coded count. Only verified Phase 14 numbers may
appear literally: 767 pytest · 9/9 golden · 42/42 suites · 17/17 clean-room ·
16/16 CLI · 10/10 smoke.

---

## 14. Performance Visualization

Charts only from measured data (readiness diff perf, coverage perf suites):

| Chart | Axes | Source |
|---|---|---|
| Diff scaling | x = findings count · y = ms | `test_readiness_diff_perf.py` (measured 10k findings ≈ 43–75 ms) |
| Readiness analysis | x = constraints · y = ms | readiness perf suite |

Spec: line charts, mono tick labels, units in axis titles, mandatory caption
`Environment: Python 3.10 · <OS> · v1.3.0 — indicative, not a benchmark against
other tools.` Tooltip: exact values + point count. No extrapolation past
measured range; no comparisons to commercial EDA tools.

---

## 15. Trust Center Wireframe

One of the product's strongest differentiators — limitations are first-class:

```
TRUST MODEL           6 status blocks (VALIDATED · PARTIALLY_VALIDATED ·
                      NETLIST_REQUIRED · TCL_EXECUTION_REQUIRED ·
                      UNSUPPORTED · NOT_VALIDATED) — each with shape+icon+label
WHAT WE VALIDATE      check-list (SDC rules, semantic refs, clock analysis,
                      coverage, interactions, readiness, diff, gates)
WHAT DESIGN CONTEXT   structural resolution only — objects/hierarchy/coverage;
  ENABLES             no timing values
WHAT WE DO NOT CLAIM  (bold, full-size, never fine print)
                      ✕ STA signoff  ✕ slack  ✕ .lib timing  ✕ physical timing
                      ✕ closure guarantee  ✕ 100% coverage = correct intent
                      ✕ CI PASS = timing closure
SECURITY / LOCAL      "Analysis runs entirely on your machine. No network, no
                      telemetry, no upload."
BENCHMARK METHODOLOGY internal verified evidence — not independent certification
KNOWN LIMITATIONS     Tcl execution not performed · SDC subset bounded ·
                      netlist optional · Python ≥3.10
```

Every trust status block links to the support matrix (`support_boundary.py`
semantics) and to the docs section that explains it.

---

## 16. Specifications Experience

A single technical specifications table page (exact repository evidence):

| Category | Value |
|---|---|
| Analysis model | Deterministic structural/semantic analysis (no timing engine) |
| Runtime | Python ≥3.10 · no LLM · no network · no external APIs |
| Primary input | SDC text/file (bounded Tcl subset: variables, comments, collections) |
| Optional context | Structural Verilog/netlist + top module |
| Outputs | Findings (severity+provenance) · JSON · HTML report · snapshot · diff · gate result |
| Design context | Optional; upgrades NETLIST_REQUIRED → VALIDATED where resolvable |
| Snapshots | Schema v2, v1 read-compatible |
| Policies | BLOCKERS_ONLY · NO_READINESS_REGRESSION · STRICT · CUSTOM (safe declarative) |
| CI | Exit codes 0/1/2/3 · machine-clean JSON stdout · never PASS on engine failure |
| Rules | 111 rules across 7 modules (rules_registry.py) |
| Trust statuses | 6-level support boundary (support_boundary.py) |

Each row links to its evidence (module file, docs page).

---

## 17. Docs Entry Experience

Docs home = 4 lanes (from architecture §31):

```
GETTING STARTED   Installation · First Validation · Understanding Results · Add Design Context
CONCEPTS          SDC Validation · Clock Intelligence · Coverage · Interactions · Trust · Readiness · Baselines · Regression
WORKFLOWS         Local Validation · Design-Aware Validation · Baseline Review · CI Integration
REFERENCE         CLI · Python API · Rules (111) · Support Matrix · Policy Schema · Snapshot Schema
```

Each doc page: left nav (240px) · content (max 720px) · right TOC (wide
screens) · prev/next footer · trust callouts inline. Rule IDs render as mono
chips linking to rule pages. Code blocks have copy buttons.

---

## 18. Release v1.3.0 Wireframe

```
RELEASE  v1.3.0 — Release Candidate        [RC_READY_WITH_KNOWN_LIMITATIONS] badge
STATUS   2026-08-06 · Phase 14 audit complete · not yet GA
CAPABILITIES   (capability chips, linked)
VERIFICATION EVIDENCE   (the 6 release metrics + clean-room summary, each an
                         Evidence Metric card with artifact links)
KNOWN LIMITATIONS       (full-size, honest — same list as Trust Center)
INSTALLATION            pip install + web extra + Docker + from-source, verified
RELEASE NOTES           changelog summary (from CHANGELOG.md, not fabricated)
ARTIFACTS               wheel · sdist · manifest · Phase 14 report
```

Explicitly **no** "certified," "enterprise-grade," or "signoff-ready" language.

---

## 19. Workspace Overview Wireframe

First screen after analysis. Prioritized, NOT equal-weight:

```
ANALYSIS HEADER (design · SDC file · netlist chip · mode · trust · readiness)

OVERALL READINESS (badge, large — top-left, the single most important datum)
TRUST / SCOPE     (trust strip: what was validated vs not — compact)
CRITICAL FINDINGS (top errors, max 5 rows, each → Findings Explorer)
CLOCK SUMMARY     (clock count + hierarchy mini-diagram + link)
DESIGN CONTEXT    (netlist supplied? objects resolved? compact)
COVERAGE          (input/output constrained-proportion bars, compact)
INTERACTIONS      (duplicates/overrides/conflicts counts)
NEXT ACTIONS      (engineered list: "Review 2 I/O constraints" → deep links)
```

The engineer can answer in order: (1) Is there a problem? (readiness + errors)
(2) How serious? (severity, counts) (3) Can I trust this? (trust/scope strip)
(4) Where do I investigate? (critical findings + next actions). Empty pre-analysis state per VDS §36.

---

## 20. Analysis Header

```
[New Analysis ▸]  design: top                SDC: design.sdc (3.2 KB)
                  netlist: top.v ✓ / none    mode: SDC-only | Design-aware
                  trust: [PARTIAL]           readiness: [REVIEW]  ·  14:03:02
```

Fields: Design/top · SDC filename · Netlist status (✓ supplied / ○ none) ·
Analysis mode · Trust chip · Readiness chip · run timestamp. High-value only —
no path dumps, no full metadata. Runs are identified by timestamp+file (no
invented persistence). The header is sticky and shows on every workspace view.

---

## 21. Findings Explorer

```
[ search ] [severity ▾ ALL] [rule ▾ ALL] [category ▾ ALL]   (segmented filters)
┌──────┬───────┬──────────────────────────────┬──────────────┬────────┬────────┐
│ SEV  │ RULE  │ FINDING                      │ OBJECT       │ CLOCK  │ LOC    │
│ ▲err │ SDC-069│ Contradictory delay window   │ data_in      │ clk    │ 42     │
│ ⚠wrn │ SDC-008│ Input delay ≥ clock period   │ din          │ clk_c  │ 41     │
└──────┴───────┴──────────────────────────────┴──────────────┴────────┴────────┘
```

Columns: Severity (icon+label) · Rule (mono) · Finding · Object (mono) · Clock
(mono) · Location (line). Secondary metadata (provenance, identity strength,
evidence) lives in the inspector, not the table. Row click → Finding Inspector.
Default sort: severity then rule ID. Sticky header; compact 30px rows;
search matches object+message+rule.

---

## 22. Finding Inspector

Right rail (400px), sections in order:

```
SDC-069 · Contradictory Delay Window          [WARNING] (badge, icon+label)
SUMMARY            One line, plain language.
WHY DETECTED       Detection semantics (rule logic, 2–3 lines).
CONSTRAINT(S)      Mono code: set_input_delay ... / set_output_delay ...
AFFECTED OBJECT    mono, clickable → context
EVIDENCE           The computed evidence the rule used.
SOURCE PROVENANCE  dual-line: L41 ↔ L42 (dashed connector, both rows tinted)
TRUST              What scope this finding was verified under (e.g. SDC-only →
                   NETLIST_REQUIRED follow-up)
REQUIRES CONTEXT?  [Yes — netlist] / No
REQUIRES STA?      [Yes — path analysis needed] / No   ← distinct marker
RULE DOCUMENTATION link
```

"REQUIRES STA" is visually distinct from provable contradictions (different
shape + label: `PATH ANALYSIS` vs `CONTRADICTION`). Esc/✕ closes; ←/→ steps
through findings.

---

## 23. Source Viewer

SDC rendered as code with:

```
 39  create_clock -name clk_core -period 10.0 [get_ports clk_core]
 40
 41  set_input_delay -max 2.0 -clock clk_core [get_ports din]      ← error tint
 42  set_output_delay -max 3.0 -clock clk_core [get_ports dout]    ← error tint
      ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ (dual-line dashed connector)
```

Features: line numbers (muted mono gutter) · finding highlights (left rule +
subtle tint, never full-row color) · dual-line provenance connector · jump
next/previous finding buttons · copy line/block · ± context lines. Not a code
editor — read-only viewer. Clicking a finding line opens the inspector.

---

## 24. Clock Intelligence

Three coordinated views in one page:

```
[INVENTORY] [HIERARCHY] [MATRIX]     (segmented tabs)
CLOCK INVENTORY (dense table, left):
  NAME      TYPE      PERIOD  SOURCE      RELATION
  clk_core  primary   10.0    clk_core    —
  div2      generated 20.0    clk_core    derived
  clk_io    primary   5.0     clk_io      async
  (row click → Clock Inspector in right rail)
```

CLOCK INSPECTOR (right rail): full ClockDef fields (name, type, period, source
node, master, divide_by, relationship, raw text), related findings, related
pairs. All text-based; the visual grammar follows VDS §30.

---

## 25. Clock Hierarchy

SVG node-edge diagram (≤100 nodes; beyond that, HTML tree fallback):

```
        ┌─ clk_core (10.0) ─┐
        │   [derived]       │   [inferred async]
   div2 (20.0)          div4 (40.0)          clk_io (5.0)
```

- Primary = filled square (accent-2) · generated = outlined square with tick ·
  virtual = outlined circle.
- Solid arcs = derived/master relationships; dashed = inferred; dotted+`?` =
  unknown.
- Click node → Clock Inspector; hover shows tooltip (name/period/source).
- Static caption: **"Structural relationships only — no timing propagation."**

---

## 26. Relationship Matrix

Pairwise matrix (existing report pattern, elevated):

```
        clk_core   div2    div4    clk_io
clk_core   —        ✓der    ✓der    ~async
div2       ✓der      —       ✓der    ~async
```

- Cells carry non-color symbols: `✓` derived/synchronous · `~` async ·
  `?` unknown · `✗` physically exclusive · `!` advisory.
- Color is reinforcement only (tooltip always available; `role=grid`).
- Declared `set_clock_groups` relationships render with a solid ring; inferred
  with dashed. Click cell → pair evidence + declared-group status.

---

## 27. Design Context

```
NETLIST: top.v ✓ (2 cells · 4 ports · 3 nets)   [replace] [remove]
TOP MODULE: top     [change ▾]
RESOLUTION: 12/14 get_ports refs resolved · 2 netlist-required
HIERARCHY (compact tree, expandable):
  top
   ├─ u_clk_gen (cell)
   │   └─ clk_out (pin)
   └─ din[3:0] (port)
COLLECTION RESOLUTION TABLE: command → objects resolved → status
UNSUPPORTED EXPRESSIONS: 1 (expr in get_pins) — shown, honest
TRUST UPGRADE note: "Providing a netlist upgraded 3 NETLIST_REQUIRED
  constructs to VALIDATED."
```

No schematic rendering. Everything is a tree/table. Missing netlist = the §36
"no netlist" empty state with "Continue SDC-only" option.

---

## 28. Coverage

```
COVERAGE SUMMARY (two direction bars — never a single percentage ring)
  INPUTS   [▓▓▓▓▓▓░░░░] 60% constrained   (secondary annotation)
  OUTPUTS  [▓▓▓▓░░░░░░] 40% constrained
  caption: "Coverage is not correctness. Constraints on an object do not
           prove correct timing intent."
LEGEND: constrained · partial · unconstrained · exempt · unknown · N/A
PORT / BUS TABLE (dense): object · direction · status chip · covering
  constraint (mono, line ref) → click opens evidence
```

---

## 29. Bus Coverage

Per-bit visualization for partial buses:

```
data_in[31:0]
 [31           15             7            0]
  ▓▓▓▓▓▓▓▓▓▓▓▓▓░░▓░░░░░░░░▓▓▓▓▓▓▓▓▓▓
   constrained      gap     constrained
```

- Filled = constrained (success); hollow gap = unconstrained (error/warning
  per severity); exempt = hatched; unknown = stippled; N/A = muted.
- Hover a bit → tooltip with covering constraint + line. Click → evidence row.
- Legend + the "coverage ≠ correctness" caption always visible.

---

## 30. Interactions

```
CATEGORY TABS: DUPLICATES · OVERRIDES · CONTRADICTIONS · OVERLAP / STA REVIEW
CONSTRAINT A  ↔  CONSTRAINT B   (two-constraint visual, dashed link)

┌─ CONTRADICTION (provable) ─────────────────────────────┐
│ set_input_delay -max 2.0  (L41)                        │
│        ⬍ CONTRADICTION · SDC-069                       │
│ set_input_delay -max 5.0  (L43)                        │
│ evidence: conflicting windows on same object+clock     │
└────────────────────────────────────────────────────────┘
┌─ OVERLAP / STA REVIEW (requires path analysis) ────────┐
│ exception A (L77) ⬍ OVERLAP · PATH ANALYSIS NEEDED ⬎ exception B (L81) │
│ badge: [PATH ANALYSIS] (distinct shape from contradiction)             │
└────────────────────────────────────────────────────────┘
```

Each row carries dual-line provenance; "provable conflict" vs "requires STA"
are visually distinct (marker shape + label + color).

---

## 31. Readiness

```
READINESS                       [REVIEW_REQUIRED] (badge, icon+label)
mode: Design-aware · disclosure: "Constraint readiness review — NOT STA signoff"

DIMENSION STACK (7 rows, clickable — see §32)
BLOCKERS      (findings that must be addressed)
REVIEW ITEMS  (warnings + NETLIST_REQUIRED items)
ADVISORIES    (info-level guidance)
RECOMMENDED ACTIONS (P0–P3 — real backend data: readiness.actions carries
  priority + category per item; each action deep-links to its finding, rule
  doc, or workspace view)
TRUST DISCLOSURE (boundary callout): "READY does not mean timing signoff.
  This is a constraint-readiness review produced by deterministic analysis."
```

No numeric score (none exists); no gauge; no "90% ready." The RECOMMENDED
ACTIONS section renders `readiness.actions` (already emitted by the CLI —
verified in cli.py); it is not an invented feature. If a revision's action
list is empty, the section shows "No recommended actions — no blockers or
review items."

---

## 32. Readiness Dimensions

Each of the 7 dimensions (CLOCKS · I/O · EXCEPTIONS · COVERAGE ·
CONSISTENCY · ANALYSIS_TRUST · DESIGN_CONTEXT) renders as:

```
CLOCKS        [▮▮▮▮▮▮▯▯▯▯]  READY              (marker + rail + status)
I/O           [▮▮▮▯▯▯▯▯▯▯]  REVIEW_REQUIRED    ← selected
  caused by: SDC-008 (L41) · SDC-009 (L42)     (evidence panel, mono refs)
```

- Rail = coarse 10-segment proportion of *evidence within scope*, derived
  client-side from the per-dimension finding counts (blockers/review/
  advisories present in the readiness result) — explicitly captioned
  "evidence proportion, not a quality score." It is a UI derivation from
  existing readiness data; no new backend field.
- Click → evidence panel listing the exact findings/items that set the
  dimension status. INSUFFICIENT_CONTEXT shows the hollow-shield marker and
  explains *which context would upgrade it* (e.g., netlist).

---

## 33. Regression Diff

Change-review experience:

```
BASELINE [READY]  →  CURRENT [BLOCKED]   [BLOCKING_REGRESSION]  gate: FAIL
FILTERS: All · NEW · RESOLVED · CHANGED · UNCHANGED   (segmented)
┌───────┬────────┬─────────────────────────────┬──────────┬──────────────┐
│ MARK  │ RULE   │ FINDING                     │ OBJECT   │ PROV         │
│ + NEW │ SDC-008│ Input delay ≥ clock period  │ din      │ L12          │
│ ↻ CHG │ SDC-046│ Unknown clock ref           │ clk_io   │ L9→L14       │
└───────┴────────┴─────────────────────────────┴──────────┴──────────────┘
COVERAGE DELTA  (newly unconstrained objects, bus strips)
TRUST DELTA     (VALIDATED → PARTIAL transitions, chip arrows)
CONTEXT DELTA   (netlist changes)
DEBT            (existing / new / resolved, blocker·review·advisory)
GATE RESULT     (policy name + exit code + why)
```

Change markers carry shape+icon+color (never red/green alone). Header always
shows baseline → current transition + classification + gate result.

---

## 34. CI / Policies

```
POLICY SELECTOR (4 cards):
  BLOCKERS_ONLY             — fails only on error findings
  NO_READINESS_REGRESSION   — fails if readiness regresses vs baseline
  STRICT                    — fails on any regression or new blocker
  CUSTOM                    — declarative policy file (safe, no code execution)
Each card: intent · what fails · what is allowed · engine-failure behavior
  ("engine failure never yields PASS — exit 3").
CUSTOM POLICY PREVIEW: rendered YAML with inline field validation (unknown
  fields flagged, never executed).
CLI INTEGRATION: command block + copy — the gate is `--gate` on `check`
  (verified against cli.py; exit codes 0=pass · 1=gate failed · 2=invalid
  input · 3=engine failure, and engine failure never yields 0):
  # 1) establish a baseline
  sdc-tools check design.sdc --save-baseline baseline.json
  # 2) gate a revision against that baseline
  sdc-tools check design.sdc --baseline baseline.json --gate STRICT
  # 3) gate without a baseline (blockers only)
  sdc-tools check design.sdc --gate BLOCKERS_ONLY
  # 4) custom declarative policy
  sdc-tools check design.sdc --baseline baseline.json \
      --gate CUSTOM --gate-policy policy.yaml
GITHUB ACTIONS EXAMPLE: one small snippet block (vendor-neutral framing:
  "GitHub Actions is one example — the gate is a plain CLI").
```

No no-code drag-drop builder; the UI explains and generates the CLI command.

---

## 35. Reports

Artifact cards, one row per supported export:

```
┌─ HTML REPORT ────────────────┐  what: human-readable analysis evidence
│ [download] generated 14:03   │  when: review/share after analysis
├─ JSON RESULT ────────────────┤  what: machine-consumable findings
│ [download]                  │  when: pipelines/tools
├─ SNAPSHOT ──────────────────┤  what: versioned analysis state (schema v2)
│ [save] [load]               │  when: establish/compare baselines
└─ BASELINE ──────────────────┘  what: reference snapshot for gates/diff
                                 when: regression + CI
```

No new formats invented. Each card explains contents, when to use it, and how
it was generated; JSON purity note: "stdout is machine-clean JSON — diagnostics
go to stderr."

---

## 36. Empty States

Designed technical empty states (each answers *what this means* + *what next*):

| State | Visual | Next action |
|---|---|---|
| No analysis | NODE diagram, mono caption | [Load SDC] [Use sample] |
| No SDC | PORT primitive | [Choose file] [Paste] |
| No netlist | NET node | [Add netlist] [Continue SDC-only] |
| No findings | shield-check | [View analysis scope] |
| No coverage | empty bus strip | [Add netlist] |
| No interactions | dashed constraint link | (none needed — auto-checked) |
| No baseline | snapshot node | [Save baseline] |
| No diff | split arrow | [Load baseline] |
| No policy | CI node | [Choose policy] |

---

## 37. Error States

Typed, never generic red alerts (VDS §37), plus behavior rules: no tracebacks
in the UI; every error links to docs; engine failure states never display a
PASS/READY result; JSON output stays clean (errors go to stderr with the
documented exit code). Workspace examples:

| Type | UI |
|---|---|
| Invalid SDC | field-level ring on source view + typed banner |
| Unsupported construct | UNSUPPORTED badge + support-matrix link |
| Insufficient context | NETLIST badge + "add netlist" action |
| Incompatible baseline | UNKNOWN badge + "baseline review required" |
| Engine failure | ERROR badge + run-id + "results are not a PASS" |
| File failure | ERROR badge + path |
| Policy error | ERROR badge + field + docs |

---

## 38. Loading / Analysis State

Stage list (honest, deterministic — no fake percentages):

```
Analyzing design.sdc
  ✓ Parsing constraints
  ✓ Analyzing clocks
  ⟳ Resolving design context   (only when netlist supplied)
  → Evaluating coverage
  → Analyzing interactions
  → Assessing readiness
  → Preparing result
```

Completed = check; current = pulse (CLOCK EDGE primitive); skipped (e.g., no
netlist) = struck-through "skipped." Reduced motion: static highlight.

---

## 39. Desktop Behavior

- ≥1280px: full shell — sidebar 240px, main fluid, inspector 400px rail.
- Tables: sticky headers; matrices scroll horizontally with sticky first column.
- Multi-panel pages (Readiness, Coverage) use 2-col grids where evidence
  panels accompany the primary view.

---

## 40. Tablet Behavior

- 1024–1279px: sidebar → 64px icon rail (labels via tooltip); inspector →
  360px overlay drawer; hero visual → static diagram; benchmark grids 2-col;
  capability grids 2-col.
- Matrices/trees: horizontal scroll, never squished.

---

## 41. Mobile Behavior

- <640px: **read-only summary mode** — analysis summary, readiness status,
  findings list (table → card list), reports download; no matrices, no
  hierarchy graph, no inspector. A persistent note: "Full analysis experience
  is designed for desktop — open on a larger screen."
- Product site: stacked, hamburger nav, CTA always visible, hero static.

---

## 42. Keyboard / Accessibility Behavior

- Full tab order; visible 2px focus ring on all interactive elements.
- Shortcuts (workspace): `[` `]` nav sections · `1`–`9` jump · `/` search ·
  `Esc` close inspector/drawer · `←` `→` step findings (when inspector open).
- **Shortcut safety:** shortcuts are opt-in (a "keyboard shortcuts" toggle in
  the analysis header); they never override browser or screen-reader
  bindings; the enabled set is exposed via `aria-keyshortcuts`; screen-reader
  users get the toggle off by default.
- Matrices: `role="grid"` with arrow-key navigation; tables have captions +
  `th scope`. Icon buttons carry `aria-label`; toasts use `role="status"`.
- All statuses convey icon+label+shape (never color alone); contrast ≥ WCAG AA.

---

## 43. Motion Behavior

- MICRO (150ms): hovers, focus, expand/collapse.
- NAV (220ms): workspace view swaps, drawer slides.
- DATA (300ms): readiness transitions, diff list updates — only when data
  changes; batch updates are instant.
- EXPLANATORY (≤900ms staged): pipeline reveal on Platform page.
- AMBIENT (6–20s loop): product-site hero only.
- No motion in data tables, coverage, source viewers, or docs.

---

## 44. Reduced Motion

`prefers-reduced-motion`: every animation becomes an instant state change.
Hero → static final diagram. Loading pulse → static highlight. No exceptions.

---

## 45. P0 Pages (must ship for v1.3.0 beta)

| Surface | Pages |
|---|---|
| Product site | Home · Platform · Capabilities (overview) · Benchmarks (overview + detail pattern) · Trust Center · Docs (getting started + concepts + reference shell) · Release v1.3.0 |
| Workspace | Overview · Validator · Clocks · Coverage · Readiness · Diff · Reports (incl. baseline) |
| Shared | Analysis header · Findings Explorer + Inspector · Source Viewer · CI/Policies page |

**Priority decision (not a suggestion):** the workspace track is the P0
must-ship — shell + Validator + Findings Explorer/Inspector + Source Viewer +
Overview + Readiness first, then Clocks/Coverage/Diff/Reports/CI. The product
site track (Home + Benchmarks + Trust + docs shell + Release) is P0 but can
ship immediately after the workspace shell, reusing the same tokens. The two
are independent streams. **Justification:** these cover the six user journeys
end-to-end (evaluate → validate → investigate → readiness → diff → CI)
without overbuilding. Interactions page ships as a section within
Readiness/Overview if full page is not ready; Context page folds into
Coverage.

## 46. P1 Pages

- Workspace: Interactions full page · Design Context full page · source syntax
  highlighting · light mode · docs search · rule pages for all 111 rules.
- Product site: individual capability pages for all 9 capabilities · full
  benchmark detail pages · engineering story page · specifications page ·
  performance charts with more series.

## 47. P2 Pages

- Workspace: column resizing · virtualized tables (>500 rows) · per-analysis
  history (local only) · saved filter presets.
- Product site: video/animated walkthrough · interactive platform playground ·
  release archive · multi-version docs.

---

## 48. Streamlit Implementation Feasibility

Per VDS §45 — the P0 workspace is **fully achievable** in Streamlit with
custom HTML/CSS:

| Workspace need | Streamlit plan |
|---|---|
| Shell (sidebar + header + main) | Sidebar + containers/columns; inspector as right rail via columns or overlay container |
| Dense tables | Custom HTML tables (styling control) |
| Status badges/markers | Custom HTML components |
| Relationship matrix | Custom HTML table (pattern already exists in reports) |
| Clock hierarchy (≤100 nodes) | Inline SVG via st.markdown |
| Bus coverage strip | Custom HTML/CSS |
| Source viewer | Custom HTML with line numbers + highlights |
| Loading stages | st.spinner-like custom stage list (honest, no fake %) |
| Animation | CSS transitions only; no JS |

**Accept:** no JS interactivity, no true virtualization, inspector as in-page
rail. **Defer:** drag-graph, smooth animated transitions → product frontend or
P2. The workspace must not fork the deterministic backend.

## 49. Separate Product Frontend Responsibilities

The product site (Home · Platform · Capabilities · Benchmarks · Trust · Docs ·
Release) is a **separate lightweight static frontend**:

- Owns: public narrative, evidence presentation, docs, release info.
- Reads content from the same sources as the product (single source of truth,
  per architecture §65): `rules_registry.py`, `support_boundary.py`,
  `RELEASE_MANIFEST.md`, benchmark manifests, version metadata.
- Does **not** run analysis; "Launch Validator" links to the workspace.
- No framework mandated; static/SSG preferred (fast, SEO, responsive).

---

## 50. Implementation Handoff Requirements

For the next coding phase (FRONTEND FOUNDATION + P0), the implementing agent
must receive:

1. This spec + VISUAL_DESIGN_SYSTEM.md + PRODUCT_EXPERIENCE_ARCHITECTURE.md.
2. The token set (VDS §47) as a single CSS/SCSS or JSON token file.
3. The component inventory (VDS §25) with states (VDS §26).
4. Verified data contracts: result JSON shapes (`check_sdc` result, readiness
   result, diff result, rules registry entry, support matrix scope) so mock UI
   renders real shapes from day one.
5. The P0 page list (§45) and the acceptance rules (no overclaim, no STA
   implication, statuses never color-only, READY ≠ signoff, JSON purity).
6. Test rule: the UI must render from *real* module outputs (fixtures derived
   from samples/) — no invented results.

---

## 51. Independent Reviewer Findings

Independent design review executed after drafting. Findings and resolutions:

| Sev | Finding | Resolution |
|---|---|---|
| MEDIUM | §13 scorecard example embedded "22 / 22" as literal content — a frontend engineer could hardcode it into the benchmark UI | Replaced with verified 9/9 golden runners; added a placeholder rule: template scorecards show `[n]/[n]` + "populate from runner output"; only verified Phase 14 numbers may appear literally (§13) |
| MEDIUM | §34 CLI snippet `sdc-tools gate check ...` was unverified | Verified against cli.py: the gate is `--gate`/`--gate-policy` on `check`. Snippet now shows the real commands with exit-code contract and a baseline-first workflow (§34) |
| MEDIUM | Findings Explorer default table risks overload if all 5 columns show full messages | Messages truncated to one line with ellipsis; full text in inspector; default filter = errors+warnings (§21) |
| MEDIUM | Readiness rail could be read as a percentage score | Rail re-labeled "evidence proportion within scope — not a quality score"; stated as a client-side derivation from per-dimension finding counts (no new backend field); overall status badge is the single headline datum (§32) |
| LOW | Performance charts could invite cross-tool comparison | Added explicit caption: indicative, not a benchmark against other tools; no extrapolation (§14) |
| LOW | "Launch Validator" CTA on every product page may over-promise the beta workspace | CTA retained (workspace is the product's core) but release page states beta scope clearly (§18) |
| LOW | Mobile summary mode might feel like a dead end | Persistent "open on desktop" note + all downloads still available (§41) |
| LOW | Keyboard shortcuts (`1`–`9`, `[`/`]`) could collide with screen-reader virtual cursors | Shortcuts are opt-in, never override browser/screen-reader bindings, exposed via `aria-keyshortcuts`, off by default for screen-reader users (§42) |
| INFO | P0 page set (16) is large for one stream | Upgraded to a decision: workspace track ships first; product-site track follows reusing the same tokens; independent streams (§45) |

Reviewer also confirmed: no generic-AI aesthetics; no glassmorphism; statuses
never color-only; benchmark claims honest and artifact-linked; hero is an
engineering visualization, not marketing motion; P0 excludes invented
features; nothing implies STA/signoff; the spec is implementable without
guessing.

---

## 52. Final Design Recommendation

1. **What should Ṛta visually feel like?** A precision engineering
   instrument — dark graphite, hairline borders, mono data, node/edge
   geometry, and quiet confidence. An instrument, not a dashboard.
2. **What makes its identity recognizably EDA?** The SILICON GRAPH primitive
   language (nodes, orthogonal arcs, bus bundles, clock-edge markers), the
   constraint-pipeline motif, and honest engineering vocabulary — not
   decorative circuits or AI aesthetics.
3. **Which visual direction?** SILICON GRAPH executed with PRECISION
   INFRASTRUCTURE restraint; TIMING INTELLIGENCE's status markers absorbed as
   a secondary motif (VDS §5).
4. **What should the hero look like?** The "Analysis Pulse" sequence: SDC
   command → constraint nodes → clock hierarchy → design objects → readiness
   (§8). Static under reduced motion.
5. **What should move/animate?** Hero background (product site only), micro
   hovers, view transitions, data-change transitions, the platform pipeline.
6. **What should never animate?** Tables, coverage, source viewers, docs, all
   workspace analysis surfaces — and anything that implies timing propagation.
7. **How should benchmarks be presented?** Scorecards with n/n counts,
   methodology drawers, artifact links, environment context, and an explicit
   "internal verified evidence, not independent certification" footer.
8. **How should readiness become a signature capability?** The dimension rail
   + overall badge + evidence panels on a dedicated workspace page, with
   "NOT STA signoff" always attached.
9. **How should clock intelligence be visualized?** Three coordinated views —
   inventory table, SVG hierarchy (≤100 nodes), and a symbol-encoded
   relationship matrix; structural, never propagating.
10. **How should coverage be visualized?** Direction bars + per-bit bus
    strips with an always-visible "coverage ≠ correctness" caption; never a
    single ring gauge.
11. **How should findings be investigated?** Explorer table → inspector rail →
    source viewer with dual-line provenance; filters never overload the default.
12. **How should trust boundaries appear?** As first-class, full-size content:
    Trust Center non-claims, capability-page boundary callouts, analysis-header
    trust chips, and READY/CI disclaimers everywhere those terms appear.
13. **What belongs on the product frontend?** Narrative, evidence, docs,
    benchmarks, trust, releases — static, fast, no analysis.
14. **What belongs inside Streamlit?** The entire workspace P0 — analysis,
    investigation, readiness, diff, reports, CI/policy.
15. **What Streamlit UI should be rebuilt?** Navigation (10 tabs → grouped
    sidebar), findings (expander cards → explorer+inspector), readiness and
    coverage (buried metrics → dedicated pages), empty/error states, emoji →
    icon system.
16. **What current UI should be retained?** Metric-card concept, severity
    semantics, expander progressive disclosure, dual-line provenance, download
    flows, rule-reference search, test-drive transparency, feedback widget.
17. **What is the minimum premium P0 experience?** §45 — 16 pages across both
    surfaces, dark theme, full status system, dense tables, honest evidence.
18. **What design work can wait until after beta?** Light mode, docs search,
    full rule pages, per-capability product pages, virtualized tables,
    animations beyond the three hero contexts, any product-history feature.
19. **What implementation risks exist?** Streamlit CSS/HTML limits (no JS —
    mitigated by the component plan), scope creep into invented features
    (mitigated by "render real module outputs only"), and the branding risk of
    drifting toward generic SaaS (mitigated by the anti-pattern list and the
    mandatory trust-boundary callout).
20. **What EXACTLY should the next coding phase implement first?** The
    **frontend foundation**: token file (VDS §47) + CSS theme + workspace
    shell (sidebar groups, analysis header, view-state navigation) + the
    Validator view with real `check_sdc` output rendered in the new Findings
    Explorer + Source Viewer, verified against real sample outputs — followed
    by Overview and Readiness pages. Product-site Home comes after the
    workspace shell, using the same tokens.

---

*End of High-Fidelity Product Specification. Design specification only — no production code was modified.*
