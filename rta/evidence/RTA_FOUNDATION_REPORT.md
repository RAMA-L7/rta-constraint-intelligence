# Ṛta Foundation — Startup Identity & Product Architecture

> **Phase report** · 2026-08-06 · Version v1.3.0 (unchanged)
> The repository's deterministic backend is untouched; this phase changed
> **product identity**, not validation semantics.

---

## 1. Executive summary

The repository — formerly presented as “SDC Validator / SDC Tools” — is now
established as **Ṛta** (“Ri-ta”), *Constraint Intelligence for Digital
Design*, with the working positioning *bring order to timing intent before
STA*.

- Visible brand **Ṛta** (Unicode U+1E5A) everywhere: website, workspace,
  CLI, reports, generated SDC, README, docs, metadata.
- Technical ASCII identifier **`rta`** added (CLI alias + `rta.cmd`);
  `sdc-tools` retained as a fully supported alias. Package/wheel names are
  unchanged this phase (documented decision).
- 10 foundation documents created under `docs/rta/`.
- README rewritten as a startup-grade product README.
- Zero validation-semantics changes; **780/780** tests, all golden runners,
  all benchmark suites, release smoke, CLI contract, UI benchmarks and
  clean-room packaging verified green after migration.

## 2. Baseline (before migration)

| Area | Result |
|---|---|
| pytest | 709 passed / **1 failed** (`test_cli_web_resolves_app_path` — Phase 17 architecture change: `cmd_web` now launches `api_server.py`, not `app.py`) |
| Release smoke | 10/10 |
| CLI contract audit | 16/16 |

The single failure was **not** a product defect: it asserted the pre-Phase-17
`app.py` launch path. It was updated to assert the current architecture
(api_server.py + webui/) with identical intent (any-cwd resolution).

## 3. Repository audit

Classified every product-facing occurrence:
- `SDC Validator` — 103 hits · `SDC Tools` — 84 hits · `sdc-tools` — 189 hits
  (technical identifier — largely preserved).

## 4. Brand migration decisions

Full classification in `docs/rta/BRAND_MIGRATION_AUDIT.md`:

- **A — MUST REBRAND:** 104 product-name occurrences → `Ṛta` (website,
  workspace, CLI, reports, generator, docs, repo presentation, agents).
- **B — TECHNICAL TERMINOLOGY KEPT:** SDC, SDC-046, `check_sdc()`,
  `sdc_preprocess.py`, rule codes — untouched.
- **C — TECHNICAL IDENTIFIERS:** `rta` alias added; package/wheel `sdc-tools`
  kept this phase (documented migration path).
- **D — HISTORICAL EVIDENCE PRESERVED:** `benchmarks/PHASE*.md`,
  `QA_REPORT.md`, `GOLDEN*`, manifests, `data/feedback.json` — untouched.
- **E — REMOVED:** stale `build/` artifacts.

## 5–6. Brand origin & positioning

See `docs/rta/BRAND_FOUNDATION.md`: inspired by the idea of **order** —
individual elements fitting into a coherent whole; restrained, non-mythological;
explicitly **not AI** (deterministic, evidence-backed, local-first).

## 7. Capability map

`docs/rta/CAPABILITY_MAP.md` — 15 core + 7 tooling capabilities, each mapped
to its backend module, trust level, CLI/UI/report surface and benchmark
evidence.

## 8. Product taxonomy

`docs/rta/PRODUCT_TAXONOMY.md` — **Ṛta Validate · Clocks · Context ·
Coverage · Interactions · Readiness · Diff · CI**, each grounded in real
backend modules; auxiliary capability grouped under Tools (fully preserved).

## 9. Technical identifier strategy

| Identifier | Decision |
|---|---|
| Visible brand | `Ṛta` (Unicode) |
| ASCII identifier | `rta` — new CLI alias + `rta.cmd` |
| CLI legacy | `sdc-tools` (alias, kept) |
| Package/wheel | `sdc-tools` / `sdc_tools-*` (unchanged this phase) |
| Python namespace | flat modules (unchanged); `rta/` package is a documented target |
| Version | `1.3.0` |

## 10–11. Website & README migration

- Website: all 15 pages rebranded (titles, meta, hero, brand lockup, CTA
  “Launch Ṛta”, hero terminal `rta check …`); zero legacy proper-nouns remain.
- README: rewritten as the Ṛta product README (quick start with `rta check`,
  module table, CLI reference, trust model, benchmarks, architecture, open
  core).

## 12. CLI / package decisions

- `pyproject.toml`: description carries the Ṛta positioning; **`rta =
  "cli:main"`** entry point added alongside `sdc-tools`.
- `cli.py`: `--version` → `Ṛta v1.3.0`; command headers → `Ṛta v1.3.0 — …`;
  `prog` now follows the invoked name (`rta`/`sdc-tools`); stdout/stderr
  forced to UTF-8 at `main()` so the Unicode brand survives Windows pipes.

## 13. Trust model

`docs/rta/TRUST_MODEL.md` — READY ≠ STA signoff; coverage ≠ correctness;
CI pass ≠ timing closure; object resolution ≠ path existence; engine failure
never passes. Trust/readiness status vocabularies defined verbatim.

## 14. Benchmark evidence

`docs/rta/BENCHMARK_EVIDENCE_MAP.md` — every headline claim mapped to a
runner; historical evidence preserved verbatim.

## 15. Open-core strategy

`docs/rta/OPEN_CORE_STRATEGY.md` — Community (open, MIT) vs future Team /
Enterprise (**additive only**; nothing existing moves behind a paywall).

## 16. Unicode verification

- `tests/test_branding.py` (70 checks): `Ṛta` present on every user surface;
  `rta` ASCII entry points; no `SDC Validator`/`SDC Tools` in migrated
  surfaces; SDC terminology preserved; CLI/report/generated-SDC Unicode safe.
- CLI forces UTF-8 stdout (`main()` reconfigure) — verified from a clean
  wheel install.

## 17. Security verification

No escaping logic changed. XSS/security suites green after migration:
`test_security`, `test_ph13_security`, `test_netlist_security`,
`test_html_report_escapes_sdc_content` (smoke), WS-18 (workspace UX).

## 18. Files changed

**New:** `docs/rta/*` (10), `tests/test_branding.py`, `rta.cmd`.
**Rewritten:** `README.md`.
**Rebranded (code):** `cli.py`, `reporter.py`, `generator.py`, `app.py`,
`api_server.py`, `webui/` (index, 5 JS modules, CSS, `__init__.py`),
`ui/*` (15 modules), `site/` (15 HTML pages, site.js, site.css),
`__init__.py`, `support_boundary.py`, `custom_rules.py`,
`custom_rules_example.yaml`, `Dockerfile`, `CHANGELOG.md`,
`CONTRIBUTING.md`, `.claude/*` (7), `docs/features/*` (10),
`docs/product/*` (5), `tests/__init__.py`, `tests/conftest.py`,
`benchmarks/README.md`, `benchmarks/run_benchmark.py`.
**Packaging:** `pyproject.toml` (description + `rta` entry point).
**Tests updated:** `tests/test_cli.py`, `tests/test_reporter.py`,
`tests/test_regressions.py`, `benchmarks/test_release_smoke.py`,
`benchmarks/release_cli_audit.py`, `benchmarks/test_ui_app.py`.
**Benchmark re-targeted:** `benchmarks/test_reference_ui.py` (Phase 6
AppTest harness → Phase 17 workspace API; identical behavioral coverage;
additionally exposed and fixed a real UI inconsistency — the Validate rail
clock count now matches the checker's unique-clock stat while the Clocks
page keeps the full parsed inventory).

## 19. Regression results (after migration)

| Area | Result |
|---|---|
| pytest | **780/780** (710 baseline + 70 brand/Unicode tests) |
| Release smoke | 10/10 |
| CLI contract audit | 16/16 |
| Golden runners | **9/9** (golden, golden_semantic, reference_designs, netlist_aware, design_coverage, interactions, readiness, readiness_diff, production_hardening) |
| Benchmark suites | **37/37** (36 green + reference_ui re-targeted 7/7) |
| UI/API benchmark | 35/35 |
| Workspace UX | 31/31 |
| State isolation | 12/12 |
| Motion | 14/14 |
| Clean-room wheel | built; installed to fresh target; `Ṛta v1.3.0` CLI + workspace with Ṛta title served; `rta` entry point in wheel metadata |

## 20. Reviewer findings & fixes

Independent review (code-reviewer) findings — all addressed:

1. **CLI Unicode stdout gap** (argparse `--version` + `cmd_web` banner could
   crash on Windows cp1252 piped stdout) → fixed: UTF-8 reconfigure at
   `main()` entry.
2. **`rta` alias vs hardcoded `prog`** → fixed: `prog` follows the invoked
   name (`rta` / `sdc-tools`).
3. **Brand-sub drift** between workspace and website → aligned on
   “Constraint Intelligence for Digital Design”.
4. **Narrow brand guard** → broadened; the broadened guard immediately
   caught 12 missed `ui/*` module docstrings, which were then fixed to the
   proper Unicode form.
5. **Stray untracked `benchmarks_0.zip` / `benchmarks_1.zip`** at repo root —
   pre-existing artifacts (not from this phase); left for the owner to
   delete/ignore.

## 21. Remaining risks

- Package/wheel name remains `sdc-tools`; the `rta` Python namespace is a
  documented target, not yet executed (gated migration path in
  `docs/rta/REPOSITORY_ARCHITECTURE.md`).
- Legacy Streamlit `ui/` still shipped (functional); retirement gated on
  webui parity.
- `rta` console script verified via wheel entry-point metadata + module
  execution; a real pip install is needed to exercise the generated
  `rta.exe` wrapper (standard mechanism).
- The Phase 17 UI-rebuild report deliverable was superseded by this phase;
  its work (workspace, website, motion, benchmarks) is complete and green.

## 22. Recommended next phase

**“Ṛta Product Experience — From-Scratch Application UI & Motion System.”**
The identity foundation is in place; the next phase builds the complete Ṛta
application experience (motion system, silicon-topology background, Clock
Intelligence / Coverage / Readiness / Diff visualizations, website →
workspace continuity) per `docs/rta/VISUAL_IDENTITY_DIRECTION.md` and
`docs/rta/PRODUCT_ROADMAP.md`.
