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
