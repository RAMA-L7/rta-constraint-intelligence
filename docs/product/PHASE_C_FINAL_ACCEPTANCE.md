# Ṛta — Phase C Final Acceptance

> **Phase C — Feature Workflow Implementation** is complete. All 19 product
> capabilities follow the feature-first contract:
>
> **FEATURE CARD → OWN INPUT → REAL BACKEND → REAL RESULT → NEXT ACTION**
>
> The deterministic engine was frozen throughout (`FUNCTIONAL_BASELINE.md`);
> this phase changed entry points, input surfaces, presentation and next
> actions only — never engineering results. Verified against the live API,
> the CLI, the 200-file parity harness and headless-Chrome browser walks.
>
> Baseline: Ṛta v1.5.8 · engine: frozen-deterministic · trust disclosures intact.

---

## Status rollup

| Metric | Value |
|---|---|
| Total capabilities | 19 |
| **PASS** | **19** |
| PARTIAL | 0 |
| FAIL | 0 |
| P0 | 0 |
| P1 | 0 |
| P2 (from acceptance report, unchanged) | 10 (none block any workflow; tracked in `PRODUCT_REBUILD_PLAN.md`) |
| Known limitations | corner editing / MMC generation not exposed in CLI (P2-1); no true READY fixture in the corpus (readiness honest-limitation); JUnit/HTML/JSON reports verified from CLI + API |
| Regressions | 0 (engine byte-identical across Groups 1–4) |
| Tests | 1,227 pytest · 58/58 workspace UX · 37/37 UI/API · 12/12 state isolation · 10/10 smoke · 17/17 cleanroom · 16/16 CLI audit · parity 0 semantic diffs |

---

## Complete capability matrix (19/19 PASS)

Legend: **E**=entry · **I**=input · **B**=backend · **O**=output · **N**=next action · **S**=standalone · **Se**=session · **Er**=error state · **Em**=empty state · **T**=tests · **Br**=browser verified · **St**=status

### Group 1 — Core

| # | Capability | E | I | B | O | N | S | Se | Er | Em | T | Br | St |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Validate | card → `#/validator` | SDC req · netlist opt · baseline/gate/custom opt | `POST /api/analyze` (frozen checker) | findings (code/sev/msg/line), stats, scope, readiness | Clocks/Coverage/Conflicts/Health/Report | yes | implicit | HTTP 400 on empty; engine failure never fakes PASS | "Ready to analyze" | UI-01..37 · WS-01..31 · 1227 pytest | ✓ | **PASS** |
| 2 | SDC Generator | card → `#/generator` | params only (design, clock, delays) | `POST /api/generate` (frozen generator) | self-consistent SDC (no malformed OC — P1-3) | **Open in Validator** · Copy · Download | yes | optional | API failure → toast | params form | gen→lint→check PASS · test_generator 31 | ✓ | **PASS** |
| 3 | SDC Linter | card → `#/linter` | SDC req | `POST /api/lint` (frozen linter) | warning count, formatted text | Download | yes | — | empty blocked + HTTP 400 | textarea prompt | test_linter 17 · API live | ✓ | **PASS** |
| 4 | SDC Converter | card → `#/converter` | SDC req · format (json/yaml) | `POST /api/convert` (frozen parser) | structured JSON/YAML + download | Download | yes | — | empty blocked + HTTP 400 | textarea prompt | test_converter 14 · API live | ✓ | **PASS** |

### Group 2 — Analysis

| # | Capability | E | I | B | O | N | S | Se | Er | Em | T | Br | St |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | Clock Intelligence | card → `#/clocks` | SDC req (own panel) | `POST /api/analyze` → clock_relations | inventory, hierarchy, matrix, mismatches + missing constraints + advisories (P1-2 split) | Coverage/Conflicts/Readiness · JSON | yes | implicit | 400 on empty | "No clocks yet" | WS-23 · generated-clock fixtures | ✓ | **PASS** |
| 6 | Coverage | card → `#/coverage` | SDC req · netlist opt | `POST /api/analyze` → 39-category + design-aware | SDC-only score/present/total/missing + **Coverage is NOT correctness**; design-aware port coverage | Review missing · Validate | yes | implicit | 400 on empty; honest insufficient | "No coverage yet" | WS-24/24b/24c | ✓ | **PASS** |
| 7 | Design Context | card → `#/context` | SDC req · netlist req for object resolution | `POST /api/analyze` → netlist parser | structural inventory + hierarchy; honest "Netlist not supplied" limitation | Coverage (design-aware) · findings | yes | implicit | no netlist → typed insufficient | "No design context" | WS-24c · both modes live | ✓ | **PASS** |
| 8 | Constraint Conflicts | card → `#/interactions` | SDC req (own panel) | `POST /api/analyze` → interactions | SDC-067/068/069 with codes/lines/what-why-review | findings · Readiness | yes | implicit | 400 on empty | paste SDC | WS-26 | ✓ | **PASS** |
| 9 | Readiness | card → `#/readiness` | SDC req · netlist opt | `POST /api/analyze` → readiness | BLOCKED/REVIEW_REQUIRED/READY + per-dimension WHY + disclosures | blockers · Report | yes | implicit | 400 on empty | paste SDC | WS-25 · BLOCKED+REVIEW verified (no READY fixture — documented) | ✓ | **PASS** |
| 10 | SDC Diff | card → `#/diff` | V1 + V2 SDC (independent) | `POST /api/diff` → readiness diff + CHG-* engine | tier delta, findings, constraint changes (before/after+why), gate, debt | Open V2 in Validate · Report · JSON | yes | none required | missing V1/V2 blocked | "No comparison yet" | WS-22b/27/27b | ✓ | **PASS** |

### Group 3 — Advanced

| # | Capability | E | I | B | O | N | S | Se | Er | Em | T | Br | St |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | Corner Manager | card → `#/corners` | preset (CLASSIC_3/5/8) | `POST /api/corners` → corner_manager | validated corner table + matrix + JSON export | **Open MMC** · Export | yes | none | API failure → toast; read-only scope disclosed | preset selector | WS-31b | ✓ | **PASS** |
| 12 | MMC | card → `#/mmc` | corner preset (REQUIRED — reaches backend) · design · clock | `POST /api/mmc` + `/zip` → mmc engine | per-corner SDCs (own OC), diffs, multi-check, ZIP | **Open in Validate** · Download | yes | optional | API failure → toast | inputs explained | WS-29/29b · UI-36/37 | ✓ | **PASS** |
| 13 | Test Drive | card → `#/test_drive` | sample choice (4) | `POST /api/analyze` with sample → real pipeline | real result summary + read-only sample + explanation | Open findings/clocks/coverage · JSON | yes | optional | backend failure → typed error | sample pre-selected | WS-31 · Test Drive parity 6/6 | ✓ | **PASS** |
| 14 | Rules | card → `#/rules` | browse: none; execute: SDC + YAML | `GET /api/rules` (119) + `POST /api/analyze` custom_rules | registry browse (sev filter, downloads) + real per-rule PASS/FAIL | Run custom rules · download registry | yes | none | invalid YAML → typed error | example ruleset 1-click | WS-30 · test_custom_rules 17 | ✓ | **PASS** |
| 15 | CI | card → `#/ci` | SDC req · baseline opt (Build baseline = real snapshot) · policy req | `POST /api/snapshot` (new) + `POST /api/analyze` gate | gate result + **exit code** + reasons + JSON; CLI contract 0/1/2/3 | Download gate JSON | yes | none | invalid baseline → "gate did not run"; empty SDC blocked | all inputs explained | WS-28/28b/28c · CLI exits verified live | ✓ | **PASS** |

### Group 4 — Output / Support

| # | Capability | E | I | B | O | N | S | Se | Er | Em | T | Br | St |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 | Reports | card → `#/reports` (+ `#/export`) | an analysis | `POST /api/report/html` (frozen reporter) + JSON + snapshot | HTML (real findings/lines/readiness/trust), JSON, readiness snapshot | Download · CLI equivalents | no (needs analysis) | yes | API failure → toast | "No analysis to report" | WS-32/32b/35/35b · CLI report 14.6 KB · JUnit verified | ✓ | **PASS** |
| 17 | Trust | card → `#/trust` | none (reads run scope) | `GET /api/evidence` (new — manifest-derived) + `/api/design` | evidence-backed facts (119 rules/886 tests/v1.5.8/no-LLM) + boundary statements + validates/requires-STA | Documentation · Reports | yes | implicit | evidence fetch fails → boundaries still render | n/a | WS-33 | ✓ | **PASS** |
| 18 | Documentation | card → `#/documentation` | none | `/api/rules` + static index | "I want to…" → real capability links + feature docs + references | Open → (lands on real pages) | yes | none | n/a | n/a | routes verified · stale `sdc-tools` removed from docs/features | ✓ | **PASS** |
| 19 | Feedback | card → `#/feedback` | feature · rating · comment (req, ≤2000) | `POST /api/feedback` → `data/feedback.json` | honest success only after backend accepts; rejection messages | — | yes | none | empty/overlong rejected; failure → toast | form explained | WS-34/34b/34c (self-cleaning) | ✓ | **PASS** |

---

## Cross-feature output flows (verified)

| Flow | Result |
|---|---|
| Validate → Report → Download | ✓ HTML (14.5 KB, real findings) + JSON |
| Coverage → Report → Download | ✓ |
| Diff → Report → Download | ✓ (readiness + CHG-* changes) |
| CI → Gate result → Download gate JSON | ✓ exit 0/1/2 with reasons |
| Test Drive → Findings → Report | ✓ sample adopts session → report |
| Generator → Validator → Report | ✓ "Open in Validator" adopts → report |

## CLI exit-code contract (verified live)

| Case | Exit |
|---|---|
| Gate PASS (no readiness regression) | 0 |
| Gate FAIL (regression introduced) | 1 |
| Invalid policy / missing baseline / invalid input | 2 |
| Engine failure | 3 (never a silent PASS) |
| Plain check with errors | 1 |
| Plain check clean | 0 |

## Trust disclosures (preserved everywhere)

- "NOT an STA timing signoff" · "READY does not mean setup/hold passes"
- "Coverage is NOT correctness" · "CI PASS ≠ timing pass"
- "Engine failure never becomes PASS" · netlist-aware analysis is structural, not a schematic
- Deterministic: no LLM, no model inference, no external AI APIs — local, reproducible, offline-capable

## Evidence / trust audit summary

- Stale `sdc-tools` product names removed from webui, website (47 refs), JUnit suite name, and `docs/features/*` (both copies).
- Stale `v1.5.6` → `v1.5.8` in `rta/website/benchmarks.html`.
- GitHub artifact URLs corrected to `RAMA-L7/rta-constraint-intelligence`.
- No stale test counts in user surfaces; Trust/Reports derive counts from `RELEASE_EVIDENCE.json` + live registry via `/api/evidence`.

## Known limitations (honest, unchanged)

1. **P2-1** — corner creation/editing and MMC generation have no CLI (API/webui only); Corner Manager page discloses read-only inspection.
2. **No true READY fixture** in the corpus — Readiness verified at BLOCKED and REVIEW_REQUIRED tiers; a READY fixture was not manufactured.
3. **Coverage ≠ correctness** — surfaced on every coverage surface; no claim of timing accuracy.
4. **P2 (10)** from the acceptance report remain tracked in `PRODUCT_REBUILD_PLAN.md`; none block any of the 19 workflows.

## Regressions

None. Groups 1–3 remain green; parity harness shows 0 semantic diffs vs the frozen baseline across all 200 corpus files and 9 batteries.

## Exact next phase

**Phase D — Feature verification sign-off** (formalize the acceptance evidence), then **Phase E — Workspace UX** and **Phase F — Visual design system**. The functional layer is complete, visible, individually usable and verified — the experience phase can begin.

---

*Document generated at the close of Phase C (Groups 1–4). Engine frozen; functional baseline intact.*
