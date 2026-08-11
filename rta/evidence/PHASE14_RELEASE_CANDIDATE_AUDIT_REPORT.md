# PHASE 14 — Release Candidate Architecture & Product Readiness Audit

**Date:** 2026-08-06 · **Target:** SDC Tools v1.3.0 (deterministic SDC Validator)

> Audit, not feature development. No new SDC rules, no STA, no AI in the
> runtime. Previously validated capability was regression-tested, not re-derived.

---

## 1. Executive release assessment

The SDC Validator is a **release candidate**. Two release-blocking defects found
during this audit were fixed and re-verified:

1. **Packaging (RC-BLOCKER → fixed):** the wheel built from `pyproject.toml`
   was missing every Phase 8–13 module, the `ui/` package, and `app.py` — an
   installed wheel would crash on `sdc-tools check` and `sdc-tools web`.
2. **Security (RC-BLOCKER → fixed):** the HTML report generator interpolated
   user-controlled SDC content (issue messages, object names, clock names)
   without escaping — a `<script>` in an SDC became stored XSS in the report.

Both are fixed, regression-tested, and re-verified from a freshly built wheel
installed into a clean virtual environment (**17/17 clean-room checks**).

**Final decision: `RC_READY_WITH_KNOWN_LIMITATIONS`** (see §51).

---

## 2. Baseline (verified before any changes)

| Suite | Result |
|---|---|
| pytest | **689/689 PASS** |
| Golden runners (9) | parser 22/22 · semantic 9/9 · reference 8/8 · coverage 12/12 · netlist-aware 10/10 · interactions 20/20 · readiness 15/15 · readiness-diff 22/22 · PH13 49/49 |
| Benchmark suites (28) | **28/28 PASS** |
| Python | 3.10 (Windows, WindowsApps distro) |
| OS / shell | Windows 10, bash |

## 3. Audit graph execution summary

```
BASELINE GATE (689/9/28 green) ─────────────┐
   │  (2 RC-blockers found immediately)     │
   ▼                                        │
PACKAGING AUDIT ──► wheel missing 9 modules  ──► FIX pyproject.toml + Dockerfile
   │                    + ui/ + app.py           └─► wheel rebuild verified
   ▼
SECURITY AUDIT ────► raw HTML interpolation  ──► FIX reporter.py esc() everywhere
   │                                             └─► XSS regression tests added
   ▼
CLI CONTRACT AUDIT (16/16) + CLEAN-ROOM (17/17) + DOCS TRUTH + SUPPORT BOUNDARY
   ▼
REVIEWER (7 findings) ──► esc() coverage gap, _COV_CSS dead code,
   │                        weak exit assertion, generate/convert writes,
   ▼                        web-from-wheel verify, .dockerignore, renames
TARGETED FIXES ──► FULL REGRESSION (691 pytest, 9 golden, 28 suites, 17/17 clean-room)
   ▼
RELEASE GATE: RC_READY_WITH_KNOWN_LIMITATIONS
```

## 4. Repository architecture inventory

| Class | Modules |
|---|---|
| CORE | `sdc_preprocess.py`, `checker.py`, `linter.py`, `tcl_resolver.py`, `wildcard_analyzer.py` |
| ANALYSIS | `clock_relations.py`, `support_boundary.py`, `constraint_interactions.py` |
| DESIGN-AWARE | `design_context.py`, `design_coverage.py`, `mmc.py`, `coverage.py` |
| READINESS | `constraint_readiness.py` |
| DIFF/CI | `readiness_diff.py`, `constraint_diff.py`, `finding_identity.py`, `policy_engine.py` |
| UI | `app.py`, `ui/` |
| REPORTING | `reporter.py`, `rules_registry.py` |
| CLI | `cli.py`, `batch_runner.py`, `sdc-tools.cmd` |
| TEST | `tests/` (27 files, 691 tests) |
| BENCHMARK | `benchmarks/` (runners + suites + fixtures + phase reports) |
| DOCUMENTATION | `README.md`, `docs/features/`, `CHANGELOG.md`, `CONTRIBUTING.md` |
| PACKAGING | `pyproject.toml`, `Dockerfile`, `.dockerignore` (new), `requirements.txt` |
| EXAMPLE | `samples/`, `policy_examples/`, `.github/workflows/sdc-readiness.yml.example` |
| LEGACY/SUSPECTED | none found — all modules are imported by the CLI, checker, UI, or tests |

## 5. Internal dependency review

- No circular imports found (checked by import smoke: `import cli` pulls the
  full stack cleanly; `import checker` from an installed wheel works).
- Layer direction is clean: `reporter`/`cli`/`app` (output) consume
  analysis engines; no analysis engine imports `cli`, `app`, or `ui`.
- No duplicate preprocess/parse/normalize: one preprocessor
  (`sdc_preprocess.py`), one Tcl resolver, one collection parser
  (`sdc_preprocess`/`design_context`), one finding-identity module.
- `coverage.py` (Phase 3 "constraint category coverage") and
  `design_coverage.py` (Phase 9 "structural coverage") are **distinct by
  design** — the former scores named constraint categories, the latter
  resolves design objects. Documented, not a duplicate.

## 6. Architecture findings

Each module has a clear responsibility and none of the 14 phases produced a
dangerous overlap. The readiness layer (Phase 11) consumes — never re-implements —
checker/scope/coverage/interactions/clock-relations evidence. The diff layer
(Phase 12) consumes readiness snapshots. Identity (Phase 13) is a shared service
for both.

## 7. Dead-code findings

- **Fixed:** duplicated `body = f"""..."""` block in `reporter.generate_check_report`.
- **Fixed:** unused `css = _CSS + _COV_CSS` in `generate_coverage_report`
  (exposed a latent bug — the coverage report's custom CSS was never rendered;
  now wired through `_page(extra_css=...)`).
- No unreferenced production functions found. `constraint_diff.py` remains the
  content-diff engine (still used by `diff`/`report diff`); readiness diff is
  the separate Phase 12 layer.

## 8. Duplication findings

All intentional or already consolidated (see §5). The two coverage modules and
two diff modules are architecturally distinct and documented as such.

## 9. Public / internal API assessment

**PUBLIC / SUPPORTED:** `checker.check_sdc`, `sdc_preprocess.preprocess_sdc`,
`design_context.parse_verilog`, `constraint_readiness` result shape,
`readiness_diff.build_snapshot` / `diff_snapshots` / `evaluate_gate`,
snapshot JSON schema, CLI commands/exit codes, JSON output keys.
**INTERNAL / MAY CHANGE:** everything else (`ui/*`, `_`-prefixed helpers,
report HTML internals).

## 10. Packaging audit

`pyproject.toml` uses standard `setuptools.build_meta`; `py-modules` now lists
**all** top-level modules including the Phase 8–13 modules, `ui/` as a package,
and `app.py`. `Dockerfile` now copies the repository (with a new
`.dockerignore` excluding dist/build/caches/tests/benchmarks/.git). Console
script `sdc-tools = cli:main` verified in the wheel's `entry_points.txt`.

## 11. Clean-install results

`pip install .` and `pip install -e .` both install cleanly. The **critical**
test — installing the built wheel into a fresh venv with no repo on the path —
passes **17/17** (`benchmarks/release_cleanroom.py`).

## 12. Wheel-install results

From the wheel in a fresh venv, verified: `python -m cli --help/--version`,
console script `sdc-tools --version`, `check` (SDC-only), `--json` purity,
`report check` HTML, `--save-baseline`, gate PASS (exit 0) and FAIL (exit 1),
CUSTOM policy gate, netlist-aware check, Python API
(`check_sdc` + `build_snapshot`), error journey, offline (no network imports).

## 13. sdist results

`sdist` builds alongside the wheel (`python -m build --wheel --sdist`). sdist
contains all source modules and package data; `.dockerignore` and clean
artifacts prevent shipping build caches.

## 14. Dependency classification

| Class | Packages |
|---|---|
| REQUIRED RUNTIME | none beyond stdlib (core is dependency-free) |
| OPTIONAL WEB | `streamlit>=1.35` (`[web]` extra) |
| OPTIONAL | `pyyaml>=6.0` (converter YAML; required for full feature set) |
| DEVELOPMENT | `pre-commit>=3.0` (`[dev]` extra) |
| TEST | pytest, (build) — dev-only |
| UNUSED | none found |

## 15. Offline-operation verification

Core validation, netlist-aware validation, readiness, snapshots, diff and CI
gates all run locally with no network access. The wheel contains no
requests/openai/anthropic/http-client imports (checked by
`release_cleanroom.py`). **No runtime AI/API/network dependency.**

## 16. CLI contract audit

All commands exercised (`check`, `generate`, `diff`, `corners`, `analyze`,
`rules`, `coverage`, `report`, `lint`, `convert`, `batch`, `web` dispatcher).
Help text, argument combinations, baseline/policy/netlist behavior all
consistent. `--gate CUSTOM` correctly requires `--gate-policy`; baseline-
dependent gates without `--baseline` exit 2 (not silent PASS).

## 17. Exit-code verification

| Code | Meaning | Verified |
|---|---|---|
| 0 | success / gate pass | clean SDC, gate PASS |
| 1 | analysis failure / gate fail | SDC with errors, new blocker under gate |
| 2 | invalid invocation/input | missing file, missing baseline, missing/bad policy, bad output path |
| 3 | engine failure | reserved; SDC-140 analysis-skip path cannot produce READY/PASS (Phase 11/13 invariant) |

## 18. JSON-output purity

`--json` stdout is pure JSON (verified by parse in audit + smoke + clean-room).
Human diagnostics go to stderr; the Phase 13 `--json --output` clobbering bug is
regression-tested.

## 19. Output-file safety

- **Fixed (audit):** `--output` to a nonexistent directory previously dumped a
  traceback with exit 1. Now `_write_output_file()`/`_write_report()` fail
  cleanly with exit 2. Applied to check JSON/text, report HTML, generate,
  convert.
- Empty-write clobbering guard (`_json_written`) retained.

## 20. Error-handling assessment

Malformed SDC, malformed netlist, missing files, wrong `--top`, invalid
baseline, invalid policy, and bad output paths all produce bounded,
understandable diagnostics — no tracebacks, no false PASS. Verified in the
clean-room error journey and CLI audit.

## 21. UI / backend parity

Backend findings, counts, readiness, coverage, trust, diff and gate info are
consumed directly by the UI (`app.py` reads `result.scope/coverage/interactions/
readiness` and `readiness_diff`). UI benchmark suites (35 tests) confirm
consistency; the UI does not re-derive semantics.

## 22. Report / JSON parity

CLI text, JSON, and HTML reports derive from the same `CheckResult` evidence.
Verified for a clean design: identical counts/severities/readiness in text,
JSON, and the HTML report (readiness section + "NOT an STA timing signoff"
disclosure present in HTML).

## 23. Documentation truth audit

Every executable quick-start command in the README was run against the repo
(and the majority against the installed wheel): `--help`, `check`, `generate`,
`--json`, `analyze clock-relations`, `rules list/show`, `coverage`, `report
check`, `diff`, `lint --check`, `convert yaml`, `batch check`, `corners list`.
All pass. No stale commands found.

## 24. Support-boundary consistency

`support_boundary.py` status vocabulary (VALIDATED / PARTIALLY_VALIDATED /
NETLIST_REQUIRED / TCL_EXECUTION_REQUIRED / UNSUPPORTED / NOT_VALIDATED) is
consistent across the CLI trust disclosure, HTML report, UI, and readiness
`ANALYSIS_TRUST` dimension. No contradictory claims found.

## 25. Trust-language audit

Searched the repo for overclaims ("timing clean", "signoff passed", "100%
timing", "fully correct SDC", "proves timing"). **None found.** Every PASS /
READY site carries the "not STA timing signoff" disclosure.

## 26. Test-suite quality assessment

691 tests across 27 files provide independent protection: golden, semantic,
reference, metamorphic, adversarial, security, performance, UI, state-isolation,
stress, and the Phase 12/13/14 CI suites. No brittle exact-message tests were
found in the audit scope; identity tests assert semantic fields. No tests pass
without exercising production code (verified by the adversarial/mutation
suites).

## 27. Benchmark organization assessment

`benchmarks/` is organized by phase with consistent `run_*` golden runners and
`test_*` adversarial/metamorphic/security/perf suites, plus fixtures and phase
reports. No stale generated artifacts; no hard-coded local paths; no duplicate
runners found.

## 28. Test-discovery assessment

`pytest` collects only genuine `test_*.py` files (benchmarks collection yields
the intended suites; standalone `run_*.py` scripts are not collected). No
accidental collection.

## 29. State-isolation results

A/B/A check (clean → perturbed → clean) produces identical findings
(verified in CLI audit). No hidden global-state leakage across checker,
readiness, snapshot, or diff.

## 30. Cross-platform / path results

No hard-coded `/` or drive paths in production code; the audit scripts use
`os.path`/`tempfile` (Windows-verified). `sdc-tools web` resolves `app.py`
relative to `cli.py` (works from any cwd — already fixed in an earlier phase).

## 31. Encoding results

UTF-8, UTF-8 BOM, CRLF, missing final newline, and non-ASCII comments all
validate correctly (verified). Reports/JSON written as UTF-8. The Windows
console requires `PYTHONIOENCODING=utf-8` (documented in README
troubleshooting).

## 32. Python-version verification

Verified on **Python 3.10** (Windows). 3.11/3.12 are claimed by
`requires-python >=3.10` but were **not executed** in this environment — stated
honestly in the manifest; not claimed as verified.

## 33. Security audit

Untrusted-input surfaces reviewed: SDC, Verilog, baseline JSON, policy
JSON/YAML, report content, output paths. YAML is loaded safely (Phase 13
alias-bomb cap), policies are inert data (no eval/exec), baselines are schema-
validated, no code execution from any input file. **HTML XSS fixed in this
audit** (see §34).

## 34. HTML-report safety

**RC-BLOCKER found and fixed:** issue messages and object names were
interpolated raw. `reporter.py` now escapes **every** user-controlled
interpolation via `esc()` (html.escape, quote=True): issue messages, codes,
rule names, stats, scope/ignored options, design metadata, coverage port
names/evidence, interaction findings, readiness dimensions/findings/actions,
readiness-diff findings/changed msgs/gate reasons, diff v1/v2 text, clock
names/ports/masters, mismatch text, rules, coverage items. Regression tests
added (`<script>` renders as `&lt;script&gt;`). The coverage-report custom CSS
was also wired in (was dead).

## 35. Resource-exhaustion sanity

Bounded behavior for large inputs is established by the existing stress suite
(21 cases) and perf suites (10k findings ≈ 43–75 ms diff; readiness aggregation
≈ 8 ms). No catastrophic scaling found in this audit.

## 36. Performance-regression assessment

No order-of-magnitude regressions introduced. Reporter escaping adds linear
string work only. Existing perf baselines (400 clocks ~1 s, 10k constraints ~1 s,
100k objects ~10 s, 10k diff findings tens of ms) remain representative.

## 37. Versioning audit

Single source of truth: `APP_VERSION = "1.3.0"` in `rules_registry.py`; CLI
(`--version`), JSON output, HTML reports, and snapshot `tool_version` all read
it. Verified identical across CLI/JSON/snapshot.

## 38. Release-artifact metadata

Wheel: `sdc_tools-1.3.0-py3-none-any.whl`. Contains all 22 modules + `ui/` +
`app.py`; console entry point present; `[web]` extra declares streamlit.
Metadata (name/version/README/license) resolves from `pyproject.toml`.

## 39. Clean-room user journey

`benchmarks/release_cleanroom.py` simulates a fresh engineer: build wheel →
fresh venv → install **the wheel** → run from a directory outside the repo →
`--help`, entry point, check, JSON, HTML report, baseline save, gate
pass/fail, CUSTOM policy, netlist-aware check, Python API, error journey,
offline check. **17/17 PASS.**

## 40. Clean-room error journey

Missing file (exit 2), invalid SDC (no traceback), missing netlist (exit 2),
malformed netlist (no traceback), invalid baseline (exit 2), wrong `--top`
(clear message), bad output path (exit 2, no traceback), malformed policy
(exit 2). All messages are actionable.

## 41. Realistic engineering workflow

Validated end-to-end on the clean corpus: SDC (+ netlist) → validation →
coverage/trust → readiness → snapshot → revision → readiness diff → CI gate →
JSON/HTML evidence. Evidence stays internally consistent across layers
(verified by the readiness/readiness-diff golden and CI-gate suites).

## 42. Release blockers found

| # | Severity | Finding | Status |
|---|---|---|---|
| B1 | **RC-BLOCKER** | Wheel missing Phase 8–13 modules + `ui/` + `app.py` | **FIXED** (pyproject.toml) + verified in wheel & clean-room |
| B2 | **RC-BLOCKER** | HTML report stored-XSS (raw `<script>` from SDC) | **FIXED** (reporter `esc()`) + regression tests |
| B3 | MAJOR | Dockerfile stale file list | **FIXED** (whole-repo COPY + `.dockerignore`) |
| B4 | MAJOR | Bad `--output` path → traceback + exit 1 | **FIXED** (exit 2, clean diagnostic) |
| B5 | MINOR | Coverage report custom CSS never rendered | **FIXED** (wired `_COV_CSS`) |

## 43. Targeted fixes applied

All fixes are minimal and evidence-backed (see §42); each has a regression
test or verification step. No speculative refactors were performed.

## 44. Independent reviewer findings

Independent review (deepseek-flash) raised 7 findings; all addressed:

1. `cov_rows`/`int_rows` unescaped (cosmetic) → **escaped.**
2. `_COV_CSS` became dead code → **wired into the report** (fixes latent bug).
3. Clean-room exit-code assertion too weak → **tightened to `== 2`.**
4. `generate`/`convert` bare `open()` → **guarded writes (exit 2).**
5. `sdc-tools web` untested from wheel → **verified `app.py`/`ui/`/entry point
   in wheel + `[web]` extra; noted as untested-launch limitation.**
6. Dockerfile ships too much → **`.dockerignore` added.**
7. `_p14_*` probe scripts read as throwaway → **renamed `release_*`.**
   Re-review: all resolved; full regression green after fixes.

## 45. Release smoke-suite results

`benchmarks/test_release_smoke.py` — **10/10 PASS** (imports, help, version,
check, JSON purity, HTML report, baseline+gate pass/fail, netlist-aware,
engine-failure-never-passes, HTML escaping). Fast (~3 s), intended for every
release.

## 46. Full regression results

| Suite | Result |
|---|---|
| pytest (`tests/`) | **691/691 PASS** (689 + 2 new reporter tests) |
| Golden runners (9) | **9/9 PASS** (22/22 · 9/9 · 8/8 · 12/12 · 10/10 · 20/20 · 15/15 · 22/22 · 49/49) |
| Benchmark suites (28) | **28/28 PASS** |
| Release clean-room (wheel) | **17/17 PASS** |
| Release CLI audit | **16/16 PASS** |
| Release smoke | **10/10 PASS** |

## 47. Files modified

Production: `pyproject.toml`, `Dockerfile`, `.dockerignore` (new), `reporter.py`,
`cli.py`. Tests: `tests/test_reporter.py` (+2). Benchmarks: `release_cleanroom.py`,
`release_cli_audit.py`, `release_packaging_probe.py` (renamed from `_p14_*`),
`test_release_smoke.py` (new), `RELEASE_MANIFEST.md` (new), plus this report.
Docs/CI: none changed beyond packaging.

## 48. Known limitations

- Python 3.11/3.12 not executed (only 3.10 available in this environment).
- `sdc-tools web` not launched from an installed wheel in this audit (Streamlit
  startup verified via repo UI suites; packaging verified statically).
- SDC/Verilog semantics bounded by the documented support boundary; constructs
  outside it are reported unsupported, never silently assumed.
- Numeric "score" in the legacy `coverage.py` report is a category-coverage
  heuristic, not readiness.

## 49. Release manifest

See `benchmarks/RELEASE_MANIFEST.md` — machine/human-readable checklist of
every verification with evidence.

## 50. Trust statement

- **Does the production SDC Validator use an LLM or AI?** **NO.** Runtime is
  deterministic Python. AI/subagents were used only to develop, audit, and
  review the software.
- **Does normal validation require Internet access?** **NO.** All analysis is
  local and offline.
- **Does READY mean STA timing signoff passed?** **NO.**
- **Does CI PASS mean timing closure is achieved?** **NO.**
- **What does READY mean?** The constraint set satisfies the validator's
  supported, evidence-backed readiness criteria for the stated analysis mode
  (SDC-only or design-aware). It is a constraint-quality verdict.
- **What does CI PASS mean?** Under the selected gate policy and stated
  analysis context, no disallowed constraint-readiness regression was detected
  against the baseline.
- **What does supplying a Verilog/netlist improve?** It enables deterministic
  structural design-context evidence: object resolution (SDC-055..059),
  structural coverage (SDC-064..066), design fingerprinting, and design-aware
  readiness. It does **not** create a timing engine.
- **What remains outside the validator's authority?** Slack, setup/hold
  signoff, timing-path correctness, physical/library-based behavior, crosstalk,
  OCV signoff, and anything requiring a full STA tool.

## 51. Final release decision

### **RC_READY_WITH_KNOWN_LIMITATIONS**

Evidence: both RC-blockers fixed and re-verified from a freshly built wheel in a
clean environment; full regression green (691 pytest, 9 golden, 28 suites,
17/17 clean-room, 16/16 CLI audit, 10/10 smoke); CLI/JSON/report contract
stable; security fixes regression-tested; documentation commands verified;
trust boundaries honest. Remaining limitations are environmental (Python 3.11+,
wheel-launched web UI) — none block release.

## 52. Next-step recommendation

**A. Release/tag/package the current validator** is the evidence-backed next
step. Then, optionally: **C. external beta with real engineers/designs** to
validate readiness/diff/CI workflows on production constraints. Do **not** add
a feature phase next; the audit found no high-value semantic gap. A future
"explain layer" (F) is research-only and must stay strictly separated from the
deterministic runtime.

---

*Phase 14 complete. The validator is installable, trustworthy within its
documented boundaries, and ready to hand to downstream engineering.*
