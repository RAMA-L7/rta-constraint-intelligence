# Driving cell / input transition / load variants.
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_driving_cell -lib_cell BUF_X4 -input_transition_rise 0.05 [get_ports din[*]]
set_input_transition 0.1 [get_ports din[0]]
set_drive 2 [get_ports din[1]]
set_load -pin_load 0.03 [get_ports dout[*]]
set_load 0.05 [get_nets net_1]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
