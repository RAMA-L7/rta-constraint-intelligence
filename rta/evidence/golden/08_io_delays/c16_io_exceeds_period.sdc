# Golden: 6.0 >= 5.0 and 5.5 >= 5.0 → SDC-008 and SDC-009.
create_clock -name clk_core -period 5.0 [get_ports clk]
set_input_delay -max 6.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 5.5 -min 0.2 -clock clk_core [all_outputs]
