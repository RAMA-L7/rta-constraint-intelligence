# create_generated_clock WITHOUT the required -source.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]
create_generated_clock -name clk_div2 -divide_by 2 [get_pins U_DIV/Q]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
