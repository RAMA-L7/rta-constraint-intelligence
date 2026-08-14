# Ṛta — Benchmark Evidence Map

> **Document kind:** traceability — every headline engineering claim maps to a
> rerunnable benchmark artifact. No marketing number may exist without
> evidence.
> **Date:** 2026-08-07 · **Version:** v1.3.0
> **Canonical source:** `RELEASE_EVIDENCE.json` (regenerated and CI-verified by
> `benchmarks/build_evidence.py --check`).

---

## 1. Policy

- Benchmark evidence is **preserved as-is** across the brand migration
  (Category D in `BRAND_MIGRATION_AUDIT.md`). Suites, manifests, golden
  expectations and historical reports were not rewritten to fit the rebrand.
- Any changed expectation must be justified as a **branding change**, never as
  “the test failed, so we changed it”.

## 2. Headline evidence table

| Claim | Suite / runner | Command | Expected | Measured (2026-08-06) |
|---|---|---|---|---|
| Unit + regression suite green | pytest suite | `python -m pytest tests/ -q` | 887 passed | 887 passed |
| Release smoke green | `benchmarks/test_release_smoke.py` | `pytest benchmarks/test_release_smoke.py -q` | 10 passed | 10 passed |
| Golden runners green | `benchmarks/golden`, `golden_semantic`, `reference_designs`, `netlist_aware` (+ runners) | per-suite runners | 9/9 | 9/9 (Phase 14/15 baselines) |
| Benchmark suites green | `benchmarks/*` | `benchmarks/run_benchmark.py` | 42/42 | 42/42 (2026-08-07) |
| UI/API benchmark | `benchmarks/test_ui_app.py` | `python benchmarks/test_ui_app.py` | 35/35 | 35/35 |
| Workspace UX benchmark | `benchmarks/test_workspace_ux.py` | `python benchmarks/test_workspace_ux.py` | 31/31 | 31/31 |
| State isolation | `benchmarks/test_ui_state_isolation.py` | `python benchmarks/test_ui_state_isolation.py` | 12/12 | 12/12 |
| Motion checks | `benchmarks/test_motion.py` | `python benchmarks/test_motion.py` | 14/14 | 14/14 |
| CLI contract | `benchmarks/release_cli_audit.py` | `python benchmarks/release_cli_audit.py` | 16/16 | 16/16 (Phase 14 baseline) |
| Clean-room wheel journey | packaging checks | build wheel → install to fresh target → serve | 17/17 | 17/17 (Phase 14 baseline) |

> Current-run values are recorded in `benchmarks/RTA_FOUNDATION_REPORT.md`.
> Entries marked “Phase 14/15 baseline” refer to the last fully recorded run
> before this phase; the full regression for this phase re-runs every suite.

## 3. Suite inventory (evidence artifacts)

| Suite | Location | Proves |
|---|---|---|
| Golden parser suite | `benchmarks/golden/` | parser determinism against reference SDC files |
| Golden semantic suite | `benchmarks/golden_semantic/` | semantic check determinism |
| Reference designs | `benchmarks/reference_designs/` | realistic multi-clock, generated-clock, DDR-style, multi-mode designs |
| Netlist-aware suite | `benchmarks/netlist_aware/` | design-context + design-aware coverage behavior |
| Adversarial suites | `test_*_adversarial.py`, `test_*_metamorphic.py`, `test_*_mutation.py`, `test_*_security.py` | robustness, mutation sensitivity, security |
| Release smoke | `test_release_smoke.py` | install + documented workflow |
| UI/API + workspace UX + state isolation + motion | `test_ui_app.py`, `test_workspace_ux.py`, `test_ui_state_isolation.py`, `test_motion.py` | product surfaces |
| CLI audit | `release_cli_audit.py` | CLI contract incl. `Ṛta v1.3.0` version output |

## 4. Trust claims traceable to evidence

| Claim | Evidence |
|---|---|
| Deterministic (identical input → identical output) | repeated-validation tests, golden suites, state isolation |
| No AI in runtime | phase 13/14 audits (`PHASE13_PRODUCTION_HARDENING_REPORT.md`) + `api_server.py` banner |
| Engine failure never passes | `test_engine_failure_never_passes` |
| XSS-safe HTML reports | `test_html_report_escapes_sdc_content` |
| O(N²) clock relations | `test_large_design_relations_fast_and_correct` |
| Structured finding identity (not line diff) | `test_save_baseline_writes_snapshot` (schema v2, identity v1) |

## 5. What is NOT evidence

Numbers on the marketing site that lack a runner here are **not published**.
The benchmarks page (`site/benchmarks.html`) links each claim to its artifact.
