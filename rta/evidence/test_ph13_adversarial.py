"""Phase 13 — adversarial false-NEW / false-RESOLVED / false-CI testing.

Tries to trick the diff + gate into:
  - reporting RESOLVED+NEW for an unchanged semantic finding (message change,
    line movement, numeric formatting, comments, CRLF, variables, option order)
  - a false CI PASS (hiding a new blocker / engine failure / incompatible
    baseline / trust regression behind formatting)
  - a false CI FAIL (harmless formatting failing the gate)
  - identity collisions between different semantic findings

Run:  python benchmarks/test_ph13_adversarial.py
Exit: 0 = all pass.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from checker import check_sdc
from finding_identity import make_identity_key, identity_from_interaction
from readiness_diff import (
    EXIT_ENGINE_FAILURE, build_snapshot, diff_snapshots, evaluate_gate,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "production_hardening", "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


CLEAN = _read("clean.sdc")
BLOCKER = _read("blocker.sdc")


def _snap(text):
    return build_snapshot(check_sdc(text), source_name="t.sdc")


PASSED = []
FAILED = []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + ("  " + detail if detail else ""))


def main():
    print("== False NEW / false RESOLVED attacks ==")

    # 1. Line movement (50 comment lines prepended).
    moved = "\n".join(f"# filler {i}" for i in range(50)) + "\n" + CLEAN
    d = diff_snapshots(_snap(CLEAN), _snap(moved))
    check("adv-line-movement", not d["findings"]["new"] and not d["findings"]["resolved"],
          f"new={d['findings']['new']}")

    # 2. CRLF + trailing whitespace.
    crlf = CLEAN.replace("\n", "\r\n").replace("  ", " \t")
    d = diff_snapshots(_snap(CLEAN), _snap(crlf))
    check("adv-crlf", not d["findings"]["new"] and not d["findings"]["resolved"])

    # 3. Tcl variable substitution (set PER 10.0; $PER used later).
    var = ("set PER 10.0\n"
           "create_clock -name clk_core -period $PER [get_ports clk_core]\n"
           "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
           "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n")
    d = diff_snapshots(_snap(CLEAN), _snap(var))
    check("adv-variable", not d["findings"]["new"] and not d["findings"]["resolved"],
          f"new={d['findings']['new']}")

    # 4. Scientific notation equivalent.
    sci = CLEAN.replace("10.0", "1e1").replace("2.0", "2.0e0").replace("0.5", "5e-1")
    d = diff_snapshots(_snap(CLEAN), _snap(sci))
    check("adv-scientific", not d["findings"]["new"] and not d["findings"]["resolved"],
          f"new={d['findings']['new']}")

    # 5. Valid option reordering (legal — min/max order swapped).
    reordered = CLEAN.replace("set_input_delay -max 2.0 -min 0.5",
                              "set_input_delay -min 0.5 -max 2.0")
    d = diff_snapshots(_snap(CLEAN), _snap(reordered))
    check("adv-option-order", not d["findings"]["new"] and not d["findings"]["resolved"],
          f"new={d['findings']['new']}")

    print("== Message independence (structured findings) ==")
    # The same command producing a blocker must not change identity when the
    # human-readable message changes (verified at the key level).
    cmd = "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]"
    f1, _, _, s1 = make_identity_key("SDC-046", "error", "old wording", cmd)
    f2, _, _, s2 = make_identity_key("SDC-046", "error", "new wording", cmd)
    check("adv-message-independence", f1 == f2 and s1 == s2 == "STRUCTURED")

    print("== Identity collisions ==")
    a = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
    b = "set_output_delay -max 2.0 -clock clk_core [get_ports din]"
    fa, _, _, _ = make_identity_key("SDC-008", "error", "same msg", a)
    fb, _, _, _ = make_identity_key("SDC-009", "error", "same msg", b)
    check("adv-collision-cmd", fa != fb, "different commands must not collide")

    i1 = identity_from_interaction("SDC-070", "POSSIBLE_CONFLICT", "set_false_path",
                                   frozenset({"clk_a"}), frozenset({"clk_b"}),
                                   "", "", "", "", direction_preserved=True)
    i2 = identity_from_interaction("SDC-070", "POSSIBLE_CONFLICT", "set_false_path",
                                   frozenset({"clk_a"}), frozenset({"clk_c"}),
                                   "", "", "", "", direction_preserved=True)
    check("adv-collision-endpoints", i1.full_key() != i2.full_key())

    print("== False CI PASS attacks ==")
    base = _snap(CLEAN)
    # A new blocker hidden behind a giant commented header must still FAIL.
    hidden = ("# " + "x" * 5000 + "\n") + BLOCKER
    cur = _snap(hidden)
    d = diff_snapshots(base, cur)
    g = evaluate_gate("NO_READINESS_REGRESSION", base, cur, d)
    check("adv-false-pass-new-blocker",
          g["result"] == "FAIL" and g["exit_code"] == 1,
          f"{g} class={d['classification']}")

    # Engine failure must never PASS even under a permissive CUSTOM policy.
    from policy_engine import load_policy
    legacy, errs = load_policy(
        open(os.path.join(HERE, "..", "..", "rta", "examples", "policies", "legacy_project.yml"),
             encoding="utf-8").read())
    assert errs == [], errs
    cur_failed = _snap(CLEAN)
    cur_failed["analysis"]["engine_failed"] = True
    d = diff_snapshots(base, cur_failed)
    g = evaluate_gate("CUSTOM", base, cur_failed, d, policy_data=legacy)
    check("adv-false-pass-engine", g["result"] == "FAIL" and
          g["exit_code"] == EXIT_ENGINE_FAILURE, str(g))

    print("== False CI FAIL attacks ==")
    # Harmless formatting must not fail a strict gate.
    fmt = "# comment\n\n" + CLEAN.replace("10.0", "10").replace("\n", "\n")
    cur = _snap(fmt)
    d = diff_snapshots(base, cur)
    for pol in ("NO_READINESS_REGRESSION", "STRICT"):
        g = evaluate_gate(pol, base, cur, d)
        check(f"adv-false-fail-{pol}", g["result"] == "PASS", str(g))

    # Resolved old debt must not fail a regression gate.
    cur_clean = _snap(CLEAN)
    d = diff_snapshots(_snap(BLOCKER), cur_clean)
    g = evaluate_gate("NO_READINESS_REGRESSION", _snap(BLOCKER), cur_clean, d)
    check("adv-resolved-debt-passes", g["result"] == "PASS", str(g))

    print()
    print(f"PH13 adversarial: {len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("FAILED:", ", ".join(FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
