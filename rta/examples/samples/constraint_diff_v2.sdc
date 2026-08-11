# ============================================================
# constraint_diff_v2.sdc — Modified constraints (V2)
# NOTE: This file is IDENTICAL to V1 — the differences are in
# the linked TCL variable files (variables_v1.tcl vs variables_v2.tcl)
# ============================================================

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF

# ── Clock Definitions ─────────────────────────────────

create_clock -name clk_core -period 5.0 [get_ports clk]
create_clock -name clk_io   -period 10.0 [get_ports clk_io]

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 0.15 [get_clocks clk_core]
set_clock_uncertainty -hold  0.075 [get_clocks clk_core]

# ── Clock Groups (CDC) ────────────────────────────────

set_clock_groups -asynchronous \ -group [get_clocks clk_core] \

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 1.2 -clock clk_core [remove_from_collection [all_inputs] [get_ports {clk clk_io rst_n}]]
set_input_delay -min 0.4 -clock clk_core [remove_from_collection [all_inputs] [get_ports {clk clk_io rst_n}]]
set_output_delay -max 1.5 -clock clk_core [all_outputs]
set_output_delay -min 0.5 -clock clk_core [all_outputs]
set_driving_cell -lib_cell BUF_X4 -pin Z \
set_load 0.05 [all_outputs]

# ── False Paths ───────────────────────────────────────

set_false_path -through $STATIC_PINS
set_false_path -from [get_ports rst_n]

# ── Multicycle Paths ──────────────────────────────────

set_multicycle_path -setup $CYCLE -through $PWR_PINS -to [get_pins U_RCV_REG/D]
set_multicycle_path -hold [expr {$CYCLE - 1}] -through $PWR_PINS -to [get_pins U_RCV_REG/D]

# ── Design Rule Constraints ───────────────────────────

set_max_fanout     20 [all_inputs]
set_max_transition 0.2 [all_nets]
set_max_capacitance 0.1 [all_nets]

# ── Ideal Networks / Reset ────────────────────────────

set_ideal_network [get_ports rst_n]

# ── Other Constraints ─────────────────────────────────

source variables.tcl
