"""
Phase 3 regression tests — verified P0/P1 fixes.

Each test encodes a finding verified in Phase 2 (GOLDEN_BENCHMARK_VERIFICATION_REPORT.md)
with an independently derived expected result. These are permanent regression
targets, not snapshots of current behavior.
"""

import pytest

from checker import check_sdc
from converter import parse_sdc
from clock_relations import analyze_clock_relations
from sdc_preprocess import preprocess_sdc, parse_number, parse_collection, logical_text


# ── Shared preprocessing primitives ───────────────────────────────────────────

class TestPreprocess:
    def test_comments_stripped(self):
        cmds = preprocess_sdc("# create_clock -name fake -period 1.0 [get_ports fake]\n"
                              "create_clock -name real -period 10.0 [get_ports clk]")
        texts = [c.text for c in cmds]
        assert len(cmds) == 1
        assert "fake" not in texts[0]

    def test_continuation_joined(self):
        cmds = preprocess_sdc("create_clock \\\n"
                              "    -name sys_clk \\\n"
                              "    -period 10.0 \\\n"
                              "    [get_ports clk]")
        assert len(cmds) == 1
        assert "-name sys_clk" in cmds[0].text
        assert "-period 10.0" in cmds[0].text
        assert "[get_ports clk]" in cmds[0].text

    def test_continuation_provenance(self):
        cmds = preprocess_sdc("create_clock \\\n    -name c \\\n    -period 5.0 [get_ports clk]")
        assert cmds[0].start_line == 1
        assert cmds[0].end_line == 3

    def test_hash_inside_braces_not_comment(self):
        cmds = preprocess_sdc("set_waveform -rise {1 # 2} [get_ports a]\n")
        # '#' inside braces is literal; the command survives intact
        assert any("#" in c.text for c in cmds)

    def test_hash_inside_brackets_not_comment(self):
        cmds = preprocess_sdc("set_dont_touch [get_cells u#1]")
        assert any("[get_cells u#1]" in c.text for c in cmds)

    def test_hash_inside_quotes_not_comment(self):
        cmds = preprocess_sdc('set_dont_touch -lib_cell "BUF#X2"')
        assert any('"BUF#X2"' in c.text for c in cmds)

    def test_sdc130_uses_original_comments(self):
        """SDC-130 corner-context must read ORIGINAL comment lines, not the
        comment-stripped logical text (reviewer regression fix)."""
        text = ("# CORNER: SSG_0P72V_M40C\n"
                "create_clock -name clk -period 5.0 [get_ports clk]\n"
                "set_operating_conditions -max WORST\n")
        r = check_sdc(text)
        assert not [i for i in r.info if i.code == "SDC-130"], "corner comment present → SDC-130 must not fire"


class TestParseNumber:
    @pytest.mark.parametrize("s,expected", [
        ("10", 10.0), ("10.0", 10.0), ("0.25", 0.25),
        ("2.5e-1", 0.25), ("1e-3", 0.001), ("1E+2", 100.0),
        ("-0.25", -0.25),
    ])
    def test_legal_formats(self, s, expected):
        assert parse_number(s) == pytest.approx(expected)

    def test_sci_never_partial(self):
        assert parse_number("2.5e-1") != 2.5  # the old \d+ bug


class TestParseCollection:
    def test_braced_list(self):
        assert parse_collection("{clk_a clk_b}") == ["clk_a", "clk_b"]

    def test_bracketed_braced(self):
        assert parse_collection("[get_clocks {clk_a clk_b}]") == ["clk_a", "clk_b"]

    def test_single(self):
        assert parse_collection("[get_clocks clk_a]") == ["clk_a"]

    def test_three(self):
        assert parse_collection("[get_clocks {clk_a clk_b clk_c}]") == ["clk_a", "clk_b", "clk_c"]


# ── Phase 4 — bounded Tcl variable support ──────────────────────────────────

class TestTclVariables:
    def test_period_variable_resolved(self):
        text = ("set CLK_PERIOD 2.5\n"
                "create_clock -name core_clk -period $CLK_PERIOD [get_ports clk]\n")
        p = parse_sdc(text)
        assert p.clocks[0].period == pytest.approx(2.5)

    def test_braced_name_form(self):
        text = ("set PERIOD 5.0\n"
                "create_clock -name c -period ${PERIOD} [get_ports clk]\n")
        p = parse_sdc(text)
        assert p.clocks[0].period == pytest.approx(5.0)

    def test_order_aware_reassignment(self):
        """set PERIOD 10 … clock a … set PERIOD 5 … clock b → a=10, b=5."""
        text = ("set PERIOD 10\n"
                "create_clock -name a -period $PERIOD [get_ports clk_a]\n"
                "set PERIOD 5\n"
                "create_clock -name b -period $PERIOD [get_ports clk_b]\n")
        p = parse_sdc(text)
        by = {c.name: c.period for c in p.clocks}
        assert by["a"] == pytest.approx(10.0)
        assert by["b"] == pytest.approx(5.0)

    def test_undefined_variable_preserved(self):
        """Unresolved tokens must NOT be silently zeroed or deleted."""
        text = ("create_clock -name c -period $UNKNOWN [get_ports clk]\n")
        cmds = preprocess_sdc(text)
        assert "$UNKNOWN" in cmds[0].text
        # converter reports a 0.0/missing period but does not crash
        p = parse_sdc(text)
        assert len(p.clocks) == 1

    def test_similar_names_not_confused(self):
        """$CLK2 must not become 10 + '2'."""
        text = ("set CLK 10\nset CLK2 5\n"
                "create_clock -name a -period $CLK [get_ports a]\n"
                "create_clock -name b -period $CLK2 [get_ports b]\n")
        p = parse_sdc(text)
        by = {c.name: c.period for c in p.clocks}
        assert by["a"] == pytest.approx(10.0)
        assert by["b"] == pytest.approx(5.0)

    def test_braced_and_plain(self):
        text = ("set P 7.5\n"
                "create_clock -name a -period $P [get_ports a]\n"
                "create_clock -name b -period ${P} [get_ports b]\n")
        p = parse_sdc(text)
        assert all(c.period == pytest.approx(7.5) for c in p.clocks)

    def test_empty_value(self):
        text = "set EMPTY {}\ncreate_clock -name c -period $EMPTY [get_ports clk]\n"
        p = parse_sdc(text)  # must not crash
        assert len(p.clocks) == 1

    def test_negative_and_sci_in_variable(self):
        text = ("set DLY -0.25\nset RATE 2.5e-1\n"
                "create_clock -name c -period $RATE [get_ports clk]\n"
                "set_input_delay -max $DLY -min 0.1 -clock c [all_inputs]\n")
        p = parse_sdc(text)
        assert p.clocks[0].period == pytest.approx(0.25)

    def test_variable_for_clock_name(self):
        text = ("set NAME core_clk\n"
                "create_clock -name $NAME -period 5.0 [get_ports clk]\n")
        p = parse_sdc(text)
        assert p.clocks[0].name == "core_clk"

    def test_variable_across_multiline(self):
        text = ("set CLK_PERIOD 10.0\n"
                "create_clock \\\n"
                "    -name sys_clk \\\n"
                "    -period $CLK_PERIOD \\\n"
                "    [get_ports clk]\n")
        p = parse_sdc(text)
        assert p.clocks[0].period == pytest.approx(10.0)

    def test_set_commands_not_sdc_confused(self):
        """set_input_delay / set_clock_groups must NOT be treated as `set`."""
        text = ("set CLK_PERIOD 2.5\n"
                "create_clock -name c -period $CLK_PERIOD [get_ports clk]\n"
                "set_input_delay -max 6.0 -min 0.2 -clock c [all_inputs]\n")
        r = check_sdc(text)
        assert any(i.code == "SDC-008" for i in r.issues), [i.code for i in r.issues]

    def test_golden_c08_end_to_end(self):
        """c08: $CLK_PERIOD=2.5, $IN_DLY=6.0 → SDC-008 after resolution."""
        text = ("set CLK_PERIOD 2.5\nset IN_DLY 6.0\n"
                "create_clock -name core_clk -period $CLK_PERIOD [get_ports clk]\n"
                "set_input_delay -max $IN_DLY -min 0.2 -clock core_clk [all_inputs]\n"
                "set_output_delay -max 1.0 -min 0.2 -clock core_clk [all_outputs]\n")
        r = check_sdc(text)
        assert sorted({i.code for i in r.issues if i.sev == "error"}) == ["SDC-008"]
        assert r.stats["Clocks"] == 1
        p = parse_sdc(text)
        by = {c.name: c.period for c in p.clocks}
        assert by["core_clk"] == pytest.approx(2.5)

    def test_logical_text_substitutes(self):
        text = "set P 3.3\ncreate_clock -name c -period $P [get_ports clk]\n"
        joined = logical_text(text)
        assert "-period 3.3" in joined
        assert "$P" not in joined

    def test_no_variable_fastpath_unchanged(self):
        text = "create_clock -name c -period 5.0 [get_ports clk]\n"
        assert preprocess_sdc(text)[0].text == "create_clock -name c -period 5.0 [get_ports clk]"

    def test_variable_reused_across_many_commands(self):
        """One variable reused in many commands resolves everywhere (no state loss)."""
        text = "set P 3.3\n" + "".join(
            f"create_clock -name c{i} -period $P [get_ports p{i}]\n" for i in range(20)
        )
        p = parse_sdc(text)
        assert len(p.clocks) == 20
        assert all(c.period == pytest.approx(3.3) for c in p.clocks)

    def test_no_cross_contamination_between_blocks(self):
        """Each preprocess call is independent (no global variable state)."""
        cmds1 = preprocess_sdc("set P 1.0\ncreate_clock -name a -period $P [get_ports a]\n")
        cmds2 = preprocess_sdc("create_clock -name b -period $P [get_ports b]\n")
        assert any("-period 1.0" in c.text for c in cmds1)
        assert any("$P" in c.text for c in cmds2), "variables must not leak across calls"

    def test_dollar_substituted_inside_quotes_with_braces(self):
        """Reviewer fix: braces inside double quotes are literal; $ must still
        be substituted there (Tcl substitutes inside "..." strings)."""
        cmds = preprocess_sdc(
            "set P 5.0\nset_dont_use -lib_cell \"BUF#X2 { $P }\" [get_lib_cells]\n")
        assert any('"BUF#X2 { 5.0 }"' in c.text for c in cmds), [c.text for c in cmds]


# ── F01 / c01 / c19 — comments must not create phantom constraints ──────────

class TestCommentNoPhantom:
    def test_comment_only_clock_line(self):
        text = ("# create_clock -name fake_clk -period 1.0 [get_ports fake_clk]\n"
                "create_clock -name real_clk -period 10.0 [get_ports clk]\n"
                "set_input_delay -max 1.0 -min 0.2 -clock real_clk [all_inputs]\n"
                "set_output_delay -max 1.0 -min 0.2 -clock real_clk [all_outputs]\n")
        r = check_sdc(text)
        assert r.stats["Clocks"] == 1, [i.code for i in r.issues]
        assert not [i for i in r.issues if i.code == "SDC-002"]  # no phantom duplicate
        # converter agrees
        p = parse_sdc(text)
        assert [c.name for c in p.clocks] == ["real_clk"]

    def test_inline_comment_after_command(self):
        text = ("create_clock -name real_clk -period 10 [get_ports clk] # master clock\n"
                "set_input_delay -max 1.0 -min 0.2 -clock real_clk [all_inputs] # setup\n"
                "set_output_delay -max 1.0 -min 0.2 -clock real_clk [all_outputs] # load\n")
        r = check_sdc(text)
        assert r.stats["Clocks"] == 1
        assert not r.errors


# ── F03 / c03 — multiline create_clock ───────────────────────────────────────

class TestMultilineClock:
    def test_multiline_create_clock(self):
        text = ("create_clock \\\n"
                "    -name sys_clk \\\n"
                "    -period 10.0 \\\n"
                "    [get_ports clk]\n"
                "set_input_delay -max 1.0 -min 0.2 -clock sys_clk [all_inputs]\n"
                "set_output_delay -max 1.0 -min 0.2 -clock sys_clk [all_outputs]\n")
        r = check_sdc(text)
        assert r.stats["Clocks"] == 1
        p = parse_sdc(text)
        assert len(p.clocks) == 1
        assert p.clocks[0].name == "sys_clk"
        assert p.clocks[0].period == pytest.approx(10.0)


# ── F04 / c04 / c20 — multiline set_input_delay keeps -min/-max ─────────────

class TestMultilineInputDelay:
    def test_multiline_keeps_min(self):
        text = ("create_clock -name sys_clk -period 10.0 [get_ports clk]\n"
                "set_input_delay \\\n"
                "    -max 2.0 \\\n"
                "    -min 0.3 \\\n"
                "    -clock sys_clk \\\n"
                "    [get_ports data_in]\n"
                "set_output_delay -max 1.0 -min 0.2 -clock sys_clk [all_outputs]\n")
        r = check_sdc(text)
        assert not [i for i in r.issues if i.code == "SDC-028"], "SDC-028 must not fire (-min present)"
        assert not r.errors

    def test_multiline_converter_delay(self):
        text = ("create_clock -name sys_clk -period 10.0 [get_ports clk]\n"
                "set_input_delay \\\n"
                "    -max 2.0 \\\n"
                "    -min 0.3 -clock sys_clk \\\n"
                "    [get_ports data_in]\n")
        p = parse_sdc(text)
        assert len(p.input_delays) == 1
        assert p.input_delays[0].value == pytest.approx(2.0)
        assert p.input_delays[0].delay_type == "max"


# ── F05 / c06 — scientific notation ──────────────────────────────────────────

class TestSciNotation:
    def test_period_2_5e_1_is_0_25(self):
        text = ("create_clock -name c -period 2.5e-1 [get_ports clk]\n"
                "set_input_delay -max 3.0e-1 -min 1.0e-2 -clock c [all_inputs]\n"
                "set_output_delay -max 1.0e-1 -min 1.0e-2 -clock c [all_outputs]\n")
        p = parse_sdc(text)
        assert p.clocks[0].period == pytest.approx(0.25)
        # 0.3 >= 0.25 → SDC-008 fires; output 0.1 < 0.25 → no SDC-009
        r = check_sdc(text)
        codes = {i.code for i in r.issues}
        assert "SDC-008" in codes
        assert "SDC-009" not in codes


# ── F10 / c22 — SDC-007 data_in ──────────────────────────────────────────────

class TestSdc007DataPorts:
    @pytest.mark.parametrize("port", ["data", "data_in", "data_out", "data0", "data_0",
                                      "addr", "addr_in", "address_bus", "din", "dout",
                                      "input_data"])
    def test_data_ports_flagged(self, port):
        text = f"create_clock -name c -period 5.0 [get_ports {port}]\n"
        r = check_sdc(text)
        assert any(i.code == "SDC-007" for i in r.issues), f"{port} should be flagged"

    @pytest.mark.parametrize("port", ["clk", "clk_core", "rst_n", "scan_en", "test_mode", "clk_sel"])
    def test_control_ports_not_flagged(self, port):
        text = f"create_clock -name c -period 5.0 [get_ports {port}]\n"
        r = check_sdc(text)
        assert not any(i.code == "SDC-007" for i in r.issues), f"{port} should NOT be flagged"


# ── F12 / c21 — flag-first set_clock_uncertainty ─────────────────────────────

class TestUncertaintyFlagFirst:
    def test_flag_first_high_value_detected(self):
        text = ("create_clock -name c -period 5.0 [get_ports clk]\n"
                "set_clock_uncertainty -setup 100.0 -hold 50.0 [get_clocks c]\n")
        r = check_sdc(text)
        codes = {i.code for i in r.issues}
        assert "SDC-023" in codes, codes

    def test_no_duplicate_for_setup_hold_pair(self):
        text = ("create_clock -name c -period 5.0 [get_ports clk]\n"
                "set_clock_uncertainty -setup 100.0 -hold 50.0 [get_clocks c]\n")
        r = check_sdc(text)
        assert len([i for i in r.issues if i.code == "SDC-023"]) == 1

    @pytest.mark.parametrize("stmt", [
        "set_clock_uncertainty 0.1 [get_clocks c]",
        "set_clock_uncertainty -setup 0.1 [get_clocks c]",
        "set_clock_uncertainty -hold 0.05 [get_clocks c]",
        "set_clock_uncertainty -setup 0.1 -hold 0.05 [get_clocks c]",
    ])
    def test_no_false_positive(self, stmt):
        text = f"create_clock -name c -period 5.0 [get_ports clk]\n{stmt}\n"
        r = check_sdc(text)
        assert not [i for i in r.issues if i.code in ("SDC-022", "SDC-023")]


# ── F11 / c15 — braced clock-group lists ─────────────────────────────────────

class TestBracedClockGroups:
    def test_braced_group_list_parsed(self):
        text = ("create_clock -name clk_a -period 5.0 [get_ports clk_a]\n"
                "create_clock -name clk_b -period 7.5 [get_ports clk_b]\n"
                "create_clock -name clk_c -period 3.3 [get_ports clk_c]\n"
                "set_clock_groups -asynchronous "
                "-group [get_clocks {clk_a clk_b}] -group [get_clocks clk_c]\n")
        res = analyze_clock_relations(text)
        # a/b same group; a/c and b/c declared async → only 1 pair genuinely
        # undeclared (the same-group pair a/b).
        assert res.stats["missing"] == 1, res.stats
        # converter agrees on the group membership
        p = parse_sdc(text)
        groups = p.clock_groups[0]["groups"]
        assert ["clk_a", "clk_b"] in groups
        assert ["clk_c"] in groups


# ── generated-clock converter period (c11/c12) ───────────────────────────────

class TestGeneratedPeriodDerivation:
    def test_divide_by_doubles_period(self):
        text = ("create_clock -name clk -period 5.0 [get_ports clk]\n"
                "create_generated_clock -name div2 -master_clock clk "
                "-source [get_ports clk] -divide_by 2 [get_pins U_DIV/clkout]\n")
        p = parse_sdc(text)
        div2 = next(c for c in p.clocks if c.name == "div2")
        assert div2.period == pytest.approx(10.0)

    def test_master_chain(self):
        text = ("create_clock -name clk -period 5.0 [get_ports clk]\n"
                "create_generated_clock -name div2 -master_clock clk "
                "-source [get_ports clk] -divide_by 2 [get_pins U_DIV/clkout]\n"
                "create_generated_clock -name div4 -master_clock div2 "
                "-source [get_pins U_DIV/clkout] -divide_by 2 [get_pins U_DIV2/clkout]\n")
        p = parse_sdc(text)
        by_name = {c.name: c for c in p.clocks}
        assert by_name["div2"].period == pytest.approx(10.0)
        assert by_name["div4"].period == pytest.approx(20.0)

    def test_pin_source_chain_without_master_clock(self):
        text = ("create_clock -name clk -period 5.0 [get_ports clk]\n"
                "create_generated_clock -name div2 -source [get_ports clk] "
                "-divide_by 2 [get_pins U_DIV/clkout]\n"
                "create_generated_clock -name div4 -source [get_pins U_DIV/clkout] "
                "-divide_by 2 [get_pins U_DIV2/clkout]\n")
        p = parse_sdc(text)
        by_name = {c.name: c for c in p.clocks}
        assert by_name["div2"].period == pytest.approx(10.0)
        assert by_name["div4"].period == pytest.approx(20.0)


# ── cross-module consistency (Step 13) ───────────────────────────────────────

CONSISTENCY_SDC = """# comment mentioning create_clock -name ghost -period 1.0
create_clock \\
    -name sys_clk \\
    -period 2.5e-1 \\
    [get_ports clk]
set_input_delay \\
    -max 3.0e-1 \\
    -min 1.0e-2 \\
    -clock sys_clk \\
    [get_ports data_in]
set_clock_groups -asynchronous \\
    -group [get_clocks {clk_a clk_b}] \\
    -group [get_clocks sys_clk]
create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 7.5 [get_ports clk_b]
"""


class TestCrossModuleConsistency:
    def test_all_modules_agree_on_clock_facts(self):
        r = check_sdc(CONSISTENCY_SDC)
        p = parse_sdc(CONSISTENCY_SDC)
        cr = analyze_clock_relations(CONSISTENCY_SDC)

        # No phantom 'ghost' clock anywhere.
        all_names = {c.name for c in p.clocks}
        assert "ghost" not in all_names
        assert "ghost" not in {c.name for c in cr.clocks}

        # sys_clk period is 0.25 everywhere it is derived.
        sys_clk_p = next(c for c in p.clocks if c.name == "sys_clk")
        assert sys_clk_p.period == pytest.approx(0.25)

        # sys_clk is a real clock in checker + clock relations.
        assert r.stats["Clocks"] >= 3
        assert "sys_clk" in {c.name for c in cr.clocks}

        # SDC-008 fires from the sci-notation input delay (0.3 >= 0.25).
        assert any(i.code == "SDC-008" for i in r.issues)

        # Braced group parsed identically by clock_relations and converter.
        assert cr.stats["missing"] == 1  # only sys_clk vs clk_a/clk_b pairs already... verify semantics
        conv_groups = p.clock_groups[0]["groups"]
        assert ["clk_a", "clk_b"] in conv_groups
        assert ["sys_clk"] in conv_groups
