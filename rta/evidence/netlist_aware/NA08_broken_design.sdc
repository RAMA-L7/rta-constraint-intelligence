set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports nonexistent_clk]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]
set_false_path -from [get_pins u_core/u_bad_reg/D] -to [get_ports data_out]
set_case_analysis 1 [get_ports stray_*]
