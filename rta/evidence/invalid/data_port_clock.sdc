# create_clock on a port that looks like DATA (data_in) instead of a clock port.
set sdc_version 2.2
create_clock -name clk_bad -period 5.0 [get_ports data_in]

set_input_delay -max 1.0 -min 0.2 -clock clk_bad [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_bad [all_outputs]
