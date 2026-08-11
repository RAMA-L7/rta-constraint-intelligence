# Three clocks:
#   clk_a, clk_b on the SAME port → physically_exclusive
#   clk_c on a different port → asynchronous vs both
# All declared correctly → 0 mismatches expected.
set sdc_version 2.2
create_clock -name clk_a -period 5.0 [get_ports clk_ab]
create_clock -name clk_b -period 10.0 [get_ports clk_ab]
create_clock -name clk_c -period 3.3 [get_ports clk_c]

set_clock_groups -physically_exclusive -group [get_clocks clk_a] -group [get_clocks clk_b]
set_clock_groups -asynchronous -group [get_clocks {clk_a clk_b}] -group [get_clocks clk_c]

set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_c [all_outputs]
