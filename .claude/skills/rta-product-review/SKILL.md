---
name: rta-product-review
description: Challenge whether a proposed Ṛta feature is worth building before implementation. Review-only; never modifies files. Ends with BUILD / DON'T BUILD / WAIT FOR EVIDENCE.
---

# rta-product-review

Review a proposed Ṛta feature before any implementation. Ask the hard questions first.

## Scope guard

- Review only. Do NOT modify files, engine, API, CLI, UI, tests, fixtures, docs, or release artifacts.
- Protect the frozen validation product (`v1.5.8-validation`) and the Plan A adoption loop: Validate → Diff → CI Gate → Report.
- Do not review aesthetics. Do not propose AI features, SaaS, or unrelated expansion.

## Questions to answer

1. What user problem does this solve? Name the user and the concrete situation.
2. Who experiences it, and what evidence do we have that they do? Label every claim EVIDENCE or ASSUMPTION.
3. Does it strengthen Validate → Diff → Gate → Report, or the evidence we collect from real engineers?
4. What existing contract could it threaten? (frozen engine, rule IDs, severities, parser, coverage/readiness math, diff/generator/converter semantics, CLI exit codes, API response shape, trust disclosures)
5. What is the smallest useful implementation? Fewest files; no new framework; no UI redesign.
6. What would make this proposal wrong? State the falsifying evidence explicitly.
7. What test would prove the feature works and does not regress parity?

## Verdict

End with exactly one of:

- **BUILD** — evidence exists; smallest useful scope defined; contracts protected.
- **DON'T BUILD** — problem weak, evidence absent, or conflicts with strategy/freeze.
- **WAIT FOR EVIDENCE** — plausible but unproven; state the specific evidence needed and the decision threshold.
