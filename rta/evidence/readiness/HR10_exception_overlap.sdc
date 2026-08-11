# HR10 — false path + multicycle path on overlapping endpoints → SDC-070
# POSSIBLE_CONFLICT (info, STA required) → REVIEW_REQUIRED, never BLOCKED.
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_false_path -from [get_ports a] -to [get_ports b]
set_multicycle_path 2 -from [get_ports a] -to [get_ports b]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
