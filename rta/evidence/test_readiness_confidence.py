"""Phase 11 — False-confidence / false-blocker readiness tests.

FALSE CONFIDENCE (never READY when a deterministic blocker exists or when
critical semantics were not understood for the claimed mode):
  - every deterministic blocker rule must make overall != READY
  - unsupported/partial analysis must not yield READY

FALSE BLOCKER (never BLOCKED merely because of):
  - INFO duplicates (SDC-067)
  - INFO overrides (SDC-068)
  - STA-required exception overlap (SDC-070)
  - heuristic advisory (SDC-020/030 style)
  - optional missing netlist in SDC-only mode
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from checker import check_sdc, InfoItem  # noqa: E402

PASS = FAIL = 0


def ok(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  ❌ {msg}")


def base_sdc():
    return [
        "set sdc_version 2.2",
        "create_clock -name c -period 10.0 [get_ports clk]",
        "set_propagated_clock [get_clocks c]",
        "set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]",
        "set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]",
    ]


def main() -> int:
    print("READINESS FALSE-CONFIDENCE / FALSE-BLOCKER")

    # ── False-confidence: each deterministic blocker forces != READY ─────────
    blocker_cases = [
        ("SDC-001 no clocks", ["set_input_delay -max 1 -clock x [get_ports din]"]),
        ("SDC-002 duplicate clock", [
            "create_clock -name c -period 10 [get_ports clk]",
            "create_clock -name c -period 5 [get_ports clk2]"]),
        ("SDC-008 input delay >= period", [
            "create_clock -name c -period 10 [get_ports clk]",
            "set_input_delay -max 12 -clock c [get_ports din]"]),
        ("SDC-046 undefined clock", [
            "create_clock -name c -period 10 [get_ports clk]",
            "set_input_delay -max 1 -clock ghost [get_ports din]"]),
        ("SDC-049 contradictory case", [
            "create_clock -name c -period 10 [get_ports clk]",
            "set_case_analysis 0 [get_ports mode]",
            "set_case_analysis 1 [get_ports mode]"]),
        ("SDC-069 max<min window", [
            "create_clock -name c -period 10 [get_ports clk]",
            "set_max_delay 5 -from [get_ports a] -to [get_ports b]",
            "set_min_delay 8 -from [get_ports a] -to [get_ports b]"]),
    ]
    for name, extra in blocker_cases:
        text = "\n".join(base_sdc() + extra)
        r = check_sdc(text)
        overall = (r.readiness or {}).get("overall")
        ok(overall not in ("READY", "READY_WITH_ADVISORIES"),
           f"FALSE-CONFIDENCE {name}: overall={overall} must not be READY*")

    # ── False-blocker: info-level findings must never BLOCK ──────────────────
    ok_cases = [
        ("duplicate SDC-067", [
            "set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]",
            "set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]"]),
        ("override SDC-068", [
            "set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]",
            "set_input_delay -max 2.5 -min 0.5 -clock c [get_ports din]"]),
        ("exception overlap SDC-070", [
            "set_false_path -from [get_ports a] -to [get_ports b]",
            "set_multicycle_path 2 -from [get_ports a] -to [get_ports b]"]),
    ]
    for name, extra in ok_cases:
        text = "\n".join(base_sdc() + extra)
        r = check_sdc(text)
        overall = (r.readiness or {}).get("overall")
        ok(overall != "BLOCKED", f"FALSE-BLOCKER {name}: overall={overall} must not be BLOCKED")
        ok(overall != "INSUFFICIENT_CONTEXT",
           f"FALSE-BLOCKER {name}: must not be INSUFFICIENT_CONTEXT")

    # ── Heuristic advisory must not BLOCK (SDC-030 style, review tier) ──────
    # Drop set_propagated_clock (index 2) → SDC-030 fires → REVIEW_REQUIRED,
    # never BLOCKED.
    s_heuristic = "\n".join(base_sdc()[:2] + base_sdc()[3:])
    r = check_sdc(s_heuristic)
    ok((r.readiness or {}).get("overall") != "BLOCKED",
       f"heuristic advisory (SDC-030) must not BLOCK (got {(r.readiness or {}).get('overall')})")

    # ── Missing netlist must never BLOCK in SDC-only mode ────────────────────
    s_nonet = "\n".join(base_sdc())
    r = check_sdc(s_nonet)
    ok((r.readiness or {}).get("overall") != "BLOCKED",
       "missing netlist must not BLOCK in SDC-only mode")

    # ── Engine failure (SDC-140) must never yield READY/READY_WITH_ADVISORIES —
    # evidence is incomplete, the claim is capped at REVIEW_REQUIRED.
    s_ok = "\n".join(base_sdc())
    r = check_sdc(s_ok)
    r.info.append(InfoItem("SDC-140", "Clock relation analysis skipped: boom"))
    from constraint_readiness import analyze_readiness
    rdy = analyze_readiness(r)
    ok(rdy.overall in ("REVIEW_REQUIRED", "BLOCKED", "INSUFFICIENT_CONTEXT"),
       f"engine failure must not yield READY* (got {rdy.overall})")
    ok(bool(rdy.engine_failed), "engine_failed flag must be set")

    # ── SDC-007 (name heuristic) must not BLOCK handoff ───────────────────────
    s_sdc007 = "\n".join([
        "create_clock -name c -period 10 [get_ports data_clk]",
        "set_propagated_clock [get_clocks c]",
        "set_input_delay -max 2.0 -min 0.5 -clock c [get_ports din]",
        "set_output_delay -max 3.0 -min 1.0 -clock c [get_ports dout]",
    ])
    r = check_sdc(s_sdc007)
    ok(any(i.code == "SDC-007" for i in r.issues),
       "SDC-007 fires on data_clk clock port (name heuristic)")
    ok((r.readiness or {}).get("overall") != "BLOCKED",
       f"SDC-007 name heuristic must not BLOCK (got {(r.readiness or {}).get('overall')})")

    print(f"READINESS FALSE-CONFIDENCE / FALSE-BLOCKER: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
