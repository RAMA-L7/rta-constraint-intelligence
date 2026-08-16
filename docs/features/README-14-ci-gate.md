# Ṛta CI Quality Gates — exit-code contract, policies & GitHub Action

The CI gate turns `rta check` into a **merge gate**: a deterministic verdict
(exit code) plus machine-readable evidence (`--json` / `--junit`) that a
pipeline can act on. This document is the one-place contract for the gate.

- **Exit-code contract** — the 0 / 1 / 2 / 3 semantics
- **Policy matrix** — what each policy gates on
- **CUSTOM policy schema** — declarative YAML/JSON policies
- **Baseline workflow** — save once, compare in CI
- **GitHub Action** — `.github/actions/rta-gate` usage
- **Trust boundary** — what a gate PASS does *not* mean

> The gate is **opt-in**. Without `--gate`, `rta check` keeps its original
> exit behavior (`0` = no errors, `1` = errors found) and never runs a gate.

---

## 1. Exit-code contract

When `--gate` is requested, the exit code is the gate verdict:

| Code | Meaning | Action in CI |
|------|---------|--------------|
| `0` | **PASS** — merge allowed | job succeeds |
| `1` | **FAIL** — merge blocked | job fails; the JSON/JUnit output lists the reasons |
| `2` | **invalid invocation / input** | job fails; fix the invocation (missing baseline, missing policy file, missing SDC, invalid policy schema) |
| `3` | **analysis engine failure** (SDC-140) | job fails; a gate can **never** report PASS on incomplete evidence |

Invariant: `stats`/verdict and the actual result collections are always
consistent — the JSON `readiness_diff.gate` carries `result`, `exit_code`, and
`reasons`, and the CLI exits with exactly that `exit_code`.

## 2. Policy matrix

| Policy | Baseline required | Fails when |
|--------|:---:|------------|
| `BLOCKERS_ONLY` | no | current readiness is `BLOCKED` |
| `NO_READINESS_REGRESSION` | yes | revision introduces a **blocking or review regression** vs baseline |
| `STRICT` | yes | blocking/review regression **or** current readiness `BLOCKED` |
| `CUSTOM` | policy-defined | declarative policy file selects the failing evidence |

Baseline-dependent policies fail with exit `2` (not silently pass) when no
baseline is supplied.

## 3. CUSTOM policy schema

Policies are **inert data** (YAML or JSON): no code execution, no expressions.
A policy only selects *which existing diff evidence* fails the gate — it never
changes what the validator detects, and engine failure can never be disabled.

```yaml
policy: CUSTOM
policy_version: 1
name: team-review-flow
fail_on:
  current_blocked: true        # current readiness == BLOCKED
  new_blockers: true           # NEW deterministic blocker vs baseline
  new_review_items: false      # NEW review-tier finding vs baseline
  trust_regression: false      # VALIDATED → PARTIAL/UNSUPPORTED scope
  coverage_regression: false   # newly unconstrained design objects
  engine_failure: true         # always effective, cannot be disabled
allow:
  new_advisories: true         # info-level additions never fail
thresholds:
  max_new_review_items: 2      # optional cap (0 = none allowed)
fail_on_new_rules: ["SDC-069"] # optional rule-specific gate
```

Unknown keys, wrong types, invalid enums, negative thresholds, unsupported
versions, and oversized files are rejected with exit `2`.

Example — a *lenient team-review* flow (new review items and coverage
regressions land in the review queue instead of blocking the merge):

```yaml
policy: CUSTOM
policy_version: 1
name: team-review-flow
fail_on:
  current_blocked: true
  new_blockers: true
  new_review_items: false
  trust_regression: false
  coverage_regression: false
  engine_failure: true
allow:
  new_advisories: true
```

See `engineer_test_kit/14_baseline_gate/gate_policy.yaml` for a working copy.

## 4. Baseline workflow

```bash
# 1. Once, on the known-good state — commit this file to the repo:
rta check my_block.sdc --netlist my_block.v --top my_block_top \
  --save-baseline baseline.json

# 2. In CI, on every change:
rta check my_block.sdc --netlist my_block.v --top my_block_top \
  --baseline baseline.json --gate STRICT
```

- The baseline snapshot is versioned against the validator tool version; a
  stale baseline (created by a different Ṛta release) is reported and must be
  regenerated — the gate will not silently compare across versions.
- Use the same `--netlist`/`--top` for baseline and CI runs; analysis-mode
  drift (DESIGN_AWARE → SDC_ONLY) makes the diff only partially comparable.
- Machine-readable output works with the gate:
  `--json` (verdict in `readiness_diff.gate`) and `--junit` (CI dashboards).

## 5. GitHub Action

The repository ships a composite action at
[`.github/actions/rta-gate/action.yml`](../../.github/actions/rta-gate/action.yml).
It installs Ṛta, runs the gate, propagates the exit code, and uploads
`rta-gate-result.json` + `rta-gate-junit.xml` as artifacts.

```yaml
jobs:
  sdc-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Ṛta CI Quality Gate
        uses: ./.github/actions/rta-gate   # or RAMA-L7/rta-constraint-intelligence/.github/actions/rta-gate@v1
        with:
          sdc: constraints/my_block.sdc
          netlist: rtl/my_block.v          # optional
          top: my_block_top                # optional
          baseline: baseline.json          # required for STRICT / NO_READINESS_REGRESSION
          gate: STRICT                    # BLOCKERS_ONLY | NO_READINESS_REGRESSION | STRICT | CUSTOM
          gate-policy: gate_policy.yaml    # required when gate=CUSTOM
          install-source: pypi             # 'pypi' (published) or 'local' (pip install .)
```

**Inputs**

| Input | Default | Purpose |
|-------|---------|---------|
| `sdc` | *(required)* | SDC file to validate |
| `baseline` | `''` | readiness baseline snapshot (required for STRICT / NO_READINESS_REGRESSION) |
| `gate` | `STRICT` | policy choice |
| `gate-policy` | `''` | CUSTOM policy file |
| `netlist` / `top` | `''` | optional design context |
| `install-source` | `pypi` | `pypi` (published release) or `local` (test unreleased code) |
| `rta-version` | latest | exact PyPI version |
| `python-version` | `3.11` | runner Python |
| `json-output` / `junit-output` | `rta-gate-result.json` / `rta-gate-junit.xml` | artifact paths |

**Outputs:** `exit-code` (0/1/2/3) and `gate-result` (PASS/FAIL). The step
exits with the gate exit code, so a blocked merge fails the job.

The repository's own CI runs this action against the
`engineer_test_kit/14_baseline_gate` fixture (`.github/workflows/ci.yml`,
`gate` job) and verifies the full exit-code contract via
`tests/run_ci_gate_verification.py`.

## 6. Trust boundary

- **CI PASS ≠ timing pass.** The gate checks for disallowed
  constraint-readiness regressions under the selected policy — it is pre-STA
  constraint intelligence, not a timing signoff.
- **Engine failure never becomes PASS** (exit 3, SDC-140).
- **Coverage is NOT correctness** — readiness regressions are compared, not
  scores to maximize.
