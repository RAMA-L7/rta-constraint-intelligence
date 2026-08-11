# SDC with warnings — clock groups, derate, uncertainty issues
# Purpose: Test checker catches SDC-024, SDC-028, SDC-030, SDC-045

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF

# ── Clock Definitions ─────────────────────────────────

create_clock -name clk_fast -period 2.0 [get_ports clk_fast]
create_clock -name clk_slow -period 20.0 [get_ports clk_slow]

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 0.01 [get_clocks clk_fast]

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 2.0 -clock clk_fast [get_ports data_in]
set_output_delay -max 2.5 -clock clk_fast [get_ports data_out]

# ── Max / Min Delay ───────────────────────────────────

set_max_delay 8.0 -from [get_ports a] -to [get_cells b]

# ── Timing Derate (AOCV) ──────────────────────────────

set_timing_derate -early -cell_delay 0.95 [all_nets]
