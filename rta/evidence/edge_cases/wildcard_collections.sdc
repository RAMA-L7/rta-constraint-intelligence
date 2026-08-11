# Broad wildcards and collection commands — common but risky patterns.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]

set_false_path -from [get_ports rst*] -to [get_pins *async*]
set_max_delay 2.0 -from [get_pins U_A/Q] -to [get_pins U_B/*]
set_dont_touch [get_cells *]
set_load 0.05 [get_ports dout*]
