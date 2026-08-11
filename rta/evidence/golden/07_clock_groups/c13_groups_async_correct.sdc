# Golden: async pair declared -asynchronous → 0 mismatches, 0 missing.
create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 7.5 [get_ports clk_b]
set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]
set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_b [all_outputs]
