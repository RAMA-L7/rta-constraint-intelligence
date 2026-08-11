"""
Unit tests for the Phase 12 readiness-diff / baseline / CI-gate module.

Covers: finding identity normalization, multiset delta (incl. per-key index
bookkeeping), snapshot validation/round-trip, baseline compatibility,
regression classification, and the gate policy/exit-code contract.
"""

import json

import pytest

import readiness_diff as rd
from checker import check_sdc


CLEAN = """set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
"""


def _snap(text=CLEAN, engine_failed=False):
    s = rd.build_snapshot(check_sdc(text), source_name="t.sdc")
    if engine_failed:
        s["analysis"]["engine_failed"] = True
    return s


# ── Normalization / identity ────────────────────────────────────────────────

class TestNormalizeMsg:
    def test_canonicalizes_numbers(self):
        assert rd.normalize_msg("delay 2.0ns") == "delay 2ns"
        assert rd.normalize_msg("delay 2.000ns") == "delay 2ns"
        assert rd.normalize_msg("delay 2.5e-1ns") == "delay 0.25ns"

    def test_strips_line_references(self):
        a = rd.normalize_msg("conflict on line 18 and line 42")
        b = rd.normalize_msg("conflict on line 42 and line 18")
        assert a == b

    def test_strip_numbers_blanking(self):
        a = rd.normalize_msg("value 11.0 vs 12.5", strip_numbers=True)
        b = rd.normalize_msg("value 1 vs 99", strip_numbers=True)
        assert a == b

    def test_collapses_whitespace(self):
        assert rd.normalize_msg("  a   b\n\t c ") == "a b c"


class TestFindingIdentity:
    def test_full_id_differs_when_value_changes(self):
        f1, _ = rd.finding_identity("SDC-008", "error",
                                    "set_input_delay 11.0ns exceeds clock period 10.0ns")
        f2, _ = rd.finding_identity("SDC-008", "error",
                                    "set_input_delay 12.5ns exceeds clock period 10.0ns")
        assert f1 != f2

    def test_base_id_same_when_value_changes(self):
        _, b1 = rd.finding_identity("SDC-008", "error",
                                    "set_input_delay 11.0ns exceeds clock period 10.0ns")
        _, b2 = rd.finding_identity("SDC-008", "error",
                                    "set_input_delay 12.5ns exceeds clock period 10.0ns")
        assert b1 == b2

    def test_identity_is_not_line_number(self):
        _, b1 = rd.finding_identity("SDC-049", "warning",
                                    "case analysis on line 7 contradicts line 12")
        _, b2 = rd.finding_identity("SDC-049", "warning",
                                    "case analysis on line 99 contradicts line 200")
        assert b1 == b2

    def test_bus_ranges_are_object_identity_not_values(self):
        # data[3:0] and data[7:4] are DIFFERENT findings (different bits of a
        # partial bus) — they must never merge via number-blanking.
        f1, b1 = rd.finding_identity("SDC-066", "warning",
                                     "bus 'data_in' partial: data[3:0] only")
        f2, b2 = rd.finding_identity("SDC-066", "warning",
                                     "bus 'data_in' partial: data[7:4] only")
        assert f1 != f2 and b1 != b2

    def test_single_bit_select_kept(self):
        _, b1 = rd.finding_identity("SDC-055", "error", "object data[7] not found")
        _, b2 = rd.finding_identity("SDC-055", "error", "object data[0] not found")
        assert b1 != b2

    def test_plain_value_still_blanked(self):
        _, b1 = rd.finding_identity("SDC-008", "error", "delay 11.0ns exceeds period 10.0ns")
        _, b2 = rd.finding_identity("SDC-008", "error", "delay 12.5ns exceeds period 10.0ns")
        assert b1 == b2


# ── Multiset delta ──────────────────────────────────────────────────────────

class TestMultisetDelta:
    def _rec(self, code, sev, msg):
        full, base = rd.finding_identity(code, sev, msg)
        return {"code": code, "severity": sev, "msg": msg,
                "full_id": list(full), "base_id": list(base), "tier": ""}

    def test_exact_duplicates_match(self):
        a = self._rec("SDC-008", "error", "delay 11.0ns exceeds period")
        b = self._rec("SDC-008", "error", "delay 11.0ns exceeds period")
        d = rd._multiset_delta([a], [b])
        assert d["unchanged"] == 1 and not d["new"] and not d["resolved"]

    def test_two_changed_across_distinct_groups(self):
        # Regression test: the used-index set used to collide across
        # different base_id groups (both groups' first candidate is index 0),
        # mis-pairing SDC-068 as NEW+RESOLVED.
        a1 = self._rec("SDC-008", "error", "delay 11.0ns exceeds period 10.0ns")
        a2 = self._rec("SDC-068", "info", "value 2.0 on line 4 overridden by 11.0 on line 6")
        b1 = self._rec("SDC-008", "error", "delay 12.5ns exceeds period 10.0ns")
        b2 = self._rec("SDC-068", "info", "value 2.0 on line 4 overridden by 12.5 on line 6")
        d = rd._multiset_delta([a1, a2], [b1, b2])
        assert len(d["changed"]) == 2, f"changed={d['changed']}"
        assert not d["new"] and not d["resolved"]

    def test_multiset_duplicates(self):
        a = self._rec("SDC-067", "info", "duplicate on objects din")
        b = self._rec("SDC-067", "info", "duplicate on objects din")
        d = rd._multiset_delta([a, a], [a, b])
        assert d["unchanged"] == 2


# ── Snapshot validation / round-trip ────────────────────────────────────────

class TestSnapshot:
    def test_round_trip(self):
        s = _snap()
        js = rd.snapshot_to_json(s)
        s2, errs = rd.load_snapshot(js)
        assert not errs and s2 is not None
        assert s2["readiness"]["overall"] == s["readiness"]["overall"]

    def test_validate_rejects_missing_keys(self):
        snap, errs = rd.load_snapshot('{"schema_version": 1}')
        assert snap is None and errs

    def test_validate_rejects_bad_json(self):
        snap, errs = rd.load_snapshot("this is not json")
        assert snap is None and errs

    def test_validate_rejects_wrong_schema(self):
        s = _snap()
        s["schema_version"] = 99
        errs = rd.validate_snapshot(s)
        assert any("schema_version" in e for e in errs)

    def test_validate_rejects_oversized(self):
        huge = '{"x": "' + "a" * (rd.MAX_SNAPSHOT_BYTES + 100) + '"}'
        snap, errs = rd.load_snapshot(huge)
        assert snap is None and errs

    def test_snapshot_records_engine_failure(self):
        s = _snap(engine_failed=True)
        assert s["analysis"]["engine_failed"] is True


# ── Compatibility ───────────────────────────────────────────────────────────

class TestCompatibility:
    def test_same_context_compatible(self):
        a, b = _snap(), _snap()
        status, reasons = rd.classify_compatibility(a, b)
        assert status == rd.COMPATIBLE

    def test_top_change_context_change(self):
        a = _snap()
        b = _snap()
        b["analysis"]["top_module"] = "other"
        status, _ = rd.classify_compatibility(a, b)
        assert status == rd.COMPATIBLE_WITH_CONTEXT_CHANGE

    def test_schema_mismatch_incompatible(self):
        a = _snap()
        b = _snap()
        b["schema_version"] = 99
        status, _ = rd.classify_compatibility(a, b)
        assert status == rd.INCOMPATIBLE

    def test_mode_change_partially_comparable(self):
        a = _snap()
        b = _snap()
        b["analysis"]["mode"] = "DESIGN_AWARE"
        status, reasons = rd.classify_compatibility(a, b)
        assert status == rd.PARTIALLY_COMPARABLE
        assert any("mode" in r for r in reasons)

    def test_tool_version_mismatch_flags_staleness(self):
        a = _snap()
        b = _snap()
        b["tool_version"] = "0.9.9-old"
        status, reasons = rd.classify_compatibility(a, b)
        assert status == rd.COMPATIBLE_WITH_CONTEXT_CHANGE
        assert any("version" in r for r in reasons)


# ── Classification ──────────────────────────────────────────────────────────

class TestClassification:
    def test_line_movement_is_neutral(self):
        moved = ("# comment moved\nset sdc_version 2.2\n"
                 "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n"
                 "set_propagated_clock [get_clocks clk_core]\n"
                 "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
                 "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n")
        d = rd.diff_snapshots(_snap(), _snap(moved))
        assert d["classification"] == rd.NEUTRAL_CHANGE
        assert not d["findings"]["new"]

    def test_new_blocker_is_blocking(self):
        bad = CLEAN + "set_input_delay -max 12.0 -clock ghost [get_ports din2]\n"
        d = rd.diff_snapshots(_snap(), _snap(bad))
        assert d["classification"] == rd.BLOCKING_REGRESSION
        assert [f["code"] for f in d["findings"]["new_blockers"]] == ["SDC-046"]

    def test_resolved_blocker_is_improvement(self):
        bad = CLEAN + "set_input_delay -max 12.0 -clock ghost [get_ports din2]\n"
        d = rd.diff_snapshots(_snap(bad), _snap())
        assert d["classification"] == rd.IMPROVEMENT

    def test_engine_failure_class(self):
        d = rd.diff_snapshots(_snap(), _snap(engine_failed=True))
        assert d["classification"] == rd.ENGINE_FAILURE

    def test_new_duplicate_only_is_advisory(self):
        dup = CLEAN + "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
        d = rd.diff_snapshots(_snap(), _snap(dup))
        assert d["classification"] == rd.ADVISORY_REGRESSION


# ── CI gates ────────────────────────────────────────────────────────────────

class TestGates:
    def test_blockers_only_clean(self):
        g = rd.evaluate_gate(rd.POLICY_BLOCKERS_ONLY, None, _snap(), {})
        assert g["result"] == "PASS" and g["exit_code"] == rd.EXIT_PASS

    def test_blockers_only_blocked(self):
        bad = CLEAN + "set_input_delay -max 12.0 -clock ghost [get_ports din2]\n"
        g = rd.evaluate_gate(rd.POLICY_BLOCKERS_ONLY, None, _snap(bad), {})
        assert g["result"] == "FAIL" and g["exit_code"] == rd.EXIT_GATE_FAILED

    def test_no_regression_needs_baseline(self):
        g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, None, _snap(), {})
        assert g["result"] == "FAIL" and g["exit_code"] == rd.EXIT_INVALID

    def test_engine_failure_never_passes(self):
        cur = _snap(engine_failed=True)
        for policy in (rd.POLICY_BLOCKERS_ONLY, rd.POLICY_NO_REGRESSION, rd.POLICY_STRICT):
            g = rd.evaluate_gate(policy, _snap(), cur, rd.diff_snapshots(_snap(), cur))
            assert g["result"] == "FAIL" and g["exit_code"] == rd.EXIT_ENGINE_FAILURE

    def test_incompatible_baseline_exit_2(self):
        bad = _snap()
        bad["schema_version"] = 99
        g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, bad, _snap(),
                             rd.diff_snapshots(bad, _snap()))
        assert g["result"] == "FAIL" and g["exit_code"] == rd.EXIT_INVALID

    def test_unknown_policy(self):
        g = rd.evaluate_gate("BOGUS", None, _snap(), {})
        assert g["result"] == "NOT_CONFIGURED" and g["exit_code"] == rd.EXIT_INVALID

    def test_baseline_aware_old_blocker_passes(self):
        bad = CLEAN + "set_input_delay -max 12.0 -clock ghost [get_ports din2]\n"
        b = _snap(bad)
        c = _snap(bad)
        d = rd.diff_snapshots(b, c)
        g = rd.evaluate_gate(rd.POLICY_NO_REGRESSION, b, c, d)
        assert g["result"] == "PASS" and g["exit_code"] == rd.EXIT_PASS

    def test_json_serializable(self):
        bad = CLEAN + "set_input_delay -max 12.0 -clock ghost [get_ports din2]\n"
        d = rd.diff_snapshots(_snap(), _snap(bad))
        json.dumps(d)  # must not raise
