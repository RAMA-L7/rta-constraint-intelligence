# set_case_analysis with an invalid value "banana" — only 0/1/rising/falling allowed.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_case_analysis banana [get_ports scan_en]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
