"""Phase 13 — structured finding identity (message-independent)."""

import pytest

from finding_identity import (
    IDENTITY_VERSION, STRENGTH_STRUCTURED, STRENGTH_LEGACY,
    FT_CLOCK_REFERENCE, FT_IO_DELAY, FT_INTERACTION, FT_RULE,
    canon_number, extract_command_fields,
    identity_from_commands, identity_from_interaction,
    identity_from_dict, identity_keys, identity_legacy, identity_simple,
    make_identity_key,
)


# ── Numeric canonicalization ─────────────────────────────────────────────────

class TestCanonNumber:
    def test_trailing_zeros(self):
        assert canon_number("2.0") == "2"
        assert canon_number("2.000") == "2"
        assert canon_number("0.50") == "0.5"

    def test_scientific_notation(self):
        assert canon_number("2.5e-1") == "0.25"
        assert canon_number("1e3") == "1000"
        assert canon_number("0.25") == "0.25"


# ── Command field extraction ─────────────────────────────────────────────────

class TestExtractCommandFields:
    def test_io_delay_fields(self):
        f = extract_command_fields(
            "set_input_delay -max 2.0 -clock clk_core [get_ports din]")
        assert f["command"] == "set_input_delay"
        assert f["primary_object"] == "din"
        assert f["clock"] == "clk_core"
        assert f["value"] == "2"
        assert f["mode"] == "max"

    def test_dual_endpoints(self):
        f = extract_command_fields(
            "set_false_path -from [get_clocks clk_a] -to [get_pins u_reg/D]")
        assert f["primary_object"] == "clk_a"
        assert f["secondary_object"] == "u_reg/D"
        assert f["command"] == "set_false_path"

    def test_generated_clock_source_as_clock(self):
        f = extract_command_fields(
            "create_generated_clock -name div2 -source [get_ports clk] "
            "-divide_by 2 [get_pins u_div/Q]")
        assert f["clock"] == "clk"
        assert f["primary_object"] == "clk"
        assert f["secondary_object"] == "u_div/Q"

    def test_min_max_modes(self):
        f = extract_command_fields(
            "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]")
        assert f["mode"] == "max,min"  # sorted

    def test_edges_and_setup_hold(self):
        f = extract_command_fields(
            "set_clock_uncertainty -setup 0.2 -hold 0.05 -rise "
            "-from [get_clocks a] -to [get_clocks b]")
        assert f["setup_hold"] == "hold,setup"
        assert f["edge"] == "rise"

    def test_empty_text(self):
        assert extract_command_fields("   ") == {}


# ── Message independence (the core Phase 13 invariant) ───────────────────────

class TestMessageIndependence:
    def test_rewording_does_not_change_key(self):
        cmd = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        f1, b1, _, s1 = make_identity_key("SDC-008", "error", "old wording: delay too large",
                                          cmd_text=cmd)
        f2, b2, _, s2 = make_identity_key("SDC-008", "error", "brand new explanation",
                                          cmd_text=cmd)
        assert f1 == f2
        assert b1 == b2
        assert s1 == s2 == STRENGTH_STRUCTURED

    def test_different_objects_do_not_collide(self):
        a = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        b = "set_input_delay -max 2.0 -clock clk_core [get_ports din2]"
        fa, _, _, _ = make_identity_key("SDC-008", "error", "m", cmd_text=a)
        fb, _, _, _ = make_identity_key("SDC-008", "error", "m", cmd_text=b)
        assert fa != fb

    def test_same_message_different_commands_do_not_collide(self):
        a = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        b = "set_output_delay -max 2.0 -clock clk_core [get_ports din]"
        fa, _, _, _ = make_identity_key("SDC-008", "error", "identical msg",
                                        cmd_text=a)
        fb, _, _, _ = make_identity_key("SDC-009", "error", "identical msg",
                                        cmd_text=b)
        assert fa != fb

    def test_numeric_formatting_does_not_change_key(self):
        a = "set_input_delay -max 2.000 -clock clk_core [get_ports din]"
        b = "set_input_delay -max 2.5e-1 -clock clk_core [get_ports din]"
        # 2.000 → 2 vs 0.25 → different VALUE: value changes must be CHANGED,
        # so the full key differs while the base key stays identical.
        fa, ba, _, _ = make_identity_key("SDC-008", "error", "m", cmd_text=a)
        fb, bb, _, _ = make_identity_key("SDC-008", "error", "m", cmd_text=b)
        assert fa != fb
        assert ba == bb


# ── Severity change semantics ────────────────────────────────────────────────

class TestSeverityChange:
    def test_severity_part_of_full_key_not_base(self):
        cmd = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        fw, bw, _, _ = make_identity_key("SDC-008", "warning", "m", cmd_text=cmd)
        fe, be, _, _ = make_identity_key("SDC-008", "error", "m", cmd_text=cmd)
        assert fw != fe      # severity change ⇒ CHANGED (via base match)
        assert bw == be      # same underlying engineering condition


# ── Bus ranges are object identity ───────────────────────────────────────────

class TestBusRangeIdentity:
    def test_distinct_ranges_do_not_collide(self):
        a = "set_input_delay -max 2.0 -clock clk_core [get_ports {data[3:0]}]"
        b = "set_input_delay -max 2.0 -clock clk_core [get_ports {data[7:4]}]"
        fa, _, _, _ = make_identity_key("SDC-066", "warning", "partial bus m",
                                        cmd_text=a)
        fb, _, _, _ = make_identity_key("SDC-066", "warning", "partial bus m",
                                        cmd_text=b)
        assert fa != fb

    def test_range_is_not_value_blanked(self):
        a = "set_input_delay -max 2.0 -clock clk_core [get_ports {data[3:0]}]"
        b = "set_input_delay -max 2.0 -clock clk_core [get_ports {data[7:4]}]"
        _, ba, _, _ = make_identity_key("SDC-066", "warning", "m", cmd_text=a)
        _, bb, _, _ = make_identity_key("SDC-066", "warning", "m", cmd_text=b)
        assert ba != bb  # ranges survive base-key value blanking


# ── Dual-constraint identity ─────────────────────────────────────────────────

class TestDualConstraintIdentity:
    def test_symmetric_relationship_canonicalizes_pair_order(self):
        a = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        b = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        i1 = identity_from_commands("SDC-067", a, b, canonicalize_pair=True,
                                    interaction_type="EXACT_DUPLICATE")
        i2 = identity_from_commands("SDC-067", b, a, canonicalize_pair=True,
                                    interaction_type="EXACT_DUPLICATE")
        assert i1.full_key() == i2.full_key()

    def test_override_preserves_direction(self):
        a = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        b = "set_input_delay -max 4.0 -clock clk_core [get_ports din]"
        i_fwd = identity_from_commands("SDC-068", a, b, canonicalize_pair=False,
                                       interaction_type="OVERRIDE")
        i_rev = identity_from_commands("SDC-068", b, a, canonicalize_pair=False,
                                       interaction_type="OVERRIDE")
        assert i_fwd.full_key() != i_rev.full_key()  # direction matters

    def test_override_value_change_is_changed_not_new(self):
        a = "set_input_delay -max 2.0 -clock clk_core [get_ports din]"
        b1 = "set_input_delay -max 4.0 -clock clk_core [get_ports din]"
        b2 = "set_input_delay -max 5.0 -clock clk_core [get_ports din]"
        i1 = identity_from_commands("SDC-068", a, b1, canonicalize_pair=False,
                                    interaction_type="OVERRIDE")
        i2 = identity_from_commands("SDC-068", a, b2, canonicalize_pair=False,
                                    interaction_type="OVERRIDE")
        assert i1.full_key() != i2.full_key()   # value changed
        assert i1.base_key() == i2.base_key()   # same condition ⇒ CHANGED


# ── Interaction identity (Phase 10 records) ──────────────────────────────────

class TestInteractionIdentity:
    def test_symmetric_endpoints_canonicalize(self):
        i1 = identity_from_interaction(
            "SDC-069", "DEFINITE_CONFLICT", "set_max_delay",
            frozenset({"data_a"}), frozenset({"data_b"}), "clk_core",
            "2", "4", "max", direction_preserved=False)
        i2 = identity_from_interaction(
            "SDC-069", "DEFINITE_CONFLICT", "set_max_delay",
            frozenset({"data_b"}), frozenset({"data_a"}), "clk_core",
            "2", "4", "max", direction_preserved=False)
        assert i1.full_key() == i2.full_key()

    def test_different_endpoints_do_not_collide(self):
        i1 = identity_from_interaction(
            "SDC-070", "POSSIBLE_CONFLICT", "set_false_path",
            frozenset({"clk_a"}), frozenset({"clk_b"}), "",
            "", "", "", direction_preserved=True)
        i2 = identity_from_interaction(
            "SDC-070", "POSSIBLE_CONFLICT", "set_false_path",
            frozenset({"clk_a"}), frozenset({"clk_c"}), "",
            "", "", "", direction_preserved=True)
        assert i1.full_key() != i2.full_key()

    def test_interaction_type_part_of_identity(self):
        i1 = identity_from_interaction(
            "SDC-070", "POSSIBLE_CONFLICT", "set_false_path",
            frozenset({"a"}), frozenset({"b"}), "", "", "", "",
            direction_preserved=True)
        i2 = identity_from_interaction(
            "SDC-070", "REDUNDANT", "set_false_path",
            frozenset({"a"}), frozenset({"b"}), "", "", "", "",
            direction_preserved=True)
        assert i1.full_key() != i2.full_key()


# ── Legacy fallback honesty ──────────────────────────────────────────────────

class TestLegacyFallback:
    def test_message_derived_is_never_structured(self):
        full, base, ident, strength = make_identity_key(
            "SDC-066", "warning", "input bus 'data_in' partially constrained")
        assert strength == STRENGTH_LEGACY
        assert ident["strength"] == STRENGTH_LEGACY

    def test_legacy_normalization_stable_across_formatting(self):
        i1 = identity_legacy("SDC-066",
                             "input bus 'data_in' is only partially constrained: 2 bits")
        i2 = identity_legacy("SDC-066",
                             "input    bus 'data_in' is only partially constrained: 2.000 bits")
        assert i1.full_key() == i2.full_key()

    def test_legacy_strips_line_references(self):
        # Frozen Phase 12 regex handles "line 42 and 99" (both line refs).
        i1 = identity_legacy("SDC-046", "undefined clock ref line 42 and 99")
        i2 = identity_legacy("SDC-046", "undefined clock ref")
        assert i1.full_key() == i2.full_key()

    def test_legacy_normalization_is_frozen_to_phase12(self):
        # The legacy key space must NEVER change (v1 baseline compat). Verify
        # the exact Phase 12 regex behavior: "line 42 and 99" strips fully,
        # "line 42 and line 99" strips only the first (old behavior).
        i1 = identity_legacy("SDC-046", "undefined clock ref line 42 and 99")
        i2 = identity_legacy("SDC-046", "undefined clock ref line 42 and line 99")
        assert i1.full_key() != i2.full_key()  # frozen: second form leaves 'and line 99'


# ── Round-trip and helpers ───────────────────────────────────────────────────

class TestRoundTrip:
    def test_identity_dict_round_trip(self):
        ident = identity_from_commands(
            "SDC-008", "set_input_delay -max 2.0 -clock clk_core [get_ports din]")
        rebuilt = identity_from_dict(ident.to_dict())
        assert rebuilt.full_key() == ident.full_key()
        assert rebuilt.base_key() == ident.base_key()
        assert rebuilt.strength == STRENGTH_STRUCTURED

    def test_identity_from_dict_tolerates_malformed(self):
        rebuilt = identity_from_dict({"rule_id": "SDC-055", "strength": [1, 2]})
        assert rebuilt.rule_id == "SDC-055"
        assert rebuilt.strength == STRENGTH_STRUCTURED  # non-scalar → default

    def test_identity_keys_include_severity_only_in_full(self):
        ident = identity_simple("SDC-059", primary_object="din")
        full, base = identity_keys(ident, "warning")
        assert full[-1] == "warning"
        assert base == list(ident.base_key())

    def test_simple_identity(self):
        ident = identity_simple("SDC-059", primary_object="din",
                                finding_type=FT_IO_DELAY, mode="max")
        assert ident.finding_type == FT_IO_DELAY
        assert ident.primary_object == "din"
        assert ident.strength == STRENGTH_STRUCTURED

    def test_version_constant(self):
        assert IDENTITY_VERSION == 1
