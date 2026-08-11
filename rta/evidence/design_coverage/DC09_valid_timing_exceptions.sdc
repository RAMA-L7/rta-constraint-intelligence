set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]
set_output_delay -max 1.0 -min 0.3 -clock clk [get_ports status]
set_false_path -from [get_ports scan_en] -to [get_ports data_out]
set_multicycle_path -setup 2 -hold 1 -from [get_ports data_in] -to [get_ports data_out]
