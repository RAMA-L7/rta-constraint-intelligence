# Ṛta — Production Root (future home)

> **Status:** FOUNDATION PLACEHOLDER — approved architecture only.
> **This folder is intentionally empty.** It is the designated future home of the
> Ṛta production application per `docs/architecture/REPOSITORY_BLUEPRINT.md`
> (product-first revision).

Nothing is moved here until the founder approves the migration plan
(`docs/architecture/MIGRATION_PLAN.md`) and the readiness conditions
(`docs/architecture/MIGRATION_READINESS.md` §5). The current repository root
remains the working tree and is untouched.

## Intended layout — product-first (one responsibility per folder)

```
rta/
├── branding/       # visual identity: tokens, type, mark (shared by every surface)
├── engine/         # deterministic analysis core (frozen — the "brain")
├── api/            # programmatic HTTP surface (api_server.py + /api/*)
├── cli/            # terminal surface (cli.py + command modules)
├── workspace/      # ENGINEERING APPLICATION — sessions, analysis, reports, tools
├── website/        # BUSINESS WEBSITE — company, benchmarks, trust, docs, release
├── tools/          # first-class tools: generate, lint, convert, corners, mmc, batch, report
├── knowledge/      # rules reference, trust model, in-app documentation
├── evidence/       # benchmarks, manifest, data, reports (verification system)
├── examples/       # sample SDC, policies, custom rules
├── assets/         # shared static material (curated icons, fonts)
├── infrastructure/ # CI, Docker, packaging, hooks, release tooling
├── tests/          # pytest suite
└── docs/           # company / foundation / product / features / architecture
```

**Preserved history lives outside this folder** in `legacy/` at the repo root —
never deleted, never imported (see `docs/architecture/LEGACY_STRATEGY.md`).

See `docs/architecture/REPOSITORY_BLUEPRINT.md` for ownership, dependencies,
naming ( `NAMING_RECOMMENDATIONS.md`) and scalability notes.
