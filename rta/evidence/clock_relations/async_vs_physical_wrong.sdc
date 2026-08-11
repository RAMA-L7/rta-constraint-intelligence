# Two PRIMARY clocks on the SAME port clk_dual, different periods.
# They are physically exclusive (only one active at a time), but the SDC
# declares them -asynchronous → SDC-060 MISMATCH expected.
set sdc_version 2.2
create_clock -name clk_1x -period 5.0 [get_ports clk_dual]
create_clock -name clk_2x -period 2.5 [get_ports clk_dual]

set_clock_groups -asynchronous -group [get_clocks clk_1x] -group [get_clocks clk_2x]

set_input_delay -max 1.0 -min 0.2 -clock clk_1x [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_2x [all_outputs]
