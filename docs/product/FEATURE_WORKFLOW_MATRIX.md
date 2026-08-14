# Ṛta — Feature Workflow Matrix

> Companion to `PRODUCT_WORKSPACE_ARCHITECTURE_V2.md`. One row per feature:
> the complete input → processing → output → next-step contract, plus where
> the workflow runs today (CLI / API / webui) and what the rebuild must
> preserve. Engine behavior frozen per `FUNCTIONAL_BASELINE.md`.

---

## Workflow matrix

| # | Feature | Entry (rebuild) | Input | Processing | Output | Next step | Today: CLI | Today: API | Today: webui |
|---|---------|-----------------|-------|------------|--------|-----------|:---:|:---:|:---:|
| 1 | **SDC Validator** | card → upload | SDC · netlist opt · top · custom-rules | preprocess + TCL resolve + rule engine + clock/interaction fold + readiness | findings (code/sev/msg/line), stats, scope | open Clocks / Coverage / Health / Design | `check` | `/api/analyze` | Findings |
| 2 | **SDC Generator** | card → form | params (design, clocks, OC, derate, scan…) | `generate_sdc` 22-section emit | SDC text (self-consistent) | open in Validator / download | `generate` | `/api/generate` | Generator |
| 3 | **SDC Linter** | card → upload | SDC | `lint_sdc` check/fix | issues + formatted text | download formatted / fix in place | `lint` | `/api/lint` | Linter |
| 4 | **SDC Converter** | card → upload + format | SDC · json/yaml | `parse_sdc` → structured | JSON / YAML doc | download / feed downstream tool | `convert` | `/api/convert` | Converter |
| 5 | **Clock Intelligence** | card → upload | SDC | `analyze_clock_relations` inference + mismatch/missing split | inventory, N×N matrix, mismatches + missing constraints | review missing constraints → add groups | `analyze clock-relations` | `/api/analyze` (clock section) | Clocks |
| 6 | **Coverage** | card → upload | SDC · netlist opt | 39-category gap analysis (+ design-aware) | score, present/total, categories, missing | fix missing categories | `coverage` | `/api/analyze` (`sdc_only_coverage`) | Coverage |
| 7 | **Design Context** | card → upload both | SDC + netlist + top | `design_context` + `design_coverage` | port/instance summary, netlist findings | review reset trees / unconstrained ports | `check --netlist` | `/api/analyze` (netlist) | Design |
| 8 | **Constraint Conflicts** | card → upload | SDC | `constraint_interactions` | duplicates/overrides/conflicts with line pairs | resolve or document | folded into `check` | `/api/analyze` (interactions) | Conflicts |
| 9 | **Readiness** | card → upload | SDC · baseline opt | `constraint_readiness` aggregation | tier + per-dimension WHY + actions | address P1/P2 actions | folded into `check` | `/api/analyze` (readiness) | Health |
| 10 | **SDC Diff** | card → upload V1+V2 | V1 SDC + V2 SDC · linked TCL opt | `constraint_diff` + tcl/wildcard | CHG-* changes (fatal/warning/info) + stats | export report / review fatals | `diff` | `/api/diff` | Changes |
| 11 | **Corner Manager** | card → manage | none (presets) / JSON | `corner_manager` model + validation | corner lists + JSON | pick corners → MMC | `corners list/show` (read-only) | `/api/corners` | Corner Manager |
| 12 | **MMC** | card → configure | template or params + corners | `mmc` generate/diff/check/zip | per-corner SDCs, cross-corner findings, ZIP | open a corner in Validator | — | `/api/mmc`, `/api/mmc/zip` | MMC |
| 13 | **Test Drive** | card → sample | sample picker or SDC | full battery through real backend | unified dashboard + JSON | open full session | — | (uses `/api/analyze`) | Test Drive |
| 14 | **Rules** | card → browse | none (browse) / SDC (execute) | `rules_registry` lookup | rule list/detail | search / export / see in results | `rules list/show` | `/api/rules` | Rules |
| 15 | **CI** | card → configure | SDC + baseline + gate policy | policy engine gate eval | PASS/FAIL + exit code + regression detail | wire to pipeline | `check --baseline --gate` | (via analyze) | CI |
| 16 | **Reports** | card → report | results per type | `reporter` HTML generation | self-contained HTML + JSON | open / share / archive | `report …` | `/api/report/html` | Report |
| 17 | **Trust** | card → read | none | presentation | standing disclosures | — | `rules`/docs | — | Trust |
| — | **Documentation** | support | none | docs rendering | guides | — | `whats-new`, help | — | Documentation |
| — | **Feedback** | support | thumbs + comment | `feedback.py` persistence | dashboard + entries | — | — | `/api/feedback` | Feedback |

---

## Workflow shape rules

1. **Input at entry** — each feature requests its own input at its own card; no
   global upload screen.
2. **Real backend** — every output is produced by the frozen engine (CLI/API
   parity verified); no mocked results (Test Drive included).
3. **Output with disclosure** — coverage, readiness, CI, and SDC-only outputs
   carry their standing trust statements.
4. **Next step always present** — every result suggests an optional next action.
5. **Session optional** — analysis-based features may share a session; diff /
   generate / convert / corners / mmc operate standalone and only link when the
   user chooses.

---

## Standalone vs session (current → target)

| Feature | Standalone today | Session today | Target |
|---|---|---|---|
| Validator | CLI `check` | webui Findings (needs analysis) | both |
| Generator | CLI + webui tool | webui "Open in Validator" link | both |
| Linter | CLI + webui tool | — | both |
| Converter | CLI + webui tool | — | both |
| Clocks | CLI `analyze clock-relations` | webui Clocks (session) | both |
| Coverage | CLI `coverage` | webui Coverage (session) | both |
| Design Context | CLI `check --netlist` | webui Design (session) | both |
| Conflicts | folded in check | webui Conflicts (session) | both |
| Readiness | folded in check | webui Health (session) | both |
| Diff | CLI `diff` | webui Changes (standalone upload) | both |
| Corners | CLI read-only | webui tool (editable) | both |
| MMC | — | webui tool | tool (+ CLI later, P2) |
| Test Drive | — | webui tool | tool |
| Rules | CLI `rules` | webui tool | both |
| CI | CLI `check --gate` | webui tool | both |
| Reports | CLI `report` | webui Report (session) | both |

---

## Input/output summary per feature (engineer's view)

| Engineer asks | Give Ṛta | Ṛta returns | Then |
|---|---|---|---|
| What's wrong with my SDC? | SDC | findings with rule codes + lines | fix errors, review warnings |
| What's missing? | SDC | coverage score + missing categories | add missing constraints |
| Are clocks right? | SDC | clocks + relation matrix + missing groups | add/verify clock groups |
| Does anything conflict? | SDC | conflict findings with line pairs | resolve/document |
| Is it ready for STA? | SDC (+ netlist) | readiness tier + WHY per dimension | clear REVIEW/BLOCKED items |
| Write me an SDC | params | generated SDC | open in Validator |
| Clean up this SDC | SDC | lint issues + formatted text | download fixed file |
| SDC → JSON/YAML | SDC + format | structured doc | feed tools |
| What changed between versions? | V1 + V2 | CHG-* changes + impact | review fatals |
| Run multi-corner | template + corners | per-corner SDCs + ZIP | check each corner |
| Should this merge? | SDC + baseline + gate | PASS/FAIL + exit code | wire to CI |
| Show me the rules | — | searchable registry | find the rule you need |
| Prove it works | SDC (or sample) | real results dashboard | open session / export |
