# Golden: negative -min delay values are legal in SDC.
create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 1.0 -min -0.25 -clock c [all_inputs]
set_output_delay -max 1.0 -min -0.25 -clock c [all_outputs]
