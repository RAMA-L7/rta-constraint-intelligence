# Ṛta — Workspace Information Architecture

> **Document kind:** product architecture blueprint (engineering application)
> **Status:** proposed — awaits founder approval · **Date:** 2026-08-07
> **Applies to:** `rta/workspace/` (engineering application; currently `webui/` SPA)
> **Predecessor docs:** `docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md`,
> `docs/product/HIGH_FIDELITY_PRODUCT_SPEC.md`, `docs/company/PRODUCT_CHARTER.md`
> **Related:** `FEATURE_MAPPING.md` (feature → route), `REPOSITORY_BLUEPRINT.md` §5
> (website/workspace separation)

---

## 1. Purpose

This document is the **blueprint of the engineering application** — how a
Physical Design, STA, or synthesis engineer moves through Ṛta from first launch
to completed analysis. It defines the first screen, the primary action, the
journey, and which tools are available before / after analysis.

**Governing principle:** the workspace is **workflow-first, not page-first**.
Engineers do not browse pages; they run a workflow: **Import → Analyze →
Understand → Export**. Navigation exists to support that workflow.

---

## 2. The engineer's journey (top level)

```
LAUNCH Ṛta
   │
   ▼
┌─────────────────────────────┐
│ FIRST SCREEN — New Analysis │   ← the only honest first step
└─────────────────────────────┘
   │  SDC (required) · Netlist (optional)
   ▼
ANALYZE  →  analysis timeline  →  workspace opens
   │
   ├──→ VALIDATION        (findings, severity, evidence)
   ├──→ CLOCK INTELLIGENCE (clock graph, inventory, matrix)
   ├──→ COVERAGE           (constraint coverage, bus coverage)
   ├──→ READINESS          (7 dimensions → verdict)
   ├──→ INTERACTIONS       (constraint conflicts/links)
   ├──→ DIFF               (baseline vs current — needs baseline)
   ├──→ CI                 (policy gate — needs policy)
   └──→ REPORTS / EXPORT   (evidence-backed outputs)
```

**First 10 seconds:** the engineer sees the Ṛta wordmark, one primary action
(**New Analysis**), and a short explainer. No walls of tools, no settings, no
dense tables — just "bring me a constraint file and I will analyze it."

---

## 3. First screen and first action

| Question | Answer |
|---|---|
| What is the first screen? | **New Analysis** (welcome + input surface) |
| What is the first action? | **New Analysis** → provide SDC |
| Why? | A constraint analysis tool is useless without constraints. Everything else is secondary until an analysis exists. |
| What is required? | SDC text or file. **Netlist is optional** and explicitly labeled as such, with a one-line reason ("enables design-aware checks; validation works without it"). |
| What is pre-filled? | A sample SDC (so the engineer can press Analyze immediately and see value). |

The old "all pages visible at launch" model is rejected: showing 15 tools before
analysis overwhelms and implies they all work without context. The workspace
**adapts to context**.

---

## 4. Tool availability model (pre / post analysis)

Tools fall into three classes. This is the heart of the information architecture.

### 4.1 Session tools — require an analysis

These consume the current Analysis Session and **unlock after analysis**:

| Tool | Why it needs the session |
|---|---|
| Validation | Findings are the session's core output |
| Clock Intelligence | Parsed clocks + relations from the session SDC |
| Coverage | Constraint/design coverage of the session |
| Readiness | 7-dimension assessment of the session |
| Interactions | Conflict/relationship analysis of the session |
| Diff | Requires baseline + current session |
| CI | Requires policy + current session (gate decision) |
| Reports / Export | Serialize session results |

### 4.2 Standalone / always-visible tools — never need an analysis

Two sub-classes here, both **visible before analysis** (founder Correction 4:
never hidden):

**Standalone tools** — complete products on their own, run on pasted input:

| Tool | Works without analysis? |
|---|---|
| Generator | ✅ creates SDC from options |
| Linter | ✅ edits SDC text directly |
| Converter | ✅ SDC ↔ JSON/YAML from text |
| Corner Manager | ✅ corner presets / generation |
| MMC | ✅ multi-corner SDC generation |
| Test Drive | ✅ runs engine over pasted SDC |

**Always-visible knowledge** — reference surfaces, not input-driven tools:

| Surface | Works without analysis? |
|---|---|
| Rules | ✅ rule reference (knowledge) |
| Trust | ✅ trust model (knowledge) |
| Documentation | ✅ in-app docs (knowledge) |
| Feedback | ✅ always |

> **Class vocabulary (single source):** `FEATURE_MAPPING.md` §2 — *session* /
> *standalone* / *always-visible*. Session tools unlock after analysis; the other
> two classes are reachable before analysis.

### 4.3 Navigation visibility rules

| Phase | What navigation shows |
|---|---|
| Before analysis | **Home / New Analysis** · Recent Sessions · Documentation · Settings — and the standalone tools group |
| After analysis | Everything: session tools unlocked, plus Results group at top |
| After baseline/policy exists | Diff and CI fully enabled |

Never-hidden (always reachable): **New Analysis**, **Recent Sessions**,
**Standalone tools group**, **Documentation**, **Settings**.

Never-under-"More": Validate, Generate, Linter, Converter, Corner Manager, MMC,
Clock Intelligence, Coverage, Design Context, Constraint Conflicts, Readiness,
Diff, CI, Rules, Trust, Documentation, Test Drive, Feedback.

---

## 5. Navigation structure (proposed)

```
START
  New Analysis            ← primary action, always present
  Recent Sessions

ANALYZE  (session tools — appear after analysis)
  Validation
  Clock Intelligence
  Coverage Intelligence
  Design Intelligence

DECIDE  (session tools — appear after analysis)
  Readiness
  Change Intelligence (Diff)
  CI

OUTPUT
  Reports
  Export

KNOWLEDGE  (always)
  Rules
  Trust
  Documentation

TOOLS  (standalone — always)
  Generator
  Linter
  Converter
  Corner Manager
  MMC
  Test Drive
  Feedback
```

Group labels (START / ANALYZE / DECIDE / OUTPUT / KNOWLEDGE / TOOLS) express
the workflow. This is the approved navigation vocabulary from Sprint 3B, kept
intact here.

---

## 6. Session-first architecture

Everything the engineer does after import belongs to an **Analysis Session**:

```
Analysis Session
├── inputs       SDC (required) · netlist (optional) · custom rules (optional)
├── results      findings · clocks · coverage · readiness · interactions
├── context      policy (for CI) · baseline (for diff)
└── outputs      reports · export artifacts
```

- The session is the single source of truth for a given analysis run.
- Switching sessions swaps all results atomically (state isolation is tested —
  `benchmarks/test_ui_state_isolation.py`).
- **No partial analysis state:** the workspace never shows results that mix two
  sessions.

---

## 7. Workflow details

### 7.1 Import (New Analysis)
1. SDC — required; file picker, paste, or sample.
2. Netlist — optional; one-line explainer why optional.
3. Advanced options — custom rules (YAML, optional), CI gate policy, baseline.
4. **Analyze** — the only primary CTA on the screen.

### 7.2 Analyze (transition)
- Indeterminate semantic timeline: PARSE → CONTEXT → VALIDATE → READINESS.
  No fake percentages; the backend returns a real per-stage status.
- On completion the workspace **auto-navigates to Validation** — the engineer
  is never left asking "where are my results?"

### 7.3 Understand
- Validation (findings explorer + inspector), Clock Intelligence (graph +
  inventory + matrix), Coverage, Readiness (dimension rail), Interactions.
- Every engineering page answers: **What is this? · Why should I care? · What
  should I do next?**

### 7.4 Export
- Reports (HTML/JSON) and evidence exports available from session results.
- Diff and CI require their respective context (baseline / policy) — the UI
  explains what is missing rather than failing silently.

---

## 8. Beginner vs expert

| | Beginner | Expert |
|---|---|---|
| Entry | New Analysis → sample → Analyze | Recent Sessions → reopen |
| Guidance | One CTA per screen; explainers on every engineering page | Keyboard-first, dense tables, batch CLI parity |
| Navigation | Visible groups, everything labeled | Collapse to session tools + command palette (future) |
| The same engine | ✅ identical deterministic backend | ✅ identical |

Both paths lead to the same backend — beginners are guided, experts are never
slowed down.

---

## 9. Information density rules

- The workspace is **denser than the website** (engineering app) but never
  cluttered: one primary action per screen.
- Findings use an explorer + inspector split (list on left, detail on right).
- Readiness uses a dimension rail, not a fake gauge/score.
- Coverage uses bus-bit and per-constraint visualizations, not generic charts.
- Diff is change-review: baseline → current, NEW/RESOLVED/CHANGED/UNCHANGED.

---

## 10. Open questions (workspace-specific)

1. **Session persistence:** in-browser only (localStorage) vs server-side
   session store in a future `rta/workspace/` service? (Deferred — current SPA
   keeps state client-side.)
2. **Command palette:** Sprint 3B placeholder — build in the Product Experience
   sprint, not this architecture phase.
3. **Tools pages:** standalone tools currently live as workspace routes; confirm
   they stay in-workspace (recommended) rather than becoming separate apps.

---

## 11. Consistency with the Charter

- ✅ First action = New Analysis (matches founder Sprint 3C feedback).
- ✅ Netlist optional with an explicit reason (matches charter + feedback).
- ✅ Advanced tools unlock after analysis (matches feedback: no overwhelm).
- ✅ Tools are first-class, never hidden (matches founder Correction 4).
- ✅ No mocked data — every view consumes real backend results.

---

*Workspace IA complete. This is the blueprint the Product Experience sprint
implements inside `rta/workspace/`.*
