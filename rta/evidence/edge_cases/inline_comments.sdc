# Inline trailing comments after every command.
set sdc_version 2.2        # SDC 2.2

create_clock -name clk_core -period 5.0 [get_ports clk] # master clock
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_core]  # jitter margin

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]   # external setup
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs] # external load
