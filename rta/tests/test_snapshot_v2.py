"""Phase 13 — snapshot schema v2, v1 migration, structural fingerprint."""

import json

import pytest

from checker import check_sdc
from design_context import parse_verilog
from readiness_diff import (
    SCHEMA_VERSION, FINGERPRINT_VERSION, ACCEPTED_SCHEMA_VERSIONS,
    INCOMPATIBLE, PARTIALLY_COMPARABLE,
    build_snapshot, classify_compatibility, design_fingerprint,
    diff_snapshots, finding_identity, load_snapshot, snapshot_migration_status,
    snapshot_to_json,
)
from finding_identity import STRENGTH_STRUCTURED

CLEAN = (
    "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n"
    "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
    "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n"
)


def _netlist(ports="input clk, input [3:0] d, output [1:0] q", body="",
             instances=""):
    return (
        f"module top ({ports});\n"
        f"  {body}\n"
        f"  {instances}\n"
        "endmodule\n"
    )


# ── Schema v2 basics ─────────────────────────────────────────────────────────

class TestSchemaV2:
    def test_snapshot_is_schema_v2(self):
        snap = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        assert snap["schema_version"] == SCHEMA_VERSION == 2
        assert snap["identity_version"] == 1
        assert snap["capabilities"]["structured_identity"] is True
        assert snap["migration"]["migration_status"] == "NATIVE"
        assert snap["analysis"]["design_fingerprint"] == ""

    def test_findings_carry_identity_and_strength(self):
        snap = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        assert snap["findings"]
        for f in snap["findings"]:
            assert "full_id" in f and "base_id" in f
            assert isinstance(f.get("identity"), dict)
            assert f.get("identity_strength") in ("STRUCTURED", "LEGACY_NORMALIZED")

    def test_round_trip(self):
        snap = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        text = snapshot_to_json(snap)
        loaded, errs = load_snapshot(text)
        assert errs == []
        assert loaded["schema_version"] == 2
        assert loaded["findings"] == snap["findings"]

    def test_json_serializable(self):
        snap = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        json.dumps(snap)  # must not raise


# ── v1 compatibility / migration ─────────────────────────────────────────────

def _downgrade_to_v1(snap: dict) -> dict:
    """Simulate a REAL Phase 12 schema-v1 snapshot.

    Phase 12 stored the legacy message-normalized key directly in
    full_id/base_id and had no identity/strength/capabilities fields. This is
    the exact shape a genuine v1 baseline file would have.
    """
    v1 = json.loads(json.dumps(snap))
    v1["schema_version"] = 1
    v1.pop("identity_version", None)
    v1.pop("capabilities", None)
    for f in v1.get("findings", []):
        lf, lb = finding_identity(f.get("code", ""), f.get("severity", "info"),
                                  f.get("msg", ""))
        f["full_id"], f["base_id"] = list(lf), list(lb)
        f.pop("identity", None)
        f.pop("identity_strength", None)
        f.pop("tier", None)
        f.pop("legacy_full_id", None)
        f.pop("legacy_base_id", None)
    for f in v1.get("interactions", []):
        lf, lb = finding_identity(f.get("code", ""), f.get("severity", "info"),
                                  f.get("msg", ""))
        f["full_id"], f["base_id"] = list(lf), list(lb)
        f.pop("identity", None)
        f.pop("identity_strength", None)
        f.pop("tier", None)
        f.pop("legacy_full_id", None)
        f.pop("legacy_base_id", None)
    v1["migration"] = {"original_schema_version": 1,
                       "current_schema_version": 1,
                       "migration_status": "NATIVE"}
    return v1


class TestMigration:
    def test_v1_snapshot_loads(self):
        v2 = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        v1 = _downgrade_to_v1(v2)
        loaded, errs = load_snapshot(snapshot_to_json(v1))
        assert errs == []
        assert loaded["schema_version"] == 1

    def test_v1_vs_v2_is_partially_comparable(self):
        v2 = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        v1 = _downgrade_to_v1(v2)
        status, reasons = classify_compatibility(v1, v2)
        assert status == PARTIALLY_COMPARABLE
        assert any("schema version differs" in r for r in reasons)

    def test_v1_vs_v2_identical_evidence_no_regression(self):
        v2 = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        v1 = _downgrade_to_v1(v2)
        d = diff_snapshots(v1, v2)
        assert d["classification"] in ("NEUTRAL_CHANGE", "IMPROVEMENT")
        assert not d["findings"]["new_blockers"]
        assert not d["findings"]["resolved_blockers"]

    def test_migration_status_values(self):
        v2 = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        v1 = _downgrade_to_v1(v2)
        assert snapshot_migration_status(v2)["migration_status"] == "NATIVE"
        assert snapshot_migration_status(v1)["migration_status"] == "MIGRATED"
        bogus = {"schema_version": 99}
        assert snapshot_migration_status(bogus)["migration_status"] == INCOMPATIBLE

    def test_v1_legacy_comparison_ignores_formatting(self):
        v2 = build_snapshot(check_sdc(CLEAN), source_name="t.sdc")
        v1 = _downgrade_to_v1(v2)
        reformatted = CLEAN.replace("10.0", "10").replace("\n", "\n\n")
        cur = build_snapshot(check_sdc(reformatted), source_name="t.sdc")
        d = diff_snapshots(v1, cur)
        assert not d["findings"]["new_blockers"]
        assert not d["findings"]["new_review"]


# ── Structural fingerprint v2 ────────────────────────────────────────────────

class TestFingerprint:
    def _ctx(self, text):
        outcome = parse_verilog(text)
        assert not outcome.errors, outcome.errors
        return outcome.context

    def test_formatting_is_invisible(self):
        v1 = _netlist(body="wire w; assign w = clk;")
        v2 = "module top ( input clk, input [3:0] d, output [1:0] q );\n" \
             "   // comment\n\n   wire   w ;\n   assign w = clk ;\nendmodule\n"
        assert design_fingerprint(self._ctx(v1)) == design_fingerprint(self._ctx(v2))

    def test_module_order_is_irrelevant(self):
        a = ("module flop (input c, input d, output q); endmodule\n"
             "module top (input clk, output q);\n"
             "  flop u0 (.c(clk), .q(q));\n"
             "endmodule\n")
        b = ("module top (input clk, output q);\n"
             "  flop u0 (.c(clk), .q(q));\n"
             "endmodule\n"
             "module flop (input c, input d, output q); endmodule\n")
        assert design_fingerprint(self._ctx(a)) == design_fingerprint(self._ctx(b))

    def test_instance_order_is_irrelevant(self):
        a = ("module top (input a, input b, output y);\n"
             "  buf u1 (.a(a));\n"
             "  buf u2 (.a(b));\n"
             "endmodule\n")
        b = ("module top (input a, input b, output y);\n"
             "  buf u2 (.a(b));\n"
             "  buf u1 (.a(a));\n"
             "endmodule\n")
        assert design_fingerprint(self._ctx(a)) == design_fingerprint(self._ctx(b))

    def test_added_port_changes_fingerprint(self):
        base = _netlist()
        extended = _netlist(ports="input clk, input [3:0] d, input en, output [1:0] q")
        assert design_fingerprint(self._ctx(base)) != \
            design_fingerprint(self._ctx(extended))

    def test_bus_width_change_changes_fingerprint(self):
        narrow = _netlist(ports="input clk, input [3:0] d, output q")
        wide = _netlist(ports="input clk, input [7:0] d, output q")
        assert design_fingerprint(self._ctx(narrow)) != \
            design_fingerprint(self._ctx(wide))

    def test_top_module_change_changes_fingerprint(self):
        a = _netlist(ports="input clk, output q")
        b = "module other (input a, output b); endmodule\n" + a
        ctx_a = self._ctx(a)                                # top = top
        out_b = parse_verilog(b, top="other")              # top = other
        assert not out_b.errors, out_b.errors
        assert design_fingerprint(ctx_a) != design_fingerprint(out_b.context)

    def test_no_context_is_empty(self):
        assert design_fingerprint(None) == ""

    def test_snapshot_records_fingerprint(self):
        ctx = self._ctx(_netlist())
        snap = build_snapshot(check_sdc(CLEAN), context=ctx, source_name="t.sdc")
        assert snap["analysis"]["design_fingerprint"]
        assert snap["analysis"]["fingerprint_version"] == FINGERPRINT_VERSION
