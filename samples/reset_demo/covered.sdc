# F2 demo — reset tree 'rst_n' IS covered by a targeted false path → clean
set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports din]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports dout]
# async reset — synchronizer handles deassertion
set_false_path -from [get_ports rst_n] -to [all_registers]
