# legacy/ — preserved material

> Hard rule of the migration (MIGRATION_PLAN.md): **nothing is deleted, only
> moved into `legacy/`.** This directory is where superseded surfaces and
> experiments are preserved for historical reference and provenance.

## Contents

| Path | What it is | Why it's here |
|---|---|---|
| `streamlit/app.py` | The original Streamlit application (the pre-workspace product UI) | The proven vertical slice before the `rta/workspace/` rebuild; historical reference for UX decisions. Retired from the launch path. |
| `streamlit/ui/` | The legacy Streamlit UI package (`components.py`, `feedback.py`, `tab_*.py`) | Same reason; its `components.py` CSS/helpers are still referenced by the workspace feedback dashboard (via `legacy.streamlit.ui.components`). |
| `streamlit/data/` | Feedback store used by the legacy app when run | Runtime data of the preserved app; the workspace store lives at `rta/workspace/data/feedback.json`. |

## Status

- **Not on the launch path.** The active surfaces are the CLI (`rta`), the API
  server (`rta/api/`), and the workspace (`rta/workspace/`).
- **Engine untouched.** This move was a pure `git mv` + import updates; no
  validation logic changed.
- **No dependencies from active code** (after the Phase 9 cleanup): the API
  server imports `rta.branding.tokens.theme` and
  `rta.workspace.server.feedback`; the workspace feedback dashboard imports
  `legacy.streamlit.ui.components` for shared render helpers.

## How to run the preserved app (optional)

Streamlit is an optional dependency (`pip install -e ".[web]"`):

```bash
streamlit run legacy/streamlit/app.py
```

The app bootstraps the repository root onto `sys.path` so the root compat
shims (`checker`, `generator`, ...) resolve from its legacy home.

## Deviations recorded during the Phase 9 move

- `svg/` (40 unreferenced icons), `graphify-out/` (gitignored experiment) and
  `.streamlit/` were listed in `MIGRATION_PLAN.md` §3.8 as Phase 9 targets but
  were **already absent from the tree** when the move executed — nothing to
  move. `graphify-out/` remains gitignored (`/.gitignore`).
- `ui/theme.py` was already moved to `rta/branding/tokens/theme.py` in
  Phase 1; the API server's stale `from ui import theme` was updated to the
  new home as part of this move (it had been dangling since Phase 1).
- `ui/feedback.py`'s production home is `rta/workspace/server/feedback.py`
  (same storage API); the legacy copy is preserved here for the Streamlit app.
- The legacy app's feedback writes to `legacy/streamlit/data/feedback.json`;
  active surfaces write to `rta/workspace/data/feedback.json`.
