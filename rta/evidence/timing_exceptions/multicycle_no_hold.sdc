# Multicycle setup 2 WITHOUT -hold → SDC-021 warning.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_multicycle_path -setup 2 -from [get_cells U_REG_A/*] -to [get_cells U_REG_B/*]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
