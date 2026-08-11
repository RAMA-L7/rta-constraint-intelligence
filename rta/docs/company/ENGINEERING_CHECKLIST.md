# Engineering Checklist — Merge Readiness

> Every PR that touches code, CI, packaging, or product surfaces must satisfy this checklist before merge. The reviewer verifies each item. Items marked **[engine]** apply only to changes touching the deterministic analysis pipeline.

---

## Pre-Merge Checklist

### Correctness

- [ ] **All tests pass.** `python -m pytest tests/ -q` produces zero failures.
- [ ] **No regressions in golden suites.** Run the relevant `run_*.py` runner(s) for changed modules and confirm green.
- [ ] **[engine] Full regression passes.** All golden runners, benchmark suites, and release smoke produce green.
- [ ] **Determinism preserved.** [engine] Identical input produces identical output. No floating-point, timing-dependent, or OS-dependent behavior introduced.
- [ ] **Edge cases covered.** The happy path, at least one boundary/edge case, and at least one error/unsupported condition are tested.

### Trust

- [ ] **Trust boundary documented.** If the change introduces or modifies a capability's trust level, the trust disclosure is updated in the relevant docs and surface.
- [ ] **No overclaim.** The PR does not describe the tool as "smart," "AI-powered," "guaranteed," or "signoff-ready."
- [ ] **[engine] Engine failure guarantee preserved.** An engine failure still never produces a passing result (exit code 3 contract).

### Evidence

- [ ] **Evidence numbers verified.** If the change affects any count displayed on the website, README, workspace, or reports (test count, rule count, benchmark counts), the numbers are re-verified and updated.
- [ ] **No stale claims.** The PR does not change a number without re-running the artifact that produced it.

### Code Quality

- [ ] **Code is readable.** Functions have docstrings. Public APIs have type hints.
- [ ] **Code follows project style.** PEP 8 (Python), consistent formatting (JS/HTML).
- [ ] **No dead code.** Removed code is actually removed, not commented out.
- [ ] **No hardcoded values.** Magic numbers have a comment explaining why. Configuration lives in the appropriate registry or config file.

### Naming

- [ ] **Brand identity correct.** User-facing surfaces use `Ṛta` (with dot below). CLI references use `rta` (ASCII). `sdc-tools` only appears as the documented alias.
- [ ] **SDC standard vocabulary preserved.** SDC commands, rule codes, and standard terminology are not renamed.
- [ ] **Module names are descriptive.** New Python modules are named after what they do, not the brand.

### Documentation

- [ ] **README updated.** If the change affects user-facing behavior, CLI, or capabilities, the README is updated.
- [ ] **CHANGELOG updated.** User-facing changes get a CHANGELOG entry.
- [ ] **Feature docs updated.** If the change affects `docs/features/`, those pages are updated.
- [ ] **[engine] ADR recorded.** Architecture changes to the engine are recorded in `docs/company/ADR_*.md`.

### Packaging

- [ ] **py-modules list updated.** [engine] If a new top-level `.py` module is added, it is added to `py-modules` in `pyproject.toml`. Omitting this crashes the wheel.
- [ ] **Package data updated.** If new static files are added to `webui/` or `site/`, the `package-data` or `include` config reflects them.
- [ ] **Clean-room feasible.** The change does not break `release_cleanroom.py` (wheel builds, installs, serves from any cwd).

### CI

- [ ] **CI passes on the PR.** The GitHub Actions workflow runs green.
- [ ] **CI lint is current.** If a new module is added, `py_compile` in CI includes it (or a comment explains why it is excluded).

### Security

- [ ] **No unescaped user content in HTML/SVG.** Every value that originates from user input (SDC text, object names, clock names, netlist identifiers) is escaped before rendering.
- [ ] **No network calls in analysis path.** The analysis engine makes no network requests.
- [ ] **No new external dependencies** in the core engine without an ADR.

---

## Post-Merge Checklist

- [ ] **CI remains green on main.** No post-merge failures.
- [ ] **Website is visually inspected.** If the change affects the website, the live site is locally verified.
- [ ] **Workspace is visually inspected.** If the change affects the workspace, the workspace is locally verified.
- [ ] **Evidence numbers are current.** Any claim on the website matches the current artifact counts.

---

## Release Checklist

Before a release, all of the above are verified, plus:

- [ ] **All golden runners pass.** Every `run_*.py` in `benchmarks/` produces green.
- [ ] **All benchmark suites pass.** Every `test_*.py` in `benchmarks/` produces green.
- [ ] **Release smoke passes.** `test_release_smoke.py` passes.
- [ ] **CLI contract audit passes.** `release_cli_audit.py` passes.
- [ ] **Clean-room wheel journey passes.** `release_cleanroom.py` passes.
- [ ] **Evidence numbers re-verified on release branch.** Website, README, and release page match.
- [ ] **Known limitations documented.** The release page states known limitations with no understatement.
- [ ] **Version bump complete.** `pyproject.toml`, `rules_registry.APP_VERSION`, and all surfaces reflect the version.
- [ ] **CHANGELOG entry complete.** All user-facing changes are documented.

---

*This checklist is a living document. Update it when a new quality gate is established.*
