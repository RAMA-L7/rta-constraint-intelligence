# Ṛta — Product Design Specification

> **Document kind:** definitive user-experience specification for Ṛta Version 1.
> **Status:** implementation reference · **Baseline:** Ṛta v1.3.0 · **Scope:** Block-Level Constraint Intelligence
> **Supersedes:** this document defines the behavioral contract. Visual implementation details (tokens, colors, typography, components) are in `VISUAL_DESIGN_SYSTEM.md`. Wireframes are in `HIGH_FIDELITY_PRODUCT_SPEC.md`. Page architecture is in `PRODUCT_EXPERIENCE_ARCHITECTURE.md`.
> **Date:** 2026-08-07

---

## Preamble

This document defines how Ṛta should *behave* from a user's perspective. It is not a visual design system. It is not a wireframe set. It is not an architecture document. It is the specification that a reviewer reads to determine whether the product as built matches the product as intended.

Every claim in this document is testable. Every rule has a rationale. Every invariant is enforceable.

---

## Part I: The Experience

---

### 1. First-Run Experience

The first time an engineer opens Ṛta, they should understand the product within 10 seconds.

**Sequence:**

1. **The engineer sees the workspace.** Dark background. Left sidebar with grouped navigation. Center area with a clear call to action. Top bar with the Ṛta brand and version.
2. **The engineer sees the sample SDC.** The workspace loads with a sample SDC pre-loaded. The sample is real — it has clocks, delays, exceptions, and two intentional defects (SDC-008 and SDC-030). It is not a toy. It is not a "hello world." It is a block-level constraint set that demonstrates the product's capabilities.
3. **The engineer can run the sample immediately.** One click. No upload required. No configuration required. No login required. The analysis runs, and the engineer sees findings with severity, rule code, message, and source line.
4. **The engineer understands the output.** Findings are presented in a dense table. Each row has: severity icon + label, rule code (mono), finding message, object name (mono), source line. The overall readiness verdict is visible in the analysis header. The trust scope is visible in the trust strip.
5. **The engineer can investigate.** Clicking a finding opens the finding inspector: rule documentation, why it was detected, the constraint text, evidence, source provenance, trust scope, and whether STA follow-up is needed. The engineer understands the finding without leaving the workspace.
6. **The engineer can try their own SDC.** A prominent "Load SDC" action is visible. Drag-and-drop or file picker. Pasting SDC text is supported. The engineer can replace the sample in under 10 seconds.

**Emotional impression:** "This is a serious engineering tool. It does something specific, and it does it with evidence. I can trust it."

**What must NOT happen on first run:**
- No tutorial overlay that blocks interaction.
- No onboarding modal that requires dismissal.
- No login screen, no account creation, no telemetry opt-in.
- No "Welcome to Ṛta!" splash. The product introduces itself through its behavior, not its copy.
- No blank state that says "Upload a file." The sample is the introduction.

---

### 2. Returning Engineer Experience

When an engineer returns to Ṛta after using it before, the experience should feel continuous.

**Sequence:**

1. **The workspace opens.** Same layout, same navigation, same dark theme. No layout shifts, no surprises.
2. **The previous analysis state is NOT preserved.** Ṛta does not persist analysis state between sessions. This is a deliberate design decision. Each session starts fresh with the sample SDC. The engineer loads their SDC explicitly.
3. **The engineer loads their SDC.** Same drag-and-drop, same file picker, same paste workflow. The analysis runs immediately.
4. **The engineer sees their findings.** Same dense table, same severity system, same trust disclosures. The experience is consistent.

**Why no persistence:**
- The product runs locally. There is no server-side state.
- Session state in a browser tab is ephemeral and unreliable.
- The engineer's workflow is: load SDC → analyze → investigate → export → close. Persistence across sessions would require storage decisions (localStorage? IndexedDB?) that add complexity without proportional value for a local analysis tool.
- Baselines (saved snapshots) provide the persistence mechanism that matters: the engineer saves a baseline, and later loads it for diff/comparison. That is the deliberate persistence path.

**What persists across sessions:**
- The `rta` CLI stores baselines as JSON files on disk (engineer-specified path).
- The workspace allows exporting baselines for the same purpose.
- The workspace does NOT auto-save SDC files, netlists, or analysis state to disk.

---

### 3. Analysis Session Lifecycle

An analysis session is the unit of work in Ṛta. It begins with an SDC input and ends with an exported result.

**Stage 1: Input**

The engineer provides an SDC file. This can be:
- A file drag-and-dropped onto the workspace.
- A file selected via file picker.
- SDC text pasted into the text area.
- The pre-loaded sample (default).

Optionally, the engineer provides:
- A Verilog netlist for design-aware mode.
- A baseline snapshot for diff/comparison.
- A policy file for CI gate evaluation.

**Stage 2: Analysis**

The workspace sends the SDC (and optional inputs) to the API server. The server runs the frozen deterministic pipeline:
1. Preprocessing (normalize SDC text).
2. Tcl variable resolution (bounded).
3. Rule engine (112 rules → findings).
4. Clock analysis (inventory + relations).
5. Design context resolution (if netlist provided).
6. Coverage analysis (object-level, bus-level).
7. Interaction analysis (duplicates, overrides, conflicts).
8. Readiness aggregation (seven dimensions).
9. Trust scope disclosure.
10. Baseline comparison (if baseline provided).
11. Gate evaluation (if policy provided).

The analysis is deterministic. The same SDC produces the same result every time.

**Stage 3: Investigation**

The engineer explores the results:
- Overview page: overall readiness, trust scope, critical findings, clock count, coverage summary.
- Validator page: findings explorer with filters (severity, rule, category), finding inspector with evidence and provenance.
- Clocks page: inventory, hierarchy, relationship matrix.
- Coverage page: per-port status, bus bit-range strips.
- Interactions page: duplicates, overrides, contradictions, overlaps.
- Readiness page: dimension rail, blockers, review items, actions.
- Diff page: baseline comparison (if baseline loaded).
- CI page: policy evaluation (if policy loaded).

**Stage 4: Export**

The engineer exports results:
- HTML report: self-contained evidence document for sharing or archiving.
- JSON output: machine-readable findings for pipeline integration.
- Snapshot: versioned baseline for future comparison.
- JUnit XML: CI ingestion.

**Stage 5: Close**

The engineer closes the workspace. No state is lost that matters — the findings were investigated, the report was exported, and the baseline was saved (if applicable).

---

### 4. Session Persistence Philosophy

**Principle:** The workspace is a stateless analysis instrument, not a stateful application.

- The workspace does not persist SDC files, netlists, analysis results, or session state across browser sessions.
- Baselines are the persistence mechanism. They are explicit, engineer-initiated, and file-based.
- The CLI provides the same persistence model: `--save-baseline` writes a JSON file; `--baseline` reads one.
- The workspace and CLI use the same persistence format (schema v2 baselines). An engineer can save a baseline in the CLI and load it in the workspace, or vice versa.

**What this means for implementation:**
- No localStorage auto-save.
- No IndexedDB.
- No session恢复 on page reload.
- The sample SDC is the default starting point for every session.
- The "Load SDC" action is the primary interaction.

---

### 5. Navigation Philosophy

The workspace navigation answers one question at every level: "Where am I, and what can I do next?"

**Structure:**

```
ANALYZE     Overview · Validator · Clocks
DESIGN      Context · Coverage
QUALITY     Interactions · Readiness
CHANGE      Diff
OUTPUT      Reports · CI / Policies
```

**Rules:**

1. **Grouped by intent, not by module.** The groups (ANALYZE, DESIGN, QUALITY, CHANGE, OUTPUT) describe what the engineer is doing, not which backend module is running.
2. **The Overview page is the landing page.** After analysis, the engineer lands on Overview. It answers: "Is there a problem? How serious? Can I trust this? Where do I investigate?"
3. **Navigation is one click to any page.** The sidebar is always visible (collapsible to icon rail on tablet). No hamburger menu on desktop.
4. **The current page is always highlighted.** Active state = accent left rule + filled icon + label weight change.
5. **Navigation never loses context.** Switching pages does not discard the current analysis. The analysis results are held in memory and available on every page.
6. **The analysis header is always visible.** The top bar shows: current SDC file, netlist status, analysis mode, trust chip, readiness chip, timestamp. This context is never hidden.

**Product site navigation** (separate surface):

```
Platform · Capabilities · Benchmarks · Trust · Docs · Release   [Launch Ṛta]
```

The product site and the workspace are distinct surfaces connected by one-click bridges. The product site never hosts live analysis. The workspace never hosts marketing.

---

### 6. Evidence Presentation Philosophy

Evidence is the product's core value. Every number, finding, and status must be traceable to a deterministic computation.

**Hierarchy of evidence:**

| Level | What the engineer sees | Click depth |
|---|---|---|
| **Summary** | Overall readiness badge, finding counts, trust chip | 0 (always visible) |
| **Finding** | Severity + rule code + message + object + line | 1 (findings table) |
| **Inspector** | Rule documentation, why detected, constraint text, evidence, provenance, trust scope | 2 (click finding → inspector) |
| **Source** | SDC text with line numbers and finding highlights | 3 (click source link in inspector) |
| **Artifact** | Benchmark runner, golden suite, phase report | 4+ (external link) |

**Rules:**

1. **Evidence precedes conclusions.** A finding shows its evidence (rule, line, message) before the engineer interprets it. The product does not tell the engineer what to think — it shows them what it found and lets them decide.
2. **Every number is traceable.** A count of "780 tests" links to the test suite. A benchmark of "9/9 golden" links to the runner. A finding of "SDC-008" links to the rule definition.
3. **No numbers without context.** Every performance number includes: OS, Python version, date, version. Every benchmark number includes: methodology, corpus size, environment.
4. **Evidence is not marketing.** Benchmark numbers are presented as "Verified Test Evidence" or "Internal Release Benchmark" — never as "industry-leading" or "certified."

---

### 7. Trust Presentation Philosophy

Trust is the product's most important differentiator. It is not a footnote. It is a first-class feature.

**How trust is communicated:**

1. **The trust strip** (always visible in the analysis header): compact icons + labels showing what was validated, partially validated, and skipped. The engineer sees this before they see any finding.
2. **Per-finding trust** (in the finding inspector): each finding carries its trust scope — was this finding produced from SDC-only analysis, or was it upgraded by design context?
3. **The trust center** (on the product site): a dedicated page explaining what Ṛta validates, what it partially validates, what requires design context, what requires Tcl execution, what is unsupported, and what it does NOT claim.
4. **The readiness disclaimer** (on every readiness surface): "This is a constraint-readiness review, not STA signoff."
5. **The coverage disclaimer** (on every coverage surface): "Coverage is not correctness."
6. **The CI disclaimer** (on every gate result): "CI pass does not mean timing closure."

**Trust never disappears.** It is not hidden behind an info icon. It is not collapsed by default. It is not a tooltip. It is visible, prominent, and persistent on every surface that presents analysis results.

---

### 8. Deterministic Analysis Explanation

The product's deterministic nature is a feature, not a limitation. It must be explained without overwhelming the user.

**How to explain determinism:**

1. **In the hero / product site:** "Identical input produces identical output. Every time."
2. **In the workspace loading state:** Stage-based progress (parsing → clocks → context → coverage → interactions → readiness → result). No fake percentages. No spinners that imply uncertainty. Completed stages get checkmarks. Current stage gets a pulse.
3. **In the analysis header:** The trust strip communicates scope. "SDC-only mode" or "Design-aware mode" is always visible.
4. **In the findings:** Each finding traces to a rule, a line, and an evidence message. The engineer can verify the finding by reading the SDC.
5. **In reports:** The report footer states: "Generated by Ṛta v1.3.0. Deterministic analysis — not an STA timing signoff."

**What NOT to say:**
- "AI-powered analysis" — there is no AI in Version 1.
- "Smart detection" — detection is rule-based, not smart.
- "99% accuracy" — accuracy implies probabilistic measurement. The tool is deterministic; it either finds the issue or it does not.
- "Automated review" — the tool provides evidence for human review, not automated judgment.

---

### 9. Visual Hierarchy for Engineering Evidence

The visual hierarchy answers: "What should the engineer notice first?"

**Priority order:**

1. **Readiness verdict** (overall status badge, large, top-left of Overview). This is the single most important datum.
2. **Trust scope** (trust strip in the analysis header). This tells the engineer how much to trust the verdict.
3. **Error findings** (top rows of the findings table, left-rule tinted). These are the blockers.
4. **Warning findings** (below errors). These need review.
5. **Clock summary** (clock count + hierarchy mini-diagram). Clock problems are the most common constraint defect.
6. **Coverage summary** (input/output constrained proportions). Coverage gaps are the second most common defect.
7. **Interactions count** (duplicates/overrides/conflicts). These are less common but higher severity when present.
8. **Next actions** (readiness page, P0–P3 recommended actions). The product tells the engineer what to do next.

**What should NOT dominate:**
- Benchmark numbers on the workspace (they belong on the product site).
- A single "percentage ready" gauge (no such number exists).
- A visual that implies timing propagation or signoff.

---

### 10. Engineer Understanding Before Export

Before the engineer exports a report, they should understand:

1. **What the tool checked.** The trust strip and analysis scope disclose the validated/partial/skipped boundaries.
2. **What the tool found.** The findings table lists every finding with severity, rule, and evidence.
3. **What the tool did NOT check.** The trust disclosure explicitly states: "Object references require a netlist" or "Tcl execution constructs were detected but not executed."
4. **What the readiness verdict means.** The readiness page states: "READY means the constraint set satisfies the validator's readiness criteria. It is not STA signoff."
5. **What the coverage means.** The coverage page states: "Coverage is not correctness. A fully constrained object can still have incorrect timing intent."

The report itself carries these same disclosures. An engineer reading the report without seeing the workspace should understand the same boundaries.

---

## Part II: Product Design Invariants

These are rules that must never be broken. They apply to every surface, every release, and every contributor. They are derived from the Product Charter's principles and are enforced through the product review process.

---

### Invariant 1: Evidence always precedes conclusions.

A finding shows its evidence (rule, line, message) before the engineer interprets it. The product does not tell the engineer what to think — it shows them what it found.

### Invariant 2: READY never implies timing signoff.

Every surface that presents a readiness verdict carries the disclaimer: "This is a constraint-readiness review, not STA signoff." This disclaimer is not collapsible, not dismissible, and not a footnote.

### Invariant 3: Every engineering claim has traceable evidence.

No number appears on the website, in a report, or in a CLI output that does not have a rerunnable artifact behind it. Stale numbers are trust failures.

### Invariant 4: Motion explains engineering activity.

Animation shows what the system is doing (pipeline flow, hierarchy resolution, state transitions). It never decorates. It never delays comprehension. It never implies timing propagation.

### Invariant 5: No AI-generated engineering conclusions.

Version 1 contains no LLM, no model inference, no probabilistic reasoning. Every finding is produced by a deterministic rule. This is a permanent product identity, not a current limitation.

### Invariant 6: Every user-facing number is traceable to deterministic computation.

Test counts, rule counts, benchmark counts, performance numbers — all are derived from artifacts, not from hardcoded strings. If the artifact changes, the number changes.

### Invariant 7: Empty states teach.

Every empty state explains what the absence means and what the engineer should do next. "Nothing here" is never the complete message. The empty state is an opportunity to educate.

### Invariant 8: Errors explain next actions.

Every error state includes a suggested next action. "Cannot parse" is followed by "Check line N." "Netlist required" is followed by "Add a netlist for design-aware mode." The engineer is never left wondering what to do.

### Invariant 9: Coverage never implies correctness.

Every surface that presents coverage carries the disclaimer: "Coverage is not correctness. A fully constrained object can still have incorrect timing intent." This is not a footnote — it is a first-class disclosure.

### Invariant 10: CI pass never implies silicon success.

Every surface that presents a gate result carries the disclaimer: "CI pass does not mean timing closure." The gate protects against regression. It does not guarantee correctness.

### Invariant 11: Trust status is never hidden.

Trust disclosures are visible, prominent, and persistent on every surface that presents analysis results. They are not collapsible. They are not behind an info icon. They are not tooltips.

### Invariant 12: Status never depends only on color.

Every status carries icon + label + shape. Color is a reinforcement, never the sole carrier. This applies to severity, readiness, trust, diff status, and coverage status.

### Invariant 13: The deterministic engine never produces a passing result on failure.

Exit code 3 (engine failure) can never produce a passing verdict or a passing exit code. This invariant is tested by `test_engine_failure_never_passes`.

### Invariant 14: Findings trace to source lines.

Every finding has a line number (and line₂ where two lines matter). The engineer can locate the finding in the SDC. Findings without provenance are not findings — they are opinions.

### Invariant 15: The SDC standard vocabulary is never renamed.

`create_clock`, `set_clock_groups`, `set_input_delay`, `SDC-001` — these belong to the standard. Brand lives on product surfaces, never on the standard's language.

### Invariant 16: The workspace is stateless between sessions.

The workspace does not persist SDC files, netlists, or analysis state across browser sessions. Baselines are the deliberate persistence mechanism. This is a design decision, not a limitation.

### Invariant 17: The product runs offline.

No network, no cloud, no external API required for analysis. Data never leaves the machine. This is a trust boundary, not a feature flag.

### Invariant 18: The product never fabricates progress.

Loading states show honest, stage-based progress. No fake percentages. No spinners that imply the tool is "thinking." Completed stages get checkmarks. Current stage gets a pulse. Skipped stages are struck through.

### Invariant 19: Every finding has a severity, rule code, and evidence message.

Findings without these three elements are not findings. The severity indicates impact. The rule code identifies the check. The evidence message explains why the check fired.

### Invariant 20: The product never implies capabilities it does not have.

The product does not compute timing. It does not propagate clocks. It does not calculate slack. It does not run STA. Every surface is honest about what the tool does and does not do.

### Invariant 21: Evidence numbers are never approximate.

"The parser golden suite passes 22/22" means exactly 22. Not "approximately 22." Not "about 22." Not "22+." Exact numbers, verified by runners.

### Invariant 22: The trust model vocabulary is consistent across all surfaces.

The six trust statuses (VALIDATED, PARTIALLY_VALIDATED, NETLIST_REQUIRED, TCL_EXECUTION_REQUIRED, UNSUPPORTED, NOT_VALIDATED) use the same names everywhere — CLI, workspace, reports, website, documentation. No abbreviations. No synonyms.

### Invariant 23: The product never presents a finding without a fix suggestion.

Every finding in the rule registry has a "fix" field. The finding inspector shows this fix. The engineer is never left without a suggested remediation.

### Invariant 24: The workspace always shows the analysis header.

The top bar always shows: SDC file, netlist status, analysis mode, trust chip, readiness chip, timestamp. This context is never hidden during navigation.

### Invariant 25: The product never uses "AI-powered" or equivalent language.

This applies to all surfaces: website, workspace, reports, documentation, code comments, commit messages, and public communication. The product is deterministic. Language that implies AI undermines trust.

### Invariant 26: Every page has a trust callout or boundary note.

Every workspace page that presents analysis results includes a trust-relevant disclosure: what was checked, what was not, and what requires further analysis. No page is exempt.

### Invariant 27: The product never auto-resolves uncertain findings.

When the tool is uncertain (e.g., a wildcard pattern, an ambiguous reference, a Tcl execution construct), it discloses the uncertainty. It does not guess. It does not "resolve" uncertain findings automatically.

### Invariant 28: Every benchmark claim is labeled as internal evidence.

Benchmark numbers are presented as "Verified Test Evidence" or "Internal Release Benchmark." They are never presented as "industry benchmark," "independent certification," or "third-party validation."

### Invariant 29: The product never shows a percentage readiness score.

Readiness is a categorical verdict (READY / READY_WITH_ADVISORIES / REVIEW_REQUIRED / BLOCKED / INSUFFICIENT_CONTEXT). There is no numeric readiness score. A "95% ready" display is forbidden.

### Invariant 30: Every exported report carries the same trust disclosures as the workspace.

The HTML report includes: what was validated, what was partially validated, what was skipped, and the "not an STA signoff" disclaimer. An engineer reading the report without the workspace understands the same boundaries.

### Invariant 31: The product never modifies the SDC file.

RICTA reads SDC files. It does not write to them, modify them, or auto-fix them. The linter (`rta lint`) produces reformatted output as a separate file, never in-place.

### Invariant 32: The product never executes Tcl constructs.

Tcl execution constructs (eval, expr, exec) are detected, never executed. They are analyzed at the text level only and reported as TCL_EXECUTION_REQUIRED.

### Invariant 33: The product always distinguishes block-level from subsystem-level scope.

RICTA Version 1 is block-level constraint intelligence. It does not analyze subsystem or top-level constraints. This scope is stated in the product site, the workspace, and the documentation.

### Invariant 34: Every interactive element has a visible focus ring.

Keyboard navigation is a first-class feature. Every button, link, input, and interactive element has a 2px focus ring. Focus is never hidden.

### Invariant 35: The product respects prefers-reduced-motion.

When the operating system requests reduced motion, all animations become instant state changes. The hero becomes a static diagram. Loading stages become static highlights. No exceptions.

### Invariant 36: Every error state is typed, not generic.

Errors are classified: INVALID_INPUT, UNSUPPORTED_ANALYSIS, INSUFFICIENT_CONTEXT, INCOMPATIBLE_BASELINE, ENGINE_FAILURE, FILE_FAILURE, POLICY_ERROR. Each type has a distinct visual treatment and message pattern.

### Invariant 37: The product never uses emoji as product icons.

Emoji may appear in documentation and sample labels. The shipped UI and product site are emoji-free. Icons are stroke-based line icons at 1.5px stroke weight.

### Invariant 38: The product never uses glassmorphism, glow effects, or gradient-heavy aesthetics.

The visual identity is a precision engineering instrument. Hierarchy comes from background contrast, hairline borders, and typography — not from decorative effects.

### Invariant 39: The workspace always provides a path to investigate any finding.

Every finding in the findings table is clickable. Clicking opens the finding inspector. The inspector links to the source viewer. The source viewer shows the SDC with line numbers. The engineer can trace every finding from summary to source.

### Invariant 40: The product never claims more than it checks.

If the tool did not check object resolution (because no netlist was provided), it says so. If the tool did not check Tcl execution constructs, it says so. "No errors" is never presented as "everything proven."

---

## Part III: Screen Specifications

---

### 11. Overview

**Purpose:** The landing page after analysis. The engineer's first question is always: "Is there a problem?"

**Primary question answered:** "What is the overall status, and where should I look first?"

**Required information:**
- Overall readiness verdict (badge, large, top-left).
- Trust scope strip (what was validated, partially validated, skipped).
- Error findings count (top errors, max 5 rows, each linking to the findings table).
- Clock summary (clock count + hierarchy mini-diagram + link to Clocks page).
- Design context summary (netlist supplied? objects resolved? compact).
- Coverage summary (input/output constrained proportions, compact).
- Interactions summary (duplicates/overrides/conflicts counts).
- Next actions (engineered list: "Review 2 I/O constraints" → deep links).

**Optional information:**
- Analysis timestamp.
- SDC file metadata (size, line count).
- Version stamp.

**What must never appear:**
- A single "percentage ready" gauge.
- Benchmark numbers (they belong on the product site).
- Timing values, slack, or delay propagation.
- An AI-generated summary.

**Success criteria:** The engineer can answer in order: (1) Is there a problem? (readiness + errors) (2) How serious? (severity, counts) (3) Can I trust this? (trust/scope strip) (4) Where do I investigate? (findings + next actions).

**Failure modes:**
- Readiness badge is missing → engineer cannot assess status at a glance.
- Trust strip is missing → engineer does not know what was checked.
- Next actions are missing → engineer does not know where to start.

**Common user mistakes:**
- Assuming readiness means signoff → the disclaimer must be prominent.
- Ignoring trust scope → the trust strip must be above the fold.

---

### 12. Validator (Findings Explorer)

**Purpose:** The engineer investigates every finding in the constraint set.

**Primary question answered:** "What did the tool find, and what does each finding mean?"

**Required information:**
- Findings table: severity icon + label, rule code (mono), finding message, object name (mono), source line.
- Filters: severity (ALL / ERROR / WARNING / INFO), rule code, category/search.
- Default view: errors and warnings visible; info visible but lower prominence.
- Finding inspector (right rail, 400px): rule documentation, why detected, constraint text, evidence, source provenance (dual-line where applicable), trust scope, requires-context flag, requires-STA flag, fix suggestion.
- Source viewer: SDC rendered with line numbers, finding highlights (left rule + subtle tint), dual-line provenance connector.

**Optional information:**
- Finding count summary (total errors, warnings, info).
- Rule category grouping.
- Object-name search.

**What must never appear:**
- Findings without rule codes.
- Findings without source lines (except engine failures).
- A "no issues found" message without the trust scope disclosure.
- An empty findings table without an explanation of what was checked.

**Success criteria:** The engineer can select any finding, understand why it was detected, see the evidence, locate it in the SDC, and know whether STA follow-up is needed.

**Failure modes:**
- Finding inspector does not open → engineer cannot investigate.
- Source viewer does not highlight the finding line → engineer cannot locate it.
- Trust scope is missing from inspector → engineer does not know the analysis boundary.

**Common user mistakes:**
- Interpreting "no errors" as "timing correct" → the trust scope and disclaimer must prevent this.
- Filtering to "info only" and missing errors → default filter shows errors and warnings.

---

### 13. Clocks

**Purpose:** The engineer understands the clock landscape of the constraint set.

**Primary question answered:** "What clocks exist, how are they related, and are there mismatches?"

**Required information (three views):**
- **Inventory tab:** dense table with columns: name (mono), type (primary/generated/virtual), period (mono), frequency (mono), source (mono), master (mono), relation.
- **Hierarchy tab:** SVG node-edge diagram (≤100 nodes) showing clock parent-child relationships. Primary = filled square. Generated = outlined square with tick. Virtual = outlined circle. Solid arcs = derived. Dashed = inferred. Static caption: "Structural relationships only — no timing propagation."
- **Matrix tab:** pairwise relationship matrix. Cells carry non-color symbols: ✓ derived/synchronous, ~ async, ? unknown, ✗ physically exclusive, ! advisory. Declared `set_clock_groups` relationships render with a solid ring; inferred with dashed. Click cell → pair evidence + declared-group status.

**Optional information:**
- Clock count summary (N primary, N generated, N virtual).
- Mismatch count (SDC-060…063).
- Clock detail inspector (right rail): full ClockDef fields, related findings, related pairs.

**What must never appear:**
- Timing propagation values (clock skew, latency, insertion delay).
- Waveform visualizations implying timing analysis.
- A "clocks are correct" statement without evidence.
- A hierarchy diagram with >100 nodes (fallback to HTML table).

**Success criteria:** The engineer can identify all clocks, understand their ancestry, classify their pairwise relationships, and detect mismatches with declared `set_clock_groups`.

**Failure modes:**
- Hierarchy diagram shows no relationships → engineer does not know if clocks are async or sync.
- Matrix does not distinguish declared vs inferred relationships → engineer cannot verify groups.
- Generated-clock ancestry is wrong → engineer trusts incorrect hierarchy.

**Common user mistakes:**
- Assuming the hierarchy implies timing propagation → the static caption must prevent this.
- Missing a clock mismatch → the mismatch count must be visible in the inventory.

---

### 14. Coverage

**Purpose:** The engineer understands which design objects are constrained and which are not.

**Primary question answered:** "Was something constrained, and what is still missing?"

**Required information:**
- Coverage summary: two direction bars (inputs / outputs) with constrained/partial/unconstrained/exempt/unknown segments. No single ring gauge. Percentage as secondary annotation only.
- Legend: constrained, partial, unconstrained, exempt, unknown, N/A.
- Port/bus table: object (mono), direction, status chip, covering constraint (mono, line ref).
- Bus coverage strips: per-bit visualization for partial buses (filled = constrained, hollow = unconstrained, hatched = exempt, stippled = unknown).
- Prominent disclaimer: "Coverage is not correctness. Constraints on an object do not prove correct timing intent."

**Optional information:**
- Design-aware mode indicator (netlist provided vs SDC-only).
- Per-bucket counts.
- Missing-only filter.

**What must never appear:**
- A single "100% coverage" ring gauge implying completeness.
- A statement that "coverage is good" without the "not correctness" disclaimer.
- Coverage data without design context (if design-aware mode is expected).

**Success criteria:** The engineer can identify every unconstrained or partially constrained object, see exactly which bits of a bus are missing coverage, and understand that coverage does not prove correctness.

**Failure modes:**
- Coverage shows "100%" without disclaimer → engineer assumes correctness.
- Bus strips do not show per-bit detail → engineer cannot see partial gaps.
- Coverage data is missing when a netlist was provided → engineer does not know why.

**Common user mistakes:**
- Interpreting 100% coverage as "done" → the disclaimer must prevent this.
- Ignoring exempt ports → exempt status must be clearly distinguished from constrained.

---

### 15. Interactions

**Purpose:** The engineer discovers semantic relationships between constraints that may indicate problems.

**Primary question answered:** "Do any constraints silently override, contradict, or duplicate each other?"

**Required information:**
- Category tabs: DUPLICATES · OVERRIDES · CONTRADICTIONS · OVERLAP / STA REVIEW.
- For each interaction: Constraint A (mono, with line) ↔ Constraint B (mono, with line). Interaction type with reason. Dual-line provenance connector.
- For contradictions (SDC-069): "provable conflict" label with explicit marker.
- For overlaps (SDC-070): "requires STA / path analysis" label with distinct marker.
- For duplicates: "exact duplicate" label.

**Optional information:**
- Interaction count summary per category.
- Object/clock grouping of interactions.
- Interaction detail inspector (right rail).

**What must never appear:**
- A statement that an overlap is a definitive conflict (overlaps require STA review).
- Interactions without dual-line provenance (line ↔ line₂).
- A "no interactions found" message without the scope disclosure.

**Success criteria:** The engineer can identify every duplicate, override, contradiction, and overlap in the constraint set, understand which are provable conflicts and which require STA review, and locate both constraints in the SDC.

**Failure modes:**
- Overlap is presented as a contradiction → engineer misjudges severity.
- Dual-line provenance is missing → engineer cannot locate both constraints.
- Interactions are hidden behind a low-prominence section → engineer misses critical conflicts.

**Common user mistakes:**
- Treating all interactions as errors → the distinction between provable and STA-required must be clear.
- Missing a contradiction because it is in the "duplicates" tab → categorization must be accurate.

---

### 16. Readiness

**Purpose:** The engineer decides whether the constraint set is ready for handoff to STA.

**Primary question answered:** "Is this constraint set ready for STA, and if not, what needs attention?"

**Required information:**
- Overall readiness verdict (badge, large): READY / READY_WITH_ADVISORIES / REVIEW_REQUIRED / BLOCKED / INSUFFICIENT_CONTEXT.
- Mode disclosure: "SDC-only" or "Design-aware."
- Disclaimer: "Constraint readiness review — NOT STA signoff."
- Dimension stack (7 rows): CLOCKS, I/O, EXCEPTIONS, COVERAGE, CONSISTENCY, ANALYSIS_TRUST, DESIGN_CONTEXT. Each with: status marker + label + mini rail + status. Click → evidence panel (which findings caused this dimension's status).
- Blockers section: findings that must be addressed.
- Review items section: warnings and NETLIST_REQUIRED items.
- Advisories section: info-level guidance.
- Recommended actions: P0–P3 priority items with deep links to findings.
- Trust disclosure: "READY does not mean timing signoff. This is a constraint-readiness review produced by deterministic analysis."

**Optional information:**
- Analysis mode (SDC-only vs design-aware).
- Readiness timestamp.
- Rule counts per dimension.

**What must never appear:**
- A numeric readiness score (no such number exists).
- A "95% ready" gauge.
- A statement that "READY means correct."
- Readiness without the "NOT STA signoff" disclaimer.
- A dimension without its evidence (findings that caused the status).

**Success criteria:** The engineer can assess overall readiness, understand why each dimension has its status, see the blockers and review items, and know what actions to take next.

**Failure modes:**
- Readiness badge is missing → engineer cannot assess status.
- Dimension evidence is missing → engineer cannot verify the dimension status.
- Disclaimer is missing → engineer may interpret READY as signoff.
- Actions are missing → engineer does not know what to fix first.

**Common user mistakes:**
- Interpreting READY as "timing will close" → the disclaimer must prevent this.
- Ignoring INSUFFICIENT_CONTEXT → the dimension must explain what context is needed.

---

### 17. Diff

**Purpose:** The engineer compares the current constraint set against a saved baseline and identifies regressions.

**Primary question answered:** "Did this revision make constraints worse?"

**Required information:**
- Header: BASELINE [READY] → CURRENT [BLOCKED] with transition marker and classification badge (BLOCKING_REGRESSION, etc.) + gate result.
- Filters: All · NEW · RESOLVED · CHANGED · UNCHANGED (segmented control).
- Change table: change marker (icon + label), rule code (mono), finding message, object (mono), line provenance.
- Coverage delta: newly unconstrained objects with bus strips.
- Trust delta: VALIDATED → PARTIAL transitions as status chips with arrows.
- Debt panel: existing / new / resolved debt with blocker · review · advisory counts.
- Gate result: policy name + exit code + reasons (if gate was evaluated).

**Optional information:**
- Baseline metadata (version, date, file).
- Current metadata (version, date, file).
- Compatibility status (NATIVE / MIGRATED / INCOMPATIBLE).
- Identity strength disclosure (STRUCTURED vs LEGACY_NORMALIZED).

**What must never appear:**
- A diff result without the baseline compatibility status.
- An INCOMPATIBLE baseline presented as comparable.
- New/regressed findings without their source provenance.

**Success criteria:** The engineer can identify every new, resolved, changed, and unchanged finding, understand whether the revision regressed, see the coverage and trust deltas, and know the gate result.

**Failure modes:**
- Baseline is INCOMPATIBLE but presented as comparable → engineer draws wrong conclusions.
- Change markers are color-only → engineer with color vision deficiency cannot distinguish.
- Debt panel is missing → engineer does not understand the overall trajectory.

**Common user mistakes:**
- Ignoring the compatibility status → the header must make it prominent.
- Focusing only on new findings and missing resolved ones → the filters must make both visible.

---

### 18. Reports

**Purpose:** The engineer exports analysis evidence for sharing, archiving, or pipeline integration.

**Primary question answered:** "What export formats are available, and which should I use?"

**Required information:**
- Artifact cards, one row per export format:
  - HTML Report: human-readable analysis evidence. [Download] Generated timestamp.
  - JSON Result: machine-consumable findings. [Download]
  - Snapshot: versioned analysis state (schema v2). [Save] [Load]
  - Baseline: reference snapshot for gates/diff. [Save] [Load]
- For each card: what it contains, when to use it, how it was generated.
- JSON purity note: "stdout is machine-clean JSON — diagnostics go to stderr."

**Optional information:**
- JUnit XML export (for CI ingestion).
- CSV/Markdown export (for CI pipelines).
- Report generation timestamp.

**What must never appear:**
- A report without the "not an STA signoff" footer.
- A report with hardcoded evidence numbers (numbers must come from the analysis).
- An export format without an explanation of when to use it.

**Success criteria:** The engineer can choose the correct export format for their use case, export it in one click, and understand what the export contains.

**Failure modes:**
- HTML report does not carry trust disclosures → reader misunderstands scope.
- JSON output mixes diagnostics with findings → pipeline integration breaks.
- Snapshot is not schema v2 → future diff cannot compare.

**Common user mistakes:**
- Using JSON for human review → the card must explain which format serves which purpose.
- Not saving a baseline before a revision → the snapshot card must explain the workflow.

---

### 19. CI / Policies

**Purpose:** The engineer configures and evaluates constraint quality gates for CI pipelines.

**Primary question answered:** "Which gate policy should I use, and how do I integrate it?"

**Required information:**
- Policy selector: four cards (BLOCKERS_ONLY, NO_READINESS_REGRESSION, STRICT, CUSTOM). Each card: intent, what fails, what is allowed, engine-failure behavior.
- Custom policy preview: rendered YAML/JSON with inline field validation (unknown fields flagged, never executed).
- CLI integration: the exact CLI command for the selected policy, with copy button.
- GitHub Actions example (one small snippet, vendor-neutral framing).
- Engine-failure behavior: "engine failure never yields PASS — exit 3."

**Optional information:**
- Policy comparison table (what each policy catches vs allows).
- Exit-code contract reference (0 pass, 1 gate failed, 2 invalid, 3 engine failure).
- Baseline workflow diagram: SDC revision → validation → snapshot → baseline diff → policy → PASS/FAIL.

**What must never appear:**
- A policy that executes arbitrary code (policies are inert data).
- A statement that a gate result implies timing closure.
- A CUSTOM policy without validation (unknown fields must be flagged).

**Success criteria:** The engineer can select the correct policy for their use case, generate the CLI command, and understand what the gate result means.

**Failure modes:**
- CUSTOM policy is executed as code → security vulnerability.
- Gate result is presented as "constraints are correct" → the disclaimer must prevent this.
- Engine failure produces PASS → the invariant is violated.

**Common user mistakes:**
- Choosing STRICT when BLOCKERS_ONLY is sufficient → the policy cards must explain the tradeoff.
- Not saving a baseline before running a gate → the workflow must explain the prerequisite.

---

## Part IV: Principles

---

### 20. Readability Rules

1. **Text hierarchy is size + weight + color, not just color.** Primary text is 15–16px Inter 400–500. Secondary is 13–14px. Muted is 11–12px. The hierarchy is clear without relying on color contrast alone.
2. **Mono is used selectively.** Rule IDs, line numbers, object names, clock names, SDC commands, metric values. Body text stays Inter. The interface is not a terminal.
3. **Labels are uppercase and 12px.** Section headers only. Not body text. Not findings. Not messages.
4. **Tables use tabular figures.** All numeric columns align properly. JetBrains Mono defaults to tabular figures; Inter enables `font-variant-numeric: tabular-nums`.
5. **Line length is bounded.** Workspace prose: max 80ch. Product site prose: max 720px (roughly 65–75ch). Long messages are truncated with ellipsis in tables; full text in the inspector.

---

### 21. Information Density Rules

1. **The workspace is dense by design.** Engineering data is dense. The product respects this with compact tables (28–32px rows), tight spacing, and minimal decoration.
2. **Density is managed with hierarchy, not thinning.** More important data gets larger type, stronger weight, and more whitespace. Less important data gets smaller type and tighter spacing. Data is never removed to make space.
3. **Three levels of information depth:** Summary (overview counts), Evidence (findings table), Detailed (inspector/source). Always one click apart.
4. **The inspector is contextual.** It opens on selection and closes with Esc or ✕. It does not replace the main content. It supplements it.
5. **Filters are always visible.** The findings filter bar is always present. The diff filter is always present. Filters are not hidden behind a menu.

---

### 22. Motion Principles

1. **Motion explains system behavior.** A node resolving, a status changing, a path flowing — these are the moments that earn animation.
2. **Motion never delays comprehension.** All transitions are under 1 second. No cinematic sequences. No loading screens that block interaction.
3. **Motion is GPU-efficient.** CSS transforms and opacity only. No layout-triggering animations. No canvas in the workspace.
4. **Motion respects the user's preference.** `prefers-reduced-motion` → all animations become instant state changes. No exceptions.
5. **Motion in the hero only.** The product site hero may animate (constraint path, clock hierarchy). The workspace does not animate backgrounds. The workspace animates only: micro-interactions (hover, focus), page transitions (200ms), and data-change transitions (300ms).

---

### 23. Empty State Principles

1. **Every empty state teaches.** "Nothing here" is never the complete message. The empty state explains what the absence means and what the engineer should do next.
2. **Every empty state has a next action.** A button, a link, or a suggestion. The engineer is never left without a path forward.
3. **Every empty state uses the visual language.** NODE primitives, PORT primitives, CONSTRAINT LINK primitives — the same visual grammar used elsewhere, applied to the empty state.
4. **Empty states are not failures.** A page with no findings is a success. A page with no baseline is a starting point. The empty state communicates this.

---

### 24. Error State Principles

1. **Errors are typed, not generic.** INVALID_INPUT, UNSUPPORTED_ANALYSIS, INSUFFICIENT_CONTEXT, INCOMPATIBLE_BASELINE, ENGINE_FAILURE, FILE_FAILURE, POLICY_ERROR. Each type has a distinct visual treatment.
2. **Errors explain next actions.** Every error state includes a suggested next action. "Cannot parse" → "Check line N." "Netlist required" → "Add a netlist."
3. **Errors never show tracebacks.** The workspace does not display Python tracebacks. Errors are presented in engineering language.
4. **Engine failure is honest.** An ENGINE_FAILURE error badge + run-id + "results are not a PASS." The engineer knows immediately that the results cannot be trusted.
5. **Errors link to documentation.** Every error state includes a link to the relevant docs or help page.

---

### 25. Accessibility Principles

1. **Full keyboard navigation.** Every interactive element is reachable by keyboard. Tab order is logical. Focus is always visible.
2. **Visible focus rings.** 2px focus ring with 2px offset on every interactive element. Never hidden. Never removed.
3. **Non-color status.** Every status carries icon + label + shape. Color reinforces, never carries.
4. **Semantic HTML.** Real headings (h1→h6 order), `<th scope>`, table captions, `aria-label` on icon buttons, `role="status"` for toasts.
5. **Reduced motion.** `prefers-reduced-motion` honored everywhere. All animations become instant state changes.
6. **Touch targets.** ≥ 40px for interactive elements on touch devices.
7. **Text scaling.** Layout survives 200% zoom without data loss.
8. **Contrast.** All text ≥ WCAG AA on their surfaces. Semantic colors checked against both backgrounds they appear on.

---

### 26. Responsive Behavior

**Product site (responsive at all sizes):**
- Mobile (<640px): stacked layout, hamburger nav, hero static, CTA always visible.
- Tablet (640–1024px): 2-column grids, hero static.
- Desktop (>1024px): full layout, hero animated.

**Workspace (desktop-first):**
- Desktop (>1280px): full shell — sidebar 240px, main fluid, inspector 400px.
- Tablet (1024–1280px): sidebar collapses to 64px icon rail, inspector becomes overlay drawer, matrices scroll horizontally with sticky first column.
- Mobile (<640px): read-only summary mode — analysis summary, readiness status, findings list (card list, not table), reports download. No matrices, no hierarchy graph, no inspector. Persistent note: "Full analysis experience is designed for desktop — open on a larger screen."

**Rules:**
- Workspace matrices and trees never squish. Horizontal scroll with sticky first column.
- The inspector is unavailable on mobile (summary mode).
- The product site CTA ("Launch Ṛta") is always visible, even on mobile.

---

## Part V: Future Product Evolution

---

### 27. How This Specification Evolves

This specification is designed for Version 1 (Block-Level Constraint Intelligence). The roadmap progresses through Version 2 (Subsystem), Version 3 (Top-Level), Version 4 (Multi-Block), and Version 5 (Enterprise Governance).

**What stays the same across all versions:**

1. The Trust Model and its six statuses. These are version-independent.
2. The readiness vocabulary (READY / READY_WITH_ADVISORIES / REVIEW_REQUIRED / BLOCKED / INSUFFICIENT_CONTEXT). These are version-independent.
3. The engineering principles (evidence over assumptions, deterministic over probabilistic, trust before automation). These are version-independent.
4. The evidence contract (every number traces to a runner). This is version-independent.
5. The non-goals (not STA, not signoff, not AI). These are version-independent.
6. The product design invariants (Part II). These are version-independent.
7. The navigation philosophy (grouped by intent, evidence hierarchy, trust always visible). This scales.
8. The screen specification pattern (purpose, required info, success criteria, failure modes). This pattern applies to any new screen.

**What changes across versions:**

1. **The analysis scope.** Version 1 analyzes a single block. Version 2 analyzes relationships across blocks. Version 3 analyzes the complete chip. Each version adds a scope layer — the UI adds a corresponding view.
2. **The navigation.** New scope levels add new navigation groups. Version 2 might add a "SUBSYSTEM" group with cross-block views. Version 3 adds a "TOP-LEVEL" group with chip-level views.
3. **The readiness model.** The seven dimensions remain, but their evidence sources expand. Version 2 adds cross-block readiness dimensions. Version 3 adds top-level dimensions.
4. **The coverage model.** Version 1 covers objects within a block. Version 2 covers cross-block interfaces. Version 3 covers top-level I/O. The coverage visualization pattern (direction bars + bus strips) scales to each level.
5. **The clock intelligence model.** Version 1 covers clocks within a block. Version 2 covers cross-block clock relationships. Version 3 covers the global clock tree. The clock hierarchy visualization scales (more nodes, but the same node-edge grammar).
6. **The diff model.** Version 1 diffs block-level baselines. Version 2 diffs subsystem baselines. Version 3 diffs top-level baselines. The diff visualization pattern (change markers + debt panel) scales.

**What is added in future versions:**

1. **Subsystem views (Version 2):** Cross-block interface analysis, multi-block clock relationship matrix, subsystem readiness aggregation.
2. **Top-level views (Version 3):** Global clock tree, chip-level coverage, top-level readiness with all dimensions.
3. **Multi-block views (Version 4):** Shared constraint analysis, hierarchical constraint inheritance, cross-block timing exception analysis.
4. **Enterprise views (Version 5):** Shared baselines, policy catalogs, review workflows, trend dashboards, audit trails.

**The pattern for adding a new scope level:**

1. Define the scope's analysis model (what it checks, what it does not).
2. Define the scope's trust boundary (what it validates, what requires context).
3. Add navigation group and pages following the existing pattern.
4. Add readiness dimensions for the new scope.
5. Add coverage model for the new scope.
6. Add diff model for the new scope.
7. Update the trust strip to include the new scope.
8. Update the analysis header to show the new scope.

The existing specification's patterns — evidence hierarchy, trust presentation, empty states, error states, navigation philosophy, and design invariants — apply unchanged to every new scope level. The product does not need to be redesigned; it needs to be extended.

---

*End of Product Design Specification. This document defines the behavioral contract for Ṛta Version 1. Implementation details are in VISUAL_DESIGN_SYSTEM.md and HIGH_FIDELITY_PRODUCT_SPEC.md. Product identity is in PRODUCT_CHARTER.md. Processes are in OPERATING_SYSTEM.md.*
