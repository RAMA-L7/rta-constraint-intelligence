# HR05 — partial bus coverage (design-aware)
# data_in is an 8-bit bus; only data_in[3:0] is constrained → SDC-066
# PARTIALLY_CONSTRAINED → REVIEW_REQUIRED (4/8 bus bits lack timing intent).
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports {data_in[3:0]}]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports {data_out}]
