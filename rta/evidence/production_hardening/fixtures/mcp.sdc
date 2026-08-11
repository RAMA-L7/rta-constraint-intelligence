# Phase 13 PH13 fixture: set_max_delay < set_min_delay on identical endpoints
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
set_max_delay 4.0 -from [get_ports din] -to [get_ports dout]
set_min_delay 6.0 -from [get_ports din] -to [get_ports dout]
