# Conflicting exceptions on the SAME path:
#   set_false_path  vs  set_max_delay  (mutually contradictory)
#   set_clock_groups async AND physically_exclusive for the same pair
set sdc_version 2.2
create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 7.5 [get_ports clk_b]

set_false_path -from [get_pins U_A/Q] -to [get_pins U_B/D]
set_max_delay 1.0 -from [get_pins U_A/Q] -to [get_pins U_B/D]

set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]
set_clock_groups -physically_exclusive -group [get_clocks clk_a] -group [get_clocks clk_b]

set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_b [all_outputs]
