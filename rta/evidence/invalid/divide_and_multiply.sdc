# create_generated_clock with BOTH -divide_by and -multiply_by (mutually exclusive).
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]
create_generated_clock -name clk_bad -source [get_ports clk] -divide_by 2 -multiply_by 3 [get_pins U_DIV/Q]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
