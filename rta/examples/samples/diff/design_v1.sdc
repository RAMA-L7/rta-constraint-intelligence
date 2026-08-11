# V1: Original constraints (RTL freeze)

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF

# ── Clock Definitions ─────────────────────────────────

create_clock -name clk -period 5.0 [get_ports clk]

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 0.20 [get_clocks clk]

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 2.0 -clock clk [get_ports data_in]
set_output_delay -max 2.5 -clock clk [get_ports data_out]

# ── False Paths ───────────────────────────────────────

set_false_path -from [get_ports rst_n]

# ── Design Rule Constraints ───────────────────────────

set_max_fanout 20 [all_inputs]
set_max_transition 0.3 [all_nets]
