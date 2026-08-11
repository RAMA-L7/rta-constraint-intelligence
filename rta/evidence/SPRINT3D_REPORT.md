# Sprint 3D — Arcade-Docs Restyle + Feature Completeness

**Ṛta Foundation → Product Experience** · Report date 2026-08-07

## Executive summary

Sprint 3D had two directives: (1) `reference-features-for-startup.md` is the
**single source of truth** for Ṛta V1 features — audit every feature, fix any
gap, never remove a capability; (2) the page background & style must follow
**docs.arcade.dev** (Arcade-docs light language). Both were delivered:

- **Full feature audit** (21 reference features) — all present and wired to the
  real deterministic backend. **One P0 gap found and fixed:** custom-rules YAML
  input had no UI surface (engine + API + result rendering existed); the input
  is now on both the New Analysis and Validator surfaces.
- **Presentation rebuilt to the Arcade-docs light achromatic language** via the
  existing token system (`ui/theme.py` → `/api/design` → `theme.js` + `app.css`
  + `viz.js`). Backend untouched; engineering semantics unchanged.

## 1. Feature coverage report

Full matrix: `docs/product/SPRINT3D_FEATURE_AUDIT.md`.

| Result | Count |
|--------|-------|
| Features in reference doc | 21 |
| Present & working before sprint | 20 |
| **P0 gaps found** | **1 (custom rules UI input)** |
| P0 gaps fixed | 1 |
| Features removed | 0 |
| Features added | 1 input surface (custom rules) — capability existed |

Every reference feature is now reachable from the workspace or documented CLI.

## 2. Missing features report

None remain. The one gap (custom rules YAML input) was closed this sprint.

## 3. Newly added features

- **Custom rules (YAML, optional)** input on `#/new_analysis` (advanced options)
  and `#/validator` (optional panel) → `custom_rules` payload → `/api/analyze`
  → findings render. Verified end-to-end (CUST-001 → passed).

## 4. Manual verification checklist (browser-verified, zero console errors)

- [x] Launch → light/white page background (`#FFFFFF`), `color-scheme: light`
- [x] Landing "Check your SDC before STA", sample pre-loaded, no sidebar
- [x] Analyze → timeline → auto-land **Findings**, RESULTS sidebar appears
- [x] Findings/metrics/table readable dark-on-light
- [x] Custom rules textarea + CI gate + baseline present on Validator input
- [x] Custom rules API round-trip (CUST-001 → passed, `ok: True`)
- [x] Background topology visible (Motion 14/14) without competing with data

## 5. Before vs after user journey

| Step | Before (Sprint 3C2) | After (Sprint 3D) |
|------|--------------------|--------------------|
| Launch | dark graphite workspace | light Arcade-style paper workspace |
| Landing | same flow (dark) | same flow, light, custom-rules advanced input |
| Analyze | dark timeline | light timeline, same honesty (checkpoints on real completion) |
| Findings | dark cards | white cells + hairline separators |
| Custom rules | **unreachable** | YAML input on New Analysis + Validator |

## 6. Design record (Arcade-docs language)

Tokens extracted from the live `docs.arcade.dev` CSS and adapted:

| Token | Arcade source | Ṛta value |
|-------|---------------|-----------|
| page background | `--background oklch(100% 0 0)` | `#FFFFFF` |
| foreground | `--foreground oklch(14.5% 0 0)` | `#18181B` |
| hairline border | `--border oklch(92.2% 0 0)` | `#EAEAEA` |
| muted surface | `--muted oklch(97% 0 0)` | `#F6F6F6` |
| muted text | (AA on white) | `#71717A` |
| success / error / warning / info | Arcade syntax `#2f6e4e / #a8453a / #8a6c14 / #2563eb` | same |

Typography unchanged (Inter + JetBrains Mono — matches reference sans/mono
pairing). Motion system unchanged (Motion 14/14); reduced-motion respected.

## 7. Remaining gaps

- `batch` remains CLI-only (reference marks it CLI-only).
- Changes page uses the readiness-diff authority; the full `constraint_diff`
  21-rule CHG-* surface stays on the CLI.
- Reference §20 backend limitations are unchanged (backend frozen by design).

## 8. Regression results

| Suite | Result |
|-------|--------|
| pytest (`tests/`) | **800/800** |
| UI/API benchmark | **35/35** |
| Workspace UX | **31/31** |
| Motion | **14/14** |
| State isolation | **12/12** |
| Release smoke | **10/10** |
| Evidence check | OK (800 tests · 111 rules · 42 suites · v1.3.0) |

## 9. Files changed

- `ui/theme.py` — light Arcade COLORS (source of truth)
- `webui/assets/js/theme.js` — fallback tokens mirror
- `webui/assets/css/app.css` — `:root` tokens + 79 rgba conversions + surface
  tints (nav, input heads, tables, source viewer, panels) + AA text-muted
- `webui/assets/js/viz.js` — light background topology colors
- `webui/index.html` — `color-scheme: light`, noscript colors
- `webui/assets/js/pages.js` — custom-rules textareas (na-rules, val-rules)
- `webui/assets/js/app.js` — payloads send `custom_rules`
- `docs/product/SPRINT3D_FEATURE_AUDIT.md` — audit matrices (new)
- `CHANGELOG.md` — entry

## 10. Independent review findings → fixes applied

- **`--text-muted` below WCAG AA on white** (`#8A8A8A` ≈ 3.4:1 on the smallest
  labels) → darkened to `#71717A` in all three token surfaces. ✓
- No dark-mode remnants (`prefers-color-scheme`/`.dark`/`color-scheme: dark`):
  confirmed absent. ✓
- Custom-rules wiring confirmed XSS-safe (values flow only through
  `JSON.stringify`; results render via `esc()`). ✓

## 11. Recommendation for next sprint

The **Health (readiness rail) and Clocks (graph/inventory/matrix) signature
visuals** inside this completed Arcade-style shell — the two most
product-defining result surfaces — then the **Coverage bus visualization**,
then a fresh interactive browser pass.
