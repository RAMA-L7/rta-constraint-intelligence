# Golden: '10' and '10.0' must both parse as period 10.0.
create_clock -name c_int -period 10 [get_ports clk_int]
create_clock -name c_f -period 10.0 [get_ports clk_f]
set_input_delay -max 1.0 -min 0.2 -clock c_int [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c_int [all_outputs]
