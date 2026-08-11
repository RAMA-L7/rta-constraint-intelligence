# Commands that exist in EDA tools but are NOT recognized by this checker.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_max_time_borrow 0.5 [all_registers]
set_clock_sense -positive [get_pins U1/A]
set_ideal_latency 1.0 [get_ports clk]
set_auto_disable_detection [get_pins U1/Q]
set_clock_gating_style -sequential_cell latch -setup 0.5

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
