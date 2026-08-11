# Legitimate false paths (async reset, scan chains) — no SDC-020 warnings.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_false_path -from [get_ports rst_n] -to [get_pins U_FF*/D]
set_false_path -through [get_pins U_SCAN*/scan_en]
set_false_path -from [get_ports test_mode] -to [get_ports dout[*]]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
