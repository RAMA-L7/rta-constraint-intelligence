# Ṛta — Trust Model

> **Document kind:** trust center foundation — what Ṛta validates, partially
> validates, requires context for, and never claims.
> **Date:** 2026-08-06 · **Version:** v1.3.0

---

## 1. The honesty contract

Ṛta's value depends on its boundaries being visible. The following statements
are enforced in product copy, CLI output, HTML reports, the website and the
docs:

1. **READY ≠ STA signoff.** Readiness is a constraint-quality verdict, not a
   timing result.
2. **100% constraint coverage ≠ timing correctness.** A fully constrained
   object can still have incorrect timing intent.
3. **CI pass ≠ timing closure.** A gate only detects disallowed
   constraint-readiness regressions under a selected policy.
4. **Object resolution ≠ path existence.** A resolved pin does not prove the
   timing path exists.
5. **No errors ≠ everything proven.** The analysis scope discloses what was
   and was not analyzed.

## 2. What Ṛta validates

- Structural SDC syntax and supported-command semantics (deterministic rule
  engine, SDC-001…132).
- Clock declarations, generated-clock ancestry and pairwise clock
  relationships inferred from SDC text.
- Reference consistency *within the analyzed scope*: undefined clocks,
  masters, groups (SDC-046…048) and delay-vs-period margins (SDC-008/009).
- Constraint interactions provable from text: exact duplicates, silent
  overrides, contradictions (SDC-069).
- Coverage (what was constrained) in SDC-only mode.
- Readiness verdicts and their deterministic actions.

## 3. What Ṛta partially validates

- Tcl variable semantics — a **bounded, non-executing** subset is resolved;
  constructs requiring execution are flagged `TCL_EXECUTION_REQUIRED`.
- Option values that are validated for shape but not fully value-analyzed →
  `PARTIALLY_VALIDATED`.
- Clock relation classification — inferred from text; netlist evidence
  strengthens but never completes it.

## 4. What requires design context (netlist)

- Object-reference verification (`get_ports`/`get_pins`/`get_cells`/
  `get_nets`/`all_*`) → `NETLIST_REQUIRED` when absent.
- Design-aware coverage (per-object and per-bus-bit statuses).
- Structural generated-clock fanout reasoning.

Without a netlist, Ṛta says so — in the analysis scope, the UI, and reports.

## 5. What requires STA

- Timing path existence and delay correctness.
- Whether a “needs STA review” overlap (SDC-070) is a real violation.
- Setup/hold closure, signal integrity, power — everything beyond constraint
  quality.

## 6. What Ṛta does NOT claim

- **Not** an STA engine, **not** a signoff tool.
- **No AI.** Analysis is deterministic; identical input → identical output.
- **No** cloud processing — local-first; data never leaves the machine.
- **No** guarantee that a passing result implies timing closure.

## 7. Trust statuses (used verbatim)

| Status | Meaning |
|---|---|
| `VALIDATED` | constructs fully analyzed by the rule engine |
| `PARTIALLY_VALIDATED` | some options/constructs not value-analyzed |
| `NETLIST_REQUIRED` | object references need design context |
| `TCL_EXECUTION_REQUIRED` | Tcl execution constructs present; not executed |
| `UNSUPPORTED` | unsupported constructs present |
| `NOT_VALIDATED` | nothing could be validated (empty/invalid input) |

## 8. Readiness statuses (used verbatim)

| Status | Meaning |
|---|---|
| `READY` | no blockers, no review items, advisories only |
| `READY_WITH_ADVISORIES` | no blockers; advisory-level items |
| `REVIEW_REQUIRED` | review items present (may include STA follow-ups) |
| `BLOCKED` | blockers present |
| `INSUFFICIENT_CONTEXT` | not enough evidence for a verdict |

## 9. Engine-failure guarantee

An analysis/policy engine failure must never produce a passing verdict or
passing exit code. The CLI contract: 0 pass / 1 gate failed / 2 invalid
invocation / 3 engine failure. Verified by `test_engine_failure_never_passes`.

## 10. Where these statements live

- Website: `site/trust.html` (Trust Center).
- Workspace: readiness + coverage + diff pages, status rail.
- CLI: analysis-scope and readiness disclosures in `rta check` output.
- Reports: “NOT an STA timing signoff” footer line in every HTML report.
