# I/O delays with edge-specific and add_delay flags (legal SDC 2.x syntax).
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_input_delay -max 1.0 -clock clk_core -clock_fall -add_delay [get_ports din[*]]
set_input_delay -max 0.8 -clock clk_core -rise -add_delay [get_ports din[*]]
set_input_delay -min 0.2 -clock clk_core -fall [get_ports din[*]]

set_output_delay -max 1.5 -clock clk_core -clock_fall -add_delay [get_ports dout[*]]
set_output_delay -min 0.4 -clock clk_core -rise [get_ports dout[*]]
