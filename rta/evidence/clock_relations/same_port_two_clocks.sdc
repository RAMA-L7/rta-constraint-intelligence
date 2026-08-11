# Two primary clocks on the same port, different periods, NO clock groups.
# Expected: inferred physically_exclusive → SDC-062 info (missing) + SDC-024 warning.
set sdc_version 2.2
create_clock -name clk_1x -period 5.0 [get_ports clk_dual]
create_clock -name clk_2x -period 2.5 [get_ports clk_dual]

set_input_delay -max 1.0 -min 0.2 -clock clk_1x [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_2x [all_outputs]
