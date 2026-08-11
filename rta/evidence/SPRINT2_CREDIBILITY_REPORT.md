# Ṛta — Sprint 2 Report: Repository Credibility & Product Integrity

> Sprint 2 implemented Epic 1 (P0 credibility) from `docs/company/STARTUP_BACKLOG.md`.
> Scope: make every public claim verifiable. No backend semantics changed, no
> frontend redesign, no new analysis features.
> Date: 2026-08-07 · Version: v1.3.0 · Status: `RC_READY_WITH_KNOWN_LIMITATIONS`

---

## 1. Executive summary

Ṛta's public evidence numbers were duplicated as hard-coded values across
README, the website, product specs and CONTRIBUTING — several had drifted
(710 vs the real 780+; 28 suites vs 42; 311 tests vs 27 files). This sprint
introduced a **single source of truth**:

- **`RELEASE_EVIDENCE.json`** — the canonical evidence manifest, regenerated
  from live computation by `benchmarks/build_evidence.py`.
- **`evidence.py`** — a canonical module that computes code-derivable facts
  (version, rule count, golden runners, benchmark-suite count, test-file count,
  phase count, brand facts) and compares them against the manifest.
- **`tests/test_evidence.py`** (20 checks) + a new **CI `credibility` job** —
  any drift between live truth, the manifest and the public surfaces fails the
  pipeline. The guard already caught two real bugs during this sprint itself.
- **`LICENSE`** (MIT, per `docs/rta/OPEN_CORE_STRATEGY.md` §6) ships in the
  wheel via PEP 639 (`License-Expression: MIT`).

The deterministic backend was **not modified**. 800/800 pytest tests pass,
42/42 benchmark suites, 9/9 golden runners, smoke 10/10, clean-room 17/17,
CLI audit 16/16, and a fresh wheel install works with the `rta` / `sdc-tools`
entry points and the `evidence` module.

## 2. Files changed (this sprint)

**New:**
- `evidence.py` — canonical evidence record (single source of truth).
- `benchmarks/build_evidence.py` — manifest generator / `--check` verifier.
- `RELEASE_EVIDENCE.json` — generated evidence manifest.
- `LICENSE` — MIT license (open-core Community license).
- `tests/test_evidence.py` — 20 evidence-consistency tests.
- `benchmarks/SPRINT2_CREDIBILITY_REPORT.md` — this report.

**Edited:**
- `README.md` — benchmarks paragraph + commands quote the manifest; LICENSE link.
- `site/index.html`, `site/benchmarks.html`, `site/release.html`,
  `site/trust.html` — pytest 710/710 → 800/800; benchmark suites 28/28 → 42/42;
  canonical tagline anchored in the home `<title>`; workspace tooltips prefer
  `rta web`.
- `docs/product/HIGH_FIDELITY_PRODUCT_SPEC.md`,
  `docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md`,
  `docs/product/PRODUCT_WEBSITE_DESIGN_DNA.md` — stale 691/28 evidence numbers
  reconciled (800/9/42/17/16/10; 27 files unchanged).
- `docs/rta/BENCHMARK_EVIDENCE_MAP.md` — 710→800, 28/28→42/42, canonical-source
  note pointing at `RELEASE_EVIDENCE.json`.
- `CONTRIBUTING.md` — test table regenerated from the manifest (27 files, real
  per-file counts), rule count 40+ → 111.
- `pyproject.toml` — `evidence` module in `py-modules`; PEP 639
  `license = "MIT"`; `license-files`; build-system `setuptools>=77`.
- `.github/workflows/ci.yml` — new `credibility` job; `evidence.py` added to
  the lint job.
- `.gitignore` — `benchmarks_*.zip`; removed stray `benchmarks_0.zip` /
  `benchmarks_1.zip` (backlog acceptance criteria 1–2).
- `benchmarks/README.md` — Phase 2 diagnostic table prefixed with a historical
  note (backlog acceptance criterion 3).
- `CHANGELOG.md` — Sprint 2 entry.

## 3. Credibility improvements

1. **One source of truth.** Test count, rule count, golden runners, benchmark
   suites, version, release status, phase count and license now live in
   `RELEASE_EVIDENCE.json`, derived from code where possible.
2. **Drift fails CI.** `benchmarks/build_evidence.py --check` runs a full
   pytest collection and compares the manifest to live truth; the new
   `credibility` CI job runs it plus the evidence/brand tests.
3. **Surfaces are guarded.** Tests assert README, the four website pages,
   CONTRIBUTING and the product docs quote the manifest numbers and contain no
   stale phrases (710/710, 691, 311 tests).
4. **License is real.** MIT `LICENSE` file, SPDX `License-Expression: MIT` in
   the wheel metadata, file shipped at `dist-info/licenses/LICENSE`.
5. **Version consistency.** CLI, rules registry, pyproject and manifest all
   agree (v1.3.0); CI derives the version from the manifest instead of
   hard-coding it.
6. **Canonical tagline anchored.** "Constraint Intelligence for Digital
   Design" is now static in the home page `<title>` and asserted across
   README / site / footer source.
7. **Honest historical records preserved.** Phase benchmark reports and the
   dated Phase 2 diagnostic table were kept and marked historical.

## 4. Evidence consistency verification

| Number | Live truth | Manifest | README/site/CONTRIBUTING |
|---|---|---|---|
| pytest tests | 800 | 800 | 800 |
| test files | 27 | 27 | 27 |
| rules | 111 | 111 | 111 |
| golden runners | 9 | 9 | 9 |
| benchmark suites | 42 | 42 | 42 |
| phase reports | 15 | 15 | 15 |
| version | 1.3.0 | 1.3.0 | 1.3.0 |
| release status | RC_READY_WITH_KNOWN_LIMITATIONS | same | site/release.html |
| clean-room | 17/17 | — | 17/17 (docs) |
| CLI audit | 16/16 | — | 16/16 (docs) |
| smoke | 10/10 | — | 10/10 |

Verified by `python benchmarks/build_evidence.py --check` (exit 0) and
`tests/test_evidence.py`.

## 5. CI improvements

New `credibility` job (ubuntu, Python 3.11):
- `python benchmarks/build_evidence.py --check` — full-collection drift guard.
- `pytest tests/test_evidence.py tests/test_branding.py` — 90 checks.
- License presence (`LICENSE`, MIT header) and CLI version derived from the
  manifest.

The `lint` job now also `py_compile`s and imports `evidence.py`.

## 6. Independent review findings

Reviewer findings (all addressed):
1. CI hard-coded `1.3.0` — **fixed**: version is derived from the manifest.
2. Reconciled docs (`docs/product/*`, `BENCHMARK_EVIDENCE_MAP.md`) were not
   test-protected — **fixed**: added to the stale-phrase guard plus a new
   count-quoting test.
3. No CHANGELOG entry — **fixed**.
4. `evidence.verify()` could raise (missing golden runner) instead of returning
   a mismatch list — **fixed**: caught and reported as a mismatch.
5. Double collection in CI — **documented** as intentional (guards pre- and
   post-pytest entry points).
6. Minor: `PHASE_COUNT` comment, mixed line endings — comment corrected;
   CONTRIBUTING verified LF-only (`\r` count = 0).

## 7. Fixes applied (beyond review)

The drift guard caught two real bugs during implementation:
- **Greedy regex** in the per-file collection parser inflated `test_files`
  (144 vs the true 27) — fixed to `test_[^:]+\.py::`.
- **Import-order bug**: `test_evidence.py` loaded the manifest at module level,
  so a missing manifest silently errored that file out of collection — fixed by
  moving the load into a fixture; collection errors now fail loudly.

Also: pytest collection now rejects any collection errors (returncode ≠ 0),
and the PEP 639 license migration required removing the redundant
`License :: OSI Approved :: MIT License` classifier (setuptools error).

## 8. Regression results

| Suite | Result |
|---|---|
| pytest (tests/) | **800/800 passed** (710 baseline + 70 brand + 20 evidence) |
| Benchmark suites | **42/42** |
| Golden runners | **9/9** |
| Release smoke | **10/10** |
| Clean-room (`release_cleanroom.py`) | **17/17** |
| CLI audit (`release_cli_audit.py`) | **16/16** |
| Website / JS integrity | all pages Ṛta-branded, no stale numbers, 6/6 JS valid |
| Wheel build | `evidence.py` + `LICENSE` + both entry points + `License-Expression: MIT` |
| Clean install | `Ṛta v1.3.0` CLI + `check` runs; `evidence` imports (111 rules) |

## 9. Remaining known limitations

- `RELEASE_EVIDENCE.json` is a repository artifact (not shipped in the wheel);
  consumers get it from the repo/CI.
- The collection drift guard adds ~10–30 s to a full pytest run and to the CI
  credibility job (deliberate cost of verification).
- `docs/product/PHASE17_*.md` retain their dated 710/710 baseline lines — they
  are historical audit documents and were intentionally preserved.
- The 42-suite count includes the UI/state/motion/smoke suites
  (`test_ui_app`, `test_workspace_ux`, `test_ui_state_isolation`,
  `test_motion`, `test_release_smoke`); historical reports used a narrower
  definition, which is why older numbers differ.

## 10. Recommendation for Sprint 3

Repository credibility is established. Recommended next sprint (in priority
order, per `docs/company/STARTUP_BACKLOG.md`): **"Ṛta Product Experience —
From-Scratch Application UI & Motion System"** (the frontend rebuild promised
at the end of the Ṛta Foundation phase). The evidence manifest and CI
credibility job will keep every claim verifiable while the product experience
is rebuilt.
