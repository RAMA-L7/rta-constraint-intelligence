# Half-cycle path: rise→fall setup without the required -hold 0 → SDC-037.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_multicycle_path -setup 1 -rise_from [get_clocks clk_core] -fall_to [get_clocks clk_core]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
