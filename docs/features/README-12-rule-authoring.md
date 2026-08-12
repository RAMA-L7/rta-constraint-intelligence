# Feature 12: Rule-Authoring Guide (built-in SDC rules)

> **Audience:** Ṛta contributors adding a new built-in checker rule.
> **Pattern source:** Features F1 (SDC-150), F2 (SDC-151..153), F3 (SDC-154..155),
> F4 (SDC-156..157) — every rule in the 150+ range shipped through this exact recipe.
> **For YAML-based team policies** (no Python), see `README-07-custom-rules.md`.

---

## 0. The contract — read this first

Every built-in rule must satisfy the project's standing discipline:

1. **Additive-only.** Never change an existing rule's code, severity, or message;
   never modify an existing engine module another feature depends on
   (`design_context.py` is load-bearing for Checker, Coverage, and Clock
   Relations). New rules land as a **new module + a new guarded section** in
   `check_sdc` — the pattern used by every phase since Phase 8.
2. **Provable-only.** A finding fires only when the evidence is structural or
   lexical, never guessed. Anything the resolver cannot prove stays silent —
   the SDC-only ↔ design-aware split exists for exactly this reason.
3. **Noise budget.** The rule must be silent on the project's own golden corpus
   (`rta/evidence/golden/`, `valid/`, `readiness/`, `netlist_aware/`) unless a
   fixture is *deliberately* exercising the new finding. Sweep the corpus
   before shipping; alarm fatigue is a defect.
4. **Severity honesty.** `error` = provable defect; `warning` = provable risk;
   `info` = advisory. When a finding is a *methodology observation* rather than
   a defect, it is **info** by default (see F4 decision #3) — upgrading to
   warning requires domain-engineer sign-off, not architecture's call.
5. **Evidence sync.** Every rule addition changes `rule_count`; regenerate the
   manifest with `python rta/evidence/build_evidence.py` and sync the test
   counts in the docs (same drift discipline as v1.5.0).

---

## 1. The eight-step recipe

### Step 1 — write the module

Create `rta/engine/analysis/<your_rule>.py`. It must expose one entry point
returning a list of `Finding` objects (`sev`, `code`, `msg`, `line`), mirroring
the F2–F4 dataclass:

```python
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Finding:
    sev: str
    code: str
    msg: str
    line: int = 0

def your_findings(text: str, ctx=None) -> List[Finding]:
    ...
```

Reuse `preprocess_sdc` (comment-stripped, continuation-joined commands) instead
of hand-rolling a parser. Boundary-guard every name/token regex — the F3/F4
corpus lessons: `_` is a **separator**, not a word char, so `(?<![0-9A-Za-z])`
(not `(?<!\w)`) is the correct guard; temperatures (`25C`, `125C`) and voltage
fractions (`0P7V`) must never match a node/number heuristic.

### Step 2 — register the rule

Add `_r(...)` entries in `rta/engine/rules/rules_registry.py`, in a new
section header. Always pass the real `added_version`:

```python
_r("SDC-156", "info", "Flat Derate on Advanced-Node Flow",
   "<what it detects>", "<why it matters>", "<how to fix>",
   "", "checker", "1.5.6")
```

> **Watch out:** the version-bump `sed` (`s/1\.5\.X/1.5.Y/g`) clobbers
> `added_version` fields. Use a **targeted** replacement for
> `APP_VERSION` in this file, never a blanket sed (SDC-151..153 were once
> silently rewritten 1.5.4 → 1.5.5 by exactly this).

### Step 3 — wire into the checker

Add a guarded section in `check_sdc` (`rta/engine/rules/checker.py`), right
after the F3/F4 blocks. The `try/except` must never let your analysis break
the check:

```python
try:
    from your_rule import your_findings
    for f in your_findings(orig, context):
        if f.sev in ("warning", "error"):
            issues.append(Issue(f.sev, f.code, f.msg, line=f.line))
        else:
            info.append(InfoItem(f.code, f.msg))   # info-level rules
except Exception as exc:
    info.append(InfoItem("SDC-140", f"<Name> analysis skipped: {exc}"))
```

### Step 4 — ship the shim + packaging entry

Every root-level module that the checker imports (`from your_rule import ...`)
needs a **root shim** so the wheel works (`rta/engine/analysis/...` is the
implementation; the root name is the compat surface — the v1.5.2 wheel bug was
exactly a missing shim):

```python
"""Ṛta migration shim — implementation moved to rta.engine.analysis.your_rule."""
import runpy as _runpy
import sys as _sys
from rta.engine.analysis import your_rule as _impl
_sys.modules[__name__] = _impl
if __name__ == "__main__":
    _runpy.run_path(_impl.__file__, run_name="__main__")
```

Add `"your_rule"` to the `py-modules` list in `pyproject.toml` and to
`legacy/streamlit/app.py`-style import surfaces if the UI needs it.

### Step 5 — tests

Add a test class in `rta/tests/test_checker.py` (mirror `TestDerateMethodology`):
one test per trigger, per noise guard, plus:

- `test_wired_into_check_sdc` — the code surfaces through the full checker.
- `test_registry_has_sdc_XXX` — registry entry exists with right severity.
- `test_golden_corpus_silence` — the noise gate as a regression test.

### Step 6 — noise sweep (the gate)

Sweep the whole corpus before shipping:

```python
import glob
for pat in ("rta/evidence/**/*.sdc", "samples/**/*.sdc", "rta/examples/**/*.sdc"):
    for sf in glob.glob(pat, recursive=True):
        ...  # assert zero (or justified) findings
```

If your literal spec fires on fixtures the corpus declares *clean* (F3's
"only 0 → SDC-154" fired on READY fixtures; F4's keyword scan fired on
section-header comments), **the corpus wins** — tighten the trigger and record
the refinement in the plan doc.

### Step 7 — evidence sync + regression

```bash
python rta/evidence/build_evidence.py      # rule/test counts change
python -m pytest rta/tests -q              # full suite green
python smoke_test.py                       # core engine intact
python rta/evidence/run_readiness.py       # 15/15
python rta/evidence/run_golden.py          # 22/22
```

Then sync the new `test_count`/`rule_count` into the docs that quote them
(README, CONTRIBUTING, website pages, product docs — the evidence tests
`test_*_quote_manifest_counts` assert this).

### Step 8 — version, changelog, publish

- Bump to the next patch: **targeted** `APP_VERSION` in
  `rules_registry.py` + `api_server.py` fallback, `version` in `pyproject.toml`,
  then sed the remaining current-version docs (never CHANGELOG history).
- Add a `## [x.y.z]` CHANGELOG entry.
- Update the feature-plan status section and `docs/features/README-11-cli-user-guide.md`.
- To publish: `python -m build` → `twine upload dist/*` → verify from a
  **clean venv outside the repo** (the `pip install` path real users hit).

---

## 2. Worked examples (shipped)

| Feature | Rules | Module | Key refinement the corpus forced |
|---|---|---|---|
| F1 | SDC-150 (warning) | `rationale_lint.py` | exception lines need ≥10-char comments within 3 lines above or inline |
| F2 | SDC-151..153 (warning) | `async_reset_check.py` | design-aware only; fixed ≥2 reset-pin threshold; blanket-cut detection |
| F3 | SDC-154..155 (warning) | `dft_scan_check.py` | "only 0" was wrong — single-value case analysis is legit; only TOTAL absence fires; fully-blanket cuts only; chain-shape from `net_pins` only, zero touch to `design_context.py` |
| F4 | SDC-156..157 (info) | `derate_methodology.py` | keyword signals restricted to named operating conditions (header comments are documentation); underscore-as-separator boundaries; `[get_pins sigma_ctrl]` is a signal name, not a derate methodology |

Each one landed as: new module → registry → guarded checker section → root
shim → py-modules → tests → corpus sweep → evidence sync → version bump →
docs → publish. Reuse this sequence for the next rule.
