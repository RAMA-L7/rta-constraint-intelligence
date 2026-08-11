# Product Review Checklist

> Every feature, page, or surface that a user sees must answer these questions before it ships. The product lead (or a designated reviewer) verifies each item.

---

## Trust

1. **Does this surface carry a trust disclosure?** If the feature has a trust boundary (what it validates, what it does not), that boundary is visible on the surface — not buried in a footnote.
2. **Does the surface imply capabilities the backend does not have?** If the backend does not compute timing, the surface must not display timing values. If the backend requires a netlist for object resolution, the surface must not present object resolution as complete without one.
3. **Is the "not an STA signoff" disclaimer visible?** Every surface that presents a readiness verdict, a coverage number, or a gate result carries the disclaimer.
4. **Could a user reasonably misunderstand what this tool does?** If yes, the misunderstanding must be explicitly addressed on the surface.

## Accuracy

5. **Are all numbers traceable?** Every count, percentage, or metric on the surface comes from a verifiable artifact — not a hardcoded value, not a mock, not an approximation.
6. **Are numbers current?** The numbers match the latest artifact. If the code has changed since the numbers were last verified, they are stale and must be re-verified.
7. **Is the environment context stated?** Performance numbers include: OS, Python version, date, and version.
8. **Is there an "internal verified evidence" note?** Benchmark numbers are presented as internal validation, not independent certification.

## Consistency

9. **Is the canonical one-liner used?** The product description is the canonical string: *"Constraint Intelligence for Digital Design."*
10. **Is the canonical CLI identity used?** The primary CLI is `rta`. `sdc-tools` appears only as the documented alias.
11. **Is the naming architecture followed?** Brand (`Ṛta`), modules (`Ṛta Validate`, `RIPTA Clocks`, …), CLI (`rta`), codes (`SDC-001`).
12. **Is the terminology correct?** Finding, severity, trust, coverage, readiness, baseline, regression — per the Terminology section of the Operating System.

## Engineering Density

13. **Does this surface respect the engineer's attention?** No generic-SaaS fluff. No glassmorphism. No fake percentages. No "magic."
14. **Is information hierarchy clear?** The most important datum is the most prominent. Secondary information is discoverable, not defaulted to.
15. **Do statuses use icon + label + shape, never color alone?** Every severity, trust level, and readiness status is conveyed through three channels.
16. **Is the dark-first theme applied?** Engineering surfaces are permanently dark. The marketing site is dark with AA contrast.

## Accessibility

17. **Does every interactive element have a visible focus ring?**
18. **Do all images and icons have `aria-label` or `aria-hidden`?**
19. **Does the surface respect `prefers-reduced-motion`?** Motion becomes instant state change.
20. **Are tables semantically structured?** `<th scope>`, `<caption>`, `role="grid"` where appropriate.

## Empty and Error States

21. **Are empty states designed?** Every "nothing here" state explains what the user should do next.
22. **Are error states typed?** Errors are classified (user input, unsupported, insufficient context, invalid configuration, internal failure) with distinct treatment.
23. **Are engine failure states honest?** An engine failure displays an ERROR badge + run-id + "results are not a PASS." It never reads as a passing result.

## Evidence

24. **Does this surface present any number that has a runner?** If yes, the runner is identified and the number is verified.
25. **If this is a benchmark surface, is the methodology section present?** Benchmark cards include: name, purpose, methodology, corpus size, expected-behavior source, result, version, environment, limitations, artifact reference.
26. **If this is a new capability page, does it follow the Capability Page Template?** Problem → How it works → Inputs → Outputs → Evidence → Trust boundary → Related docs → Launch CTA.

## Scope

27. **Is this surface within the P0/P1/P2 scope?** If it is P2 or not categorized, it should not ship without a deliberate scope decision.
28. **Does this surface exist in the approved product architecture?** If it is a new surface, is it covered by an approved RFC?

---

## Review Outcome

| Item | Status | Notes |
|---|---|---|
| Trust | | |
| Accuracy | | |
| Consistency | | |
| Engineering Density | | |
| Accessibility | | |
| Empty/Error States | | |
| Evidence | | |
| Scope | | |

**Reviewer:** _______________
**Date:** _______________
**Decision:** Approved / Needs revision (list findings)

---

*This checklist is the product equivalent of the Engineering Checklist. It exists because shipping a surface that misleads an engineer damages trust more than shipping no surface at all.*
