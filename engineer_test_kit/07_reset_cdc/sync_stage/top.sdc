# F2 demo, reset tree 'rst_n' has NO timing exception, so SDC-151 fires
set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
set_input_delay -max 2.0 -min 0.5 -clock clk [get_ports din]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports dout]
