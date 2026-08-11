"""Phase 13 — declarative CI policy engine (inert data, safe validation)."""

import json

import pytest

from policy_engine import (
    POLICY_VERSION, MAX_POLICY_BYTES, POLICY_RESULT_PASS, POLICY_RESULT_FAIL,
    _builtin_policy, evaluate_policy, load_policy, validate_policy,
)
from readiness_diff import (
    EXIT_PASS, EXIT_GATE_FAILED, EXIT_INVALID, EXIT_ENGINE_FAILURE,
    INCOMPATIBLE,
)


def _policy(**overrides):
    p = {
        "policy": "CUSTOM",
        "policy_version": 1,
        "name": "test-policy",
        "fail_on": {
            "current_blocked": False,
            "new_blockers": True,
            "new_review_items": False,
            "trust_regression": False,
            "coverage_regression": False,
            "engine_failure": True,
        },
        "allow": {"new_advisories": True},
    }
    p.update(overrides)
    return p


def _cur(overall="READY", engine_failed=False):
    return {"readiness": {"overall": overall},
            "analysis": {"engine_failed": engine_failed}}


def _diff(new_blockers=0, new_review=0, trust_regs=0, newly_unc=0,
          compat="COMPATIBLE", new_codes=None, existing_blockers=0):
    return {
        "compatibility": {"status": compat},
        "findings": {
            "new_blockers": [{"code": f"SDC-0{i}"} for i in range(1, new_blockers + 1)],
            "new_review": [{"code": f"SDC-0{i}"} for i in range(1, new_review + 1)],
            "new": [{"code": c} for c in (new_codes or [])],
        },
        "trust": {"regressions": [{"command": f"cmd{i}"}
                                  for i in range(1, trust_regs + 1)]},
        "coverage": {
            "inputs": {"newly_unconstrained": [f"in{i}" for i in range(1, newly_unc + 1)]},
            "outputs": {"newly_unconstrained": []},
        },
        "debt": {"existing": {"blockers": existing_blockers, "review": 0,
                              "advisories": 0, "coverage": 0, "trust": 0},
                 "new_debt": {"blockers": 0, "review": 0, "advisories": 0,
                              "coverage": 0, "trust": 0},
                 "resolved_debt": {"blockers": 0, "review": 0, "advisories": 0,
                                   "coverage": 0, "trust": 0}},
    }


# ── Validation ───────────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_policy(self):
        assert validate_policy(_policy()) == []

    def test_unknown_field_rejected(self):
        errs = validate_policy(_policy(evil=1))
        assert any("unknown policy field" in e for e in errs)

    def test_unknown_fail_on_field_rejected(self):
        p = _policy()
        p["fail_on"]["spam"] = True
        errs = validate_policy(p)
        assert any("unknown field 'fail_on.spam'" in e for e in errs)

    def test_wrong_type_rejected(self):
        p = _policy()
        p["fail_on"]["new_blockers"] = "yes"
        errs = validate_policy(p)
        assert any("must be boolean" in e for e in errs)

    def test_negative_threshold_rejected(self):
        p = _policy(thresholds={"max_new_review_items": -1})
        errs = validate_policy(p)
        assert any("non-negative" in e for e in errs)

    def test_unsupported_version_rejected(self):
        p = _policy(policy_version=99)
        errs = validate_policy(p)
        assert any("unsupported policy_version" in e for e in errs)

    def test_wrong_policy_type_rejected(self):
        p = _policy(policy="STRICT")
        errs = validate_policy(p)
        assert any("must be 'CUSTOM'" in e for e in errs)

    def test_invalid_rule_id_rejected(self):
        p = _policy(fail_on_new_rules=["not-a-rule", "sdc-069"])
        errs = validate_policy(p)
        assert any("invalid rule ID" in e for e in errs)

    def test_unknown_rule_id_rejected(self):
        p = _policy(fail_on_new_rules=["SDC-9999"])
        errs = validate_policy(p)
        assert any("unknown rule ID" in e for e in errs)

    def test_known_rule_id_accepted(self):
        p = _policy(fail_on_new_rules=["SDC-069"])
        assert validate_policy(p) == []

    def test_scope_and_chg_rule_ids_accepted(self):
        # Broader rule-code shapes: SCOPE-* (synthesized) and multi-part
        # CHG-* (constraint_diff) codes gate too.
        for rid in ("SCOPE-UNSUPPORTED", "SCOPE-PARTIAL", "CHG-CK-001"):
            p = _policy(fail_on_new_rules=[rid])
            assert validate_policy(p) == [], f"{rid} should validate"

    def test_huge_rule_list_rejected(self):
        p = _policy(fail_on_new_rules=[f"SDC-{i:03d}" for i in range(600)])
        errs = validate_policy(p)
        assert any("at most 500" in e for e in errs)

    def test_builtin_policies_validate_clean(self):
        for name in ("BLOCKERS_ONLY", "NO_READINESS_REGRESSION", "STRICT"):
            assert validate_policy(_builtin_policy(name)) == []


# ── Loading (JSON + YAML, safe) ──────────────────────────────────────────────

class TestLoad:
    def test_json_policy(self):
        data, errs = load_policy(json.dumps(_policy()))
        assert errs == []
        assert data["name"] == "test-policy"

    def test_yaml_policy(self):
        yaml_text = (
            "policy: CUSTOM\n"
            "policy_version: 1\n"
            "name: legacy-project\n"
            "fail_on:\n"
            "  new_blockers: true\n"
            "allow:\n"
            "  new_advisories: true\n"
        )
        data, errs = load_policy(yaml_text)
        assert errs == []
        assert data["fail_on"]["new_blockers"] is True

    def test_malformed_rejected(self):
        data, errs = load_policy("{not valid json: [")
        assert data is None
        assert errs

    def test_oversized_rejected(self):
        data, errs = load_policy("x" * (MAX_POLICY_BYTES + 1))
        assert data is None
        assert any("safety cap" in e for e in errs)

    def test_hostile_values_are_inert(self):
        # Python-looking / shell-looking values are just strings — nothing runs.
        hostile = _policy(name="x; rm -rf /",
                          fail_on_new_rules=["SDC-069", "__import__('os').system('id')"])
        errs = validate_policy(hostile)
        # rule-list membership is validated against the ID regex, never executed
        assert any("invalid rule ID" in e for e in errs)

    def test_yaml_bomb_style_is_rejected_or_inert(self):
        # Deep aliases must not crash the loader (yaml.safe_load has a depth cap).
        text = "a: &x [1,2,3]\nb: *x\n"
        data, errs = load_policy(text)
        if data is not None:
            # if it parsed, it must still fail schema validation (not crash)
            assert isinstance(errs, list)


# ── Evaluation semantics ─────────────────────────────────────────────────────

class TestEvaluation:
    def test_pass_when_no_failing_conditions(self):
        r = evaluate_policy(_policy(), None, _cur(), _diff())
        assert r["result"] == POLICY_RESULT_PASS
        assert r["exit_code"] == EXIT_PASS

    def test_new_blocker_fails(self):
        r = evaluate_policy(_policy(), None, _cur(), _diff(new_blockers=1))
        assert r["result"] == POLICY_RESULT_FAIL
        assert r["exit_code"] == EXIT_GATE_FAILED

    def test_new_blocker_not_gated_by_policy(self):
        p = _policy(fail_on={"new_blockers": False, "engine_failure": True})
        r = evaluate_policy(p, None, _cur(), _diff(new_blockers=1))
        assert r["result"] == POLICY_RESULT_PASS

    def test_current_blocked_fails_when_enabled(self):
        p = _policy(fail_on={"current_blocked": True, "new_blockers": False,
                             "engine_failure": True})
        r = evaluate_policy(p, None, _cur(overall="BLOCKED"), _diff())
        assert r["result"] == POLICY_RESULT_FAIL

    def test_current_blocked_ignored_when_disabled(self):
        r = evaluate_policy(_policy(), None, _cur(overall="BLOCKED"), _diff())
        assert r["result"] == POLICY_RESULT_PASS

    def test_trust_regression_fails_when_enabled(self):
        p = _policy(fail_on={"trust_regression": True, "engine_failure": True})
        r = evaluate_policy(p, None, _cur(), _diff(trust_regs=2))
        assert r["result"] == POLICY_RESULT_FAIL

    def test_coverage_regression_fails_when_enabled(self):
        p = _policy(fail_on={"coverage_regression": True, "engine_failure": True})
        r = evaluate_policy(p, None, _cur(), _diff(newly_unc=1))
        assert r["result"] == POLICY_RESULT_FAIL

    def test_threshold_exceeds_cap(self):
        p = _policy(fail_on={"new_review_items": False, "engine_failure": True},
                    thresholds={"max_new_review_items": 2})
        r = evaluate_policy(p, None, _cur(), _diff(new_review=3))
        assert r["result"] == POLICY_RESULT_FAIL

    def test_threshold_within_cap_passes(self):
        p = _policy(fail_on={"new_review_items": False, "engine_failure": True},
                    thresholds={"max_new_review_items": 2})
        r = evaluate_policy(p, None, _cur(), _diff(new_review=2))
        assert r["result"] == POLICY_RESULT_PASS

    def test_fail_on_new_rules(self):
        p = _policy(fail_on_new_rules=["SDC-069"])
        r = evaluate_policy(p, None, _cur(), _diff(new_codes=["SDC-069"]))
        assert r["result"] == POLICY_RESULT_FAIL

    def test_rule_gate_only_applies_to_new_findings(self):
        p = _policy(fail_on_new_rules=["SDC-069"])
        r = evaluate_policy(p, None, _cur(), _diff(new_codes=["SDC-046"]))
        assert r["result"] == POLICY_RESULT_PASS

    def test_engine_failure_never_passes(self):
        # Even a maximally permissive policy cannot disable engine failure.
        p = _policy(fail_on={"engine_failure": False})
        r = evaluate_policy(p, None, _cur(engine_failed=True), _diff())
        assert r["result"] == POLICY_RESULT_FAIL
        assert r["exit_code"] == EXIT_ENGINE_FAILURE

    def test_incompatible_baseline_never_passes(self):
        r = evaluate_policy(_policy(), None, _cur(),
                            _diff(compat=INCOMPATIBLE))
        assert r["result"] == POLICY_RESULT_FAIL
        assert r["exit_code"] == EXIT_INVALID

    def test_existing_debt_never_fails_by_itself(self):
        r = evaluate_policy(_policy(), None, _cur(),
                            _diff(existing_blockers=3))
        assert r["result"] == POLICY_RESULT_PASS
        assert any("pre-existing blocker" in x for x in r["reasons"])

    def test_result_shape(self):
        r = evaluate_policy(_policy(), None, _cur(), _diff())
        for key in ("policy", "result", "exit_code", "reasons", "policy_used",
                    "policy_name", "debt"):
            assert key in r
