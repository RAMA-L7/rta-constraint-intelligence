# Ṛta — Sprint 3D Feature Audit

> Audited against `reference-features-for-startup.md` (the official feature
> inventory of Ṛta Version 1 — **single source of truth**).
> Scope: every feature in the reference must be **present, reachable and working**
> in the redesigned workspace (`webui/` + `api_server.py` + CLI). Backend
> deterministic modules are frozen; this audit is about product reachability.

Audit date: 2026-08-07 · Baseline: pytest **800/800** · UI **35/35** · UX **31/31**
· Motion **14/14** · State **12/12** · Smoke **10/10** · Evidence OK.

---

## 1. Audit matrix (before redesign fixes)

Every feature from `reference-features-for-startup.md` mapped to the workspace.
"Present" means wired to the real deterministic backend — no mock data.

| # | Feature (reference §) | Backend module | Workspace surface | Present | Missing | Notes |
|---|-----------------------|----------------|-------------------|:-------:|:-------:|-------|
| 1 | Validate / check (§3) | `checker.py` | **Findings** (`#/validator`) | ✅ | | metrics + table + inspector + source provenance |
| 2 | Generate (§4) | `generator.py` | **Generator** tool | ✅ | | Copy / Download .sdc / Open in Validator (Sprint 3C) |
| 3 | Lint / format (§5) | `linter.py` | **Linter** tool | ✅ | | fix vs check-only, issue list |
| 4 | Convert SDC→JSON/YAML (§6) | `converter.py` | **Converter** tool | ✅ | | JSON/YAML output + download |
| 5 | Batch runner (§7) | `batch_runner.py` | CLI only (`batch`) | ✅ | | reference marks it CLI-only; not a web surface |
| 6 | Semantic diff (§8) | `constraint_diff.py` + `tcl_resolver.py` + `wildcard_analyzer.py` | **Changes** (`#/diff`) | ✅ | | V1/V2 + Compare; linked-TCL via CLI flags |
| 7 | Clock relations (§10) | `clock_relations.py` | **Clocks** (`#/clocks`) | ✅ | | inventory + hierarchy + N×N matrix |
| 8 | Multi-corner manager (§11) | `corner_manager.py` + `mmc.py` | **Corner Manager** + **MMC** tools | ✅ | | presets, corner diff, cross-corner, ZIP |
| 9 | Constraint coverage (§12) | `coverage.py` | **Coverage** (`#/coverage`) | ✅ | | score + 6 categories + bus detail |
| 10 | Custom rules engine (§13) | `custom_rules.py` | Findings results render; **input was missing** | ⚠️ | **P0** | API + rendering existed; no YAML input surface → **fixed this sprint** |
| 11 | Rules registry (§14) | `rules_registry.py` | **Rules** tool | ✅ | | searchable + filterable |
| 12 | HTML reports (§15) | `reporter.py` | **Report** (`#/reports`) | ✅ | | HTML + JSON download |
| 13 | TCL resolver (§9) | `tcl_resolver.py` | via diff / CLI linked files | ✅ | | `--linked-v1/v2` CLI; UI Change page uses readiness authority |
| 14 | Wildcard analyzer (§9) | `wildcard_analyzer.py` | via diff risk text | ✅ | | CHG-WC rules surface in Changes |
| 15 | CI gates / policy | policy engine | **CI** tool | ✅ | | gate select in input + `#/ci` |
| 16 | Export | — | **Export** (`#/export`) | ✅ | | JSON snapshot + baseline download |
| 17 | Test drive (run-all) | all modules | **Test Drive** tool | ✅ | | sample picker → unified dashboard |
| 18 | Feedback dashboard | `ui/feedback.py` | **Feedback** tool | ✅ | | thumbs + comments persisted |
| 19 | Web UI | `api_server.py` + `webui/` | the workspace itself | ✅ | | |
| 20 | CLI (12 commands) | `cli.py` | CLI | ✅ | | unchanged contract |
| 21 | Packaging / Docker / CI workflows | `pyproject.toml`, `Dockerfile`, `.github` | repo surfaces | ✅ | | |

**P0 found:** feature #10 — custom-rules YAML input had no UI surface (engine + API
+ result rendering existed). A PD/STA engineer could not supply a team policy file
from the workspace.

---

## 2. Post-redesign audit matrix (verified)

| # | Feature | Verified Working | Manual / Browser Test | UI Location |
|---|---------|:-----------------:|:---------------------:|-------------|
| 1 | Validate | ✅ 800-test baseline | ✅ live run → Findings | `#/validator` |
| 2 | Generate | ✅ (Sprint 3C) | ✅ Generate → Copy/Download/Open | `#/generator` |
| 3 | Lint | ✅ | ✅ | `#/linter` |
| 4 | Convert | ✅ | ✅ | `#/converter` |
| 5 | Batch | ✅ CLI | CLI | `rta batch` |
| 6 | Semantic diff | ✅ | ✅ Compare → NEW/CHANGED/RESOLVED | `#/diff` |
| 7 | Clock relations | ✅ | ✅ matrix + hierarchy | `#/clocks` |
| 8 | Multi-corner | ✅ | ✅ presets + ZIP | `#/corners`, `#/mmc` |
| 9 | Coverage | ✅ | ✅ real netlist data | `#/coverage` |
| 10 | **Custom rules** | ✅ API round-trip | ✅ **UI input added + CUST-001 passes** | input on `#/new_analysis` + `#/validator` |
| 11 | Rules registry | ✅ | ✅ | `#/rules` |
| 12 | Reports | ✅ | ✅ HTML/JSON download | `#/reports` |
| 13 | TCL resolver | ✅ | ✅ CLI | `rta diff --linked-v1/v2` |
| 14 | Wildcard risk | ✅ | ✅ | `#/diff` risk text |
| 15 | CI gates | ✅ | ✅ gate policy select | `#/ci`, input panel |
| 16 | Export | ✅ | ✅ | `#/export` |
| 17 | Test drive | ✅ | ✅ | `#/test_drive` |
| 18 | Feedback | ✅ | ✅ | `#/feedback` |
| 19 | Web UI | ✅ | ✅ 200 on `/`, zero console errors | root |
| 20 | CLI | ✅ | ✅ | `rta` |
| 21 | Packaging | ✅ | ✅ evidence check | wheel |

**No feature removed. One feature completed (custom rules input).**

---

## 3. Design change record (this sprint)

The workspace presentation was rebuilt to the **Arcade-docs light language**
per founder directive (`docs.arcade.dev/en/home` style for page background/style):

- **Tokens** (`ui/theme.py` = single source of truth → `/api/design` → `theme.js` + `app.css`):
  pure-white page `#FFFFFF`, near-black text `#18181B`, hairline borders `#EAEAEA`,
  muted surfaces `#F6F6F6`; semantic status colors taken from the Arcade docs
  syntax palette — success `#2F6E4E`, error `#A8453A`, warning `#8A6C14`,
  info `#2563EB`.
- **Background layers**: white paper base + subtle hairline grid + restrained
  blue radial tint; `viz.js` topology redrawn for light (near-black hairline
  edges, blue pulses at low opacity).
- **Surfaces**: cmdbar/nav/rail/session-head now white-on-white with hairline
  borders; metric/readiness/trust rails use white cells + hairline separators
  (the Arcade "white cells on hairline grid" pattern); primary button is
  near-black with white text.
- **Typography unchanged** (Inter + JetBrains Mono — matches the reference
  sans/mono pairing).

No engineering semantics changed; the redesign is presentation-only.

---

## 4. Before vs after user journey

| Step | Before (Sprint 3C2) | After (Sprint 3D) |
|------|---------------------|-------------------|
| Launch | dark graphite workspace | light Arcade-style paper workspace |
| First screen | "Check your SDC before STA" landing, no sidebar | same flow, light palette, custom-rules advanced input |
| Analyze | timeline → auto-land Findings | unchanged behavior, light surfaces |
| Findings | dark cards | white cells + hairline separators, near-black text |
| Clocks / Coverage | dark matrix | light matrix, same interactions |
| Custom rules | **unreachable from UI** | YAML input on New Analysis + Validator |

---

## 5. Remaining gaps (honest)

- `batch` stays CLI-only (per reference).
- Diff UI uses the readiness-diff authority; the full `constraint_diff`
  21-rule CHG-* surface remains CLI (`rta diff`).
- Reference-doc §20 known limitations are backend notes (unchanged; backend frozen).
