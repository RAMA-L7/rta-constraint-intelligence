# Ṛta — Phase F Visual Design Foundation: Status

> **Scope:** visual design pass on the frozen Phase E workspace (the Streamlit
> tool). No engine / API / rule / calculation / feature / route / input /
> result / trust-disclosure changes. No new features. No IA changes.
> Phase E information architecture is frozen.

---

## 1. Visual changes

**Design tokens** (light + dark) — new token system in `legacy/streamlit/ui/components.py`:

- Depth: `--rta-shadow-sm / md / lg`, `--rta-focus-ring`
- Borders: `--rta-border-strong`
- Accent: refined `--rta-accent` (deeper green) + `--rta-accent-soft` halo
- `--rta-radius-sm` for inputs/controls vs `--rta-radius` for cards

**Typography hierarchy**
- Explicit `h1–h4` scale (1.9rem → 1rem), tighter leading, consistent weights
- `strong` emphasized; tabular-nums on metrics/values/code so numbers stay crisp
- Header title refined (32px/800), eyebrow letterspacing increased

**Cards / panels**
- Metric cards, home cards, issue cards, trust line, sidebar brand, expanders,
  native metrics: subtle resting shadow → hover elevation (`translateY(-2px)`)
  — depth, not decoration
- Issue cards: source line now right-aligned mono; hover border/shadow lift
- Home catalog: white cards with shadow + hover accent border/elevation

**Status indicators**
- Banners keep flat tints; icon gets a small chip; banners get a quiet shadow

**Buttons**
- Primary: solid ink, shadow, hover lift, active press, `:focus-visible` ring
- Secondary / download: defined border + hover, focus ring

**Navigation / command bar**
- Tabs restyled as a bordered segmented pill rail; active tab = raised card
  (crisper than the old underline-only state)
- Header nav links become quiet pill buttons (hover = border+fill)

**Input surfaces** (native Streamlit widgets)
- Text areas/inputs: mono font, focus ring on accent, placeholder muted
- Selectbox / number input: bordered, focus-within accent ring
- File uploader: dashed dropzone, accent hover

**Result surfaces**
- Tables: uppercase mini headers, hover row highlight
- DataFrames: bordered, rounded
- Native metrics: shadow + tabular value

**Responsive readability**
- Tab rail scrolls horizontally instead of wrapping/clipping; cards keep the
  full contract; no text shrinks below readable sizes

---

## 2. Files changed

| File | Change |
|---|---|
| `legacy/streamlit/ui/components.py` | Design token system, typography, cards/panels/buttons/tabs/header, input + result surface styling, dark-mode parity (35 new token references) |
| `rta/tests/test_regressions.py` | `test_cli_web_resolves_app_path` → `test_cli_web_retired_contract` (matches the intentional `rta web` retirement from the earlier workspace decision) |
| `rta/evidence/manifest/RELEASE_EVIDENCE.json` | Regenerated via `build_evidence.py` (test_count 886 → 887 — live truth; drift was pre-existing) |
| `README.md`, `CONTRIBUTING.md`, `rta/website/{index,benchmarks,release,trust}.html`, `rta/docs/product/*`, `rta/docs/rta/BENCHMARK_EVIDENCE_MAP.md` | Stale 886 count → 887 to match the regenerated manifest (project convention: surfaces quote the manifest) |

**Unchanged:** engine, API, rules, calculations, feature behavior, routes,
input requirements, backend results, trust disclosures, IA.

---

## 3. Tests

| Suite | Result |
|---|---|
| Full pytest (`rta/tests/`) | **887 passed** (was 885 passed / 2 pre-existing failures — evidence count drift + retired `rta web` contract; both corrected) |

---

## 4. Browser result

Live server at `http://localhost:8502` — health `ok`, **zero app errors / no
console errors** in the server log.

AppTest smoke across the required surfaces (all **zero exceptions**):

- **Catalog / home** — hero, CTAs, 18 cards render
- **Validate** (tab 0) — renders, own input surface
- **Clocks** (tab 7) — renders
- **Coverage** (tab 8) — renders
- **Generator** (tab 1) — renders
- **Test Drive** — full analysis run: Checker/Coverage/Clock/Errors/Warnings
  sections + 4 metric tiles, real backend results

(Headless-screenshot pixel checks are limited by Streamlit's websocket render;
AppTest + live-server log are the authoritative verification.)

---

## 5b. Layout changes (follow-up request)

A follow-up asked for a **layout** change across the whole app, the
header/sidebar, and feature pages. Done on top of the Phase F design system:

**Whole-app layout**
- Content area widened 1180px → 1280px for dense engineering tables
- Home catalog grid densified from 2-per-row → **3-per-row** product grid

**Header / sidebar layout**
- Header is now a **compact command bar**: brand block (eyebrow + title +
  version badge inline) on the left, business-site nav right-aligned; tagline
  moved to its own quiet line below
- Sidebar is now a **capability navigation rail**: brand card, Home button,
  then three grouped nav sections (Analysis capabilities / Engineering
  tools / Output & Knowledge) with one entry per capability — each jumps to
  the matching tab/view or opens the business page (no dead entries)
- Rail nav labels mirror the business-site feature names

**Feature-page layout**
- Tabs keep the two-column input pattern (upload | paste) where it exists;
  consistent vertical rhythm between input, primary action, and results
- Inputs (uploader / textarea / textinput) and expanders get uniform spacing
  inside each tab; result sections breathe below the primary action

Verified: sidebar rail navigation across all groups (tabs 0/1/4/6/7/8/10/11
+ Test Drive view) — zero exceptions; home hero + rail + cards all render;
887 tests still pass; live server healthy with no console errors.

---

## 6. Follow-up fixes (layout + dark mode)

After user review of the Phase F pass, the following defects were fixed and
verified in a real browser (Selenium + computed styles + screenshots):

1. **Dark mode covered only the sidebar/cards — the main app stayed white.**
   Root cause: `st.html(unsafe_allow_javascript=True)` never executes its
   script in Streamlit 1.56 (DOMPurify strips `<script>` before mount — the
   `stHtml` element was empty, `window.__rtaSidebarOnce` never set). Switched
   the toggle to `st.components.v1.html`, whose component iframe sandbox
   includes `allow-same-origin`, so the script reaches `window.parent.document`
   and reliably sets/removes `data-theme`. Added `html[data-theme="dark"]`
   overrides for the native app surface (`.stApp` / `stAppViewContainer` /
   `body` → `#0c0c0d`), native widget labels, expander/code/alert text, and
   default + sidebar buttons, so the whole app is dark — not dark cards on a
   white page.

2. **Dark toggle could not return to light.** The script now always runs
   (set *or* remove `data-theme`) instead of only when dark, so toggling off
   clears the attribute.

3. **Sidebar not auto-hiding.** `initial_sidebar_state="collapsed"` only
   applies on first load (browser persists the expanded state). Added a
   one-shot script that clicks `stSidebarCollapseButton` on page load when
   `aria-expanded="true"` (guarded by `window.__rtaSidebarOnce` so it never
   fights the user after they open it). Verified collapsed on fresh load.

4. **Feature cards misaligned / different sizes.** Two bugs: the catalog
   rendered masonry-style (`cols[i % 3]` cycles cards into fixed columns
   instead of rows), and the equal-height CSS never reached the card through
   Streamlit's wrapper chain. Fixed `view_home.py` to chunk cards row-major
   (3 per row) and added scoped `:has(.home-card)` flex rules (with
   `min-height: 0`) covering every wrapper between column and card so cards in
   a row are equal height and the "Open →" buttons align.

Verified: sidebar auto-collapsed, whole-app dark (`rgb(12,12,13)`),
light restores (`rgb(255,255,255)`), all card rows equal-height + buttons
aligned (≤2px), 0 console errors, and the full pytest suite green
(**1230 passed** — evidence manifest regenerated 887 → 889 and doc surfaces
synced).

## 5c. Targeted catalog visual refinement (follow-up request)

A follow-up asked to make the catalog/home feel like a premium engineering
product rather than a documentation prototype — a visual-hierarchy and
information-density refinement only (`view_home.py` + `components.py`).

**Capability cards — lower density, product-tool feel**
- Cards now show: monogram tile + title, one-line purpose, input chips, and a
  **Details disclosure** (progressive disclosure — "What it does · What you
  get · Next steps" in a native `<details>` element). The dense four-line
  Does/Get/Next block is no longer the first thing you see.
- Input requirements rendered as quiet **chips** (split on "·") instead of a
  bold "Input:" line.
- Emoji icons replaced with **consistent monogram tiles** (2-letter codes:
  SD / CK / DX / CV / IX / RD / CI / GN / LN / CN / DF / MM / RU / TD / RP /
  TR / DO / FB) — one professional technical treatment across all 18 cards.

**Visual hierarchy**
- Hero upgraded: accent pip + uppercase eyebrow ("Ṛta Engineering Platform"),
  larger title (30px/800), wider positioning line — platform entrance, not a
  docs page.
- Group labels now carry a quiet **count pill** (e.g. "Analysis capabilities
  7") for scannability.
- Trust line: accent left rule added, slight padding increase.

**Sidebar de-emphasis**
- Sidebar narrowed to **264px** (product area is the focus).
- Brand block is now a plain compact wordmark (no card background), What's
  New condensed to short bullets, sidebar buttons/emoji trimmed.

**Verified (real browser, Selenium + computed styles)**
- 18 cards + 18 monogram tiles + 18 Details disclosures render
- Row 1 cards equal-height and aligned: tops 558/558/558, bottoms
  749/749/749, "Open →" buttons 797/797/797 (≤1px)
- Sidebar width 264px; hero renders
- Dark mode: whole-app `rgb(12,12,13)`; light restores `rgb(255,255,255)`
- Tile treatment verified (`rgb(236,253,243)` accent-soft)
- **0 console errors**; catalog → Validate / Clock navigation works (AppTest,
  zero exceptions)
- Full pytest suite green (**1228 passed**; manifest 887 — temp verification
  files removed so the branding parametrized scan is back to the stable count)

## 5d. Final visual polish (follow-up request)

A follow-up asked for the last premium pass on the catalog/home only —
stronger value proposition, obvious four-group hierarchy, product-tool cards,
and a quieter sidebar. Functional/IA/backend untouched
(`view_home.py` + `components.py` only).

**Product hierarchy — canonical four groups** (`view_home.py`)
- Catalog regrouped to the Phase E canonical order:
  **CORE** (Validate · Generator · Linter · Converter), **ANALYZE** (Clock ·
  Coverage · Design Context · Interactions · Readiness · Diff), **ADVANCED**
  (Corners/MMC · Test Drive · Rules · CI), **OUTPUT & KNOWLEDGE** (Reports ·
  Trust · Documentation · Feedback).
- Group headers now render with a quiet hairline rule + count pill (e.g.
  `CORE 4`), so the four-group hierarchy reads at a glance.

**Hero — clearer value proposition, less dead space**
- Headline changed from a question to the engineering value prop:
  *"Constraint intelligence for block-level design."* with a tighter
  sub-line (119 rules · no LLM · know what's wrong/missing/covered before STA).
- Vertical padding reduced (hero `10px` → `2px` top, group margin `34px` →
  `24px`), so the capability grid appears sooner.
- CTA row de-emoji'd and differentiated: **Validate an SDC** (primary) +
  **Start with Test Drive** (secondary) + quiet caption.

**Cards — selectable engineering tools** (`components.py`)
- Hover now picks up the **Ṛta green**: accent-tinted border + lift, and the
  monogram tile deepens its accent border (light + dark variants).
- Tile gets a subtle inner top highlight (premium depth, flat base).
- **Open actions styled as tool launchers**: outline buttons that fill with
  the accent-soft green and turn green on hover (light + dark), matching the
  tile/details accent language.
- Details disclosure summary shortened to **"More details"** — the first
  view is scannable; Does/Get/Next stay one click away.

**Subtle premium depth**
- App surface gets a faint **green radial wash behind the header area** only
  (two soft tints, ~5% opacity — never behind result surfaces), with a dark
  counterpart. No glow, no blur, no gradients elsewhere.

**Sidebar de-emphasis**
- Width narrowed `264px` → `250px`; content unchanged.

**Verified (real browser, Selenium + computed styles)**
- Group labels render: `CORE 4 / ANALYZE 6 / ADVANCED 4 / OUTPUT & KNOWLEDGE 4`
- 18 cards; CTA labels clean (no emoji); hero value prop present
- Row-1 cards pixel-aligned: tops 536.7/536.7/536.7, bottoms
  727.7/727.7/727.7, Open buttons 735.7/735.7/735.7
- Dark mode: app `rgb(12,12,13)`, tiles `rgb(74,222,128)`; light restores
  `rgb(255,255,255)`
- **0 console errors**; catalog → Validate navigation works (AppTest,
  zero exceptions)
- Full pytest suite green (**1228 passed**; manifest 887 — temp verification
  files removed so the branding parametrized scan stays at the stable count)

## 5e. Final catalog polish (follow-up request)

Two refinements only — the approved CORE / ANALYZE / ADVANCED / OUTPUT &
KNOWLEDGE hierarchy is untouched (`components.py` only; no group/name/
description/route/input changes).

**1. Card + Open action = one cohesive tool card**
- The "Open … →" action is now the **card's footer**: flush under the card
  (0.1px gap), full card width, shared side outline, card's bottom border
  acting as the separator hairline, `border-radius` only on the footer's
  bottom corners.
- **Joint hover state** (CSS `:has`): hovering the card lights up its footer
  button (green + accent-soft fill), and hovering the footer button lights
  up the card border — the unit reacts as one interactive tool card.
- Root cause of the old gap: Streamlit's default 16px flex `gap` between the
  card element and the button element; set to `0` for catalog columns.

**2. Quieter sidebar**
- Width `250px` → **236px**; background blends with the app (`--rta-bg` /
  `#0c0c0d` in dark, hairline border only); brand title 17px → 16px;
  sidebar buttons 13px/6px → 12.5px/5px.

**Verified (real browser, Selenium + computed styles)**
- 18 cards; card-bottom → button-top gap **0.1px**, button width == card width
- Card hover → button green (`rgba(21,128,61,1)`) + accent-soft fill;
  button hover → card border green (`rgba(21,128,61,0.35)`)
- Sidebar 236px; dark app `rgb(12,12,13)`; **0 console errors**
- Full pytest suite green (**1228 passed**; manifest 887 — temp verification
  files removed)

## 5f. Final Open-button footer fix (follow-up request)

A follow-up reported the footer actions, though attached, still read as
separate buttons and made lower rows look uneven. Fixed the visual treatment
only (`components.py`; no names / descriptions / grouping / routes / inputs /
sidebar / hero / backend / IA changes).

**One continuous outline (no double border / gap)**
- Card: `border-bottom: none`, `border-radius: 14px 14px 0 0`, card shadow
  removed. Footer: `border-top: none`, `border-radius: 0 0 14px 14px`,
  depth moved to a soft bottom shadow on the footer. The unit now has a
  single shared outline with an invisible seam (background change only) —
  verified `0px / 0px` borders at the seam and a 0.06px gap.

**Consistent footer height across ALL cards**
- Root cause: `st.link_button` renders an `<a>` (URL cards: CI / Reports /
  Trust / Documentation) while tab cards render `<button>`; the styling
  targeted the `.stLinkButton` wrapper so links kept Streamlit defaults
  (40px vs 47px). Now both `.stButton > button` and `.stLinkButton a` get
  the identical box — verified **one height, 44px, across all 18 cards**.

**Per-row vertical alignment**
- Flex chain unchanged; verified every row's footers sit at the same Y
  (footer bottoms aligned across Core / Analyze / Advanced / Output rows).

**Joint hover lifts the WHOLE unit**
- Old bug: only the card lifted on hover (`translateY(-2px)`), opening a gap
  below it. Now the footer wrapper lifts with the card — verified card and
  footer both shift exactly −2px and the seam stays closed.
- Hover anywhere lights both: card → footer green; footer → card border green
  (light + dark).

**Quieter action zone, accessible focus**
- Neutral panel surface + border at rest (no heavy fill); subtle Ṛta green
  on hover; `:focus-visible` outline (2px accent + soft ring, light + dark).
  Action text stays centered (flex centering).

**Responsive**
- Desktop 3-column unchanged; narrow viewport verified: cards stack 1-up at
  x=16, footers attached (−0.1px), no horizontal overflow.

**Verified (real browser, Selenium + computed styles)**
- 18 cards; seam 0px/0px; footer heights `{44}` uniform; per-row Y aligned;
  joint lift −2/−2; footer-hover card border green; focus outline 3px;
  dark app `rgb(12,12,13)`; **0 console errors**
- Full pytest suite green (**1228 passed**; manifest 887 — temp verification
  files removed)

## 5. Remaining visual issues

- Headless-Chrome full-page screenshots can catch Streamlit mid-render; no app
  defect — visual confirmation is best done interactively in a browser.
- Dark-mode input/select/file-uploader overrides are in place but best
  eyeballed interactively in the dark theme toggle.
- The 12-tab rail is intentionally more compact (segmented pills); on very
  narrow viewports it scrolls horizontally — acceptable per the responsive
  priority (task → result → action → detail).

---

## STOP condition met

- No business-website redesign, no animations, no new functionality.
- Phase E IA frozen; every capability still visible; no More Tools /
  Quick Actions / global Import / Settings reintroduced.
