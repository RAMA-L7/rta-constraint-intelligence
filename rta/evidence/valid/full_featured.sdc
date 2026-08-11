# ── Production-style SDC: 28nm SoC block ─────────────────────────────────────
set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kOhm -voltage V -current mA

# ── Clocks ───────────────────────────────────────────────────────────────────
create_clock -name clk_sys -period 5.0 [get_ports clk]
create_clock -name clk_io  -period 10.0 [get_ports clk_io]
create_generated_clock -name clk_sys_div2 -source [get_ports clk] -divide_by 2 [get_pins U_PLL/clkout2]
create_generated_clock -name clk_sys_div4 -master_clock clk_sys_div2 -source [get_pins U_PLL/clkout2] -divide_by 2 [get_pins U_CLKDIV/clkout]

set_clock_latency -source 1.2 [get_clocks clk_sys]
set_clock_transition 0.1 [get_clocks clk_sys]
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_sys]
set_clock_jitter -cycle 0.05 [get_clocks clk_sys]
set_propagated_clock [get_clocks clk_sys]

# ── Clock groups ─────────────────────────────────────────────────────────────
set_clock_groups -asynchronous \
    -group [get_clocks {clk_sys clk_sys_div2 clk_sys_div4}] \
    -group [get_clocks clk_io]

# ── I/O ──────────────────────────────────────────────────────────────────────
set_input_delay  -max 1.2 -min 0.4 -clock clk_sys [get_ports {din[*] ctrl[*]}]
set_output_delay -max 1.5 -min 0.5 -clock clk_sys [get_ports {dout[*] status[*]}]
set_driving_cell -lib_cell BUF_X4 [get_ports din[*]]
set_load 0.05 [get_ports dout[*]]

# ── Timing exceptions ────────────────────────────────────────────────────────
set_false_path -from [get_ports rst_n] -to [get_pins U_RST*/async]
set_false_path -through [get_pins U_SCAN*/scan_en] -through [get_pins U_SCAN*/Q]
set_multicycle_path -setup 2 -hold 1 -from [get_cells U_REG_A/*] -to [get_cells U_REG_B/*]
set_max_delay 2.0 -datapath_only -from [get_pins U_A/Q] -to [get_pins U_B/D]
set_min_delay 0.5 -from [get_pins U_A/Q] -to [get_pins U_B/D]

# ── Case analysis / DFT ──────────────────────────────────────────────────────
set_case_analysis 0 [get_ports scan_en]
set_ideal_network [get_ports rst_n]
set_disable_timing -from S0 -to Z [get_cells U_MUX]

# ── Design rules ─────────────────────────────────────────────────────────────
set_max_fanout 20 [all_inputs]
set_max_transition 0.2 [all_nets]
set_max_capacitance 0.1 [all_outputs]

# ── Operating conditions / derate (AOCV) ─────────────────────────────────────
set_operating_conditions WORST
set_timing_derate -early -cell_delay 1.08 [all_cells]
set_timing_derate -late  -cell_delay 0.92 [all_cells]
set_timing_derate -early -net_delay  1.05 [all_nets]
set_timing_derate -late  -net_delay  0.95 [all_nets]

# ── Wire load / power ────────────────────────────────────────────────────────
set_wire_load_mode enclosed
set_wire_load_model -name typical -library tsmc28
set_max_dynamic_power 100.0 [all_designs]
set_max_leakage_power 10.0 [all_designs]
set_min_pulse_width -high 0.5 [get_clocks clk_sys]
set_dont_use [get_lib_cells {CLKBUF_X1 INVD0 BUFD1}]
