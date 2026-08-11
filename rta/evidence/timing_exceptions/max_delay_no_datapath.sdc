# set_max_delay without -datapath_only → SDC-027 warning (hold may be violated).
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_max_delay 2.0 -from [get_pins U_A/Q] -to [get_pins U_B/D]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
