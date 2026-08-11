set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]
set_false_path -from [get_ports rst_n] -to [all_registers]
