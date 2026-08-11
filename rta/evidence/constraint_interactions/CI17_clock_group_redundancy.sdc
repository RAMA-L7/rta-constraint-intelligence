set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]
set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]
