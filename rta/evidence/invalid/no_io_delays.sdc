# Clock defined but NO input/output delays — all ports unconstrained.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk_core -period 5.0 [get_ports clk]
set_clock_uncertainty -setup 0.15 [get_clocks clk_core]
