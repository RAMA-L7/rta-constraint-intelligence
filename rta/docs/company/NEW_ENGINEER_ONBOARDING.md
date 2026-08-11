# New Engineer Onboarding

> **Document kind:** one-day onboarding sequence for a senior engineer joining Ṛta.
> **Goal:** By end of day, the engineer can read the codebase, run the tool, understand the product, review a PR, and propose a change.
> **Last updated:** 2026-08-07

---

## Day Plan

| Time block | Activity | Duration |
|---|---|---|
| Morning 1 | Read the Charter and the product | 60 min |
| Morning 2 | Repository tour and architecture | 60 min |
| Afternoon 1 | Run the tool and examine the evidence | 60 min |
| Afternoon 2 | Review a PR and propose a change | 60 min |

---

## Morning 1: Read the Charter and the Product (60 min)

### Step 1: Read the Product Charter (20 min)

Read `docs/company/PRODUCT_CHARTER.md` completely. This is the constitution. Everything else implements it.

Key things to internalize:
- What Ṛta is (Constraint Intelligence Platform).
- What it is NOT (not STA, not signoff, not AI, not a cloud service).
- The current scope (Version 1: Block-Level Constraint Intelligence).
- The Trust Model and its six statuses.
- The five Product Decision Questions.
- The engineering principles (evidence over assumptions, deterministic over probabilistic, trust before automation).

### Step 2: Read the Operating System (15 min)

Read `docs/company/OPERATING_SYSTEM.md` — specifically §1 (Company Principles), §2 (Decision Making), §5 (Definition of Done), §6 (Definition of Trust), §7 (Definition of Evidence), and §14 (Naming Standards).

You do not need to memorize the entire document. You need to know it exists and where to find it.

### Step 3: Read the Glossary (10 min)

Read `docs/company/GLOSSARY.md`. The terminology in this project is precise. "Readiness" does not mean "signoff." "Coverage" does not mean "correctness." "Trust" does not mean "certainty." Using the wrong term is a product error.

### Step 4: Skim the README (5 min)

Read `README.md`. This is the external-facing description of the product. Understand what the product claims and how it presents itself.

### Checkpoint

You should now be able to answer:
1. What is Ṛta?
2. What does Version 1 do?
3. What is the Trust Model?
4. Why is the engine deterministic?
5. What is NOT an STA tool?

---

## Morning 2: Repository Tour and Architecture (60 min)

### Step 1: Read the Repository Map (10 min)

Read `docs/company/REPOSITORY_MAP.md`. This tells you where everything lives, who owns what, and where future work belongs.

### Step 2: Tour the source files (30 min)

Read the key files in this order:

**The analysis pipeline** (the core product):

1. `sdc_preprocess.py` — Normalizes raw SDC text into a structured command stream. Handles comments, multiline, Tcl variables, collections.
2. `tcl_resolver.py` — Resolves bounded Tcl scalar variables from linked TCL files. Does not execute Tcl.
3. `checker.py` — The deterministic rule engine. 111 rules. Each produces an Issue with code, severity, message, and line provenance.
4. `rules_registry.py` — The single source of truth for all rules: code, severity, description, why-it-matters, fix, module, version.
5. `support_boundary.py` — Reports what was validated, partially validated, and skipped. The Trust Model's runtime implementation.
6. `clock_relations.py` — Clock inventory, generated-clock ancestry, pairwise relationship classification.
7. `wildcard_analyzer.py` — Risk-scores wildcard patterns in SDC object specs.
8. `design_context.py` — Parses structural Verilog netlists and resolves SDC object references.
9. `design_coverage.py` — Per-port, per-bus, per-bit-range constraint coverage.
10. `coverage.py` — Category-level coverage (39-item, 6 categories).
11. `constraint_interactions.py` — Duplicates, overrides, contradictions (SDC-069), overlaps (SDC-070).
12. `constraint_readiness.py` — Seven-dimension readiness aggregation.
13. `readiness_diff.py` — Semantic baseline comparison (new/resolved/changed/unchanged).
14. `finding_identity.py` — Structured finding comparison (message-independent).
15. `policy_engine.py` — Declarative CI gate policies (BLOCKERS_ONLY, NO_READINESS_REGRESSION, STRICT, CUSTOM).

**The surfaces** (how users interact):

16. `cli.py` — CLI entry point (`rta` / `sdc-tools`). Dispatches to all commands.
17. `api_server.py` — Stdlib HTTP server. Serves the workspace and exposes the backend as JSON.
18. `webui/` — Vanilla JS workspace SPA (hash router, inspector, status rail).
19. `site/` — Static marketing website (15 pages, canvas background, evidence cards).
20. `reporter.py` — HTML report generator.

**The tools** (auxiliary capabilities):

21. `generator.py` — SDC scaffold generation.
22. `linter.py` — SDC formatting.
23. `converter.py` — SDC → JSON/YAML.
24. `corner_manager.py` — PVT corner presets.
25. `mmc.py` — Multi-corner SDC generation.
26. `batch_runner.py` — Directory-scale processing.

### Step 3: Understand the data flow (10 min)

Trace a single `rta check design.sdc` call:

```
cli.py (parse args, dispatch)
  → sdc_preprocess.py (normalize SDC text)
  → tcl_resolver.py (resolve Tcl variables)
  → checker.py (111 rules → issues)
  → clock_relations.py (clock inventory + relations)
  → support_boundary.py (analysis scope disclosure)
  → constraint_interactions.py (duplicates, overrides, conflicts)
  → constraint_readiness.py (seven-dimension verdict)
  → reporter.py (HTML/JSON output)
```

If a netlist is supplied, `design_context.py` and `design_coverage.py` are added after the preprocessing step.

### Step 4: Read the architecture docs (10 min)

Skim:
- `docs/rta/REPOSITORY_ARCHITECTURE.md` — current and target repository structure.
- `docs/rta/CAPABILITY_MAP.md` — every capability mapped to its backend module.
- `docs/rta/PRODUCT_TAXONOMY.md` — product module definitions.

### Checkpoint

You should now be able to answer:
1. What does each module do?
2. How does data flow through the analysis pipeline?
3. Where does the workspace get its data?
4. What does the API server expose?
5. Where does future work belong (per the target architecture)?

---

## Afternoon 1: Run the Tool and Examine the Evidence (60 min)

### Step 1: Set up the environment (15 min)

```bash
cd sdc-tools
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[web]"
```

### Step 2: Run the validator (10 min)

```bash
# Basic validation
rta check samples/example.sdc

# JSON output
rta check samples/example.sdc --json

# With design context
rta check samples/example.sdc --netlist samples/check_variants/good_complex.sdc

# Clock analysis
rta analyze clock-relations samples/example.sdc

# Coverage
rta coverage samples/example.sdc
```

Examine the output. Understand the finding format: severity, rule code, message, line number. Understand the trust scope disclosure.

### Step 3: Run the test suite (10 min)

```bash
python -m pytest tests/ -q
```

Watch it run. Understand the test structure: `tests/test_checker.py` tests the rule engine, `tests/test_clock_relations.py` tests clock analysis, etc. The count should be 780 passing.

### Step 4: Run a golden runner (10 min)

```bash
python benchmarks/run_golden.py
```

This runs the golden parser suite and compares results against expected outcomes. Understand what "golden" means: the expected behavior is independently derived from SDC semantics, not from the tool's output.

### Step 5: Examine the evidence (10 min)

Read `docs/rta/BENCHMARK_EVIDENCE_MAP.md`. Understand how every product claim maps to a rerunnable artifact. Read the benchmark files:

- `benchmarks/test_release_smoke.py` — verifies documented workflows.
- `benchmarks/release_cli_audit.py` — verifies CLI contract (exit codes, JSON purity).
- `benchmarks/release_cleanroom.py` — verifies clean-room wheel journey.

### Step 6: Launch the workspace (5 min)

```bash
rta web
```

Open `http://127.0.0.1:8501`. Load the sample SDC. Examine the workspace: navigation, findings explorer, clock page, readiness page, coverage page. Understand that every number comes from the backend, not from a mock.

### Checkpoint

You should now be able to:
1. Run the validator on any SDC file.
2. Interpret the output format.
3. Run the test suite and understand the results.
4. Run a golden runner and understand what it proves.
5. Launch the workspace and navigate it.

---

## Afternoon 2: Review a PR and Propose a Change (60 min)

### Step 1: Read the Engineering Checklist (10 min)

Read `docs/company/ENGINEERING_CHECKLIST.md`. This is what every PR must satisfy. Understand the pre-merge and post-merge requirements.

### Step 2: Read the Product Review Checklist (5 min)

Read `docs/company/PRODUCT_REVIEW_CHECKLIST.md`. This is what every user-facing change must satisfy.

### Step 3: Review an existing PR (20 min)

If there are open PRs on GitHub, review one. Apply the checklists:

1. Does the PR description reference an issue or RFC?
2. Do all tests pass?
3. Is the trust boundary preserved?
4. Are evidence numbers current (if affected)?
5. Is documentation updated?
6. Does the PR align with the Product Charter?

If there are no open PRs, read a recent merged PR's discussion to understand the review culture.

### Step 4: Propose a small change (25 min)

Pick a small, low-risk change. Examples:
- Fix a stale number in a feature doc.
- Add a comment to a module that lacks one.
- Write a missing edge-case test.

Before implementing:
1. Check: does this change align with the Product Charter? (Charter §11)
2. Check: does this change require an RFC? (Operating System §17)
3. Check: does this change require an ADR? (Operating System §18)

If the change is small and non-architectural, implement it directly. If it touches the engine, the Trust Model, or the product boundary, write an RFC first.

### Step 5: Open a PR (if applicable)

Follow the GitHub workflow (Operating System §24):
1. Create a feature branch: `feature/<slug>`.
2. Make the change.
3. Run tests: `python -m pytest tests/ -q`.
4. Commit with a conventional message.
5. Open a PR with the issue or RFC reference.
6. Fill in the Engineering Checklist.

### Checkpoint

You should now be able to:
1. Review a PR against the Engineering Checklist.
2. Identify whether a change needs an RFC or ADR.
3. Implement a small change and open a PR.
4. Articulate why a change aligns (or does not align) with the Charter.

---

## Key References

Keep these open during your first week:

| Document | When to consult |
|---|---|
| `PRODUCT_CHARTER.md` | Before any product decision |
| `OPERATING_SYSTEM.md` | Before any process decision |
| `GLOSSARY.md` | Whenever writing documentation or product text |
| `REPOSITORY_MAP.md` | Whenever you are unsure where code belongs |
| `ENGINEERING_CHECKLIST.md` | Before every PR |
| `PRODUCT_REVIEW_CHECKLIST.md` | Before every user-facing change |

---

## After Day 1

You are not expected to know everything. You are expected to know:

1. What the product is and what it is not.
2. Where the key files are.
3. How to run the tool and the tests.
4. How to review a PR.
5. How to propose a change.
6. Where to find the documentation when you need it.

Everything else is learned by doing. The documentation exists. Use it.

---

*Welcome to Ṛta. The product is built on trust. Your work will be reviewed against that standard. The bar is high because the engineers who use this tool trust it with silicon-quality decisions. That trust is worth maintaining.*
