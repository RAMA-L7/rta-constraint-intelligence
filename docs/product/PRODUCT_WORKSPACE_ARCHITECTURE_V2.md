# Ṛta — Product Workspace Architecture V2

> **Status:** architecture only — no implementation in this sprint.
> **Baseline:** Ṛta v1.5.8 (see `FUNCTIONAL_BASELINE.md` for the frozen
> functional contract).
> This document defines the target product architecture for the rebuild.
> The deterministic engine is frozen; everything below concerns surfaces,
> navigation, entry points, and workflow models.

---

## 1. Two distinct surfaces

Ṛta has two separate products with different jobs. They must not be blurred.

### Surface A — Business website (marketing)

- **Job:** explain Ṛta, build trust, and lead engineers into the tool.
- **Content:** what Ṛta is, why constraint intelligence matters, capability
  catalog, engineering philosophy, trust evidence, benchmarks, documentation,
  product story, roadmap.
- **Relationship to the tool:** external. It links *into* the workspace but is
  not part of it. Existing surface: `rta/business-site/` (GitHub Pages) and
  `rta/website/` pages.
- **Boundary rule:** the business site never shows analysis inputs or results;
  the workspace never shows marketing copy.

### Surface B — Ṛta Engineering Tool (the workspace)

- **Job:** let an engineer actually use the capabilities on their SDC.
- **First screen:** must answer "WHAT IS ṚTA?" in one line, then present the
  capability catalog as feature cards. No upload-first wall, no dashboard dump.
- **Boundary rule:** every card leads to a working workflow backed by the real
  deterministic engine — no decorative cards, no dead routes.

---

## 2. First screen (feature-first entry)

The entry screen has three parts, in order:

1. **Positioning line** (one sentence, deterministic framing):
   > "Ṛta is a deterministic constraint-intelligence workspace for block-level
   > digital design — validate, generate, and review SDC before STA."

2. **Primary capability catalog** — every primary capability visible as a
   card, never hidden under "More Tools" / "Quick Actions" / "Tools" menus.

3. **One-line call to action per card** — e.g. "Validate my SDC", "Generate an
   SDC", "Convert SDC → JSON", "Analyze clocks", "Check coverage", "Compare two
   SDCs", "Create MMC scenarios".

### Primary capability catalog (17 cards)

| # | Capability | One-line entry |
|---|---|---|
| 1 | SDC Validator | Validate my SDC |
| 2 | SDC Generator | Generate an SDC |
| 3 | SDC Linter | Lint / format my SDC |
| 4 | SDC Converter | Convert SDC → JSON/YAML |
| 5 | Clock Intelligence | Analyze clocks & relations |
| 6 | Coverage | Check constraint coverage |
| 7 | Design Context | Verify against my netlist |
| 8 | Constraint Conflicts | Find conflicts / interactions |
| 9 | Readiness | Is my SDC ready for STA review? |
| 10 | SDC Diff | Compare two SDCs |
| 11 | Corner Manager | Manage PVT corners |
| 12 | MMC | Generate multi-corner SDCs |
| 13 | Test Drive | Try Ṛta on a sample |
| 14 | Rules | Browse the rule catalog |
| 15 | CI | Gate SDC changes in CI |
| 16 | Reports | Generate signoff reports |
| 17 | Trust | Read our trust disclosures |

**Supporting surfaces (not primary cards):** Documentation · Feedback.

---

## 3. Capability card anatomy

Every card must answer the Phase 7 questions visibly (before clicking):

- **WHAT IS THIS?** — 1–2 sentence capability description (plain engineering language).
- **WHAT INPUT DO I NEED?** — "SDC required · netlist optional", "Two SDCs",
  "Generation parameters", etc.
- **WHAT WILL ṚTA DO?** — the processing in one sentence.
- **WHAT WILL I GET?** — the output in one sentence (findings with rule codes,
  generated SDC, JSON, matrix, HTML report…).
- **WHAT SHOULD I DO NEXT?** — the natural next step (open in Validator, export
  report, set up CI…).

No unexplained icons, no dead buttons, no decorative names without a workflow.

---

## 4. Standalone workflow model

Every capability is independently usable — the user never has to pass through
a global upload screen to reach a tool that needs different inputs.

| Capability | Its own input | Entry |
|---|---|---|
| SDC Validator | SDC (netlist optional) | card → upload → findings |
| SDC Generator | parameters (no SDC needed) | card → form → generated SDC |
| SDC Linter | SDC | card → upload → lint result |
| SDC Converter | SDC + format | card → upload → JSON/YAML |
| Clock Intelligence | SDC | card → upload → clocks + matrix |
| Coverage | SDC (netlist optional) | card → upload → score + categories |
| Design Context | SDC + netlist + top | card → upload both → context + netlist findings |
| Constraint Conflicts | SDC | card → upload → conflicts |
| Readiness | SDC (netlist optional, baseline optional) | card → upload → tier + dimensions |
| SDC Diff | V1 SDC + V2 SDC (+ linked TCL) | card → upload both → changes |
| Corner Manager | none (presets) / JSON | card → manage corners |
| MMC | template or params + corners | card → configure → per-corner SDCs + ZIP |
| Test Drive | sample picker or SDC | card → run-all dashboard |
| Rules | none to browse | card → searchable registry |
| CI | SDC + baseline + gate policy | card → configure → verdict |
| Reports | results (per type) | card → report → HTML download |
| Trust | none | card → disclosures |

Rule: a feature's input is requested **at that feature's entry**, never on a
separate global screen.

---

## 5. Session workflow model

Sessions remain first-class for the analysis pattern:

1. Engineer enters **SDC Validator** → uploads SDC → receives findings.
2. From findings, optionally opens **Clocks**, **Coverage**, **Conflicts**,
   **Readiness**, **Design** — all bound to the same analysis (session context).
3. Session keeps: SDC text, netlist, filename, analysis results, baseline,
   gate policy.

Session rules:
- A session is **created implicitly** when any analysis-capable capability
  receives input; it never requires the user to create it explicitly first.
- Results-led navigation appears **only after** an analysis exists (current
  model, preserved).
- Cross-feature links must be **optional**: opening Clocks from findings never
  forces a new upload; entering Diff standalone never requires a session.

Support both patterns naturally:

```
Engineer A:  Validator → findings → Clocks → Coverage → Readiness   (session)
Engineer B:  Generator → generated SDC → Open in Validator          (session link)
Engineer C:  Diff → upload V1 + V2 → changes                        (standalone)
```

---

## 6. Input model

| Kind | Where defined | Example |
|---|---|---|
| SDC text/file | capability input | validator, linter, converter, clocks, coverage, conflicts, readiness |
| Netlist (Verilog) | optional second input | validator, coverage, design context |
| Top module | optional (required if netlist ambiguous) | netlist-aware surfaces |
| Linked TCL vars | diff-specific | `--linked-v1/v2` equivalent in Diff |
| Baseline JSON | readiness diff / CI | save / load baseline |
| Gate policy | CI | gate choice + custom policy YAML |
| Generation params | generator / MMC | design, clocks, derate, scan… |
| Corner set | corner manager / MMC | preset or custom JSON |
| Custom rules YAML | validator (advanced) | team policy |
| Format | converter | json / yaml |

Validation rules (frozen from P1-6): required SDC missing/empty/whitespace →
HTTP 400 structured error; optional fields may be legitimately empty.

---

## 7. Output model

Every capability returns a **real backend result** (never mock data):

| Capability | Output |
|---|---|
| Validator | findings (code/severity/message/line), stats, scope |
| Generator | SDC text (self-consistent: passes lint + check) |
| Linter | issues + formatted text |
| Converter | JSON / YAML document |
| Clocks | clock inventory, N×N relation matrix, mismatches + missing constraints |
| Coverage | score, present/total, categories, missing items + "NOT correctness" |
| Design Context | port/instance summary, netlist-backed findings |
| Conflicts | duplicate/override/conflict findings with line pairs |
| Readiness | tier + per-dimension WHY + actions |
| Diff | added/removed/modified with CHG-* severity + impact text |
| Corners | preset/custom corner lists + JSON |
| MMC | per-corner SDCs, cross-corner findings, ZIP |
| Test Drive | unified dashboard from real `/api/analyze` |
| Rules | registry listing / detail |
| CI | PASS/FAIL verdict + exit code semantics |
| Reports | self-contained HTML + JSON |
| Trust | standing disclosures |

Every output keeps its **trust disclosure** attached (coverage ≠ correctness;
readiness ≠ signoff; CI PASS ≠ timing pass; SDC-only = limited verification).

---

## 8. Navigation model

- **Pre-analysis:** the capability catalog IS the navigation (feature-first).
  No sidebar of results that don't exist yet.
- **Post-analysis (session):** results-led navigation appears — Findings,
  Clocks, Coverage, Design, Conflicts, Health, Changes, Report, Export.
- **Tools:** reachable from the catalog at any time; **not** hidden under a
  collapsed disclosure. Each tool remains reachable even inside a session
  (they operate standalone or on session input when relevant).
- **Brand mark:** returns to the catalog / new analysis.

Grouping proposal (no menu naming that hides capabilities):

```
CATALOG        (entry — feature cards)
  Validate  Generate  Lint  Convert  Clocks  Coverage  Design  Conflicts
  Readiness  Diff  Corners  MMC  Test Drive  Rules  CI  Reports  Trust
SESSION (appears after analysis)
  Summary  Findings  Clocks  Coverage  Design  Conflicts  Health  Changes
  Report  Export
SUPPORT
  Documentation  Feedback
```

---

## 9. Cross-feature links

Explicit, purposeful, optional:

| From | To | When |
|---|---|---|
| Generator | Validator | "Open generated SDC in Validator" (exists today — keep) |
| Validator | Clocks / Coverage / Conflicts / Health | session results |
| Validator | Design Context | when netlist supplied |
| Test Drive | Validator | sample analysis → open full session |
| MMC | Validator / Reports | per-corner SDC → check / report |
| Diff | Reports | changes → change-impact HTML report |
| Rules | Validator | rule detail → "see in live results" |
| CI | Export | gate config → JSON snapshot |

Never require an unrelated page to complete a workflow.

---

## 10. Feature ownership (who owns the workflow)

| Feature | Backend owner (frozen) | Surface owner |
|---|---|---|
| Validator | `checker.py` + preprocess + tcl_resolver | Findings page + check results |
| Generator | `generator.py` | Generator tool |
| Linter | `linter.py` | Linter tool |
| Converter | `converter.py` | Converter tool |
| Clocks | `clock_relations.py` | Clocks page |
| Coverage | `coverage.py` + `design_coverage.py` | Coverage page |
| Design Context | `design_context.py` + `design_coverage.py` | Design page |
| Conflicts | `constraint_interactions.py` | Conflicts page |
| Readiness | `constraint_readiness.py` + policy engine | Health page |
| Diff | `constraint_diff.py` + tcl_resolver + wildcard_analyzer | Changes page + CLI |
| Corners | `corner_manager.py` | Corner Manager tool |
| MMC | `mmc.py` | MMC tool |
| Test Drive | all engine modules | Test Drive tool |
| Rules | `rules_registry.py` | Rules tool |
| CI | `policy_engine.py` | CI tool |
| Reports | `reporter.py` | Report page + CLI |
| Trust | presentation | Trust page + inline disclosures |

---

## 11. Trust disclosures (per surface, non-negotiable)

- Readiness: "Constraint-readiness review, NOT an STA timing signoff — READY
  does not mean setup/hold passes."
- Coverage: "Coverage is NOT correctness — a fully covered design can still
  have timing errors."
- SDC-only mode: "Limited design verification — upload a netlist to verify
  object references."
- CI: "CI PASS ≠ timing pass."
- Engine failure: never report PASS on incomplete evidence.

These appear wherever the corresponding output appears (CLI, API, webui).

---

## 12. User journeys

### Beginner journey (first 10 seconds)
1. Lands on catalog → reads the positioning line.
2. Reads cards: each answers what/input/process/output/next.
3. Picks "Try Ṛta on a sample" (Test Drive) or "Validate my SDC".
4. Gets a real result with the trust callout visible.
5. Follows the card's "next step" (e.g. open Clocks).

Success criterion: the beginner never has to guess what a feature does, what
to upload, or what the result means.

### Expert journey
1. Lands on catalog → picks the capability directly ("Compare two SDCs").
2. Inputs exactly what that capability needs (two SDCs) — no detour.
3. Gets CHG-* changes with impact text; exports HTML report or JSON.
4. Optionally opens the session to inspect clocks/coverage on the same files.
5. Moves to CI: saves baseline, sets a gate, wires it to their pipeline.

Success criterion: zero clicks to unrelated functionality; every step has a
next action.

---

## 13. Design direction (for the later visual sprint — not implemented here)

The visual system is **premium engineering product**:

- clean, high contrast, clear typography (technical but approachable)
- subtle depth; controlled glass/gloss accents
- white/light base with hairline structure; near-black text (current Arcade
  light language is the baseline to refine)
- **NOT**: cluttered, arcade-like, blurry, excessive gradients, dark-text-on-
  dark, giant information dumps, dozens of tiny nav items.

Design must serve **engineering readability**: findings readable at a glance,
matrices scannable, disclosures always legible. The detailed visual system
lives in a later sprint (Phase F of PRODUCT_REBUILD_PLAN.md); `rta/docs/
product/VISUAL_DESIGN_SYSTEM.md` and `PRODUCT_WEBSITE_DESIGN_DNA.md` are the
starting references.

---

## 14. Boundary summary

| Question | Answer |
|---|---|
| Business website | explains + leads into the tool; never hosts analysis I/O |
| Tool | runs capabilities on real input; never shows marketing copy |
| First screen | positioning line + full primary capability catalog |
| Capability visibility | all 17 primary cards visible; nothing hidden in "More" |
| Input | requested at the feature entry, never a global screen |
| Output | always real backend results + trust disclosure |
| Session | implicit; results-led nav after analysis; optional links |
| Standalone | every capability independently reachable |
| Engine | frozen — presentation adapts, results identical |

*Architecture only — no implementation performed. See
PRODUCT_REBUILD_PLAN.md for the staged execution plan.*
