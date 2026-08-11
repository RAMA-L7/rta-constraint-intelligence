# Minimal but fully valid SDC — golden reference for a single-clock design.
set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kOhm -voltage V -current mA

create_clock -name clk_core -period 5.0 [get_ports clk]

set_clock_latency -source 1.0 [get_clocks clk_core]
set_clock_transition 0.1 [get_clocks clk_core]
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_core]

set_input_delay -max 1.0 -min 0.3 -clock clk_core [all_inputs]
set_output_delay -max 1.5 -min 0.5 -clock clk_core [all_outputs]

set_driving_cell -lib_cell BUF_X4 [all_inputs]
set_load 0.05 [all_outputs]

set_max_fanout 20 [all_inputs]
set_max_transition 0.2 [all_nets]
set_max_capacitance 0.1 [all_outputs]
