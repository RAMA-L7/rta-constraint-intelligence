set sdc_version 2.2
create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 8.0 [get_ports clk_b]
set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]
set_input_delay -max 2.0 -min 0.5 -clock clk_a [get_ports data_in]
set_output_delay -max 2.0 -min 0.5 -clock clk_a [get_ports data_out_a]
set_output_delay -max 2.0 -min 0.5 -clock clk_b [get_ports data_out_b]
