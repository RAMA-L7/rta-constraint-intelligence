# Multi-corner SDC template — constraints shared across PVT corners
# Purpose: Test MMC generation and cross-corner checks

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF -resistance kOhm

# ── Clock Definitions ─────────────────────────────────

create_clock -name clk_core -period 5.0 [get_ports clk_core]
create_clock -name clk_io -period 10.0 [get_ports clk_io]
create_generated_clock -name clk_div2 -source [get_ports clk_core] \

# ── Generated Clock Definitions ───────────────────────

create_generated_clock -name clk_div2 -source [get_ports clk_core] \

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 0.15 [get_clocks clk_core]
set_clock_uncertainty -hold 0.08 [get_clocks clk_core]
set_propagated_clock [all_clocks]

# ── Clock Groups (CDC) ────────────────────────────────

set_clock_groups -asynchronous \ -group [get_clocks clk_core] \

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 1.5 -clock clk_core [get_ports data_in*]
set_input_delay -min 0.4 -clock clk_core [get_ports data_in*]
set_output_delay -max 1.8 -clock clk_core [get_ports data_out*]
set_output_delay -min 0.5 -clock clk_core [get_ports data_out*]

# ── Design Rule Constraints ───────────────────────────

set_max_fanout 20 [all_inputs]
set_max_transition 0.2 [all_nets]
set_max_capacitance 0.1 [all_nets]
