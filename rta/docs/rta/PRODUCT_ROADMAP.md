# Ṛta — Product Roadmap

> **Document kind:** maturity-based roadmap. No arbitrary dates. Speculative
> items are marked **[speculative]**.
> **Date:** 2026-08-06

---

## Foundation ✅ (this phase)

- Ṛta identity: visible brand, ASCII identifier `rta`, brand migration audit.
- Product docs set under `docs/rta/`.
- CLI alias `rta` + Windows `rta.cmd`.
- Website, workspace, reports, CLI and docs speak Ṛta's product language.
- Deterministic backend untouched; full regression green.

## Product Experience (next major phase)

- From-scratch Ṛta application experience (workspace is the proven vertical
  slice; extend the design system across all pages).
- Motion system per VISUAL_IDENTITY_DIRECTION.md levels 1–4 (the Phase 17
  background visibility gap on the canonical silicon-topology background is
  fixed — `rta/workspace/webui/assets/{css/app.css,js/viz.js}`).
- Technical visualizations: clock tree, relation matrix, bus coverage strips,
  readiness dimension rail, constraint interaction links, baseline→current diff.
- Website → workspace continuity (shared tokens, typography, background
  grammar, status language).

## Developer Experience

- Install polish: `pip install rta` **[post package-namespace migration]**.
- CLI completion/aliases, `rta --help` parity with `sdc-tools`.
- GitHub Actions starter workflows + badge.
- CI evidence bundles (gate verdict + snapshot artifacts) **[speculative]**.

## Community

- Docs site under `docs/rta` + `docs/features`.
- Example library: real design constraint sets + golden outcomes.
- Contribution guide, good-first-issues, rule-authoring guide (custom rules).
- Benchmark dashboard that reruns suites and publishes evidence.

## Team Product **[speculative]**

- Shared baselines & policy catalogs.
- Centralized history and trend dashboards.
- Constraint change review flows, finding assignment.

## Enterprise **[speculative]**

- Governance: org policies, audit trails, signoff evidence exports.
- Native GitHub/GitLab apps, enterprise CI integrations.
- Support offering.

## Explicitly NOT planned (unless requested)

- LLMs / generative AI in the analysis path — the product is deterministic.
- Licensing/paywalls — open-core boundary is additive (OPEN_CORE_STRATEGY.md).
- Cloud processing of customer SDC/netlist data without explicit opt-in.
