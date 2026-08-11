# PHASE 13 — PRODUCTION HARDENING REPORT

**Structured Finding Identity · Declarative Policy Engine · Snapshot v2 · CI Integration · Diff UX**

Date: 2026-08-06 · Validator version: 1.3.0 · Deterministic Python SDC validator — **no AI in the runtime product layer.**

---

## 1. Graph Execution Summary

Executed as a development graph with evidence-producing nodes and gates, not independent parallel agents:

| Node | Artifact produced | Gate result |
|------|-------------------|-------------|
| BASELINE | pytest 602/602 + all 24 prior suites green | PASS |
| RESEARCH — identity audit | Finding-identity weakness matrix (§4) | PASS |
| RESEARCH — policy/snapshot/fingerprint | Design decisions (§11, §16, §13) | PASS |
| DESIGN GATE | Architecture: structured `FindingIdentity` + dual key space + frozen legacy keys + inert policy engine | PASS |
| IMPLEMENTATION | `finding_identity.py`, `policy_engine.py`, `readiness_diff.py` v2, CLI/reporter/app wiring | PASS (smoke) |
| ADVERSARIAL | PH13-23/24, `test_ph13_adversarial.py`, `test_readiness_diff_adversarial.py` (clock-rename contract update) | PASS |
| SECURITY | `test_ph13_security.py` (30 checks) | PASS |
| PERFORMANCE | `test_ph13_perf.py` (7 checks) | PASS |
| INDEPENDENT REVIEW | 1 medium + 4 low findings (§37) | PASS after fixes |
| FULL REGRESSION | pytest 689/689, 9 golden runners, 28 benchmark suites | PASS |
| RELEASE GATE | All 16 release criteria verified | PASS |

**Failure-routing events:** the independent review found a real v1→v2 migration key-drift hazard → routed to the identity/architecture owner → frozen the legacy normalization + added a regression test that pins the exact Phase 12 regex behavior.

---

## 2. Baseline

Recorded before any Phase 13 production changes:

- pytest: **602/602**
- Parser golden 22/22 · Semantic golden 9/9 · Reference designs 8/8 · Design coverage 12/12
- Netlist-aware 10/10 · Constraint interactions 20/20 · Readiness 15/15 · Readiness diff 22/22
- CI gate suite PASS · Diff adversarial/metamorphic/confidence/perf PASS
- UI 35/35 · State isolation 6/6 · Security 5/5 · Stress 21/21
- Diff performance: 10k findings ≈ 43–75 ms

Final (post-Phase-13): **pytest 689/689** (+87 new tests), all prior suites green, PH13 golden 49/49.

---

## 3. Phase 12 Architecture Audit

Phase 12 identified findings as `(rule, severity, normalized message)` via `normalize_msg()`. The audit produced this **identity weakness matrix** — every row shows how the old identity could fail:

| Change | Message-based identity result | Phase 13 structured result |
|--------|------------------------------|----------------------------|
| Explanation reworded | RESOLVED + NEW (false regression) | UNCHANGED |
| Punctuation/whitespace change | RESOLVED + NEW | UNCHANGED |
| Severity changed | RESOLVED + NEW | CHANGED |
| Line numbers moved | line stripped → UNCHANGED (fragile) | UNCHANGED (identity is line-free by construction) |
| Object presentation changed | RESOLVED + NEW | UNCHANGED |
| Numeric formatting (2.0 vs 2.000) | UNCHANGED (normalized) | UNCHANGED (canonicalized) |
| Bus range changed | may collapse (both ranges blanked) | DIFFERENT (ranges are object identity) |
| Clock renamed | UNCHANGED when message is clock-agnostic | DIFFERENT (clock is a semantic field — collision rule) |

Conclusion: message text was entangled with identity. Phase 13 separates **IDENTITY / PRESENTATION / PROVENANCE** (§5).

---

## 4. Finding-Identity Weakness Matrix

See §3. The definitive failure mode fixed in Phase 13: **rewording a human explanation could silently turn UNCHANGED into RESOLVED+NEW.** The permanent invariant test (`PH13-01`, `test_finding_identity.py::TestMessageIndependence`) proves it cannot.

---

## 5. Structured FindingIdentity Model

`finding_identity.py` — `FindingIdentity` with fields:

```
identity_version, rule_id, finding_type, command,
primary_object, secondary_object, clock, value,
mode, edge, setup_hold, interaction_type,
endpoint_signature, strength, context
```

- **IDENTITY** = the 14 semantic fields above (value-insensitive `base_key` + value/severity-sensitive `full_key`).
- **PRESENTATION** = the message (truncated to 240 chars in snapshots; never part of identity).
- **PROVENANCE** = line/line2 (presentation only, never identity).

Extraction is pure regex over the SDC command text (or the Phase 10 `ConstraintRecord` for interactions) — deterministic, bounded, no execution.

**Identity strength (never fake certainty):**
- `STRUCTURED` — command-/record-derived. Rewording can never change it.
- `LEGACY_NORMALIZED` — message-derived fallback, honestly labeled (never called structured). Used only for synthesized SCOPE-* and design-aware findings without command provenance.

---

## 6. Identity Versioning

`IDENTITY_VERSION = 1`, independent of `SCHEMA_VERSION = 2`.

They answer different questions: identity version = "did the **semantic** identity contract change?" (new fields, different canonicalization); schema version = "did the **stored shape** change?" A reworded message bumps neither; adding an identity field bumps identity only; restructuring the snapshot JSON bumps schema only.

---

## 7. Rule-Family Identity Strategy

A shared `_RULE_FAMILY` map assigns each rule a `finding_type` (CLOCK_DEFINITION, CLOCK_REFERENCE, IO_DELAY, EXCEPTION, ELECTRICAL, CASE_ANALYSIS, DESIGN_OBJECT, CONSTRAINT_INTERACTION, ANALYSIS_SCOPE, RULE). One shared `extract_command_fields()` + `identity_from_commands()` handles all families — **no per-rule parsers**. SDC-002/046/047/048 (clock/ref), SDC-055–066 (design-aware), SDC-049 (case analysis), SDC-067–070 (interactions) are all covered by the shared model. Unlisted rules fall back to `FT_RULE` (command name still discriminates).

---

## 8. Dual-Constraint Identity

For SDC-049 / SDC-067 / SDC-068 / SDC-069 / SDC-070 (two-command findings):

- **Symmetric relationships** (duplicates, conflicts, case-analysis contradictions): pair ordering is **canonicalized** — `identity_from_commands(A, B)` ≡ `identity_from_commands(B, A)`. Values are sorted. Line numbers never determine ordering.
- **Order-sensitive OVERRIDE (SDC-068)**: direction is **preserved** — the caller passes earlier→later; value order (`"2;4"` ≠ `"4;2"`) carries the direction. A reviewer-found bug where the value fallback re-sorted even order-sensitive pairs was fixed (`test_override_preserves_direction`).

---

## 9. Legacy Identity Fallback

`identity_legacy()` produces `LEGACY_NORMALIZED` identities with **frozen** Phase 12 normalization (whitespace collapse, line-ref strip, numeric canonicalization, bit-select preservation). The normalization is deliberately frozen (§37 finding 1): legacy keys must stay byte-identical to what a real v1 baseline stored, or v1↔v2 migration produces false NEW+RESOLVED. A regression test pins the exact Phase 12 regex behavior.

---

## 10. Severity-Change Semantics

Severity is part of the **full key** but excluded from the **value-insensitive base key**:

- Same finding, WARNING→ERROR ⇒ full keys differ, base keys match ⇒ **CHANGED** (never RESOLVED+NEW).
- `_multiset_delta` step 4 pairs base-key candidates as CHANGED.
- Readiness/gate logic then decides whether the severity change is a regression (e.g., a new ERROR tier maps to BLOCKED).

---

## 11. Snapshot Schema v2 Decision

**Adopted (schema v2)**. Phase 13 materially requires it. Additions over v1:

- `identity_version`, per-finding `identity` dict + `identity_strength`
- `capabilities` metadata (structured_identity, fingerprint_version, design_aware, interactions, coverage, readiness, readiness_diff, custom_policies)
- `migration` metadata (NATIVE / MIGRATED / INCOMPATIBLE)
- `analysis.design_fingerprint` + `fingerprint_version`
- **`legacy_full_id` / `legacy_base_id` on every finding** — the legacy key space is stored alongside the structured key so a v1 baseline can be compared in the same key space.

**V1 compatibility (§12):** v1 snapshots remain loadable (`ACCEPTED_SCHEMA_VERSIONS = (1, 2)`). v1 baseline + v2 current ⇒ `PARTIALLY_COMPARABLE` via **legacy normalized comparison on both sides** — never a silent structured claim. Never fabricated structured identity. Never rewritten on disk.

---

## 12. V1 Compatibility / Migration

- `snapshot_migration_status()`: NATIVE (v2), MIGRATED (v1), INCOMPATIBLE (unknown).
- `load_snapshot()` accepts v1; `diff_snapshots()` detects `legacy_only` and compares on legacy keys for **both** sides.
- Tests: `test_v1_snapshot_loads`, `test_v1_vs_v2_is_partially_comparable`, `test_v1_vs_v2_identical_evidence_no_regression`, `test_v1_legacy_comparison_ignores_formatting` (PH13-07) — including a downgrade helper that simulates a **real** Phase 12 v1 shape (legacy keys in `full_id`, no identity fields).

---

## 13. Design Fingerprint v2

`design_fingerprint(context)` — SHA-256 of a **structural** payload: top module, sorted module set, sorted port entries (`name:direction[:msb:lsb]`), sorted instance entries (`path:module`), sorted net names, sorted connectivity counts. Never raw source text.

---

## 14. Fingerprint Stability

Proven (PH13-09/10/11 + `test_snapshot_v2.py::TestFingerprint`):

| Change | Fingerprint |
|--------|-------------|
| Comments / whitespace / reformat | same |
| Module order / instance order in netlist | same (sorted at join; instance-order fix applied) |
| Added/removed port | different |
| Bus width change | different |
| Hierarchy change | different |
| Top-module change | different |

---

## 15. Fingerprint Performance

100k-object synthetic design (50k ports + 50k instances + 50k nets): fingerprint ≈ **0.9 s**, well under the 10 s budget. Parse dominates; the fingerprint itself is a single sorted-join + hash.

---

## 16. Policy-Engine Architecture

`policy_engine.py` — a **declarative, inert** policy surface for the `CUSTOM` gate.

- Policies are **data** (JSON or YAML via `yaml.safe_load`), never code: no eval/exec/imports/shell/templates/callbacks.
- Schema (version 1): `policy: CUSTOM`, `policy_version`, `name`, `fail_on` (`current_blocked`, `new_blockers`, `new_review_items`, `trust_regression`, `coverage_regression`, `engine_failure`), `allow.new_advisories`, `thresholds.max_new_review_items`, `fail_on_new_rules[]`.
- A policy **selects which existing diff evidence fails the gate** — it can never change what the validator detects.
- Built-ins (BLOCKERS_ONLY / NO_READINESS_REGRESSION / STRICT) are expressed in the **same declarative schema** (`_builtin_policy`), so their Phase 12 semantics are preserved by construction and regression-tested.

---

## 17. Built-In Policy Compatibility

`test_policy_engine.py::TestValidation::test_builtin_policies_validate_clean` + `benchmarks/test_ph13_ci_workflow.py` verify BLOCKERS_ONLY / NO_READINESS_REGRESSION / STRICT behave identically to Phase 12 (clean → PASS, blocked/new-blocker → FAIL, exit-code contract).

---

## 18. CUSTOM Policy Schema

```yaml
policy: CUSTOM
policy_version: 1
name: legacy-project
fail_on:
  current_blocked: false      # pre-existing blockers are debt, not regressions
  new_blockers: true          # NEW deterministic blocker vs baseline → fail
  new_review_items: false
  trust_regression: false
  coverage_regression: false
  engine_failure: true        # ALWAYS effective — cannot be disabled
allow:
  new_advisories: true
thresholds:
  max_new_review_items: 2     # soft cap when new_review_items is disabled
fail_on_new_rules: ["SDC-069"]  # optional rule-specific gate
```

Working examples ship in `policy_examples/` (`legacy_project.yml`, `mature_project.yml`, `strict_handoff.yml`) — validated in `test_ph13_ci_workflow.py` and the golden suite.

---

## 19. Policy Validation

Rejects safely (exit code 2 via `fatal(..., code=2)`):
- unknown fields (top-level, `fail_on.*`, `allow.*`, `thresholds.*`)
- wrong types (non-boolean flags, non-int thresholds)
- invalid `policy` value (must be CUSTOM), unsupported `policy_version`
- negative thresholds, threshold-type errors
- invalid / unknown rule IDs in `fail_on_new_rules` (validated against the registry + SCOPE-* family; regex accepts SDC-069, CHG-CK-001, SCOPE-UNSUPPORTED shapes)
- oversized inputs (256 KB file cap + **4 MB expanded-structure cap** — see §37 finding 2)
- malformed JSON/YAML

---

## 20. Policy Security

- **Inert by construction**: `yaml.safe_load` only, schema-only interpretation, no callbacks.
- Hostile values (`x; rm -rf /`, `__import__('os').system('id')`, `{{ 7*7 }}`) load as plain strings or are rejected — never executed (`test_ph13_security.py`, 30 checks).
- **YAML alias expansion bounded**: a 4 MB expanded-structure cap after parse defends against billion-laughs style policies; input-size cap alone cannot.
- Security tests cover malformed JSON, deep nesting, wrong enums/types, negative counts, duplicate entries, unknown schema, non-object findings — all fail safely (None + errors), never crash, never execute.

---

## 21. Baseline Debt Model

`diff["debt"] = {existing, new_debt, resolved_debt}` with buckets `{blockers, review, advisories, coverage, trust}`.

- **Existing debt** = pre-existing known evidence in the baseline. Never re-labeled as new; never fails a regression gate by itself.
- **New debt** = added findings. A new deterministic blocker **always** fails `new_blockers` policies (baseline can never hide a new blocker).
- **Resolved debt** = removed findings (visible as improvement).

Proven: PH13-21 (existing debt unchanged → PASS, debt visible), PH13-22 (resolved debt → IMPROVEMENT + PASS), CLI `test_existing_debt_visible_in_output`.

---

## 22. CI Output

```
Constraint Readiness: BLOCKED
Blockers:
- SDC-046 line 6 ↔ 2 ...
Review:
- SDC-070 ...
Analysis mode: SDC-only
Readiness diff: READY → BLOCKED (REGRESSION, classification: BLOCKING_REGRESSION)
  gate [NO_READINESS_REGRESSION]: FAIL (exit 1)
```

Concise text output (`_render_readiness_diff`); full evidence in JSON. Debt summary line: `existing=1B/0R/0A new=1B/0R/0A resolved=0B/0R/0A`.

---

## 23. Generic CI Integration

The core is vendor-independent: the **CLI is the integration boundary** (`sdc-tools check --save-baseline / --baseline / --gate / --gate-policy`). Works in GitHub Actions, GitLab CI, Jenkins, Buildkite, or local scripts. No GitHub-specific logic in the engine.

---

## 24. GitHub Actions Example

`.github/workflows/sdc-readiness.yml.example` demonstrates: checkout → Python setup → install → current analysis with `--netlist` → baseline comparison → `--gate` (exit-code contract drives CI success/failure) → JSON artifact (`--json --output`) + HTML report (`report check --output`) → artifact preservation. Never auto-commits baselines.

---

## 25. Baseline Update Workflow

Documented (report §25 + workflow comments + CLI tests `wf-baseline-regen`):

```
Developer modifies SDC/netlist
   ↓
CI compares against committed baseline (--baseline --gate)
   ↓
Engineer reviews semantic delta (readiness_diff JSON / report)
   ↓
Change approved
   ↓
Engineer intentionally regenerates baseline (--save-baseline)
   ↓
Updated baseline committed
```

No automatic baseline acceptance. A regenerated baseline keeps the schema + identity version; gate passes on the regenerated baseline.

---

## 26. Diff UX Improvements

`app.py` readiness-diff expander now shows:

- **Debt metrics**: Existing / New / Resolved debt (blk·rev) + advisory delta row.
- **Identity disclosure**: `identity v1 · 7/9 findings carry structured identity (message-independent)`, baseline-vs-current identity version note, migration status (`baseline migrated (MIGRATED)`).
- **NEW/RESOLVED/CHANGED filter** (`st.radio`) applied to the delta lists; provenance (line numbers) labeled presentation-only.
- Compatibility reasons, coverage/trust regressions, and the CI-gate verdict unchanged (plus a "CI PASS ≠ timing pass" disclaimer).

`reporter.py` HTML diff section also surfaces debt, identity strength, and CHANGED findings.

---

## 27. JSON/API Contract

Stable machine-readable contracts (documented in module docstrings):

- **Snapshot**: `{schema_version, identity_version, tool_version, capabilities, analysis{...}, readiness{...}, findings[] (full_id, base_id, legacy_full_id, legacy_base_id, identity, identity_strength, tier), coverage, scope, interactions, migration}`
- **FindingIdentity**: the 14-field dict (§5).
- **readiness diff**: `{compatibility{status,reasons,legacy_normalized,migration}, engine_failed, readiness, findings{new,resolved,changed,unchanged,new_blockers,...}, debt, coverage, trust, interactions, design, classification}`.
- **Gate result**: `{policy, result: PASS|FAIL|NOT_CONFIGURED, exit_code, reasons, policy_used, policy_name, debt}`.
- **Policy**: the declarative schema (§18).

No internal Python implementation details leak (lists, not tuples; `default=str` serialization guard in CLI JSON).

---

## 28. Deterministic Serialization

- All key lists are sorted at build (modes/edges/setup_hold, pair values, endpoint signatures).
- Findings preserve issue order (deterministic given same input).
- Fingerprint, debt buckets, coverage deltas, trust deltas are order-stable.
- `snapshot_to_json` is deterministic; the same SDC always produces the same JSON artifact (git-review friendly).

---

## 29. Identity Collision Results

Zero known collisions (PH13-03/04/05, `TestBusRangeIdentity`, `TestInteractionIdentity`, adversarial):

| Pair | Must differ? | Result |
|------|--------------|--------|
| same rule + different port | yes | differ ✓ |
| same rule + different clock | yes | differ ✓ |
| same rule + different bus range (`data[3:0]` vs `data[7:4]`) | yes | differ ✓ (ranges survive value blanking) |
| same interaction type + different endpoints | yes | differ ✓ |
| same message + different semantic fields | yes | differ ✓ |
| same object + different mode | yes | differ ✓ |
| symmetric interaction reordered | no (canonicalize) | same ✓ |
| override reversed (direction) | yes | differ ✓ |

---

## 30. Identity Stability Results

Message independence + line-movement stability proven end-to-end:

- PH13-01: rewording ⇒ identical keys.
- PH13-23: 50-line header shift ⇒ zero false NEW/RESOLVED.
- PH13-24: numeric/whitespace/comment formatting ⇒ zero false NEW/RESOLVED.
- `test_readiness_diff_adversarial`: line reorder (neutral), sci-notation (unchanged), variables, CRLF — all stable.
- Clock-rename is **intentionally** NEW+RESOLVED (clock is a semantic identity field — collision rule); classification stays BLOCKING_REGRESSION (safe for renames).

---

## 31. False-NEW Results

Zero false NEW for semantically equivalent revisions (message change, line movement, numeric formatting, variables, multiline, comments, CRLF, valid option ordering). Proven by PH13-23/24, `adv-*` adversarial checks, `test_readiness_diff_metamorphic`, and `test_snapshot_v2.py::TestMigration`.

---

## 32. False-RESOLVED Results

Zero false RESOLVED under the same transformations (same suites). A finding is only RESOLVED when its semantic identity genuinely disappears.

---

## 33. False-CI-PASS Results

The gate never reports PASS when:

- a new deterministic blocker exists (even hidden behind a 5 KB comment header) — `adv-false-pass-new-blocker` FAIL exit 1
- engine failure occurred (SDC-140) — FAIL exit 3 under **every** policy including maximally permissive CUSTOM — `adv-false-pass-engine`, PH13-18
- baseline is incompatible/corrupt — FAIL exit 2
- a trust regression or coverage regression is gated by the active policy — PH13-19/20

---

## 34. False-CI-FAIL Results

Harmless changes never fail the gate:

- formatting (`# comment` + `10.0→10`) → NO_READINESS_REGRESSION and STRICT both PASS (`adv-false-fail-*`)
- resolved old debt → PASS (IMPROVEMENT classification)
- existing baseline debt unchanged → PASS under NO_READINESS_REGRESSION and legacy CUSTOM policy (PH13-21)
- informational duplicates → advisory only, never blocking

---

## 35. Snapshot Security

`load_snapshot()` is the trust boundary: JSON-only, size-capped (20 MB), schema/type-validated (required keys, analysis.mode enum, engine_failed boolean, findings list of objects, identity-object type check), unknown schema rejected, and `identity_from_dict` coerces non-scalar identity fields to safe strings. Nothing is executed. 30 security checks pass, including malformed/oversized/deep/hostile inputs.

---

## 36. Performance

| Benchmark | Result | Budget |
|-----------|--------|--------|
| 10k structured identities | 0.17 s | 2.0 s |
| diff 10k findings | 0.19 s (near-linear) | 1.0 s |
| diff 50k findings | 1.1 s (near-linear) | 6.0 s |
| 1000 custom-policy evaluations | 0.02 s | 0.5 s |
| 100k-object fingerprint | 0.9 s | 10.0 s |
| 10k-finding snapshot JSON | 0.31 s | 3.0 s |

Diff complexity is near-linear (Counter-based multiset matching + dict indexing — **no all-pairs comparison**). Phase 13 does not degrade Phase 12 performance.

---

## 37. Independent Reviewer Findings

| # | Severity | Finding | Owner | Fix | Regression test |
|---|----------|---------|-------|-----|-----------------|
| 1 | **MEDIUM** | v1↔v2 migration key drift: editing `_LINE_REF_RE` (and any future `normalize_msg` edit) silently changes the legacy key space; real Phase 12 baselines would produce false NEW+RESOLVED. Migration tests regenerate both sides with the same function, so they can't catch cross-version drift. | identity owner | **Froze legacy normalization** to the exact Phase 12 regex; documented `FROZEN` in both `readiness_diff.py` and `finding_identity.py`; unit test pins the exact old-regex behavior | `test_legacy_normalization_is_frozen_to_phase12` |
| 2 | LOW-MED | Policy YAML alias expansion unbounded (billion-laughs); 256 KB input cap doesn't bound expanded structure | security | **4 MB expanded-structure cap** after JSON/YAML parse (`_bounded_structure`) | `sec-oversized` + `sec-yaml-bomb-*` extended; policy size cap path |
| 3 | LOW | `fail_on_new_rules` regex rejected SCOPE-*/CHG-* shapes; unknown IDs silently accepted if registry import fails | CI/security | Broadened regex (`^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$`); SCOPE-* family added to known IDs; registry failures degrade to format-only validation | `test_scope_and_chg_rule_ids_accepted` |
| 4 | LOW | OutputWriter `_json_written` guard only covered file mode; stdout mode could emit a trailing empty line after JSON | CLI | Guard set for **both** modes | `wf-json-has-diff` (CI workflow) |
| 5 | LOW | 240-char message truncation in legacy keys could theoretically collide two long messages sharing a prefix | — | Accepted — legacy fallback is honestly labeled; documented in §40 | — |

Reviewer also independently confirmed (no action needed): severity-change semantics, message independence, fingerprint stability, engine-failure-never-PASS, incompatible-baseline exit 2, gate exit-code contract, and the CLI `--json --output` clobbering bug that the Phase 12 `OutputWriter.flush()` had (fixed by the `_json_written` guard — caught by `test_ph13_ci_workflow.py`).

**Re-review result: PASS.**

---

## 38. Full Regression Results

| Suite | Result |
|-------|--------|
| pytest | **689/689** (was 602; +87: identity 34, policy 28, snapshot v2 14, CLI custom-policy +11) |
| Parser golden | 22/22 |
| Semantic golden | 9/9 |
| Reference designs | 8/8 |
| Design coverage golden | 12/12 |
| Netlist-aware golden | 10/10 |
| Constraint interaction golden | 20/20 |
| Constraint readiness golden | 15/15 |
| Readiness diff golden | 22/22 |
| **PH13 production-hardening golden** | **49/49** |
| Security / trust / no-false-confidence / semantic-adversarial | 5/5 · 8/8 · 6/6 · 13/13 |
| Reference metamorphic / mutation / cross-module | 10/10 · 7/7 · consistent |
| Netlist metamorphic / adversarial / security | 4/4 · 12/12 · 7/7 |
| Coverage metamorphic / adversarial | 7/7 · 14/14 |
| Readiness adversarial / confidence / metamorphic / perf | 9 · 18 · 8 · 3 |
| Readiness-diff adversarial / metamorphic / confidence / perf / CI-gate | ALL PASS |
| Preprocess stress | 21/21 |
| UI / state isolation | 35/35 · 6/6 |
| PH13 adversarial / security / perf / CI workflow | 13 · 30 · 7 · 18 |

No previous suite regressed (the only expectation change is the **clock-rename** case, which is the deliberate Phase 13 identity-contract upgrade documented in §30 — not a weakening).

---

## 39. Files Modified

**New production modules**
- `finding_identity.py` — structured FindingIdentity model, rule-family map, command/record extractors, legacy fallback, versioning
- `policy_engine.py` — declarative CUSTOM policy engine (validation, security caps, evaluation)

**Modified production modules**
- `readiness_diff.py` — schema v2, `legacy_full_id/base_id` dual key space, migration metadata, fingerprint v2 (instance-order sort), debt model, frozen legacy normalization, gate CUSTOM routing
- `checker.py` — `Issue.identity` field, `CheckResult.logical` commands, interaction-identity wiring
- `constraint_interactions.py` — structured identity attached at finding generation
- `cli.py` — `--gate-policy` wiring, OutputWriter `_json_written` guard (fixes `--json --output` clobbering), debt in diff rendering
- `reporter.py` — debt / identity-strength / CHANGED in the HTML diff section
- `app.py` — debt metrics, identity-strength disclosure, NEW/RESOLVED/CHANGED filter, migration note

**Tests** (new)
- `tests/test_finding_identity.py` (34)
- `tests/test_policy_engine.py` (28)
- `tests/test_snapshot_v2.py` (14)
- `tests/test_cli.py` (+11 Phase 13 CUSTOM-policy / debt / YAML-policy CLI tests)

**Benchmarks** (new)
- `benchmarks/production_hardening/` (README, fixtures: clean/blocker/mcp .sdc + top.v)
- `benchmarks/run_production_hardening.py` — PH13-01..25 golden (49 assertions)
- `benchmarks/test_ph13_adversarial.py` (13) · `test_ph13_security.py` (30) · `test_ph13_perf.py` (7) · `test_ph13_ci_workflow.py` (18)
- `benchmarks/test_readiness_diff_adversarial.py` — clock-rename expectation updated to the Phase 13 identity contract

**CI / docs / examples** (new)
- `.github/workflows/sdc-readiness.yml.example`
- `policy_examples/legacy_project.yml` · `mature_project.yml` · `strict_handoff.yml`
- `benchmarks/PHASE13_PRODUCTION_HARDENING_REPORT.md` (this file)

---

## 40. Remaining Limitations

1. **Legacy identity is message-derived** (honestly labeled `LEGACY_NORMALIZED`) for findings without command provenance (SCOPE-* counts, some design-aware). Rewording such messages still changes their identity — visible via the strength disclosure in the UI/report.
2. **v1↔v2 migration is a legacy-normalized comparison** — a genuine Phase 12 baseline compares in the message-normalized key space. It cannot benefit from structured identity; this is by design and surfaced as `PARTIALLY_COMPARABLE`.
3. **240-char message truncation** in legacy keys: two long messages sharing the first 240 chars would collide in the legacy space (accepted; legacy is fallback-only).
4. **Clock renames are NEW+RESOLVED** (clock is a semantic identity field). The classification stays BLOCKING_REGRESSION — safe, but a global rename shows as a full finding churn. Compatible with the Phase 12 adversarial "gate fails on renames" intent.
5. **Fingerprint excludes connectivity details** beyond counts — two structurally different designs with identical port/instance/net inventories and identical connectivity *counts* could fingerprint identically. Enumerated connectivity content is not included to keep the fingerprint cheap.
6. **Rule-ID gating** validates against the registry when available; if the registry import fails it degrades to format-only validation.
7. The gate is **opt-in** — no CI behavior is active without `--gate`.

---

## 41. TRUST STATEMENT

**What makes a finding identity stable?**
Stability comes from deriving identity from **structured semantic fields of the SDC command text / interaction records** (rule, finding_type, command, objects, clock, value, mode, edge, interaction type, endpoint signature) instead of the human-readable message. Message rewording, line movement, numeric formatting, variables, and whitespace cannot change it. Presentation (message) and provenance (line numbers) are explicitly excluded from identity. Identity versioning and the frozen legacy key space protect it across releases.

**What does a CUSTOM CI policy control?**
A CUSTOM policy controls **which existing diff evidence fails the gate**: new blockers, new review items, current BLOCKED status, trust regressions, coverage regressions, rule-specific gates, thresholds, and whether advisories are allowed. It is declarative, inert data.

**What can a CUSTOM policy NOT change?**
A CUSTOM policy cannot change any underlying validator semantics: what is detected, what is parsed, severity of rules, identity of findings, coverage/trust computation, or readiness classification. It cannot disable engine-failure handling (a crashed analysis always exits 3). It cannot bypass incompatible/corrupt baseline rejection (exit 2). It cannot execute code.

**What does CI PASS guarantee?**
Exactly: *"No disallowed constraint-readiness regression was detected between the baseline and the current revision, under the selected policy and the stated analysis context (SDC-only or design-aware)."* It also implies the analysis engines did not crash and the baseline was compatible.

**What does CI PASS NOT guarantee?**
CI PASS does **not** mean timing passes, setup/hold is met, slack is positive, the design is fully constrained, the constraints are correct, or that an engineering review is unnecessary. A revision with zero *regressions* can still carry pre-existing debt, unknown-intent objects, or correctness problems that no validator-without-STA can prove. CI PASS ≠ TIMING PASS.

**Does the production SDC Validator use an LLM or AI?**
**NO.** The production validator is a deterministic Python tool: parsing, validation, design resolution, coverage, constraint interactions, readiness, baseline comparison, and CI gating are all plain logic. AI / subagents (Freebuff / DeepSeek) were used **only to develop, research, review, and test** the software in this phase — never at runtime. If an AI-generated conclusion conflicts with deterministic evidence, authoritative SDC semantics, or regression tests, the deterministic evidence wins.

---

## 42. Phase 14 Recommendation

**Recommendation: a RELEASE-CANDIDATE / ARCHITECTURE AUDIT, not another feature phase.**

Evidence from Phase 13:
1. Twelve phases have layered substantial capability (preprocessing → variables → semantic rules → relations → support boundary → netlist awareness → coverage → interactions → readiness → diff → CI → identity/policy hardening). The feature surface is broad and cross-cutting; the highest remaining risk is **integration and packaging**, not a missing feature.
2. The deterministic/LLM separation is now explicit and worth formalizing in a release audit (verify no AI dependency is importable in the runtime path, no network calls, reproducible builds).
3. Phase 13 itself recommends a hardening/audit cadence: structured identity, snapshot v2, frozen legacy keys, and policy files are the kinds of surfaces that deserve a **documented public API contract** and a **semver policy** before external teams depend on them.

Proposed Phase 14 scope (if a release audit is accepted):
- Public API / JSON-contract freeze + documentation pass (snapshot, FindingIdentity, diff, gate, policy).
- Packaging & CI review: `pyproject.toml` extras, Docker, pinned deps, `sdc-tools` entry-point verification on clean clones (Windows/Linux/macOS).
- Determinism audit: no hash-randomization dependence, no locale/encoding dependence, byte-reproducible JSON artifacts.
- A small `sdc-tools audit` command summarizing validator capabilities + trust boundaries for handoff documents.

Do **not** start Phase 14 without the owner confirming the release-audit direction over another feature phase.

---

## SUCCESS CRITERIA — VERIFIED

- ✅ Message changes do not create fake regressions (PH13-01, 23, 24)
- ✅ Line movement never changes semantic identity
- ✅ Equivalent syntax (numeric/variable/whitespace/CRLF/option order) stays stable
- ✅ Different semantic findings do not collide (§29)
- ✅ Severity changes are represented correctly (CHANGED, never RESOLVED+NEW)
- ✅ Interaction ordering correct (symmetric canonicalized, override direction preserved)
- ✅ v1 baselines remain safely usable (legacy-normalized comparison, `PARTIALLY_COMPARABLE`)
- ✅ Structural fingerprint ignores harmless formatting; detects real design changes
- ✅ CUSTOM policies are declarative, inert, validated, cannot execute code
- ✅ Baseline debt visible; new debt detectable; a new blocker is never hidden by baseline
- ✅ Engine failure never produces PASS (exit 3)
- ✅ CI remains platform-independent (CLI is the boundary)
- ✅ Diff investigation is easier (debt metrics, identity strength, NEW/RESOLVED/CHANGED filter)
- ✅ All existing deterministic semantics unchanged; every prior suite green
- ✅ No AI dependency in production validation
