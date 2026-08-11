# Extreme values: 0.05ns period, 100ns uncertainty, huge fanout, tiny transition.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk_fast -period 0.05 [get_ports clk]

set_clock_uncertainty -setup 100.0 -hold 50.0 [get_clocks clk_fast]
set_max_fanout 9999 [all_inputs]
set_max_transition 0.001 [all_nets]
set_max_capacitance 9999.0 [all_outputs]

set_input_delay -max 0.02 -min 0.001 -clock clk_fast [all_inputs]
set_output_delay -max 0.02 -min 0.001 -clock clk_fast [all_outputs]
