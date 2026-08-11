# Ṛta — Open-Core Strategy

> **Document kind:** open-core boundary planning. No licensing, paywalls,
> authentication or cloud infrastructure is implemented in this phase.
> **Date:** 2026-08-06

---

## 1. Model

Ṛta is designed as an **open-core** product: a strong MIT-licensed Community
core that is genuinely useful on its own, plus (future, additive) team and
enterprise offerings.

The guiding rule:

> **Nothing that exists today is moved behind a paywall.** Commercial scope is
> additive — it extends collaboration and governance, it never degrades what
> is already open.

## 2. Ṛta Community (open source — MIT)

Candidate open scope (all currently implemented capabilities):

- SDC preprocessing + bounded Tcl variable resolution
- deterministic validation rule engine + rules registry
- clock extraction, ancestry, relation inference + mismatch detection
- design context (Verilog subset) + design-aware coverage
- constraint interactions, readiness, snapshots, semantic diff
- CLI (`rta` / `sdc-tools`), local HTML/JSON reports
- baseline + gate evaluation for local CI
- reference designs, benchmarks, docs, website

## 3. Ṛta Team / Enterprise (future hypotheses — NOT implemented)

Candidate future scope, in rough order of value:

1. **Team baselines & shared policies** — org-wide readiness snapshots,
   declarative policy catalogs, policy versioning.
2. **Centralized history & dashboards** — multi-project trend views.
3. **Enterprise CI integration** — native GitHub/GitLab apps, audit trails,
   gate evidence bundles.
4. **Collaboration** — review flows for constraint changes, annotations,
   finding assignments.
5. **Governance & analytics** — org-level coverage/readiness analytics,
   signoff evidence exports.
6. **Support** — SLA-backed support for methodology teams.

## 4. Boundary principles

- **Engine stays open.** The analysis engine is the brand; closing it would
  destroy trust and contradict the Trust Model.
- **Differentiation is workflow, not analysis.** Teams pay for shared state and
  process, not for the right answer.
- **Data portability.** Any future cloud feature must export and import the
  same baseline/policy formats used locally (schema v2/identity v1).
- **No vendor lock-in.** The CLI remains the integration boundary; CI works
  from a shell with no SaaS dependency.

## 5. Risks

- **Cannibalization:** strong local features reduce perceived need for team
  features → mitigate by making team features *dramatically* better for
  multi-engineer orgs (shared context, review, governance), not by nerfing
  local ones.
- **Enterprise feature creep:** avoid building enterprise plumbing before the
  Community product is excellent. Roadmap gates this (see
  PRODUCT_ROADMAP.md).

## 6. License & governance (current)

- MIT (repository license).
- Contributions governed by CONTRIBUTING.md; security policy exists for
  findings.
- Trademark note: `Ṛta` is the product brand; the open-core repository uses the
  ASCII identifier `rta` per the naming architecture. Future trademark policy
  is a legal matter, out of scope here.
