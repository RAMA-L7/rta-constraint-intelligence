# Two clocks on the same physical port clk_dual - only one is ever active.
# Marked -asynchronous, but the correct grouping is -physically_exclusive
# (SDC-060). One clock per configuration: 5.0ns or 2.5ns.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk_1x -period 5.0 [get_ports clk_dual]
create_clock -name clk_2x -period 2.5 [get_ports clk_dual] -add

set_clock_groups -asynchronous \
    -group [get_clocks clk_1x] \
    -group [get_clocks clk_2x]
