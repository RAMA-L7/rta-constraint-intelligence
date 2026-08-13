# Clean minimal block - batch check should pass this file.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk]
set_propagated_clock [get_clocks clk]

set_input_delay -max 1.5 -min 0.2 -clock clk [get_ports {din[*] ctl[*]}]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports {dout[*] ack}]
