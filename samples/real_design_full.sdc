# =============================================================================
# SDC Constraints for RV32IM_CORE — 32-bit RISC-V Processor
# Design: rv32im_core  |  Tech: 28nm CMOS  |  Target: 500MHz (2.0ns)
# =============================================================================

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF -resistance kOhm -voltage V

# ── Clock Definitions ─────────────────────────────────

create_clock -name clk_core -period 2.0 [get_ports clk_core]
create_clock -name clk_axi  -period 5.0 [get_ports clk_axi]
create_clock -name clk_mem  -period 3.3 [get_ports clk_mem]
create_clock -name vclk_core -period 2.0 -virtual
create_clock -name vclk_axi  -period 5.0 -virtual

# ── Generated Clock Definitions ───────────────────────

create_generated_clock -name clk_core_div2 -source [get_ports clk_core]
create_generated_clock -name clk_core_div4 -source [get_ports clk_core]

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 0.15 [get_clocks clk_core]
set_clock_uncertainty -hold  0.08 [get_clocks clk_core]
set_clock_uncertainty -setup 0.25 [get_clocks clk_axi]
set_clock_uncertainty -hold  0.12 [get_clocks clk_axi]
set_clock_latency -source 0.40 [get_clocks clk_core]
set_clock_latency -source 0.60 [get_clocks clk_axi]
set_clock_transition 0.10 [all_clocks]
set_propagated_clock [get_clocks {clk_core clk_axi clk_mem}]

# ── Clock Groups (CDC) ────────────────────────────────

set_clock_groups -asynchronous  -group [get_clocks {clk_core clk_core_div2 clk_core_div4}]
set_clock_groups -asynchronous  -group [get_clocks clk_core]

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 0.80 -clock vclk_core [get_ports {inst_addr* inst_data*}]
set_input_delay -min 0.15 -clock vclk_core [get_ports {inst_addr* inst_data*}]
set_output_delay -max 0.90 -clock vclk_core [get_ports {result* status*}]
set_output_delay -min 0.20 -clock vclk_core [get_ports {result* status*}]
set_input_delay -max 1.50 -clock vclk_axi [get_ports {axi_aw* axi_w* axi_ar*}]
set_input_delay -min 0.30 -clock vclk_axi [get_ports {axi_aw* axi_w* axi_ar*}]
set_output_delay -max 1.80 -clock vclk_axi [get_ports {axi_b* axi_r*}]
set_output_delay -min 0.40 -clock vclk_axi [get_ports {axi_b* axi_r*}]
set_driving_cell -lib_cell BUF_X4 -pin Z [remove_from_collection [all_inputs] [all_outputs]]
set_load 0.05 [all_outputs]

# ── False Paths ───────────────────────────────────────

set_false_path -from [get_ports rst_n]
set_false_path -from [get_ports test_mode]
set_false_path -from [get_clocks clk_core] -to [get_clocks clk_axi]
set_false_path -from [get_clocks clk_axi] -to [get_clocks clk_core]
set_false_path -through [get_pins *bist*]

# ── Multicycle Paths ──────────────────────────────────

set_multicycle_path -setup 3 -from [get_cells *mult*] -to [get_cells *acc*]
set_multicycle_path -hold  2 -from [get_cells *mult*] -to [get_cells *acc*]
set_multicycle_path -setup 4 -from [get_cells *div*] -to [get_cells *reg*]
set_multicycle_path -hold  3 -from [get_cells *div*] -to [get_cells *reg*]

# ── Max / Min Delay ───────────────────────────────────

set_max_delay 8.0 -from [get_ports data_in*] -to [get_cells capture_reg*]

# ── Case Analysis ─────────────────────────────────────

set_case_analysis 0 [get_ports test_mode]   # Functional mode
set_case_analysis 0 [get_ports scan_en]     # Not scan mode
set_case_analysis rising [get_ports clk_sel] # Core clock selected

# ── Disable Timing Arcs ───────────────────────────────

set_disable_timing -from A -to Z [get_cells *hold_buf*]

# ── Design Rule Constraints ───────────────────────────

set_max_fanout      16 [all_inputs]
set_max_transition  0.20 [all_nets]
set_max_capacitance 0.08 [all_nets]
set_max_area        50000

# ── Operating Conditions ──────────────────────────────

set_operating_conditions -max TT_0p9V_25C

# ── Timing Derate (AOCV) ──────────────────────────────

set_timing_derate -late  -cell_delay 0.92 [all_nets]
set_timing_derate -early -cell_delay 1.08 [all_nets]
set_timing_derate -late  -net_delay  0.95 [all_nets]
set_timing_derate -early -net_delay  1.05 [all_nets]

# ── Power Constraints ─────────────────────────────────

set_max_dynamic_power 100 mW
set_max_leakage_power  10 mW

# ── Don't-Use / Don't-Touch Cells ─────────────────────

set_dont_use [get_lib_cells */SLOW_*]
set_dont_use [get_lib_cells */WEAK_*]
