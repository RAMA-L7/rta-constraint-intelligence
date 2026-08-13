# Generated-clock chain - the clean reference case for clock relations:
# pll_clk -> /2 -> clk_div2 -> /2 -> clk_div4, with the async group
# declared correctly. Expect no errors.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name pll_clk -period 2.0 [get_ports pll_clk]
create_generated_clock -name clk_div2 \
    -source [get_ports pll_clk] -divide_by 2 \
    [get_pins u_div2/out]
create_generated_clock -name clk_div4 \
    -source [get_pins u_div2/out] -divide_by 2 \
    [get_pins u_div4/out]

set_clock_groups -asynchronous \
    -group [get_clocks pll_clk] \
    -group [get_clocks clk_div4]
