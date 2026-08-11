# ADR Template

> Copy this file to `docs/company/ADR_NNN_<slug>.md`. ADRs are **immutable once accepted.** If a decision is superseded, write a new ADR that references the old one; update the old ADR's status to "Superseded."

---

# ADR_NNN: <Title>

> **Status:** Proposed · **Date:** YYYY-MM-DD · **Decision owner:** <name>

---

## Context

What is the situation? What forces are at play? Why does a decision need to be made now?

Be specific about:
- What part of the system is affected.
- What constraints are in play (Trust Model, deterministic architecture, open-core boundary, packaging).
- What the current state is.

## Decision

What is the decision? State it in one sentence.

> We choose <approach> for <scope>.

## Alternatives Considered

| Alternative | Description | Pros | Cons |
|---|---|---|---|
| A | | | |
| B | | | |
| C | | | |

## Rationale

Why this alternative over the others? What specific evidence or principle drove the choice?

Reference the relevant Operating System principle if applicable (e.g., "Principle 1.3: Deterministic over probabilistic").

## Consequences

### Positive

- What becomes easier or better because of this decision?

### Negative

- What becomes harder or worse because of this decision?

### Risks

- What could go wrong? How would we detect it?

### Trust impact

- Does this change what the tool validates, partially validates, or discloses?
- Does this introduce any surface where the tool could misrepresent its scope?

## Evidence

- What test, benchmark, or artifact proves this decision is correct?
- Is there a golden suite that covers the affected behavior?
- Does the full regression still pass?

## Review

| Date | Reviewer | Outcome |
|---|---|---|
| | | |

## Status

- [ ] Proposed
- [ ] Accepted
- [ ] Rejected (with rationale)
- [ ] Superseded by ADR_NNN

---

*ADRs are the memory of the architecture. Write them so that someone joining the team in two years can understand why this choice was made.*
