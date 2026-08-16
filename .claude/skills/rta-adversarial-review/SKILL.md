---
name: rta-adversarial-review
description: Assume a proposed Ṛta implementation is wrong and find how it fails. Review-only; never modifies files. Ends with BLOCK / FIX / ACCEPT plus required evidence.
---

# rta-adversarial-review

Assume the proposed change is incorrect or incomplete. Attack it. Find the failure modes before they ship.

## Scope guard

- Review only. Do NOT modify any files.
- Do NOT touch frozen contracts: engine, rule IDs, severities, parser, coverage/readiness/conflict math, diff/generator/converter semantics, CLI exit codes, API response shape, trust disclosures, validation sample, tests.
- Protect the frozen validation product (`v1.5.8-validation`). No review may modify it.
- Do NOT weaken existing regression coverage.

## Attack surfaces — check each

1. **Functional regressions** — parity tests, exit codes (0/1/2/3), deterministic output (run twice, must be identical).
2. **False positives / false negatives** — findings that fire wrongly or miss real issues; invented line numbers; empty collections reported as mismatches.
3. **Misleading UX** — fake states, static numbers, fake success/loading; stale results from another session.
4. **Trust/disclosure violations** — anything implying STA signoff, setup/hold passes, coverage = correctness, CI PASS = timing PASS, or engine failure shown as PASS.
5. **Portability** — absolute/machine-specific paths, hard-coded line endings, environment-dependent output.
6. **Test gaps** — behavior changed with no regression test; tests asserting formatting instead of semantics.
7. **Scope expansion** — features, UI redesign, engine changes, or AI not requested.

## Method

1. Read the actual diff and the touched contracts.
2. Run the existing tests (at least the focused subset, ideally full pytest).
3. Verify exit codes and determinism where relevant.
4. Confirm no tracked-file side effects from running the change.

## Verdict

End with exactly one of:

- **BLOCK** — a frozen contract, trust disclosure, or regression coverage is violated; state the evidence.
- **FIX** — correctable defects found; list each with the evidence required to consider it fixed.
- **ACCEPT** — the attack failed; state what was checked and that the evidence is clean.
