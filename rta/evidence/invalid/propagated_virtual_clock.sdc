# set_propagated_clock on a VIRTUAL clock is illegal — no physical source exists.
set sdc_version 2.2
create_clock -name vclk_ext -period 10.0
create_clock -name clk_core -period 5.0 [get_ports clk]

set_propagated_clock [get_clocks vclk_ext]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
