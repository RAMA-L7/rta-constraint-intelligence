# SDC Tools — Release Manifest

Verified against **v1.3.0** (Phase 14 release-candidate audit, 2026-08-06).

This manifest records what was actually verified for this release candidate. It
is a checklist with evidence, not certification language.

## Verification matrix

| Check | Result | Evidence |
|---|---|---|
| Python version used | 3.10 (Windows) | `python --version` |
| OS / environment | Windows 10, bash shell | — |
| Full pytest suite | 689/689 PASS | `python -m pytest tests/ -q` |
| Golden runners | 9/9 PASS | `run_golden`, `run_golden_semantic`, `run_reference_designs`, `run_design_coverage`, `run_netlist_aware`, `run_constraint_interactions`, `run_readiness`, `run_readiness_diff`, `run_production_hardening` |
| Benchmark suites | 28/28 PASS | `test_*.py` benchmark suites (adversarial, metamorphic, security, perf, CI gate, UI, state, stress) |
| Wheel build | PASS | `python -m build --wheel --sdist`; all modules + `ui/` + `app.py` present |
| Wheel install (fresh venv) | PASS | `benchmarks/release_cleanroom.py` — 17/17 (install, CLI, entry point, check, JSON, report, baseline, gate pass/fail, custom policy, netlist-aware, Python API, error journey, offline) |
| sdist build | PASS | built alongside wheel in same `python -m build` run |
| CLI `--help` / `--version` | PASS | exit 0, correct output |
| Core validation (SDC-only) | PASS | `sdc-tools check samples/example.sdc` |
| Netlist-aware validation | PASS | `--netlist` smoke + clean-room |
| JSON output purity | PASS | stdout parses as JSON; no banner/progress mixed in |
| JSON output-file safety | PASS | `--json --output file` writes parseable content (regression-fixed) |
| HTML report generation | PASS | `report check` produces valid HTML with readiness + trust disclosures |
| HTML escaping (XSS) | PASS | `<script>` content renders escaped; regression tests added |
| Baseline save/load | PASS | `--save-baseline` / `--baseline` round-trip |
| Readiness diff | PASS | semantic diff vs baseline |
| CI gate PASS | PASS | same SDC vs baseline → exit 0 |
| CI gate FAIL | PASS | new blocker vs baseline → exit 1 |
| CI gate invalid invocation | PASS | missing baseline / missing policy / bad policy → exit 2 |
| Exit-code contract | PASS | 0=pass, 1=fail, 2=invalid, 3=engine (see report §17) |
| Engine failure never PASS | PASS | malformed policy → exit 2; SDC-140 path tested |
| Snapshot schema v2 + v1 compat | PASS | Phase 13 suites |
| CUSTOM policy (inert data) | PASS | no eval/exec; security suite |
| Offline operation | PASS | no network imports in wheel; validation runs locally |
| Version consistency | PASS | CLI `1.3.0` == JSON `1.3.0` == snapshot `tool_version` `1.3.0` |
| Release smoke suite | 10/10 PASS | `benchmarks/test_release_smoke.py` |
| Web UI (installed wheel) | Deferred to deploy-time smoke | Streamlit UI not launched in audit (see report §Known limitations) |

## What PASS means here

- **pytest PASS** — the deterministic test suite passes; it exercises the
  validator's documented semantics.
- **Gate PASS (exit 0)** — under the selected policy, no disallowed
  constraint-readiness regression was detected against the stated baseline.
- **Readiness READY** — the constraint set satisfies the validator's
  supported, evidence-backed readiness criteria for the stated analysis mode.

None of the above means STA timing signoff, timing closure, or path
correctness.

## Known limitations (disclosed)

- Python 3.10 tested on Windows; 3.11/3.12 not executed in this audit
  (requires additional environments).
- Web UI startup verified only via repo tests, not via an installed-wheel
  launch in this audit run.
- SDC/Verilog support is bounded by the documented support boundary
  (see `docs/features/README-07` and support matrix); constructs outside it
  are reported as unsupported, not silently assumed correct.

## Release decision

See `benchmarks/PHASE14_RELEASE_CANDIDATE_AUDIT_REPORT.md` §51.
