set sdc_version 2.2
set PERIOD 10.0
create_clock -name clk_core -period $PERIOD [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 11.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
