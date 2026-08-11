# SDC with I/O constraints but NO clock — synthesis has no timing reference.
set sdc_version 2.2
set_units -time ns -capacitance pF

set_input_delay -max 1.0 -min 0.2 -clock vclk [get_ports din[*]]
set_output_delay -max 1.0 -min 0.2 -clock vclk [get_ports dout[*]]
