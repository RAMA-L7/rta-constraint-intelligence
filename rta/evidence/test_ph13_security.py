"""Phase 13 — snapshot / policy security suite.

Attacks:
  - malformed JSON / deep nesting / huge lists / wrong enums / wrong types /
    negative counts / duplicate entries / unknown schema
  - YAML alias/bomb behavior, Python-looking and shell-looking policy values
  - policies must remain INERT: no execution, no uncontrolled recursion,
    no crash
  - baseline/policy files are untrusted input: never trusted silently, never
    executed

Run:  python benchmarks/test_ph13_security.py
Exit: 0 = all pass.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from policy_engine import load_policy, validate_policy
from readiness_diff import load_snapshot, snapshot_to_json, MAX_SNAPSHOT_BYTES
from checker import check_sdc
from readiness_diff import build_snapshot

PASSED = []
FAILED = []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + ("  " + detail if detail else ""))


def main():
    snap = build_snapshot(check_sdc("create_clock -name c -period 10 [get_ports clk]\n"),
                          source_name="t.sdc")

    print("== Malformed snapshots (fail safely, never execute) ==")
    hostile = [
        ("not json at all", "{oops"),
        ("empty string", ""),
        ("json null", "null"),
        ("json list", "[1,2,3]"),
        ("unknown schema", json.dumps({"schema_version": 99})),
        ("missing required keys", json.dumps({"schema_version": 2})),
        ("wrong engine_failed type", json.dumps({**snap, "analysis": {**snap["analysis"],
                                                                      "engine_failed": "yes"}})),
        ("findings not a list", json.dumps({**snap, "findings": {}})),
        ("finding not an object", json.dumps({**snap, "findings": [42]})),
        ("finding identity not an object",
         json.dumps({**snap, "findings": [{"code": "SDC-1", "identity": "x"}]})),
        ("bad mode", json.dumps({**snap, "analysis": {**snap["analysis"], "mode": "MAGIC"}})),
    ]
    for name, payload in hostile:
        s, errs = load_snapshot(payload)
        check(f"sec-snap-{name}", s is None and errs, str(errs))

    print("== Deep nesting / size attacks ==")
    deep = json.dumps({"schema_version": 2, "a": {"b": {"c": {"d": {"e": 1}}}}})
    s, errs = load_snapshot(deep)
    check("sec-deep-but-invalid", s is None, "deep JSON is just rejected")
    huge = " " * (MAX_SNAPSHOT_BYTES + 1)
    s, errs = load_snapshot(huge)
    check("sec-oversized", s is None and any("safety cap" in e for e in errs), str(errs))

    print("== Policies are inert data ==")
    # Hostile-shaped VALUES inside an otherwise valid policy must load as plain
    # inert strings — never executed — and stay rejectable where structurally
    # invalid.
    inert_names = [
        ("shell value", "x; rm -rf /"),
        ("python expression value", "__import__('os').system('id')"),
        ("template value", "{{ 7*7 }}"),
    ]
    for name, val in inert_names:
        text = f"policy: CUSTOM\npolicy_version: 1\nname: {val!r}\n"
        data, errs = load_policy(text)
        # Inert: loads as data (never executed) OR is rejected — never a crash.
        check(f"sec-policy-{name}-inert", data is not None or bool(errs), str(errs))
        if data is not None:
            check(f"sec-policy-{name}-kept-literal", data["name"] == val,
                  repr(data.get("name")))

    hostile_policies = [
        ("unknown field with exec", "policy: CUSTOM\npolicy_version: 1\nexec: 'os.system(\"id\")'\n"),
        ("bad fail_on type", "policy: CUSTOM\npolicy_version: 1\nfail_on: 42\n"),
        ("negative threshold", "policy: CUSTOM\npolicy_version: 1\nthresholds:\n  max_new_review_items: -3\n"),
        ("unknown threshold", "policy: CUSTOM\npolicy_version: 1\nthresholds:\n  evil: 1\n"),
        ("policy as list", "- a\n- b\n"),
        ("not yaml", ":::(((("),
        ("rule id injection", "policy: CUSTOM\npolicy_version: 1\nfail_on_new_rules:\n  - 'SDC-069; import os'\n"),
    ]
    for name, text in hostile_policies:
        data, errs = load_policy(text)
        check(f"sec-policy-{name}", data is None and errs, str(errs))

    # Valid policy with python-looking harmless strings must load as data and
    # never execute anything.
    weird = {
        "policy": "CUSTOM", "policy_version": 1,
        "name": "__import__('os').system('id')",
        "fail_on": {"new_blockers": True},
    }
    data, errs = load_policy(json.dumps(weird))
    check("sec-policy-weird-name-inert", data is not None and errs == [] and
          data["name"] == weird["name"], str(errs))

    print("== YAML bombs must not crash ==")
    yaml_bombs = [
        "a: &a [1,2,3]\nb: *a\n",
        "a: &a {x: 1}\nb: *a\nc: *a\n",
    ]
    for i, bomb in enumerate(yaml_bombs):
        try:
            data, errs = load_policy(bomb)
            # Either rejected as invalid policy, or validated — never a crash.
            check(f"sec-yaml-bomb-{i}", True)
        except Exception as e:  # pragma: no cover
            check(f"sec-yaml-bomb-{i}", False, f"CRASH: {e}")

    print("== Duplicate / malformed identity fields ==")
    bad_finding = dict(snap["findings"][0]) if snap["findings"] else {}
    if bad_finding:
        bad_finding["identity"] = {"rule_id": ["evil", "list"]}
        mutated = json.loads(json.dumps(snap))
        mutated["findings"] = [bad_finding]
        s, errs = load_snapshot(json.dumps(mutated))
        # identity with non-scalar fields is tolerated structurally but the
        # rebuild must coerce to safe scalars (no crash anywhere downstream).
        if s is not None:
            from finding_identity import identity_from_dict
            ident = identity_from_dict(s["findings"][0].get("identity") or {})
            check("sec-identity-coercion", isinstance(ident.rule_id, str), str(ident.rule_id))
        else:
            check("sec-identity-coercion", True)

    print()
    print(f"PH13 security: {len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("FAILED:", ", ".join(FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
