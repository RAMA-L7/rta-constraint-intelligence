# Ṛta — Startup Backlog

> **Source:** Repository audit (2026-08-07). **Status:** living document.
> Epics are ordered by leverage: fix a credibility problem, prevent a loss, or unblock the next phase.
> Stories within each epic are ordered by dependency (first story is unblocked).

---

## Epic 1: Credibility Repair

> **Objective:** Make every external-facing claim verifiable and consistent. The product's core promise is "no fabricated numbers." Every stale number on the website or README undermines that promise.
> **Priority:** P0 · **Suggested sprint:** Sprint 1

### Story 1.1: Reconcile evidence numbers across every surface

| | |
|---|---|
| **As a** | Technical evaluator reviewing Ṛta |
| **I want** | every surface to show the same, current, verified numbers |
| **So that** | I can trust the product's evidence claims |
| **Priority** | P0 |
| **Effort** | 0.5 days |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `README.md` shows 780 (not 710). (2) `site/index.html` stats band shows 780/780. (3) `site/benchmarks.html` shows 780/780. (4) `site/release.html` shows 780/780. (5) `site/trust.html` shows 780/780. (6) `docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md` is updated to 780. (7) `docs/product/HIGH_FIDELITY_PRODUCT_SPEC.md` is updated to 780. (8) A `tests/test_branding.py` check (or new test) fails if the website/README states a test count ≠ the collected count from `pytest tests/ --collect-only`. |
| **Risks** | None — pure documentation fix. |

### Story 1.2: Add MIT LICENSE file

| | |
|---|---|
| **As a** | Contributor or evaluator |
| **I want** | a LICENSE file that matches the MIT claim in pyproject.toml and README |
| **So that** | the legal status is unambiguous |
| **Priority** | P0 |
| **Effort** | 0.25 days |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `LICENSE` file exists at repo root containing the MIT license text. (2) pyproject.toml `license` field matches. (3) README references it. (4) CONTRIBUTING.md references it. |
| **Risks** | Legal review recommended if this is the first public-facing MIT claim. |

### Story 1.3: Commit the Ṛta Foundation phase

| | |
|---|---|
| **As a** | Team member |
| **I want** | all Ṛta identity work committed to version control |
| **So that** | the work is recoverable and the branch is not behind origin |
| **Priority** | P0 |
| **Effort** | 0.5 days |
| **Dependencies** | None (should be done before 1.4 to avoid merge conflicts) |
| **Acceptance criteria** | (1) `git status` shows clean working tree. (2) `git log` shows the Ṛta Foundation phase as a committed change set. (3) `git status` shows branch is not behind origin. (4) The commit includes: docs/rta/*, webui/*, site/*, tests/test_branding.py, RTA_FOUNDATION_REPORT.md, rta.cmd, brand-migrated files. |
| **Risks** | Large commit — consider splitting into logical commits (brand migration, docs, workspace, website). |

### Story 1.4: Unify CLI brand on user surfaces

| | |
|---|---|
| **As a** | New user reading the website |
| **I want** | the CLI examples to use `rta check` consistently, with `sdc-tools` noted as the alias |
| **So that** | the product identity is clear |
| **Priority** | P0 |
| **Effort** | 1 day |
| **Dependencies** | Story 1.3 (committed state) |
| **Acceptance criteria** | (1) `site/index.html` hero terminal title says `rta check`. (2) All CTA tooltips say `rta web` (not `sdc-tools web`). (3) `site.js` hero animation uses `rta check` (already true). (4) `docs/features/README-01-checker.md` uses `rta check` as primary. (5) `docs/features/README-07-custom-rules.md` uses `rta check` as primary. (6) Grep for `sdc-tools check` in site/ and docs/features/ returns zero hits (excluding historical Class D evidence and the alias documentation). |
| **Risks** | Must preserve the documented `sdc-tools` alias somewhere (CONTRIBUTING.md, README alias section). |

### Story 1.5: Make CI protect the evidence

| | |
|---|---|
| **As a** | Release owner |
| **I want** | CI to run golden runners and release smoke on every PR that touches the engine |
| **So that** | evidence claims cannot regress without CI noticing |
| **Priority** | P0 |
| **Effort** | 2 days |
| **Dependencies** | Story 1.3 (clean commit state) |
| **Acceptance criteria** | (1) `.github/workflows/ci.yml` includes a job that runs `run_golden.py`, `run_golden_semantic.py`, `test_release_smoke.py`, and `release_cli_audit.py` on at least one OS (ubuntu-latest, Python 3.10). (2) The job passes on the PR branch. (3) A comment in the workflow explains what each runner proves. (4) The job is gated (required check) for PRs touching `*.py` in the root directory. |
| **Risks** | CI runtime increases — benchmark suites may take longer than pytest alone. Consider a separate job or a conditional trigger. |

---

## Epic 2: Documentation Integrity

> **Objective:** Make every documentation surface accurate, current, and internally consistent.
> **Priority:** P0 · **Suggested sprint:** Sprint 1–2

### Story 2.1: Refresh docs/features/ to current truth

| | |
|---|---|
| **As a** | Contributor reading feature docs |
| **I want** | accurate rule counts, correct CLI identity, and correct surface descriptions |
| **So that** | the docs match the implementation |
| **Priority** | P0 |
| **Effort** | 1 day |
| **Dependencies** | Story 1.4 (CLI brand unified) |
| **Acceptance criteria** | (1) `README-01-checker.md` says "111 rules" (not "40+"). (2) `README-01-checker.md` uses `rta check` as primary CLI. (3) `README-10-web-ui.md` describes the vanilla-JS workspace (not Streamlit as current). (4) All10 feature docs use `rta check` as primary CLI. (5) CONTRIBUTING.md test table updated to reflect current file count and test count (780 across ~28+ files). |
| **Risks** | Feature docs have substantial content — audit all10 files, not just the two identified. |

### Story 2.2: Canonicalize the hero line

| | |
|---|---|
| **As a** | Marketing evaluator or technical lead |
| **I want** | one consistent product description across every surface |
| **So that** | the product identity is coherent |
| **Priority** | P0 |
| **Effort** | 0.5 days |
| **Dependencies** | Story 1.4 |
| **Acceptance criteria** | (1) One canonical string is chosen and documented in `docs/rta/BRAND_FOUNDATION.md` §10. (2) The canonical string appears in: README tagline, site `<title>`, site footer, workspace sub-brand, workspace `<title>`. (3) Any deviation in other surfaces is corrected. (4) The `tests/test_branding.py` check (or new test) verifies the canonical string on key surfaces. |
| **Risks** | The three competing strings ("Constraint Intelligence for Digital Design," "Constraint Quality Intelligence & Pre-STA Validation," "Bring order to timing intent before STA") each have a home. Choose one for external; keep others as internal descriptors. |

### Story 2.3: Document baseline snapshot and policy schemas

| | |
|---|---|
| **As a** | CI adopter integrating Ṛta into a pipeline |
| **I want** | to understand the snapshot JSON schema and policy file format without reading source code |
| **So that** | I can generate custom baselines and policies |
| **Priority** | P1 |
| **Effort** | 1.5 days |
| **Dependencies** | Story 2.1 (docs freshness) |
| **Acceptance criteria** | (1) `docs/rta/SNAPSHOT_SCHEMA.md` documents schema v2 fields and v1 compatibility. (2) `docs/rta/POLICY_SCHEMA.md` documents the CUSTOM policy format (fail_on, allow, thresholds). (3) Both include a minimal example. (4) Both are linked from the README CLI reference and the workspace CI page. |
| **Risks** | Schemas may evolve — mark documents as versioned. |

### Story 2.4: Add docs index / landing page

| | |
|---|---|
| **As a** | New user navigating the documentation |
| **I want** | a single entry point that maps the docs hierarchy |
| **So that** | I can find what I need without guessing |
| **Priority** | P1 |
| **Effort** | 1 day |
| **Dependencies** | Story 2.1 |
| **Acceptance criteria** | (1) `docs/README.md` (or `docs/INDEX.md`) exists and maps: Getting Started / Concepts / Workflows / Reference to existing content. (2) `site/docs.html` links to this index. (3) The index is accurate (every linked document exists and is current). |
| **Risks** | Docs content is thin — the index may expose gaps. Accept this as intentional signal. |

---

## Epic 3: Evidence Infrastructure

> **Objective:** Ensure the evidence that the product sells is reproducible, traceable, and protected.
> **Priority:** P0–P1 · **Suggested sprint:** Sprint 1–2

### Story 3.1: Automate evidence-number verification in CI

| | |
|---|---|
| **As a** | Release owner |
| **I want** | CI to fail if the README or website states a test count that does not match the collected count |
| **So that** | stale evidence numbers are caught before merge |
| **Priority** | P0 |
| **Effort** | 1 day |
| **Dependencies** | Story 1.5 (CI evidence job) |
| **Acceptance criteria** | (1) A CI step runs `pytest tests/ --collect-only -q` and extracts the count. (2) The count is compared against the canonical value in `RELEASE_EVIDENCE.json` (new file) or a test assertion. (3) If the count diverges, CI fails. (4) `RELEASE_EVIDENCE.json` is created with the current verified counts (780 tests, 111 rules, 9 golden, 28 suites, etc.). |
| **Risks** | New CI artifact to maintain — but it is the single source of truth. |

### Story 3.2: Verify evidence numbers for all 111 rules

| | |
|---|---|
| **As a** | Evaluator counting rules |
| **I want** | the website to say "111 rules" (not "100+" or "40+"), and that number to be accurate |
| **So that** | I can trust the rule-count claim |
| **Priority** | P0 |
| **Effort** | 0.25 days |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `site/index.html` says "111 rules" (not "100+"). (2) `README.md` rule count is accurate. (3) All feature docs are accurate. (4) A test or CI step verifies the rule count matches `len(get_all_rules())`. |
| **Risks** | None. |

### Story 3.3: Document the benchmark-evidence traceability model

| | |
|---|---|
| **As a** | Release owner |
| **I want** | a documented pipeline from runner output to website numbers |
| **So that** | evidence numbers cannot drift |
| **Priority** | P1 |
| **Effort** | 1 day |
| **Dependencies** | Story 3.1 |
| **Acceptance criteria** | (1) `docs/rta/EVIDENCE_PIPELINE.md` documents: runner → manifest → RELEASE_EVIDENCE.json → website/README. (2) The pipeline is implementable (not just design). (3) The document links to the relevant runners. |
| **Risks** | Full automation is P2; this story documents the manual process. |

---

## Epic 4: Developer Experience Foundations

> **Objective:** Make contributing to Ṛta straightforward for a new engineer.
> **Priority:** P1 · **Suggested sprint:** Sprint 2

### Story 4.1: Update CONTRIBUTING.md for current state

| | |
|---|---|
| **As a** | New contributor |
| **I want** | accurate setup, test, and contribution instructions |
| **So that** | I can contribute without guessing |
| **Priority** | P1 |
| **Effort** | 1 day |
| **Dependencies** | Story 2.1 (docs freshness) |
| **Acceptance criteria** | (1) Test count and file count are accurate. (2) The "Adding a New Feature" section mentions the `py-modules` packaging step. (3) CLI examples use `rta` as primary. (4) The PR checklist matches `ENGINEERING_CHECKLIST.md`. (5) The code-style section mentions the brand conventions (no "AI-powered", no marketing language in code comments). |
| **Risks** | None. |

### Story 4.2: Add SECURITY.md

| | |
|---|---|
| **As a** | Security researcher or evaluator |
| **I want** | a clear process for reporting security issues |
| **So that** | I know how to report a vulnerability responsibly |
| **Priority** | P1 |
| **Effort** | 0.25 days |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `SECURITY.md` exists at repo root. (2) It describes the reporting process (private report, no public exploit details). (3) It states the response SLA (24 hours acknowledgment). (4) It is linked from the website footer and README. |
| **Risks** | None. |

### Story 4.3: Update CI lint coverage

| | |
|---|---|
| **As a** | Contributor |
| **I want** | CI to verify all new modules can be imported |
| **So that** | broken imports are caught before merge |
| **Priority** | P1 |
| **Effort** | 0.5 days |
| **Dependencies** | Story 1.5 |
| **Acceptance criteria** | (1) `ci.yml` lint job py_compiles or imports every module in `py-modules`. (2) A comment explains the list is derived from `py-modules`. (3) If a new module is added, the lint job catches the omission. |
| **Risks** | May require a dynamic approach (read py-modules from pyproject.toml). |

---

## Epic 5: Repository Hygiene

> **Objective:** Clean up the repository root and organization so the first impression matches the product quality.
> **Priority:** P1 · **Suggested sprint:** Sprint 2

### Story 5.1: Remove stale artifacts from repo root

| | |
|---|---|
| **As a** | Contributor cloning the repository |
| **I want** | a clean repo root without stray zip files or build directories |
| **So that** | the first impression matches the product quality |
| **Priority** | P1 |
| **Effort** | 0.25 days |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `benchmarks_0.zip` and `benchmarks_1.zip` are deleted. (2) `build/` and `dist/` are added to `.gitignore` if not already. (3) `benchmarks/README.md` Phase 2 diagnostic table is prefixed with a note: "Historical diagnostic (Phase 2, 2026-08-04). Current evidence is in `RTA_FOUNDATION_REPORT.md`." |
| **Risks** | None. These are pre-existing artifacts, not from current work. |

### Story 5.2: Add benchmarks/README.md navigation note

| | |
|---|---|
| **As a** | Contributor reading benchmark documentation |
| **I want** | to understand which numbers in benchmarks/README.md are current vs historical |
| **So that** | I do not confuse Phase 2 diagnostic tables with current evidence |
| **Priority** | P1 |
| **Effort** | 0.5 days |
| **Dependencies** | Story 5.1 |
| **Acceptance criteria** | (1) The Phase 2 diagnostic section is clearly marked as historical. (2) The current evidence section links to `RTA_FOUNDATION_REPORT.md` and `BENCHMARK_EVIDENCE_MAP.md`. (3) The layout guides the reader: current evidence first, historical diagnostic second. |
| **Risks** | None. |

### Story 5.3: De-duplicate design tokens between site/ and webui/

| | |
|---|---|
| **As a** | Frontend developer modifying the visual identity |
| **I want** | a single source of truth for CSS custom properties |
| **So that** | changes to the design system propagate to both surfaces |
| **Priority** | P1 |
| **Effort** | 1.5 days |
| **Dependencies** | Story 5.1 (clean state) |
| **Acceptance criteria** | (1) A shared `tokens.css` (or equivalent) contains all CSS custom properties. (2) `site/assets/css/site.css` imports/references the shared tokens. (3) `webui/assets/css/app.css` imports/references the shared tokens. (4) Both surfaces render identically after the change. (5) A test or documentation notes that the shared tokens are the single source of truth. |
| **Risks** | CSS variable names may differ between surfaces — requires careful reconciliation. |

---

## Epic 6: Product Strategy Foundations

> **Objective:** Document the strategic decisions that will guide the next two years.
> **Priority:** P1–P2 · **Suggested sprint:** Sprint 2–3

### Story 6.1: Write the competitive landscape memo

| | |
|---|---|
| **As a** | Founder or advisor |
| **I want** | a clear analysis of where Ṛta sits relative to adjacent tools |
| **So that** | positioning decisions are evidence-based |
| **Priority** | P1 |
| **Effort** | 2 days |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `docs/company/COMPETITIVE_LANDSCAPE.md` exists. (2) It covers: PrimeTime `check_timing`, Tempus, SpyGlass constraints, OpenSTA, and any open-source SDC linters. (3) For each, it describes: what it does, how it compares, where Ṛta is additive. (4) It includes a positioning map. (5) It does not make disparaging claims about competitors. |
| **Risks** | Requires domain knowledge of commercial EDA tools — may need input from STA engineers. |

### Story 6.2: Codify release/versioning/deprecation policy

| | |
|---|---|
| **As a** | Release owner |
| **I want** | a documented versioning policy so releases are predictable |
| **So that** | the project can grow without versioning chaos |
| **Priority** | P1 |
| **Effort** | 0.5 days |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `docs/company/RELEASE_POLICY.md` documents: semantic versioning rules, `sdc-tools` alias deprecation timeline, release checklist reference, pre-release naming. (2) It is linked from CONTRIBUTING.md and the website release page. |
| **Risks** | The deprecation timeline for `sdc-tools` requires a deliberate decision (when to warn, when to remove). |

### Story 6.3: Track open strategy decisions

| | |
|---|---|
| **As a** | Founder |
| **I want** | the open strategic decisions documented so they are not forgotten |
| **So that** | the company makes deliberate choices, not accidental ones |
| **Priority** | P2 |
| **Effort** | 1 day |
| **Dependencies** | None |
| **Acceptance criteria** | (1) `docs/company/STRATEGY_DECISIONS.md` tracks: pricing hypothesis (current: not decided), workspace-as-product end-state (current: TBD), package-namespace migration timing (current: next packaging phase). (2) Each decision has a status (open / decided / deferred). (3) Decisions are reviewed quarterly. |
| **Risks** | Strategy decisions may be sensitive — consider access controls if the repo is public. |

---

## Epic 7: Workspace Readiness

> **Objective:** Ensure the workspace is ready for external beta use.
> **Priority:** P1 · **Suggested sprint:** Sprint 2–3

### Story 7.1: Verify workspace launches from clean install

| | |
|---|---|
| **As a** | New user running `pip install sdc-tools[web] && rta web` |
| **I want** | the workspace to open in my browser with no errors |
| **So that** | the first-run experience works |
| **Priority** | P1 |
| **Effort** | 1 day |
| **Dependencies** | Story 1.3 (clean commit state) |
| **Acceptance criteria** | (1) The workspace opens at `http://127.0.0.1:8501` with no console errors. (2) The sample SDC loads and analyzes correctly. (3) All workspace pages are reachable via navigation. (4) The `Release smoke` suite passes for the workspace. |
| **Risks** | Port 8501 may conflict with Streamlit's default — the workspace should gracefully handle this (documented behavior). |

### Story 7.2: Fix hardcoded localhost in website CTAs

| | |
|---|---|
| **As a** | Technical evaluator reading the website |
| **I want** | the "Launch" CTA to explain how to start the workspace, not hardcode a port |
| **So that** | I understand the local-first model |
| **Priority** | P1 |
| **Effort** | 0.5 days |
| **Dependencies** | Story 1.4 (CLI brand unified) |
| **Acceptance criteria** | (1) The "Launch Ṛta" CTA on the website links to an anchor explaining how to start the workspace locally (`rta web` or `pip install sdc-tools[web] && rta web`). (2) The tooltip says "Run `rta web` locally" (not a hardcoded port). (3) The workspace topbar link points to the same documentation. |
| **Risks** | None. |

### Story 7.3: Add workspace launch smoke test

| | |
|---|---|
| **As a** | Release owner |
| **I want** | a CI test that verifies the workspace launches without errors |
| **So that** | workspace regressions are caught before merge |
| **Priority** | P1 |
| **Effort** | 1.5 days |
| **Dependencies** | Story 1.5 (CI evidence job) |
| **Acceptance criteria** | (1) A CI test starts `api_server.py` in a subprocess. (2) It hits `GET /api/health` and verifies the response contains the correct version. (3) It hits `GET /api/design` and verifies the response is valid JSON with expected keys. (4) The test passes on the PR branch. (5) The test is added to the CI evidence job. |
| **Risks** | Port conflicts in CI — use a random port or a dedicated test fixture. |

---

## Sprint Summary

| Sprint | Epics | Stories | Estimated effort |
|---|---|---|---|
| **Sprint 1** (credibility) | Epic 1 (1.1–1.5), Epic 3 (3.2) | 6 stories | ~6 days |
| **Sprint 2** (integrity) | Epic 2 (2.1–2.2), Epic 3 (3.1), Epic 4 (4.1–4.2), Epic 5 (5.1–5.2) | 6 stories | ~5 days |
| **Sprint 3** (product) | Epic 2 (2.3–2.4), Epic 4 (4.3), Epic 5 (5.3), Epic 6 (6.1–6.2), Epic 7 (7.1–7.3) | 8 stories | ~10 days |
| **Sprint 4** (long game) | Epic 6 (6.3) + remaining P2 items | 1+ stories | ~1 day + ongoing |

**Critical path:** Story 1.3 (commit the phase) should be done first; it unblocks 1.4, 1.5, and most Sprint 2 work.

**The single highest-leverage story is 1.3** — committing the uncommitted Ṛta Foundation work. Without it, the credibility repair stories (1.1, 1.4, 1.5) cannot be reliably merged.

---

*This backlog is a living document. Update it as epics are completed and new needs emerge.*
