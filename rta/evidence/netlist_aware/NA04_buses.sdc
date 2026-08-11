set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in[3]]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in[*]]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports addr_out[9]]
set_false_path -from [get_ports data_in[9]] -to [get_ports data_out]
