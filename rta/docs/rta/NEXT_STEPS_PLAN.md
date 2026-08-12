# Ṛta — Next Steps Plan (Block-Level E2E + Feature Gaps)

> **Document kind:** execution plan for review — **no implementation until approved**
> **Date:** 2026-08-12 · **Baseline:** v1.5.0 published to PyPI; Streamlit app live on Community Cloud; full suite 763/763 green
> **Source of truth:** `PRODUCT_ROADMAP.md`, `STARTUP_BACKLOG.md`, `FEATURE_MAPPING.md`, `FULLCHIP_DESIGN_CONTEXT_PLAN.md`

---

## 0. Goal of this phase

Make the **block-level flow work end-to-end** — one SDC (+ one optional netlist) through every analysis surface with consistent results — then close the highest-leverage feature gaps that are already scoped but not wired up. Full-chip stays a separate, already-designed phase (FULLCHIP_DESIGN_CONTEXT_PLAN.md).

**Definition of "block-level E2E" for this phase:** the same inputs (SDC + optional block-level netlist + optional TCL vars + optional custom rules) can be run through Check → Coverage → Clock Relations → Interactions → Readiness → Report, on **both the CLI and the Streamlit app**, with netlist-awareness available wherever the engine supports it, and identical numbers on both surfaces.

---

## 1. Audit: what already works (verified)

| Surface | Status | Evidence |
|---|---|---|
| `rta check` + `--netlist` + `--top` | ✅ working | SDC-055..059 netlist resolution + SDC-064..066 design-aware coverage; verified live |
| `rta check` JSON/JUnit/CSV/markdown, `--custom-rules`, `--gate`, baseline diff | ✅ working | 763-test suite + live runs |
| Streamlit app: Checker, Coverage, Clock tabs thread netlist | ✅ working | `_netlist_upload_widget` wired in all three |
| Engine `analyze_coverage(text, ctx)` — design-aware coverage | ✅ exists | `rta/engine/analysis/design_coverage.py:515` |
| PyPI install (`pip install rta-constraint-intelligence`) | ✅ done | v1.5.0 live, wheel+sdist, `[web]` extra verified |
| CLI docs / engineer guide | ✅ done | `docs/features/README-11-cli-user-guide.md` |

---

## 2. Audit: block-level E2E gaps (what's missing — verified)

| # | Gap | Where | Impact | Engine supports it? |
|---|-----|-------|--------|---------------------|
| G1 | **`rta coverage` has no `--netlist` flag** | CLI | Design-aware coverage (SDC-064..066) is unreachable from CLI — engine + Streamlit have it | ✅ yes (`analyze_coverage(text, ctx)`) |
| G2 | **`rta analyze clock-relations` has no netlist cross-check** | CLI | Clock source ports not verified against the netlist (Streamlit Clock tab does this) | ⚠️ partial — Streamlit does it via `validate_design_references`; needs wiring into CLI |
| G3 | **`rta report check` has no `--netlist`** | CLI | HTML report omits netlist-aware findings even though `rta check --netlist` produces them | ✅ yes (re-run with ctx) |
| G4 | ~~Readiness missing from report~~ — **verified FALSE** | `reporter.py` | HTML report already includes the 7-dimension readiness section + design-aware metadata (verified live: READY ×4, REVIEW_REQUIRED ×3 in output). Replace with: **lock it with a regression test** | ✅ already works |
| G5 | **No shared "run everything at once" CLI command** | CLI | Engineer must run 5 commands separately; no single-command E2E | ⚠️ new surface (Test Drive exists in UI only) |
| G6 | **Netlist not threaded to Diff / Interactions / Readiness tabs** | Streamlit | UI parity — these tabs are SDC-only today | ⚠️ by design (SDC-only analysis), verify only |
| G7 | Stray artifact `my_block_report.html` in repo root | repo | untracked file from testing | — |

---

## 3. Feature candidates (roadmap-aligned, highest leverage first)

### Tier A — Block-level E2E completion (this phase)

1. **CLI netlist parity (G1+G2+G3):** add `--netlist/--top` to `rta coverage`, `rta analyze clock-relations`, `rta report check` — engine already supports it; this is CLI-surface wiring, behavior-preserving. *Small, high-value, directly serves the engineer testing now.*
2. **Readiness in HTML check report (G4):** include the 7-dimension readiness verdict + fix-actions in `rta report check`. *Makes the report a true signoff artifact.*
3. **`rta analyze all` / `rta report all` (G5):** one command that runs check+coverage+clock+interactions+readiness and emits one summary (and one combined HTML report). *The E2E "one shot" the engineer asked for.*

### Tier B — Developer Experience (roadmap "Developer Experience" section)

4. **CI status badge** in README (`actions/workflows/ci.yml` badge) — CI already exists, badge doesn't. *5-minute win, visible credibility.*
5. **Shell completion** for `rta` (bash/zsh) + `--help` parity audit. *Nice-to-have for CLI users.*
6. **CI evidence bundle** `[speculative]` — attach gate verdict + snapshot JSON to CI runs. *Defer unless requested.*

### Tier C — Product Experience (roadmap next phase; depends on Streamlit app being the product app)

7. **Technical visualizations in the Streamlit app** (clock tree, relation matrix already partly there, coverage strips, readiness rail, interaction links). *The SPA visualizations don't apply — the product app is the Streamlit app; port the highest-value ones.*
8. **Website → workspace continuity** (shared tokens/typography). *Marketing polish; defer.*

### Tier D — Community

9. **Example library** — real design constraint sets + golden outcomes (reuse `rta/evidence/netlist_aware/` fixtures + samples). *Good for the engineer's evaluation.*
10. **Rule-authoring guide** for custom rules. *Docs task.*

### Explicitly deferred (do NOT do unless separately requested)

- **Full-chip / hierarchical resolution** — designed in FULLCHIP_DESIGN_CONTEXT_PLAN.md; separate gated phase after this one.
- **LLMs in the analysis path** — explicitly ruled out by roadmap.
- **Cloud processing without opt-in** — roadmap hard rule.
- **Team/Enterprise features** — speculative, undated.

---

## 4. Proposed next steps (ordered)

| Step | Work | Files touched | Est. effort | Gate |
|------|------|---------------|:-----------:|------|
| S1 | CLI netlist parity: `coverage --netlist`, `analyze clock-relations --netlist`, `report check --netlist` | `rta/cli/cli.py` + CLI tests | 0.5–1 day | ✅ done |
| S2 | **Regression test locking readiness-in-report** (feature exists; make it a contract) | test file | 0.25 day | ✅ done |
| S3 | `rta analyze all` (one-shot E2E, text/JSON/HTML) | `rta/cli/cli.py`, tests, guide | 1–1.5 days | ✅ done |
| S4 | CI badge + PyPI badge in README | `README.md` | 15 min | ✅ done |
| S5 | Regression: full pytest + smoke + clean PyPI re-verify | CI | — | 763/763 + smoke 19/19 |
| S6 | Update `README-11-cli-user-guide.md` + feature docs for new flags | docs | 0.5 day | docs match CLI |

**Definition of done for this phase:** an engineer can take one SDC + one block-level netlist and run `rta analyze all --netlist design.v --top top -o report.html` and get check + coverage + clock relations + interactions + readiness + one HTML report — with the same numbers in the Streamlit app.

---

## 5. Open questions for review

1. **Scope of S1:** add `--netlist` to all three commands (recommended), or only `coverage` + `report` (clock-relations netlist cross-check is the least-developed)?
2. **S3 shape:** `rta analyze all` (one combined JSON/text summary) + `rta report all` (one HTML)? Or a single `rta analyze all --html out.html`?
3. **Tier C priority:** start Streamlit visualizations after S1–S3, or after the engineer's feedback round?
4. **Example library (Tier D):** worth doing before the engineer finishes evaluating, or wait for their feedback?
