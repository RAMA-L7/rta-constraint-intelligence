# Two create_clock with the same name on the same port - expect a
# duplicate-clock-name finding.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_clock -name clk -period 5.0 [get_ports clk] -add
