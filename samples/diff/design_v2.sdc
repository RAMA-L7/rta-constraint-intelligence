# V2: Updated constraints (ECO #42 — timing optimization)

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF

# ── Clock Definitions ─────────────────────────────────

create_clock -name clk -period 4.0 [get_ports clk]

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 0.15 [get_clocks clk]
set_clock_uncertainty -hold 0.08 [get_clocks clk]
set_clock_latency -source 0.5 [get_clocks clk]
set_propagated_clock [get_clocks clk]

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 1.2 -clock clk [get_ports data_in]
set_input_delay -min 0.4 -clock clk [get_ports data_in]
set_output_delay -max 2.0 -clock clk [get_ports data_out]
set_output_delay -min 0.6 -clock clk [get_ports data_out]

# ── False Paths ───────────────────────────────────────

set_false_path -from [get_ports rst_n]
set_false_path -from [get_ports test_mode] -to [get_cells *]

# ── Multicycle Paths ──────────────────────────────────

set_multicycle_path -setup 2 -from [get_cells slow_reg] -to [get_cells fast_reg]

# ── Design Rule Constraints ───────────────────────────

set_max_fanout 16 [all_inputs]
set_max_transition 0.2 [all_nets]
set_max_capacitance 0.1 [all_nets]
