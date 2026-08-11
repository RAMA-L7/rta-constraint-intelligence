"""
Shared test fixtures for the SDC Tools test suite.
"""

import pytest


# ── Sample SDC texts ────────────────────────────────────────────────────────────

@pytest.fixture
def empty_sdc():
    """An empty SDC file (no constraints)."""
    return ""


@pytest.fixture
def minimal_sdc():
    """A minimal valid SDC with one clock and no other constraints."""
    return """set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 5.0 [get_ports clk]
"""


@pytest.fixture
def full_sdc():
    """A complete SDC with clocks, I/O, exceptions, design rules, derate, and power."""
    return """set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kOhm

# ── Clocks ──
create_clock -name clk_core -period 5.0 [get_ports clk_core]
create_clock -name clk_slow -period 20.0 [get_ports clk_slow]
create_generated_clock -name gen_clk -source [get_ports clk_core] -divide_by 2 [get_pins gen_clk_pin]
create_clock -name vclk -period 10.0 -virtual
set_clock_uncertainty -setup 0.15 [get_clocks clk_core]
set_clock_uncertainty -hold 0.08 [get_clocks clk_core]
set_clock_latency -source 0.5 [get_clocks clk_core]
set_clock_transition 0.1 [all_clocks]
set_propagated_clock [all_clocks]
set_clock_groups -asynchronous -group [get_clocks clk_core] -group [get_clocks clk_slow]
set_clock_jitter -clock [get_clocks clk_core] -cycle 0.05
set_clock_gating_check -setup 0.2 -hold 0.1

# ── I/O ──
set_input_delay -max 1.5 -clock clk_core [get_ports data_in]
set_input_delay -min 0.4 -clock clk_core [get_ports data_in]
set_output_delay -max 1.8 -clock clk_core [get_ports data_out]
set_output_delay -min 0.5 -clock clk_core [get_ports data_out]
set_driving_cell -lib_cell BUF_X4 -pin Z [all_inputs]
set_load 0.05 [all_outputs]

# ── Exceptions ──
set_false_path -from [get_ports rst_n]
set_false_path -from [get_cells async_reg] -to [get_cells sync_reg]
set_multicycle_path -setup 2 -from [get_cells slow_ff] -to [get_cells capture_ff]
set_max_delay 10.0 -from [get_ports data_in] -to [get_cells capture_reg]
set_min_delay 1.0 -from [get_cells launch_reg] -to [get_pins capture_reg/D]
group_path -name input2reg -from [get_ports data_in]

# ── Design rules ──
set_max_fanout 20 [all_inputs]
set_max_transition 0.2 [all_nets]
set_max_capacitance 0.1 [all_nets]
set_max_area 50000

# ── Operating conditions ──
set_operating_conditions -max WORST

# ── Derate (AOCV) ──
set_timing_derate -late -cell_delay 0.92 [all_nets]
set_timing_derate -early -cell_delay 1.08 [all_nets]

# ── DFT / Power ──
set_case_analysis 0 [get_ports scan_en]
set_ideal_network [get_ports rst_n]
set_dont_use [get_lib_cells */SLOW_*
set_max_dynamic_power 100 mW
set_max_leakage_power 10 uW
set_min_pulse_width -low 0.3 [all_clocks]
"""


@pytest.fixture
def buggy_sdc():
    """SDC with many issues to trigger checker warnings and errors."""
    return """set_input_delay -max 1.5 -clock ref_clk [get_ports data_in]
set_input_delay -max 1.5 -clock ref_clk [get_ports data_in]
set_output_delay 1.8 -clock ref_clk [get_ports data_out]

# Duplicate clock name
create_clock -name dupe -period 5.0 [get_ports port_a]
create_clock -name dupe -period 10.0 [get_ports port_b]

# Generated clock without -source
create_generated_clock -name bad_gen -divide_by 2 [get_pins gen/A]

# Data port as clock
create_clock -name data_clk -period 4.0 [get_ports data_bus]

# Clock on same port?
set_clock_uncertainty 0.01 [get_clocks ref_clk]
set_clock_uncertainty 0.6 [get_clocks clk_b]

# No set_propagated_clock
# No set_clock_groups — multiple clocks
create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 10.0 [get_ports clk_b]
"""


@pytest.fixture
def tcl_params():
    """Simple TCL parameter file content."""
    return """set CYCLE 10.0
set PERIOD_NS 5.0
set CLK_PORT clk_in
set RST_PORT rst_n
set DATA_PINS {data_a data_b data_c}
set STATIC_PINS [get_pins *static_inst*]
set NUM_CYCLES 3
# Comment line
"""


@pytest.fixture
def tcl_with_nested_refs():
    """TCL with variables referencing other variables."""
    return """set BASE_PERIOD 5.0
set FAST_CLOCK $BASE_PERIOD
set SLOW_CLOCK [expr {$BASE_PERIOD * 4}]
set DESIGN_NAME "my_chip"
set CLK_PORT ${DESIGN_NAME}/clk
set MULTIPLIER 2
set OUTPUT_PERIOD [expr {$FAST_CLOCK / $MULTIPLIER}]
"""


@pytest.fixture
def sample_sdc_path(tmp_path):
    """Create a temporary SDC file and return its path."""
    path = tmp_path / "test.sdc"
    path.write_text("""set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
set_input_delay -max 1.5 -clock clk [get_ports data_in]
""", encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_tcl_path(tmp_path):
    """Create a temporary TCL file and return its path."""
    path = tmp_path / "params.tcl"
    path.write_text("set CYCLE 5.0\nset CLK_PORT sys_clk\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def yaml_rules_path(tmp_path):
    """Create a temporary YAML custom rules file and return its path."""
    path = tmp_path / "my_rules.yaml"
    path.write_text("""name: Test Rules
version: "1.0"
description: Test rules for unit tests
rules:
  - id: TST-001
    name: "Clock period ≤ 10ns"
    severity: warning
    command: create_clock
    condition: value_above
    field: period
    threshold: 10.0
    message: "Clock period {value}ns exceeds 10ns"

  - id: TST-002
    name: "Require propagated clock"
    severity: error
    command: set_propagated_clock
    condition: present
    message: "No set_propagated_clock"
""", encoding="utf-8")
    return str(path)
