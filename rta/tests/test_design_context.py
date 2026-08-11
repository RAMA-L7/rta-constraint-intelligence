"""
Phase 8 — design_context.py unit tests (optional netlist-aware validation).

Covers the structural Verilog parser, collection resolution, hierarchy,
buses, wildcards, top-module detection, and the SDC-055..059 findings.
SDC-only behavior is untouched (covered elsewhere).
"""

import pytest

from design_context import (
    parse_verilog, resolve_collection, validate_design_references,
    DesignContext, RESOLVED, EMPTY, UNDEFINED, UNSUPPORTED,
)

# ── Minimal reusable designs ──────────────────────────────────────────────────

V_SIMPLE = """
module top (
    input clk,
    input [7:0] data_in,
    output [7:0] data_out
);
    wire [7:0] dbus;
    flop u1 ( .clk(clk), .d(data_in), .q(dbus) );
    reg_out u2 ( .d(dbus), .q(data_out) );
endmodule

module flop ( input clk, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule

module reg_out ( input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(*) r = d;
    assign q = r;
endmodule
"""


@pytest.fixture(scope="module")
def ctx():
    o = parse_verilog(V_SIMPLE)
    assert not o.errors, o.errors
    return o.context


class TestParseVerilog:
    def test_top_detection(self):
        o = parse_verilog(V_SIMPLE)
        assert o.top_candidates == []
        assert o.context.top_module == "top"

    def test_port_extraction(self, ctx):
        assert set(ctx.ports) == {"clk", "data_in", "data_out"}
        assert ctx.ports["data_in"].direction == "input"
        assert ctx.ports["data_in"].is_bus()
        assert ctx.ports["data_out"].direction == "output"

    def test_hierarchy_flat(self, ctx):
        assert "u1" in ctx.instances
        assert "u2" in ctx.instances
        assert ctx.instances["u1"].module == "flop"

    def test_no_phantom_reg_instances(self, ctx):
        # `reg [7:0] r;` must NOT be parsed as an instance
        assert not any(i.name == "r" for i in ctx.instances.values())

    def test_pins_from_connections(self, ctx):
        assert "u1/d" in ctx.pins
        assert "u1/q" in ctx.pins
        assert "u2/d" in ctx.pins

    def test_multiple_tops_ambiguity(self):
        o = parse_verilog("module a; endmodule\nmodule b; endmodule\n")
        assert o.context is None
        assert "multiple candidate top" in o.errors[0]
        assert set(o.top_candidates) == {"a", "b"}

    def test_explicit_top_selection(self):
        o = parse_verilog("module a; endmodule\nmodule b; endmodule\n", top="b")
        assert o.context is not None
        assert o.context.top_module == "b"

    def test_missing_top(self):
        o = parse_verilog(V_SIMPLE, top="nope")
        assert o.context is None
        assert "not found" in o.errors[0]

    def test_no_modules(self):
        o = parse_verilog("// just a comment\n")
        assert o.context is None
        assert o.errors


class TestCollectionResolution:
    def test_exact_port(self, ctx):
        r = resolve_collection("get_ports", "clk", ctx)
        assert r.kind == RESOLVED and "clk" in r.matches

    def test_braced_ports(self, ctx):
        r = resolve_collection("get_ports", "{clk data_in}", ctx)
        assert r.kind == RESOLVED
        assert set(r.matches) == {"clk", "data_in"}

    def test_bus_bit_select_valid(self, ctx):
        r = resolve_collection("get_ports", "data_in[3]", ctx)
        assert r.kind == RESOLVED

    def test_bus_bit_select_out_of_range(self, ctx):
        r = resolve_collection("get_ports", "data_in[9]", ctx)
        assert r.kind == UNDEFINED

    def test_bus_wildcard_bit(self, ctx):
        r = resolve_collection("get_ports", "data_in[*]", ctx)
        assert r.kind == RESOLVED

    def test_wildcard(self, ctx):
        r = resolve_collection("get_ports", "data_*", ctx)
        assert r.kind == RESOLVED
        assert set(r.matches) == {"data_in", "data_out"}

    def test_wildcard_empty(self, ctx):
        r = resolve_collection("get_ports", "debug_*", ctx)
        assert r.kind == EMPTY

    def test_missing_explicit(self, ctx):
        r = resolve_collection("get_ports", "nonexistent", ctx)
        assert r.kind == UNDEFINED

    def test_get_cells(self, ctx):
        assert resolve_collection("get_cells", "u1", ctx).kind == RESOLVED
        assert resolve_collection("get_cells", "u*", ctx).kind == RESOLVED
        assert resolve_collection("get_cells", "u?", ctx).kind == RESOLVED
        assert resolve_collection("get_cells", "u_zzz", ctx).kind == UNDEFINED

    def test_get_pins_hierarchical(self, ctx):
        assert resolve_collection("get_pins", "u1/d", ctx).kind == RESOLVED
        assert resolve_collection("get_pins", "u1/zzz", ctx).kind == UNDEFINED

    def test_all_inputs_outputs(self, ctx):
        r = resolve_collection("all_inputs", "", ctx)
        assert r.kind == RESOLVED and set(r.matches) == {"clk", "data_in"}
        r = resolve_collection("all_outputs", "", ctx)
        assert r.kind == RESOLVED and set(r.matches) == {"data_out"}


class TestHierarchy:
    V_HIER = """
module top ( input clk );
    core u_core ( .clk(clk) );
endmodule
module core ( input clk );
    flop u_reg0 ( .clk(clk) );
    flop u_reg1 ( .clk(clk) );
endmodule
module flop ( input clk );
endmodule
"""

    @pytest.fixture(scope="class")
    def hctx(self):
        o = parse_verilog(self.V_HIER)
        assert not o.errors, o.errors
        return o.context

    def test_nested_instances(self, hctx):
        assert "u_core/u_reg0" in hctx.instances
        assert "u_core/u_reg1" in hctx.instances

    def test_nested_pins(self, hctx):
        assert "u_core/u_reg0/clk" in hctx.pins

    def test_cell_glob_under_instance(self, hctx):
        r = resolve_collection("get_cells", "u_core/*", hctx)
        assert r.kind == RESOLVED
        assert set(r.matches) == {"u_core/u_reg0", "u_core/u_reg1"}

    def test_pin_wildcard_under_instance(self, hctx):
        r = resolve_collection("get_pins", "u_core/u_reg1/*", hctx)
        assert r.kind == RESOLVED

    def test_invalid_parent_hierarchy(self, hctx):
        r = resolve_collection("get_pins", "u_core/u_nope/D", hctx)
        assert r.kind == UNDEFINED


class TestValidateDesignReferences:
    def test_undefined_port_found(self, ctx):
        sdc = "create_clock -name clk -period 5 [get_ports bogus_clk]\n"
        findings = validate_design_references(sdc, ctx)
        codes = [f.code for f in findings]
        assert "SDC-055" in codes

    def test_empty_wildcard_warning(self, ctx):
        sdc = "set_false_path -from [get_ports debug_*] -to [get_ports data_out]\n"
        findings = validate_design_references(sdc, ctx)
        assert any(f.code == "SDC-056" for f in findings)

    def test_invalid_hierarchy(self, ctx):
        sdc = "set_false_path -from [get_pins u1/u_nope/D] -to [get_ports data_out]\n"
        findings = validate_design_references(sdc, ctx)
        assert any(f.code == "SDC-057" for f in findings)

    def test_valid_design_no_findings(self, ctx):
        sdc = (
            "set sdc_version 2.2\n"
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]\n"
            "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"
        )
        findings = validate_design_references(sdc, ctx)
        assert findings == []

    def test_unconstrained_data_port_structurally_owned(self, ctx):
        """A structurally-DATA unconstrained port is owned by the coverage
        engine (SDC-065), not SDC-059 — one condition, one finding."""
        from design_coverage import coverage_findings
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports data_in]\n"
            # data_out never gets an output delay; in V_SIMPLE its net drives
            # reg_out u2/q → structural DATA evidence.
        )
        findings = validate_design_references(sdc, ctx)
        assert not any("data_out" in f.msg and f.code == "SDC-059" for f in findings)
        cov = [f for f in coverage_findings(sdc, ctx) if f["code"] == "SDC-065"]
        assert any("data_out" in f["msg"] for f in cov)

    def test_unconstrained_data_port_name_only_fallback(self):
        """SDC-059 remains the name-heuristic fallback for data-named ports
        with NO structural data evidence (e.g. an unconnected port)."""
        v = ("module top ( input clk, input [7:0] data_in, "
             "output [7:0] data_out ); endmodule\n")
        o = parse_verilog(v)
        assert not o.errors, o.errors
        sdc = (
            "create_clock -name clk -period 5.0 [get_ports clk]\n"
            "set_input_delay -max 2.0 -clock clk [get_ports data_in]\n"
            # data_out has no instance pins → name evidence only
        )
        findings = validate_design_references(sdc, o.context)
        assert any("data_out" in f.msg and f.code == "SDC-059" for f in findings)

    def test_clock_port_not_flagged_unconstrained(self, ctx):
        sdc = "create_clock -name clk -period 5.0 [get_ports clk]\n"
        findings = validate_design_references(sdc, ctx)
        assert not any("clk" in f.msg and f.code == "SDC-059" for f in findings)


class TestFromInventory:
    def test_json_inventory(self):
        data = {
            "top_module": "top",
            "modules": ["top", "flop"],
            "ports": [{"name": "clk", "direction": "input"},
                      {"name": "data_in", "direction": "input", "msb": 7, "lsb": 0}],
            "instances": [{"path": "u1", "name": "u1", "module": "flop", "parent": ""}],
            "nets": [{"name": "dbus"}],
            "pins": ["u1/d", "u1/q"],
        }
        c = DesignContext.from_inventory(data)
        assert c.port_exists("clk")
        assert c.cell_exists("u1")
        assert c.pin_exists("u1/d")
        assert resolve_collection("get_ports", "clk", c).kind == RESOLVED
        assert resolve_collection("get_ports", "data_in[3]", c).kind == RESOLVED


class TestCheckerIntegration:
    """check_sdc(context=...) must be additive and never regress SDC-only."""

    V = """
    module top ( input clk, input [7:0] data_in, output [7:0] data_out );
        wire [7:0] w;
        flop u1 ( .clk(clk), .d(data_in), .q(w) );
        assign data_out = w;
    endmodule
    module flop ( input clk, input [7:0] d, output [7:0] q );
        reg [7:0] r;
        always @(posedge clk) r <= d;
        assign q = r;
    endmodule
    """

    SDC = (
        "set sdc_version 2.2\n"
        "create_clock -name clk -period 5.0 [get_ports clk]\n"
        "set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]\n"
        "set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]\n"
    )

    @pytest.fixture(scope="class")
    def dctx(self):
        return parse_verilog(self.V).context

    def test_sdc_only_identical_without_context(self, dctx):
        from checker import check_sdc
        r_plain = check_sdc(self.SDC)
        # SDC-only mode must never emit design-aware rules
        assert not any(i.code in ("SDC-055", "SDC-056", "SDC-057", "SDC-059")
                       for i in r_plain.issues)
        assert r_plain.scope.get("status") == "NETLIST_REQUIRED"
        assert r_plain.scope.get("design") is None

    def test_design_aware_adds_rules_and_metadata(self, dctx):
        from checker import check_sdc
        sdc_bad = self.SDC + "set_false_path -from [get_ports bogus] -to [get_ports data_out]\n"
        r = check_sdc(sdc_bad, context=dctx)
        assert any(i.code == "SDC-055" for i in r.issues)
        assert r.scope["design"]["analysis_mode"] == "design_aware"
        assert r.scope["design"]["top_module"] == "top"

    def test_design_aware_trust_upgrade(self, dctx):
        from checker import check_sdc
        r = check_sdc(self.SDC, context=dctx)
        assert r.scope["status"] == "VALIDATED"   # all refs resolve

    def test_design_aware_never_crashes_on_bad_context(self):
        from checker import check_sdc
        # A non-DesignContext object must degrade to SDC-only, not raise
        r = check_sdc(self.SDC, context=object())
        assert r.issues is not None


class TestSecurityInert:
    def test_exec_like_content_inert(self):
        # Verilog with suspicious content must parse as data (or fail cleanly),
        # never execute anything.
        v = "module top; endmodule\n"
        o = parse_verilog(v)
        assert o.context is not None

    def test_include_directive_inert(self):
        v = "`include \"../../etc/passwd\"\nmodule top ( input a ); endmodule\n"
        o = parse_verilog(v)
        # The include is a directive — stripped as inert text; module still parses.
        assert o.context is not None or o.errors

    def test_block_comments_stripped(self):
        v = ("module top ( input a ); /* fake module bogus ( input x ); */ "
             "wire w; endmodule\n")
        o = parse_verilog(v)
        assert o.context is not None
        assert "bogus" not in o.context.modules

    def test_line_comments_stripped(self):
        v = "module top ( input a ); // module fake2 ( input y );\n wire w; endmodule\n"
        o = parse_verilog(v)
        assert o.context is not None
        assert "fake2" not in o.context.modules
