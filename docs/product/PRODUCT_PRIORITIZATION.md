# Ṛta — Product Prioritization (19 Capabilities)

> **Document kind:** strategy / planning classification · **Status:**
> planning only — **nothing is removed, hidden, or rebuilt.** This matrix
> classifies where a small team should invest, in service of
> `PLAN_A_PRIMARY.md` and the decision tree. The 19 capabilities and the
> frozen engine are unchanged.
>
> Role legend: **wedge** (first value) · **retention** (why users stay) ·
> **trust** (credibility/evidence) · **workflow-enabling** (feeds the loop) ·
> **differentiation** (why us) · **supporting** (convenience/completeness).

---

## 0. Canonical capability inventory (authority)

**Total: 19 capabilities.** The engineering tool catalog renders **18 cards**
because **Corner Manager and MMC share one card** ("Corners / MMC") — no
capability is missing, merged, or duplicated anywhere else. This is the
single authoritative inventory for the strategy package; display names on
other surfaces (catalog cards, business-site pages) are aliases of the
canonical names below.

| # | Canonical name (Phase C acceptance) | Catalog card title (18 cards) | Alias / merge note |
|---|---|---|---|
| 1 | Validate | SDC Validation | same capability, display-name alias |
| 2 | SDC Generator | Generator | same capability, display-name alias |
| 3 | SDC Linter | Linter | same capability, display-name alias |
| 4 | SDC Converter | Converter | same capability, display-name alias |
| 5 | Clock Intelligence | Clock Intelligence | identical name |
| 6 | Coverage | Constraint Coverage | same capability, display-name alias |
| 7 | Design Context | Design Context | identical name |
| 8 | Constraint Conflicts | Constraint Interactions | same capability, display-name alias |
| 9 | Readiness | Readiness | identical name |
| 10 | SDC Diff | Diff | same capability, display-name alias |
| 11 | Corner Manager | **Corners / MMC** (one card) | distinct capability — see #12 |
| 12 | MMC | **Corners / MMC** (one card) | distinct capability — the only merged card: 19 capabilities, 18 cards |
| 13 | Test Drive | Test Drive | identical name |
| 14 | Rules | Rules Reference | same capability, display-name alias |
| 15 | CI | CI Quality Gates | same capability, display-name alias |
| 16 | Reports | Reports | identical name |
| 17 | Trust | Trust | identical name |
| 18 | Documentation | Documentation | identical name |
| 19 | Feedback | Feedback | identical name |

**Count reconciliation (verified from the repository):**

- `legacy/streamlit/ui/view_home.py` CATALOG renders **18 cards** — Core (4),
  Analyze (6), Advanced (4), Output & Knowledge (4); the Advanced group's
  "Corners / MMC" card carries **two capabilities**.
- `docs/product/PHASE_C_FINAL_ACCEPTANCE.md` lists **19 capabilities** with
  Corner Manager (#11) and MMC (#12) as separate rows.
- No two canonical names represent the same capability; the only pair that
  shares a surface is Corner Manager + MMC (one catalog card).
- This matrix (rows below) covers all 19 canonical capabilities.

---

## 1. The matrix

| # | Capability | Role | Investment class | Plan A posture | Notes |
|---|---|---|---|---|---|
| 1 | Validate (checker) | **Wedge + differentiation** | **KEEP / STRENGTHEN** | Lead capability; the 5-minute entry loop | Actionable messages + speed on real SDCs are the top two investments |
| 2 | Diff | **Retention + differentiation** | **KEEP / STRENGTHEN** | The "why you keep using Ṛta" loop | Semantic diff + why-it-matters is rare; strengthen the review guidance surface |
| 3 | CI gate | **Retention + differentiation** | **KEEP / STRENGTHEN** | Team adoption loop; the differentiator | Ship the GitHub Action; fix P2-3 exit-code semantics; P2-10 contract doc |
| 4 | Readiness | **Retention + trust** | **MAINTAIN** | Handoff artifact | Keep the honest WHY + disclosures; never a signoff claim |
| 5 | Reports | **Trust + retention** | **KEEP / STRENGTHEN** | Shareable evidence | HTML/JSON from real analysis; P2-7 download bundle is a nice-to-have |
| 6 | Rules (registry) | **Trust** | **MAINTAIN** | Depth-of-engineering proof | Already searchable; keep registry as source of truth |
| 7 | Trust (page/scope) | **Trust** | **MAINTAIN** | Frozen disclosures | Never weaken; evidence-backed facts from `/api/evidence` |
| 8 | Documentation | **Trust + supporting** | **MAINTAIN** | Adoption funnel | Add the 5-minute real-SDC guide; P2-10 one-place contract |
| 9 | Test Drive | **Trust + wedge (demo)** | **KEEP / STRENGTHEN** | Best demo asset | Add realistic multi-clock sample + netlist (P2-6) |
| 10 | Clock Intelligence | **Workflow-enabling** | **MAINTAIN** | Feeds Validate/Readiness | Relationship matrix + mismatches/missing split already correct |
| 11 | Coverage | **Workflow-enabling + trust** | **MAINTAIN** | Feeds Readiness; honest "NOT correctness" | Keep SDC-only vs design-aware distinction clear |
| 12 | Design Context | **Workflow-enabling** | **MAINTAIN** | Honest netlist-aware tier | Structural only; never overclaim |
| 13 | Constraint Conflicts | **Workflow-enabling** | **MAINTAIN** | Feeds Validate/Readiness | SDC-067/068/069 with what/why/review |
| 14 | Linter | **Supporting** | **MAINTAIN** | Convenience; not strategic | Fine as-is; no investment priority |
| 15 | Converter | **Supporting** | **MAINTAIN / SIMPLIFY** | Convenience | Keep working; do not polish into a product story |
| 16 | Generator | **Supporting** | **MAINTAIN / SIMPLIFY** | Convenience | Self-consistent output already guaranteed; do not market as the wedge |
| 17 | Corner Manager | **Supporting** | **DEFER** | Keep read-only honest scope | P2-1 (CLI editing) deferred: not an adoption driver |
| 18 | MMC | **Supporting** | **DEFER** | Keep working; no new investment | Same rationale as Corner Manager |
| 19 | Feedback | **Supporting** | **MAINTAIN** | Measurement channel | Feeds the decision tree's feedback themes |

**POTENTIALLY REMOVE:** none. Every capability stays — this is a planning
classification only. **POTENTIAL FUTURE EXPANSION:** subsystem intelligence
(charter V2), regression/health intelligence, evidence platform, org
governance, optional AI assistance — see `PLAN_C_EXPANSION.md` (all gated,
none built).

---

## 2. Investment ordering (what a small team funds first)

1. **Strengthen:** Validate (actionability + speed), Diff (review
   guidance), CI gate (GitHub Action + exit-code semantics), Reports
   (evidence), Test Drive (realistic sample). — These are the Plan A loop.
2. **Maintain:** everything else — keep green, keep honest, no new
   features.
3. **Defers:** Corners/MMC investment (P2-1), Converter/Generator polish.
4. **Never:** engine changes, trust-disclosure changes, new rules.

## 3. Capability → strategy mapping

| Strategic need | Capabilities that serve it |
|---|---|
| **Wedge features** (first value, 5 min) | Validate, Test Drive, Linter |
| **Retention features** (repeat usage) | Diff, CI gate, Readiness, Reports |
| **Trust features** (credibility) | Trust, Rules registry, Documentation, Evidence/benchmarks, Test Drive |
| **Workflow-enabling** (feed the loop) | Clock Intelligence, Coverage, Design Context, Conflicts |
| **Differentiation features** (why us) | Diff, CI gate, Validate (determinism/evidence) — the loop, not the list |
| **Supporting features** (completeness) | Generator, Converter, Corners/MMC, Feedback |

*The product is already built. This matrix decides where the *next hour of
engineering* goes — and the answer is the validate → diff → CI → report
loop plus its evidence surface, not new capability.*
