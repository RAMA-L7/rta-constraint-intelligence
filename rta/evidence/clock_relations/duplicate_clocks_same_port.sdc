# Two IDENTICAL primary clocks (same port, same period, different names).
# Expected: physically_exclusive ("duplicates") for the pair → SDC-062 info.
set sdc_version 2.2
create_clock -name clk_a -period 5.0 [get_ports clk_dual]
create_clock -name clk_b -period 5.0 [get_ports clk_dual]

set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
