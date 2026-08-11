# HR07 — set_max_delay 5 < set_min_delay 8 on provably identical endpoints
# → SDC-069 DEFINITE_CONFLICT → BLOCKED (impossible timing window).
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_max_delay 5 -from [get_ports a] -to [get_ports b]
set_min_delay 8 -from [get_ports a] -to [get_ports b]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
