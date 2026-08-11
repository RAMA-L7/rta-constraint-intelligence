set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports data_in]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports data_out]
set_false_path -from [get_pins u_core/u_reg0/D] -to [get_pins u_io/u_out0/DOUT]
set_multicycle_path 2 -from [get_cells u_core/u_reg0] -to [get_cells u_core/u_reg9]
