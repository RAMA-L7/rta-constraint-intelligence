# Golden: -max and -min on the same port+clock are distinct legal constraints.
# Expected: NO SDC-046..049 (and no duplicate/conflict findings).
create_clock -name c -period 10.0 [get_ports clk]
set_input_delay -max 2.0 -clock c [get_ports din]
set_input_delay -min 0.5 -clock c [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
