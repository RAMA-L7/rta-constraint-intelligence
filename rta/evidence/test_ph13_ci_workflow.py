"""Phase 13 — end-to-end CI workflow suite (CLI level).

Exercises the documented workflow through the actual CLI:
  save baseline  →  modify SDC  →  compare + gate  →  exit code contract

Run:  python benchmarks/test_ph13_ci_workflow.py
Exit: 0 = all pass.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "production_hardening", "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def _cli(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, os.path.join(ROOT, "cli.py"), *args],
                          capture_output=True, text=True, env=env, cwd=ROOT)


PASSED = []
FAILED = []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + ("  " + detail if detail else ""))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        sdc = os.path.join(tmp, "design.sdc")
        base_json = os.path.join(tmp, "baseline.json")

        with open(sdc, "w", encoding="utf-8") as f:
            f.write(_read("clean.sdc"))

        print("== 1. Save baseline ==")
        r = _cli("check", sdc, "--save-baseline", base_json)
        check("wf-save-baseline", r.returncode == 0, r.stderr[-300:])
        with open(base_json, encoding="utf-8") as f:
            snap = json.load(f)
        check("wf-schema-v2", snap["schema_version"] == 2, str(snap.get("schema_version")))

        print("== 2. Identical revision + gate = PASS (exit 0) ==")
        r = _cli("check", sdc, "--baseline", base_json,
                 "--gate", "NO_READINESS_REGRESSION")
        check("wf-gate-pass", r.returncode == 0, f"exit={r.returncode} {r.stderr[-300:]}")

        print("== 3. Harmless formatting + gate = PASS ==")
        fmt = os.path.join(tmp, "design_fmt.sdc")
        with open(fmt, "w", encoding="utf-8") as f:
            f.write("# comment\n\n" + _read("clean.sdc").replace("10.0", "10"))
        r = _cli("check", fmt, "--baseline", base_json,
                 "--gate", "NO_READINESS_REGRESSION")
        check("wf-format-pass", r.returncode == 0, f"exit={r.returncode} {r.stderr[-300:]}")

        print("== 4. New blocker + gate = FAIL (exit 1) ==")
        bad = os.path.join(tmp, "design_bad.sdc")
        with open(bad, "w", encoding="utf-8") as f:
            f.write(_read("blocker.sdc"))
        r = _cli("check", bad, "--baseline", base_json,
                 "--gate", "NO_READINESS_REGRESSION")
        check("wf-gate-fail-blocker", r.returncode == 1,
              f"exit={r.returncode} {r.stderr[-300:]}")

        print("== 5. BLOCKERS_ONLY works without baseline ==")
        r = _cli("check", bad, "--gate", "BLOCKERS_ONLY")
        check("wf-blockers-only-blocked", r.returncode == 1, f"exit={r.returncode}")
        r = _cli("check", sdc, "--gate", "BLOCKERS_ONLY")
        check("wf-blockers-only-clean", r.returncode == 0, f"exit={r.returncode}")

        print("== 6. CUSTOM policy file ==")
        pol = os.path.join(tmp, "legacy.yml")
        with open(pol, "w", encoding="utf-8") as f:
            f.write(open(os.path.join(ROOT, "rta", "examples", "policies", "legacy_project.yml"),
                         encoding="utf-8").read())
        r = _cli("check", bad, "--baseline", base_json,
                 "--gate", "CUSTOM", "--gate-policy", pol)
        check("wf-custom-new-blocker-fails", r.returncode == 1, f"exit={r.returncode}")
        r = _cli("check", sdc, "--baseline", base_json,
                 "--gate", "CUSTOM", "--gate-policy", pol)
        check("wf-custom-clean-passes", r.returncode == 0, f"exit={r.returncode}")

        print("== 7. Invalid policy = exit 2 ==")
        bad_pol = os.path.join(tmp, "bad.yml")
        with open(bad_pol, "w", encoding="utf-8") as f:
            f.write("policy: CUSTOM\npolicy_version: 1\nevil: true\n")
        r = _cli("check", sdc, "--baseline", base_json,
                 "--gate", "CUSTOM", "--gate-policy", bad_pol)
        check("wf-invalid-policy-exit2", r.returncode == 2, f"exit={r.returncode}")

        print("== 8. CUSTOM without policy = exit 2 ==")
        r = _cli("check", sdc, "--baseline", base_json, "--gate", "CUSTOM")
        check("wf-custom-no-policy-exit2", r.returncode == 2, f"exit={r.returncode}")

        print("== 9. Malformed baseline = exit 2 (never PASS) ==")
        bad_base = os.path.join(tmp, "bad_baseline.json")
        with open(bad_base, "w", encoding="utf-8") as f:
            f.write("{corrupt")
        r = _cli("check", sdc, "--baseline", bad_base,
                 "--gate", "NO_READINESS_REGRESSION")
        check("wf-malformed-baseline-exit2", r.returncode == 2, f"exit={r.returncode}")

        print("== 10. Missing baseline for regression gate = exit 2 ==")
        r = _cli("check", sdc, "--gate", "NO_READINESS_REGRESSION")
        check("wf-no-baseline-exit2", r.returncode == 2, f"exit={r.returncode}")

        print("== 11. JSON artifact includes readiness_diff + gate ==")
        out_json = os.path.join(tmp, "out.json")
        r = _cli("check", bad, "--baseline", base_json,
                 "--gate", "NO_READINESS_REGRESSION",
                 "--json", "--output", out_json)
        with open(out_json, encoding="utf-8") as f:
            data = json.load(f)
        rd = data.get("readiness_diff") or {}
        check("wf-json-has-diff", "readiness" in rd, str(list(rd.keys())))
        check("wf-json-has-gate", rd.get("gate", {}).get("result") == "FAIL",
              str(rd.get("gate")))

        print("== 12. Baseline update workflow (explicit regen) ==")
        # Engineer approves, intentionally regenerates the baseline, commits it.
        # The SDC still has errors, so the plain check exits 1 — but the
        # baseline must have been WRITTEN (the exit reflects the SDC, not the
        # baseline write).
        r = _cli("check", bad, "--save-baseline", base_json)
        check("wf-baseline-regen", os.path.exists(base_json) and
              os.path.getsize(base_json) > 0, r.stderr[-200:])
        with open(base_json, encoding="utf-8") as f:
            check("wf-baseline-regen-schema",
                  json.load(f).get("schema_version") == 2)
        r = _cli("check", bad, "--baseline", base_json,
                 "--gate", "NO_READINESS_REGRESSION")
        check("wf-regen-gate-passes", r.returncode == 0, f"exit={r.returncode}")

    print()
    print(f"PH13 CI workflow: {len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("FAILED:", ", ".join(FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
