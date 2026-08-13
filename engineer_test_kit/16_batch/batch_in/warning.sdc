# Has review warnings: no propagated clock, no -min on delays, uncertainty
# ratio off - but no hard errors.
set sdc_version 2.2

create_clock -name clk -period 10.0 [get_ports clk]

set_input_delay -max 1.5 -clock clk [get_ports din]
set_output_delay -max 2.0 -clock clk [get_ports dout]
