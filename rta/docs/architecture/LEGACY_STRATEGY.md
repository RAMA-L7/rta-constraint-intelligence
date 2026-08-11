# Ṛta — Legacy Strategy

> **Document kind:** architecture policy · **Status:** proposed — awaits founder approval
> **Date:** 2026-08-07 · **Applies to:** `legacy/` (repo root)
> **Founder requirement (Correction 6):** no historical work may be lost. This
> document defines what belongs in `legacy/`, what never moves there, and how
> future engineers understand the difference.

---

## 1. The hard rules

1. **Nothing in `legacy/` is ever deleted.** Removal requires founder sign-off
   plus a recorded git-history reference.
2. **Nothing in `legacy/` is imported** by any runtime surface (engine, api,
   cli, workspace, website, tests, benchmarks). It is reference material.
3. **`legacy/` never receives current product work.** If a file is load-bearing
   today, it lives in `rta/` — not `legacy/`.
4. **`legacy/` is not a graveyard of shame.** It is the company's preserved
   engineering history, indexed so any engineer can understand why each item
   exists.

---

## 2. What belongs in `legacy/`

| Item | What it is | Why it is preserved (not deleted) |
|---|---|---|
| `legacy/streamlit/` | `app.py` + `ui/` (the Streamlit application, superseded by `webui/` SPA) | The first product UI. Historical reference for UX decisions; its `ui/theme.py` lineage is the ancestor of today's token system. |
| `legacy/streamlit/config/` | `.streamlit/config.toml` (stale "SDC Validator" branding + old dark palette) | Records the old brand moment. Safe to keep as history. |
| `legacy/experiments/` | `graphify-out/` (gitignored knowledge-graph experiment) | Documents an explored-and-rejected direction — prevents re-litigating it. |
| `legacy/assets/` | `svg/` (40 unreferenced generated icons) | Candidate iconography for future curation; preserved for reference. |
| `legacy/working-copies/` | `reference-features-for-startup.md` (once `docs/product/PRODUCT_CAPABILITY_CATALOG.md` becomes canonical) | The working inventory that drove sprints; archived as provenance. |
| `legacy/LEGACY_README.md` | Index of everything above | The key a future engineer needs to navigate the archive. |

## 3. What NEVER moves to `legacy/`

These are the load-bearing product assets and always stay in `rta/`:

| Asset | Why it never moves |
|---|---|
| `rta/engine/` (17 frozen modules) | The product's brain. Frozen, tested, benchmarked. |
| `rta/workspace/` (`webui/` SPA) | The product engineers use today. |
| `rta/website/` (`site/`) | The public face. |
| `rta/tests/` · `rta/evidence/` (benchmarks + manifest) | Verification is a live, current asset. |
| `rta/evidence/` expected values | Moving or editing them would falsify history. |
| Packaging, CI, README, LICENSE | Current operations. |

## 4. How future engineers understand the difference

```
rta/        = the product. If you run it, test it, ship it — it lives here.
legacy/     = the history. If it is superseded or experimental — it lives here.
             Read LEGACY_README.md before looking for anything inside.
```

Decision procedure for a new engineer:
1. Is it used by a runtime surface, test, benchmark, or CI? → `rta/`.
2. Is it superseded, experimental, or a stale copy of something in `rta/`?
   → `legacy/`.
3. Unsure? → Ask; never guess. Anything moved into `legacy/` requires a review.

## 5. Lifecycle of an item entering `legacy/`

1. Confirm the capability has a live replacement in `rta/` (or was deliberately
   abandoned — record why).
2. `git mv` into `legacy/<category>/`.
3. Add/update an entry in `LEGACY_README.md`: what, why superseded, when,
   replacement location.
4. Run the full regression (legacy items are never imported, so no behavioral
   change is expected — the regression is a safety check).

## 6. Relationship to git history

`legacy/` and git history are complementary, not substitutes:
- **git history** is the complete, auditable timeline (every commit ever made).
- **`legacy/`** is the curated, *searchable* history — the items worth knowing
  about without digging through the log.
- The founder's "never lose anything" guarantee is satisfied by both layers.

## 7. Open question (legacy-specific)

- Should `legacy/` be committed to the repository, or stay as a local-only
  directory with the real history living in git? **Recommendation:** commit it —
  "visible, recoverable, documented" beats "smaller tree" for a startup that
  explicitly wants nothing lost.

---

*Legacy strategy complete. Consistent with `REPOSITORY_BLUEPRINT.md` §8 and
`NAMING_RECOMMENDATIONS.md` §2.*
