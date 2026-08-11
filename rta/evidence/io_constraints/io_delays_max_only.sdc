# Only -max delays (no -min) → SDC-028 and SDC-029 warnings (hold unconstrained).
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_input_delay -max 1.2 -clock clk_core [get_ports din[*]]
set_output_delay -max 1.5 -clock clk_core [get_ports dout[*]]
