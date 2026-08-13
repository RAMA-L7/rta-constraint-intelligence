# Has hard errors: input delay exceeds the clock period.
set sdc_version 2.2

create_clock -name clk -period 10.0 [get_ports clk]
set_input_delay -max 15.0 -clock clk [get_ports din]
set_output_delay -max 2.0 -clock clk [get_ports dout]
