# No I/O delays - expect SDC-005 (all inputs unconstrained) and
# SDC-006 (all outputs unconstrained) as blockers.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
