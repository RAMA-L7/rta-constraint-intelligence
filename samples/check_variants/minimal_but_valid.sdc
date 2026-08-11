# VARIANT B: Minimal but fully valid SDC
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 5.0 [get_ports clk]
set_clock_uncertainty -setup 0.2 [get_clocks clk]
set_propagated_clock [all_clocks]

set_input_delay -max 2.0 -clock clk [all_inputs]
set_output_delay -max 2.5 -clock clk [all_outputs]

set_false_path -from [get_ports rst_n]
set_max_fanout 20 [all_inputs]
set_max_transition 0.2 [all_nets]
set_operating_conditions -max WORST
