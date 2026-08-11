set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
create_generated_clock -name clk_div2 -source [get_ports clk] -divide_by 2 [get_ports clk_div2]
create_generated_clock -name bad_gen -source [get_ports pll_out] -divide_by 2 [get_ports clk_div2] -add
