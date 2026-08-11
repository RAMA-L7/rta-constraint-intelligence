set sdc_version 2.2
create_clock -name clk_core -period 1.0e1 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 1.1e1 -min 5.0e-1 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
