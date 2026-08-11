# Golden: 2.5e-1 == 0.25 ns period; 3.0e-1 == 0.3 ns input delay >= 0.25 → SDC-008.
create_clock -name c -period 2.5e-1 [get_ports clk]
set_input_delay -max 3.0e-1 -min 1.0e-2 -clock c [all_inputs]
set_output_delay -max 1.0e-1 -min 1.0e-2 -clock c [all_outputs]
