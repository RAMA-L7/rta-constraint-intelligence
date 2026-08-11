# EDGE CASE: Malformed SDC — various syntax issues
# Expected: SDC-007 (clock on data port), SDC-011 (invalid case analysis),
#           SDC-022 (tight uncertainty), SDC-025 (wildcard dont_touch)
# Clock on a data port name

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── Clock Definitions ─────────────────────────────────

create_clock -name clk_data -period 5.0 [get_ports data_bus_0]
create_clock -name dupe_clk -period 5.0 [get_ports port_a]
create_clock -name dupe_clk -period 10.0 [get_ports port_b]

# ── Generated Clock Definitions ───────────────────────

create_generated_clock -name bad_gen -divide_by 2 [get_pins inst_A]
create_generated_clock -name conflict_gen -source [get_ports clk] \

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 0.001 [get_clocks clk]
set_clock_uncertainty -setup 0.99 [get_clocks clk]

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 2.0 -clock vclk [get_ports data_in]

# ── Multicycle Paths ──────────────────────────────────

set_multicycle_path -setup 3 -from [get_cells inst_A] -to [get_cells inst_B]

# ── Max / Min Delay ───────────────────────────────────

set_max_delay 10.0 -from [get_ports in] -to [get_pins reg/D]

# ── Case Analysis ─────────────────────────────────────

set_case_analysis maybe [get_ports test]

# ── Operating Conditions ──────────────────────────────

set_operating_conditions -max CUSTOM_CORNER_XYZ

# ── Don't-Use / Don't-Touch Cells ─────────────────────

set_dont_touch [all_cells]
