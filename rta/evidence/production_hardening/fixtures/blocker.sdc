# Phase 13 PH13 fixture: clean block + undefined clock reference (SDC-046 blocker)
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]
