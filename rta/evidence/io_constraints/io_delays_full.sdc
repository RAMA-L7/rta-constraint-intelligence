# Complete I/O delays with both -max and -min → no SDC-028/029 warnings.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_input_delay -max 1.2 -min 0.3 -clock clk_core [get_ports din[*]]
set_output_delay -max 1.5 -min 0.4 -clock clk_core [get_ports dout[*]]
