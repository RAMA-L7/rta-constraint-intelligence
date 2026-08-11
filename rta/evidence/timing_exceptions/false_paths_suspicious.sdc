# False paths on ordinary logic with no async/scan keyword — SDC-020 warns.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_false_path -from [get_pins U_A/Q] -to [get_pins U_B/D]
set_false_path -from [get_ports din[0]] -to [get_pins U_B/D]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
