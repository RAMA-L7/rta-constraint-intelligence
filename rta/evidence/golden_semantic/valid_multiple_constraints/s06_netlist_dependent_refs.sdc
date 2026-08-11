# Golden: get_ports/get_pins/all_clocks/wildcards are netlist-dependent.
# Expected: NO SDC-046..048.
create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock [get_ports clk] [all_inputs]
set_clock_groups -asynchronous -group [get_clocks c] -group [get_clocks *]
create_generated_clock -name g -master_clock [get_clocks c] -source [get_pins U/A] -divide_by 2 [get_pins U/B]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
