set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
create_generated_clock -name clk_div2 -source [get_ports clk] -divide_by 2 [get_pins u_div/clk_out]
set_input_delay -max 2.0 -min 0.5 -clock clk_div2 [get_ports data_in]
set_output_delay -max 2.0 -min 0.5 -clock clk_div2 [get_ports data_out]
