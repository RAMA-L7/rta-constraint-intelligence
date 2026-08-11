"""
Declarative CI Policy Engine (Phase 13 — production hardening).

Phase 12 introduced four gate policies (BLOCKERS_ONLY, NO_READINESS_REGRESSION,
STRICT, CUSTOM). Phase 13 makes CUSTOM a *safe declarative policy surface*:

  - Policies are INERT DATA (JSON or YAML). No eval, exec, Python expressions,
    imports, shell, templates with execution, or arbitrary callbacks. The
    engine interprets only a fixed, validated schema.
  - A policy cannot change any underlying validator semantics. It selects
    WHICH EXISTING DIFF EVIDENCE (new blockers, review items, trust/coverage
    regressions, engine failure) fails the gate — never what the validator
    detects.
  - Engine failure can never be disabled: a crashed analysis always fails
    with exit code 3, regardless of policy.
  - Built-in policies are expressed in the SAME declarative schema, so
    BLOCKERS_ONLY / NO_READINESS_REGRESSION / STRICT semantics are preserved
    by construction and remain regression-tested.

Policy schema (version 1):

    {
      "policy": "CUSTOM",
      "policy_version": 1,
      "name": "legacy-project",
      "fail_on": {
        "current_blocked": false,       # current readiness == BLOCKED
        "new_blockers": true,           # NEW deterministic blocker vs baseline
        "new_review_items": false,      # NEW review-tier finding vs baseline
        "trust_regression": false,      # VALIDATED → PARTIAL/UNSUPPORTED
        "coverage_regression": false,   # newly unconstrained design objects
        "engine_failure": true          # always effective, cannot be disabled
      },
      "allow": {
        "new_advisories": true          # info-level additions never fail
      },
      "thresholds": {
        "max_new_review_items": 2       # optional cap (0 = none allowed)
      },
      "fail_on_new_rules": ["SDC-069"]  # optional rule-specific gate
    }

Only keys in the schema are accepted; unknown fields, wrong types, invalid
enum values, negative thresholds, unsupported versions, and oversized inputs
are rejected with exit code 2 (invalid invocation/input).

Design decision — why no numeric score: a single "87/100 ready" percentage is
rejected. Readiness is categorical; a definite contradiction may BLOCK handoff
even when every dimension average looks green. Policies select categories, not
weights.
"""

import json
import re
from typing import Dict, List, Optional, Tuple

from readiness_diff import (
    BLOCKED, REVIEW_REQUIRED, READY_WITH_ADVISORIES,
    EXIT_PASS, EXIT_GATE_FAILED, EXIT_INVALID, EXIT_ENGINE_FAILURE,
    INCOMPATIBLE,
)

POLICY_VERSION = 1
MAX_POLICY_BYTES = 256 * 1024  # 256 KB safety cap for policy files

POLICY_RESULT_PASS = "PASS"
POLICY_RESULT_FAIL = "FAIL"
POLICY_NOT_CONFIGURED = "NOT_CONFIGURED"

# ── Built-in policies expressed declaratively (semantics preserved) ──────────

def _builtin_policy(name: str) -> dict:
    """Return the declarative equivalent of a Phase 12 built-in policy."""
    if name == "BLOCKERS_ONLY":
        return {"policy": "CUSTOM", "policy_version": POLICY_VERSION,
                "name": "BLOCKERS_ONLY",
                "fail_on": {"current_blocked": True,
                            "new_blockers": False,
                            "new_review_items": False,
                            "trust_regression": False,
                            "coverage_regression": False,
                            "engine_failure": True},
                "allow": {"new_advisories": True}}
    if name == "NO_READINESS_REGRESSION":
        return {"policy": "CUSTOM", "policy_version": POLICY_VERSION,
                "name": "NO_READINESS_REGRESSION",
                "fail_on": {"current_blocked": False,
                            "new_blockers": True,
                            "new_review_items": True,
                            "trust_regression": True,
                            "coverage_regression": True,
                            "engine_failure": True},
                "allow": {"new_advisories": True}}
    if name == "STRICT":
        return {"policy": "CUSTOM", "policy_version": POLICY_VERSION,
                "name": "STRICT",
                "fail_on": {"current_blocked": True,
                            "new_blockers": True,
                            "new_review_items": True,
                            "trust_regression": True,
                            "coverage_regression": True,
                            "engine_failure": True},
                "allow": {"new_advisories": True}}
    raise ValueError(f"unknown built-in policy '{name}'")


# ── Validation (reject safely, nothing executes) ─────────────────────────────

_ALLOWED_KEYS = {"policy", "policy_version", "name", "fail_on", "allow",
                 "thresholds", "fail_on_new_rules"}
_ALLOWED_FAIL_ON = {"current_blocked", "new_blockers", "new_review_items",
                    "trust_regression", "coverage_regression", "engine_failure"}
_ALLOWED_ALLOW = {"new_advisories"}
_ALLOWED_THRESHOLDS = {"max_new_review_items"}
# Accepts SDC-069, CHG-001-002, SCOPE-UNSUPPORTED, etc. — any valid
# rule-code shape (code words separated by dashes, ending in an optional
# numeric suffix).
_RULE_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")
_KNOWN_RULES = None  # lazily loaded from rules_registry to avoid import cost


def _known_rule_ids() -> set:
    global _KNOWN_RULES
    if _KNOWN_RULES is None:
        known = set()
        try:
            from rules_registry import RULES  # Dict[code, Rule]
            known = set(RULES) - {""}
        except Exception:
            known = set()
        # Synthesized readiness-layer codes are also legitimate gating targets
        # (they appear in snapshots as findings).
        known |= {"SCOPE-UNSUPPORTED", "SCOPE-PARTIAL"}
        _KNOWN_RULES = known
    return _KNOWN_RULES


def _validate_bool_section(data: dict, key: str, allowed: set,
                           errs: List[str]) -> None:
    section = data.get(key)
    if section is None:
        return
    if not isinstance(section, dict):
        errs.append(f"'{key}' must be an object")
        return
    for k, v in section.items():
        if k not in allowed:
            errs.append(f"unknown field '{key}.{k}' (allowed: {sorted(allowed)})")
        elif not isinstance(v, bool):
            errs.append(f"'{key}.{k}' must be boolean, got {type(v).__name__}")


def validate_policy(data) -> List[str]:
    """Return a list of policy schema/type errors. Empty list == valid.

    Rejects: unknown fields, wrong types, invalid enum values, negative
    thresholds, unsupported versions, oversized/oversized rule lists,
    contradictory booleans (not applicable — all combos are legal), and
    malformed structure. Policies are inert data — nothing is executed.
    """
    errs: List[str] = []
    if not isinstance(data, dict):
        return ["policy is not an object"]
    for k in data:
        if k not in _ALLOWED_KEYS:
            errs.append(f"unknown policy field '{k}' (allowed: {sorted(_ALLOWED_KEYS)})")
    if "policy" in data and data["policy"] != "CUSTOM":
        errs.append(f"policy.type must be 'CUSTOM', got {data['policy']!r}")
    pv = data.get("policy_version")
    if pv is None:
        errs.append("missing 'policy_version'")
    elif not isinstance(pv, int) or isinstance(pv, bool):
        errs.append("'policy_version' must be an integer")
    elif pv != POLICY_VERSION:
        errs.append(f"unsupported policy_version {pv} (expected {POLICY_VERSION})")
    name = data.get("name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        errs.append("'name' must be a non-empty string")
    _validate_bool_section(data, "fail_on", _ALLOWED_FAIL_ON, errs)
    _validate_bool_section(data, "allow", _ALLOWED_ALLOW, errs)

    thr = data.get("thresholds")
    if thr is not None:
        if not isinstance(thr, dict):
            errs.append("'thresholds' must be an object")
        else:
            for k, v in thr.items():
                if k not in _ALLOWED_THRESHOLDS:
                    errs.append(f"unknown threshold '{k}' (allowed: {sorted(_ALLOWED_THRESHOLDS)})")
                elif not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    errs.append(f"threshold '{k}' must be a non-negative integer")

    rules = data.get("fail_on_new_rules")
    if rules is not None:
        if not isinstance(rules, list) or len(rules) > 500:
            errs.append("'fail_on_new_rules' must be a list of at most 500 rule IDs")
        else:
            known = _known_rule_ids()
            for rid in rules:
                if not isinstance(rid, str) or not _RULE_ID_RE.match(rid):
                    errs.append(f"invalid rule ID {rid!r} "
                                f"(expected e.g. 'SDC-069', 'CHG-001-002', "
                                f"'SCOPE-UNSUPPORTED')")
                elif known and rid not in known:
                    errs.append(f"unknown rule ID '{rid}' — not in the rules registry")
    return errs


# Expanded policy structure cap: bounds alias/entity expansion (YAML
# billion-laughs style) after parsing — the INPUT byte cap alone cannot bound
# the EXPANDED structure.
MAX_POLICY_STRUCT_BYTES = 4 * 1024 * 1024  # 4 MB expanded


def _bounded_structure(data) -> Tuple[bool, str]:
    """Return (ok, err) — reject structures that expand beyond the cap."""
    try:
        size = len(json.dumps(data, default=str))
    except Exception:
        return False, "policy structure is not serializable"
    if size > MAX_POLICY_STRUCT_BYTES:
        return False, (f"policy expands to {size} bytes — exceeds "
                       f"{MAX_POLICY_STRUCT_BYTES} expanded-size safety cap")
    return True, ""


def _load_json_or_yaml(text: str):
    """Parse policy text as JSON, falling back to YAML. Returns (data|None, err)."""
    if len(text.encode("utf-8")) > MAX_POLICY_BYTES:
        return None, f"policy file exceeds {MAX_POLICY_BYTES} bytes safety cap"
    stripped = text.lstrip()
    try:
        if stripped.startswith("{") or stripped.startswith("["):
            data = json.loads(text)
        else:
            import yaml
            # safe_load: no arbitrary object construction, no code execution.
            # (Policy files are untrusted; YAML tags/anchors are not expanded
            # into objects beyond plain data.)
            data = yaml.safe_load(text)
        ok, err = _bounded_structure(data)
        if not ok:
            return None, err
        return data, None
    except json.JSONDecodeError as e:
        try:
            import yaml
            data = yaml.safe_load(text)
            ok, err = _bounded_structure(data)
            if not ok:
                return None, err
            return data, None
        except Exception as ye:
            return None, f"policy is not valid JSON or YAML: {ye}"
    except Exception as e:
        return None, f"policy is not valid JSON or YAML: {e}"


def load_policy(text: str) -> Tuple[Optional[dict], List[str]]:
    """Load + validate a policy from JSON/YAML text.

    Returns (policy, errors). On any validation error the policy is None and
    the caller must fail safely with exit code 2. Nothing is ever executed.
    """
    data, err = _load_json_or_yaml(text)
    if data is None:
        return None, [err or "could not parse policy"]
    errs = validate_policy(data)
    if errs:
        return None, errs
    return data, []


# ── Policy evaluation ────────────────────────────────────────────────────────

def _fail_flags(policy: dict) -> Dict[str, bool]:
    fo = policy.get("fail_on") or {}
    defaults = {"current_blocked": False, "new_blockers": False,
                "new_review_items": False, "trust_regression": False,
                "coverage_regression": False, "engine_failure": True}
    defaults.update({k: v for k, v in fo.items() if isinstance(v, bool)})
    return defaults


def evaluate_policy(policy: dict, base: Optional[dict], cur: dict,
                    diff: dict) -> dict:
    """Evaluate a validated declarative policy.

    Returns the same result shape as readiness_diff.evaluate_gate:
      {"policy", "result", "exit_code", "reasons", "policy_used",
       "debt", "policy_name"}

    Engine failure is ALWAYS a FAIL with exit 3 — a policy cannot disable it.
    Incompatible baselines are ALWAYS FAIL with exit 2 — a policy cannot
    silently gate on an invalid comparison.
    """
    reasons: List[str] = []
    flags = _fail_flags(policy)
    failed = False
    exit_code = EXIT_PASS

    # 1. Engine failure — hard rule, cannot be overridden.
    if bool(cur.get("analysis", {}).get("engine_failed")):
        return {"policy": "CUSTOM", "result": POLICY_RESULT_FAIL,
                "exit_code": EXIT_ENGINE_FAILURE, "policy_used": True,
                "reasons": ["analysis engine failed (SDC-140) — a gate can "
                            "never report PASS on incomplete evidence"],
                "policy_name": policy.get("name", "CUSTOM"),
                "debt": diff.get("debt", {})}

    # 2. Incompatible baseline — hard rule.
    if diff.get("compatibility", {}).get("status") == INCOMPATIBLE:
        return {"policy": "CUSTOM", "result": POLICY_RESULT_FAIL,
                "exit_code": EXIT_INVALID, "policy_used": True,
                "reasons": ["baseline is incompatible with current analysis — "
                            "refusing to gate on an invalid comparison"],
                "policy_name": policy.get("name", "CUSTOM"),
                "debt": diff.get("debt", {})}

    # 3. Baseline-dependent conditions.
    f = diff.get("findings", {}) or {}
    debt = diff.get("debt", {}) or {}

    if flags["current_blocked"]:
        overall = cur.get("readiness", {}).get("overall", "")
        if overall == BLOCKED:
            failed = True
            reasons.append(f"current analysis is BLOCKED "
                           f"({len(cur.get('readiness', {}).get('dimensions', {}))} "
                           f"dimensions evaluated)")

    new_blockers = f.get("new_blockers", [])
    if flags["new_blockers"] and new_blockers:
        failed = True
        codes = sorted({b.get("code", "") for b in new_blockers})
        reasons.append(f"{len(new_blockers)} NEW blocker(s): {', '.join(codes)}")

    new_review = f.get("new_review", [])
    if flags["new_review_items"] and new_review:
        failed = True
        codes = sorted({r.get("code", "") for r in new_review})
        reasons.append(f"{len(new_review)} NEW review item(s): {', '.join(codes)}")

    thr = (policy.get("thresholds") or {}).get("max_new_review_items")
    if thr is not None and not flags["new_review_items"] and len(new_review) > thr:
        failed = True
        reasons.append(f"{len(new_review)} new review items exceed threshold "
                       f"max_new_review_items={thr}")

    trust_reg = diff.get("trust", {}).get("regressions", [])
    if flags["trust_regression"] and trust_reg:
        failed = True
        cmds = sorted({t.get("command", "") for t in trust_reg})
        reasons.append(f"{len(trust_reg)} trust regression(s): "
                       f"{', '.join(cmds[:5])}")

    cov = diff.get("coverage", {}) or {}
    newly_unc = (cov.get("inputs", {}).get("newly_unconstrained", []) +
                 cov.get("outputs", {}).get("newly_unconstrained", []))
    if flags["coverage_regression"] and newly_unc:
        failed = True
        reasons.append(f"{len(newly_unc)} newly unconstrained object(s): "
                       f"{', '.join(sorted(newly_unc)[:5])}")

    rule_gate = policy.get("fail_on_new_rules") or []
    if rule_gate:
        new_codes = {x.get("code", "") for x in f.get("new", [])}
        hits = sorted(set(rule_gate) & new_codes)
        if hits:
            failed = True
            reasons.append(f"NEW finding(s) on gated rule(s): {', '.join(hits)}")

    # 4. Baseline debt is never a failure by itself — it is exposed so the
    #    caller (CI output) can distinguish pre-existing debt from new debt.
    existing = debt.get("existing", {})
    if existing.get("blockers"):
        reasons.append(f"{existing['blockers']} pre-existing blocker(s) unchanged "
                       f"(baseline debt, not new)")

    if not reasons:
        reasons.append("no failing conditions under the selected policy")

    return {"policy": "CUSTOM", "result": POLICY_RESULT_FAIL if failed else POLICY_RESULT_PASS,
            "exit_code": EXIT_GATE_FAILED if failed else EXIT_PASS,
            "policy_used": True, "reasons": reasons,
            "policy_name": policy.get("name", "CUSTOM"),
            "debt": debt}
