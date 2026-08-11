# Two clocks with the SAME name "clk_core" — duplicate clock name error.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]
create_clock -name clk_core -period 10.0 [get_ports clk2]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
