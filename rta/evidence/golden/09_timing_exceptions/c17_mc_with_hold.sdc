# Golden: multicycle -setup 2 with -hold 1 → no SDC-021.
create_clock -name clk_core -period 5.0 [get_ports clk]
set_multicycle_path -setup 2 -hold 1 -from [get_cells U_A/*] -to [get_cells U_B/*]
set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
