# Golden: set_clock_groups references a clock that is not defined.
# Expected: SDC-048 (for ghost2); defined clk_a NOT flagged.
create_clock -name clk_a -period 10.0 [get_ports clk]
set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks ghost2]
set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
