# Golden: '{clk_a clk_b}' is a braced Tcl list = 2 clocks in one group.
# clk_a & clk_b are both async to clk_c → those 2 pairs must NOT be reported missing.
create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 7.5 [get_ports clk_b]
create_clock -name clk_c -period 3.3 [get_ports clk_c]
set_clock_groups -asynchronous -group [get_clocks {clk_a clk_b}] -group [get_clocks clk_c]
set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_c [all_outputs]
