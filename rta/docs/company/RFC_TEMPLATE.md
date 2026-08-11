# RFC Template

> Copy this file to `docs/company/RFC_NNN_<slug>.md` and fill in every section. Delete optional sections only if they are genuinely not applicable. No section is "N/A" because it is hard to answer — if it is hard to answer, that is a signal the RFC needs more thought.

---

# RFC_NNN: <Title>

> **Status:** Draft · **Author:** <name> · **Date:** YYYY-MM-DD · **Reviewers:** <names>

---

## 1. Summary

One paragraph. What is this RFC proposing? Write it for a reviewer who has 30 seconds.

## 2. Motivation

Why does this matter? What engineer experiences what friction, and how often?

- What is the current behavior?
- What is the problem with the current behavior?
- Who is affected?
- How frequently does this come up?

## 3. Proposal

What are you proposing to change? Be specific. Describe the change in engineering terms:

- What new or changed module, function, or interface?
- What does the user see (CLI, workspace, website)?
- What does the backend compute?

## 4. Trust Impact

Does this change touch the Trust Model? If so, how?

- [ ] No trust impact.
- [ ] Adds a new trust status. Describe: _______
- [ ] Changes an existing trust status. Describe: _______
- [ ] Introduces a new surface where the tool could misrepresent its scope. Describe risk: _______

## 5. Evidence

What proves this works?

- [ ] New or modified test(s) in `tests/`.
- [ ] New or modified golden suite in `benchmarks/`.
- [ ] Benchmark suite passes for affected modules.
- [ ] Performance is not regressed (if applicable).
- [ ] The change is verifiable from a clean wheel install.

## 6. Alternatives Considered

What else did you consider? Why was this approach chosen over others?

| Alternative | Pros | Cons | Why not chosen |
|---|---|---|---|
| A | | | |
| B | | | |
| C | | | |

## 7. Impact on Open Core

- [ ] No impact. This is Community-scope work.
- [ ] Extends Community scope. Describe: _______
- [ ] Touches the open-core boundary. Requires review by company lead.

## 8. Rollout

How does this ship?

- [ ] Feature flag / phased rollout.
- [ ] Immediately on merge to main.
- [ ] Requires a release. Which version? _______

## 9. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| | | |

## 10. Open Questions

What is not yet decided? List every open question so the reviewer does not have to find them.

## 11. Dependencies

Does this RFC depend on another RFC, ADR, or external work?

- [ ] Depends on RFC_NNN: _______
- [ ] Depends on external: _______
- [ ] No dependencies.

## 12. Timeline Estimate

Not a commitment. An estimate to help with sprint planning.

| Work | Estimate |
|---|---|
| Implementation | |
| Tests | |
| Documentation | |
| Review | |
| Total | |

---

## Decision

| Date | Decision | Record |
|---|---|---|
| | | |

---

*After implementation, add a note here: "Implemented in PR #NNN, merged YYYY-MM-DD."*
