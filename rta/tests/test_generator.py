"""
Tests for the SDC Generator module.
"""

import pytest
from generator import (
    SDCParams, ClockDef, FalsePath, MultiCyclePath,
    generate_sdc, HalfCyclePath, CaseAnalysisEntry, DisableArc, PathGroup,
)


class TestSDCParams:
    """Tests for the SDCParams dataclass."""

    def test_default_params(self):
        p = SDCParams(design_name="TEST")
        assert p.design_name == "TEST"
        assert p.sdc_version == "2.2"
        assert len(p.clocks) == 1
        assert p.clocks[0].name == "clk_core"
        assert p.clocks[0].period == 5.0

    def test_minimal_params(self):
        p = SDCParams(
            design_name="MINIMAL",
            clocks=[ClockDef(name="clk", port="clk", period=10.0)],
        )
        assert p.design_name == "MINIMAL"
        assert p.clocks[0].period == 10.0


class TestGenerateBasic:
    """Tests for basic SDC generation."""

    def test_generate_empty(self):
        """Should generate something even with minimal params."""
        p = SDCParams(
            design_name="EMPTY",
            clocks=[],
            add_units=False,
            add_ideal_rst=False,
            add_propagated=False,
        )
        sdc = generate_sdc(p)
        assert "EMPTY" in sdc
        assert "sdc_version" in sdc

    def test_generate_with_clock(self):
        p = SDCParams(design_name="MY_CHIP")
        sdc = generate_sdc(p)
        assert "create_clock" in sdc
        assert "clk_core" in sdc
        assert "5.000" in sdc

    def test_generate_with_units(self):
        p = SDCParams(design_name="U", add_units=True)
        sdc = generate_sdc(p)
        assert "set_units" in sdc
        assert "-time ns" in sdc
        assert "-capacitance pF" in sdc

    def test_generate_without_units(self):
        p = SDCParams(design_name="U", add_units=False)
        sdc = generate_sdc(p)
        assert "set_units" not in sdc

    def test_generate_with_derate(self):
        p = SDCParams(
            design_name="D",
            add_derate=True,
            derate_cell_late=0.90,
            derate_cell_early=1.10,
        )
        sdc = generate_sdc(p)
        assert "set_timing_derate" in sdc
        assert "0.9" in sdc  # Python formats 0.90 as 0.9
        assert "1.1" in sdc

    def test_generate_with_ideal_reset(self):
        p = SDCParams(design_name="RST", add_ideal_rst=True, rst_port="rst_n")
        sdc = generate_sdc(p)
        assert "set_ideal_network" in sdc
        assert "rst_n" in sdc

    def test_generate_with_scan(self):
        p = SDCParams(design_name="SCAN", add_scan=True, scan_port="scan_en")
        sdc = generate_sdc(p)
        assert "set_case_analysis" in sdc
        assert "scan_en" in sdc

    def test_generate_with_propagated(self):
        p = SDCParams(design_name="P", add_propagated=True)
        sdc = generate_sdc(p)
        assert "set_propagated_clock" in sdc

    def test_generate_virtual_clock(self):
        p = SDCParams(
            design_name="VIRT",
            clocks=[ClockDef(name="vclk", clk_type="virtual", period=10.0)],
        )
        sdc = generate_sdc(p)
        assert "Virtual clock" in sdc or "virtual" in sdc

    def test_generated_clock_output(self):
        p = SDCParams(
            design_name="GEN",
            clocks=[
                ClockDef(name="clk", clk_type="primary", port="clk_in", period=5.0),
                ClockDef(name="gen_clk", clk_type="generated", port="clk_out",
                         master_port="clk_in", divide_by=2),
            ],
        )
        sdc = generate_sdc(p)
        assert "create_generated_clock" in sdc
        assert "-divide_by 2" in sdc


class TestGenerateIO:
    """Tests for I/O constraint generation."""

    def test_input_delay_generated(self):
        p = SDCParams(
            design_name="IO",
            in_delay_max=2.0,
            in_delay_min=0.5,
        )
        sdc = generate_sdc(p)
        assert "set_input_delay" in sdc
        assert "-max 2.0" in sdc
        assert "-min 0.5" in sdc

    def test_output_delay_generated(self):
        p = SDCParams(
            design_name="IO",
            out_delay_max=2.5,
            out_delay_min=0.8,
        )
        sdc = generate_sdc(p)
        assert "set_output_delay" in sdc
        assert "-max 2.5" in sdc

    def test_driving_cell(self):
        p = SDCParams(
            design_name="DC",
            add_drive_cell=True,
            drive_cell_name="BUF_X8",
        )
        sdc = generate_sdc(p)
        assert "set_driving_cell" in sdc
        assert "BUF_X8" in sdc

    def test_output_load(self):
        p = SDCParams(design_name="LD", add_load=True, load_val=0.1)
        sdc = generate_sdc(p)
        assert "set_load" in sdc


class TestGenerateDesignRules:
    """Tests for design rule constraint generation."""

    def test_max_fanout(self):
        p = SDCParams(design_name="DR", max_fanout=16)
        sdc = generate_sdc(p)
        assert "set_max_fanout" in sdc
        assert "16" in sdc

    def test_max_transition(self):
        p = SDCParams(design_name="DR", max_transition=0.15)
        sdc = generate_sdc(p)
        assert "set_max_transition" in sdc
        assert "0.15" in sdc

    def test_max_capacitance(self):
        p = SDCParams(design_name="DR", max_cap=0.2)
        sdc = generate_sdc(p)
        assert "set_max_capacitance" in sdc
        assert "0.2" in sdc


class TestGenerateExceptions:
    """Tests for timing exception generation."""

    def test_false_paths(self):
        p = SDCParams(
            design_name="FP",
            false_paths=[FalsePath(from_obj="async_in", to_obj="sync_reg")],
        )
        sdc = generate_sdc(p)
        assert "set_false_path" in sdc
        assert "async_in" in sdc

    def test_multicycle_paths(self):
        p = SDCParams(
            design_name="MC",
            mc_paths=[MultiCyclePath(from_cell="ff_a", to_cell="ff_b", cycles=3)],
        )
        sdc = generate_sdc(p)
        assert "set_multicycle_path" in sdc
        assert "-setup 3" in sdc
        assert "-hold" in sdc

    def test_half_cycle_paths(self):
        p = SDCParams(
            design_name="HC",
            half_paths=[HalfCyclePath(clock="clk_core", direction="rise_to_fall")],
        )
        sdc = generate_sdc(p)
        assert "rise_to" in sdc
        assert "multicycle_path" in sdc


class TestGeneratePower:
    """Tests for power constraint generation."""

    def test_power_constraints(self):
        p = SDCParams(
            design_name="PWR",
            add_power=True,
            max_dyn_power=150.0,
            max_leak_power=15.0,
        )
        sdc = generate_sdc(p)
        assert "max_dynamic_power" in sdc
        assert "max_leakage_power" in sdc

    def test_power_not_included_by_default(self):
        p = SDCParams(design_name="NP", add_power=False)
        sdc = generate_sdc(p)
        assert "max_dynamic_power" not in sdc


class TestGenerateMisc:
    """Tests for miscellaneous generation features."""

    def test_wire_load(self):
        p = SDCParams(
            design_name="WL",
            add_wire_load=True,
            wire_load_mode="enclosed",
            wire_load_model="smic18_wl10",
        )
        sdc = generate_sdc(p)
        assert "set_wire_load_mode" in sdc
        assert "smic18_wl10" in sdc

    def test_case_analysis_entries(self):
        p = SDCParams(
            design_name="CA",
            case_entries=[
                CaseAnalysisEntry(target="test_mode", value="0"),
                CaseAnalysisEntry(target="bypass", value="1"),
            ],
        )
        sdc = generate_sdc(p)
        assert "set_case_analysis 0 [get_ports test_mode]" in sdc
        assert "set_case_analysis 1 [get_ports bypass]" in sdc

    def test_dont_use_cells(self):
        p = SDCParams(
            design_name="DU",
            dont_use=["SLOW_*", "WEAK_*"],
        )
        sdc = generate_sdc(p)
        assert "set_dont_use" in sdc
        assert "SLOW" in sdc

    def test_disable_arcs(self):
        p = SDCParams(
            design_name="DA",
            disable_arcs=[
                DisableArc(cell="inst_1", from_pin="A", to_pin="Z"),
            ],
        )
        sdc = generate_sdc(p)
        assert "set_disable_timing" in sdc
        assert "inst_1" in sdc

    def test_date_in_generated_output(self):
        import datetime
        today = datetime.date.today().isoformat()
        p = SDCParams(design_name="DATE")
        sdc = generate_sdc(p)
        assert today in sdc

    def test_clock_uncertainty_generated(self):
        p = SDCParams(design_name="CU")
        sdc = generate_sdc(p)
        assert "set_clock_uncertainty" in sdc
        assert "-setup" in sdc
        assert "-hold" in sdc

    def test_multiple_clock_groups(self):
        p = SDCParams(
            design_name="MCG",
            clocks=[
                ClockDef(name="clk_a", port="clk_a", period=5.0),
                ClockDef(name="clk_b", port="clk_b", period=10.0),
            ],
        )
        sdc = generate_sdc(p)
        assert "set_clock_groups" in sdc
        assert "-asynchronous" in sdc
