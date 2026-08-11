# 6 set_disable_timing commands, NONE with -from/-to → SDC-035 + 6× SDC-036.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_disable_timing [get_cells U1]
set_disable_timing [get_cells U2]
set_disable_timing [get_cells U3]
set_disable_timing [get_cells U4]
set_disable_timing [get_cells U5]
set_disable_timing [get_cells U6]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
