# PHASE 17 — New UI Specification

> From-scratch specification for the separate-frontend Ṛta workspace.
> This is the implementation contract for `webui/` + `api_server.py`.
> Internal engineering document — not a public milestone.

Design DNA: docs/product/PRODUCT_WEBSITE_DESIGN_DNA.md (SILICON GRAPH /
PRECISION INFRASTRUCTURE). Architecture: docs/product/PHASE17_FRONTEND_ARCHITECTURE_DECISION.md.

---

## 1. Experience model

The user opens the application and immediately reads **"a specialized
semiconductor constraint-analysis environment"**:

```
┌──────────────────────────────────────────────────────────────────────┐
│ SDC VALIDATOR   design_top.sdc · netlist: off · SDC_ONLY   v1.3.0    │  TOP BAR
├──────────────┬───────────────────────────────────────────────────────┤
│ NAV          │  PAGE TITLE + STATUS                                 │
│              ├───────────────────────────────────────────────────────┤
│ ANALYZE      │                                                       │
│   Overview   │                 ACTIVE WORKSPACE                      │
│   Validator  │        (dense tables · visualizations · actions)      │
│   Clocks     │                                                       │
│ DESIGN       │                                                       │
│   Context    │                                                       │
│   Coverage   ├───────────────────────────────────────────────────────┤
│ QUALITY      │  ANALYSIS / TRUST / READINESS STATUS RAIL             │
│   Interactions│                                                      │
│   Readiness  │                                                       │
│ CHANGE       │                                                       │
│   Diff       │                                                       │
│ OUTPUT       │                                                       │
│   Reports    │                                                       │
│   CI         │                                                       │
│ TOOLS        │                                                       │
│   Generator  │                                                       │
│   Linter     │                                                       │
│   Converter  │                                                       │
│   Corners    │                                                       │
│   MMC        │                                                       │
│   Rules      │                                                       │
│   Test Drive │                                                       │
│   Feedback   │                                                       │
└──────────────┴───────────────────────────────────────────────────────┘
```

- **Top bar**: brand, active file/netlist/mode context, trust + readiness
  status chips, version. Uses only data that exists.
- **Left nav**: grouped (ANALYZE/DESIGN/QUALITY/CHANGE/OUTPUT/TOOLS), one
  active item, indicator-rail microinteraction, keyboard navigation.
- **Main area**: page title system (section label / page title / purpose) then
  page content.
- **Status rail**: compact technical rail (errors/warnings/info + trust +
  readiness) — not metric cards.

## 2. Global background (Layer 0–5)

Canvas-drawn technical topology across the whole workspace, behind content:

- **Layer 0** graphite base `#0B0E14`
- **Layer 1** subtle technical grid (CSS linear-gradient, low opacity)
- **Layer 2** sparse netlist topology: nodes (ports/cells) joined by paths
- **Layer 3** routing/constraint edges; occasional pulse travels an edge
- **Layer 4** a clock-edge pulse occasionally propagates through a small branch
- **Layer 5** localized depth gradient (radial, near top-left)

Rules: nodes idle-illuminate extremely subtly; the graph never moves position;
movement is slow and purposeful; paused when the tab is hidden; **disabled
entirely under `prefers-reduced-motion`** (content stays, static grid only).

## 3. Motion system

| Level | Used for | Duration | Notes |
|---|---|---|---|
| AMBIENT | background topology | slow | canvas; paused on hidden tab |
| EXPLANATORY | clock tree build, readiness dimension resolution, coverage resolution | 300–600ms | sequential short steps after analysis completes |
| INTERACTION | hover/focus/selected/filter/accordion | 120–200ms | ease-out |
| PAGE | route change | 180–260ms | fade + 8px translate; respects reduced motion |

**Never animate**: findings tables, source viewers, coverage detail lists while
scrolling, matrix cells while reading. `prefers-reduced-motion` → all
nonessential animation disabled, information fully available.

## 4. Analysis transition (honest, no fake progress)

On ANALYZE the UI shows a **stage tracker** — PARSE → CLOCKS → DESIGN CONTEXT →
CONSTRAINT QUALITY → READINESS — advancing only on real HTTP completion of each
API stage (the server performs stages sequentially and reports them). If a
stage has no distinct backend step it is skipped, never faked with a timer.

## 5. Page specifications

### 5.1 Overview (control center)
Priority: **readiness** → trust → blockers → clock health → coverage →
interactions → change status → actions. Hierarchy via weight, not cards.
Clicking a blocker/clock links to the owning page (Validator/Clocks).

### 5.2 Validator
- **Input surface**: code-style SDC textarea with line numbers, monospace,
  drag/drop + file picker, file state, optional netlist upload, baseline upload
  + gate select, custom-rules upload, ANALYZE button.
- **Summary rail**: compact errors/warnings/info/clocks + trust + readiness.
- **Findings explorer**: severity/rule/search filters (presentation only),
  dense table: Severity · Rule · Finding · Object · Clock · Loc.
- **Finding inspector**: right-side contextual panel — rule, severity, summary,
  why detected, affected object, clock, evidence, source provenance with
  Lx ↔ Ly dual-line, trust/context, STA follow-up when explicitly flagged,
  rule doc reference.
- **Source viewer**: line numbers, finding-line highlights, dual-line ↔
  markers, context around findings, copy line.
- Secondary panels: scope / coverage / interactions / readiness / baseline
  diff / custom rules.

### 5.3 Clock Intelligence (signature)
Three coordinated views:
- **Clock inventory**: dense table — Clock · Type · Period · Frequency · Source
  · Master · Generated · Relations · Status; row click → inspector.
- **Clock hierarchy**: SVG clock tree — PRIMARY node pulsing slowly, generated
  branches branching visibly, divide labels, pulse propagates into branches
  (explanatory, never timing simulation). Large designs (>40 nodes) fall back
  to a searchable tree/table.
- **Relation matrix**: symbols + labels + colors (never color alone), sticky
  labels, hover highlights row/column, legend.

### 5.4 Design Context
Netlist status, top module, object counts, compact hierarchy tree (from real
`parse_verilog` output), collection-resolution table (resolved/empty/
unsupported), trust upgrade note. No schematic rendering.

### 5.5 Coverage
Object/evidence-oriented: inputs, outputs, buses, partial, unconstrained,
exempt, unknown, n/a — from `design_coverage.to_dict()`. **Bus visualization**:
`data_in[31:0]` strip showing constrained vs missing ranges with exact
evidence on hover. Prominent disclosure: **COVERAGE ≠ CORRECTNESS**.

### 5.6 Interactions
Constraint↔constraint representation: Constraint A ⇄ interaction ⇄ Constraint
B with type (DUPLICATE / OVERRIDE / CONTRADICTION / OVERLAP-STA), rule, Lx ↔ Ly,
objects, reason, STA follow-up callout. Provable conflict visually distinct
from needs-STA overlap.

### 5.7 Readiness (signature)
Overall status → **7-dimension rail** (CLOCKS, I/O, EXCEPTIONS, COVERAGE,
CONSISTENCY, ANALYSIS_TRUST, DESIGN_CONTEXT) → BLOCKERS → REVIEW ITEMS →
ADVISORIES → actions (P0–P3 from backend) → disclosure **READY ≠ STA SIGNOFF**.
No gauge, no invented percentage. Dimension resolution animates on analysis
completion (result presentation, not analysis progress).

### 5.8 Diff
Change-review: BASELINE → CURRENT header with readiness transition, gate
result, context compatibility, trust change; filters NEW / RESOLVED / CHANGED /
UNCHANGED; CHANGED rows show before → after (severity/value/status) from real
snapshot evidence; coverage delta, trust delta, context delta, debt. Identity
based on structured finding identity, not line numbers.

### 5.9 Reports
Artifact cards for real outputs only: HTML report, JSON result, readiness
snapshot, baseline. Purpose · status · action (download). Generated via the
frozen `reporter.py` + `readiness_diff.build_snapshot`.

### 5.10 CI / Policies
Policy selector (BLOCKERS_ONLY / NO_READINESS_REGRESSION / STRICT / CUSTOM),
gate behavior, engine-failure guarantee, what fails/passes, CUSTOM policy
preview + validation, CLI command snippet (`sdc-tools check --gate …`), GitHub
Actions example. Real `policy_engine` + `evaluate_gate` data.

### 5.11 Tools (functional, same shell)
Generator, Linter, Converter, Corner Manager, MMC SDC, Rules, Test Drive,
Feedback — each a real API-backed page in the new shell. No old-UI island.

## 6. Status system (never color alone)

Every status renders **icon + label + shape/pattern + color**:
severity (FATAL/ERROR/WARNING/INFO), trust (VALIDATED/PARTIAL/NETLIST/TCL EXEC/
UNSUPPORTED/NOT CHECKED), readiness (READY/READY+/REVIEW/BLOCKED/LIMITED/N/A),
diff (NEW/RESOLVED/CHANGED/UNCHANGED), pass/fail. Metadata comes from the
single source of truth (`ui/theme.py`) via `GET /api/design`; the frontend
renders it — it never invents labels.

## 7. Components (product-owned, not dashboard cards)

SDCButton · SDCNav · AnalysisHeader · AnalysisSurface · FindingRow ·
FindingInspector · SourceViewer · ClockNode · ClockTree · RelationMatrix ·
BusCoverage · ConstraintLink · ReadinessRail · TrustBadge · EvidencePanel ·
DiffRow · BaselineComparison · CommandViewer · UploadZone · AnalysisInput ·
TechnicalTooltip · StatusPill. Restraint: hierarchy via spacing, surface
contrast, borders, typography — not shadows/glassmorphism.

## 8. Empty / error / loading states

- **Empty**: No analysis / No SDC / No netlist / No findings / No baseline /
  No diff — each answers *what does this mean* and *what can I do next*.
- **Error**: distinguished INVALID INPUT / UNSUPPORTED ANALYSIS /
  INSUFFICIENT CONTEXT / INCOMPATIBLE BASELINE / ENGINE FAILURE / FILE FAILURE
  / POLICY ERROR — never one red box; raw traces never shown to users.
- **Loading**: stage tracker (above); no fake percentages.

## 9. Responsive

Desktop-first: 1920 / 1440 / 1280 / 1024. Below 1024 the nav collapses to an
icon rail; inspectors stack; tables scroll horizontally; matrix scrolls
internally. Mobile is best-effort for the workspace; the product website
remains the mobile-optimized surface.

## 10. Security

Every user-controlled value (SDC, object names, clock names, netlist
identifiers, baseline content, policy content) is escaped at render time via a
tested JS `esc()`; SVG/HTML/tooltips/inspectors all go through it. Adversarial
probes (`<script>`, `<img onerror>`, quotes, ampersands, angle brackets) must
render inert.

## 11. Accessibility

- Visible focus-visible rings; logical tab order; Enter/Space activation;
  Escape closes the inspector; no global shortcuts that fire while typing.
- Status never depends on color alone (icon+label+shape).
- All visualizations have textual equivalents (tables/trees alongside graphs).
- `prefers-reduced-motion` honored globally.

## 12. Delivery checklist (implementation contract)

- `api_server.py` — stdlib-only; endpoints in §5 of the ADR.
- `webui/index.html` + `webui/assets/*.css` + `webui/assets/*.js` — no build step.
- `sdc-tools web` → launches `api_server.py`.
- Wheel ships `api_server` + `webui/` assets; clean-room re-verified.
- UI benchmarks rewritten to the API with equal behavioral coverage.
- MOTION-01..10 checks; screenshots; interactive browser verification.
