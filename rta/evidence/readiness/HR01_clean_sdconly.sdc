# HR01 — clean, complete single-clock SDC (SDC-only readiness)
# A realistic handoff-quality constraint set: every rule-clean section present.
set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kOhm -voltage V -current mA -power mW

create_clock -name clk_core -period 10.0 -waveform {0 5} [get_ports clk_core]
set_clock_uncertainty -setup 0.15 -hold 0.07 [get_clocks clk_core]
set_clock_latency -source 0.5 [get_clocks clk_core]
set_clock_transition 0.1 [get_clocks clk_core]
set_propagated_clock [get_clocks clk_core]

set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports {din_a din_b}]
set_input_transition 0.2 [all_inputs]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports {dout_a dout_b}]
set_load 0.05 [get_ports {dout_a dout_b}]

set_max_transition 0.3 [all_outputs]
set_max_capacitance 0.2 [all_outputs]
set_max_fanout 20 [all_outputs]

set_operating_conditions -max SSG
set_timing_derate -early -cell_delay 1.1 -late -cell_delay 0.9
set_case_analysis 0 [get_ports scan_en]
set_ideal_network -no_propagate [get_ports scan_en]
set_dont_use {INVD0 SLOW_X1}
set_clock_gating_check -setup 0.5 -hold 0.2 [get_clocks clk_core]
set_min_pulse_width 0.5 [get_clocks clk_core]
set_clock_jitter 0.02 [get_clocks clk_core]
set_wire_load_mode top
set_max_area 0
set_max_dynamic_power 100
set_max_leakage_power 50
group_path -name g_core -to [get_ports {dout_a dout_b}]
