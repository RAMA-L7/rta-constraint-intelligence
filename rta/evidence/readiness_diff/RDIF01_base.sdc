set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
