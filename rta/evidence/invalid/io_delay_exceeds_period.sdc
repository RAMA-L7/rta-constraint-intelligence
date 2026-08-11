# set_input_delay 6.0 >= period 5.0 → no margin; same for output delay 5.5.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_input_delay -max 6.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 5.5 -min 0.2 -clock clk_core [all_outputs]
