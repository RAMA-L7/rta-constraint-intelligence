# Phase 13 — Production Hardening Golden Suite (PH13-01..25)

Structured finding identity, snapshot v2 / migration, structural fingerprint v2,
declarative CUSTOM policy engine, and CI gate behavior.

Run: `python benchmarks/run_production_hardening.py` (exit 0 = all pass).

Each case has an **independently derived** expected result recorded below.
Expected results come from the Phase 10–13 rule semantics and the module
contracts, NOT from the implementation under test.

| Case  | Focus | Expected |
|-------|-------|----------|
| PH13-01 | message changed / identity same | `new == [] and resolved == []` (UNCHANGED) |
| PH13-02 | severity changed | finding pair classified CHANGED, never NEW+RESOLVED |
| PH13-03 | same rule / different object | identities differ (distinct findings) |
| PH13-04 | different bus ranges | identities differ (ranges are object identity) |
| PH13-05 | symmetric interaction reordered | same identity (pair order canonicalized) |
| PH13-06 | order-sensitive override | direction preserved (reversed pair ≠ same identity) |
| PH13-07 | schema v1 vs v2 | PARTIALLY_COMPARABLE, no false regression |
| PH13-08 | malformed snapshot | load fails safely (None + errors) |
| PH13-09 | same design reformatted | identical structural fingerprint |
| PH13-10 | design port added | fingerprint differs; diff flagged CONTEXT_CHANGE |
| PH13-11 | hierarchy changed | fingerprint differs |
| PH13-12 | BLOCKERS_ONLY | clean → PASS; BLOCKED → FAIL |
| PH13-13 | NO_READINESS_REGRESSION | new blocker → FAIL; unchanged debt → PASS |
| PH13-14 | STRICT | BLOCKED or review regression → FAIL |
| PH13-15 | CUSTOM legacy policy | new blocker → FAIL; old debt → PASS |
| PH13-16 | CUSTOM mature policy | trust/coverage/new-review regressions → FAIL |
| PH13-17 | invalid policy | rejected with exit-2 semantics |
| PH13-18 | engine failure | gate never PASS (exit 3) under any policy |
| PH13-19 | trust regression | detected; gated by mature policy |
| PH13-20 | coverage regression | newly unconstrained object detected |
| PH13-21 | existing debt unchanged | exposed as baseline debt, never new |
| PH13-22 | resolved debt | visible as resolved, classification IMPROVEMENT |
| PH13-23 | false-new attack (line movement) | zero false NEW / RESOLVED |
| PH13-24 | false-resolved attack (formatting) | zero false NEW / RESOLVED |
| PH13-25 | realistic CI workflow | save baseline → gate pass → gate fail with evidence |

## Fixtures

- `fixtures/clean.sdc`  — fully constrained single-clock block (SDC-030 advisory only)
- `fixtures/blocker.sdc` — clean + undefined clock reference (SDC-046, BLOCKED)
- `fixtures/mcp.sdc`     — max/min delay window contradiction (SDC-069, BLOCKED)
- `fixtures/top.v`       — structural netlist for design-aware cases
