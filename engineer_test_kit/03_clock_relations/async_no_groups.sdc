# Two independent clock domains with NO set_clock_groups - the tool will
# analyze all cross-clock paths as synchronous, missing real CDC issues.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk_a -period 5.0 [get_ports clk_a]
create_clock -name clk_b -period 3.0 [get_ports clk_b]
