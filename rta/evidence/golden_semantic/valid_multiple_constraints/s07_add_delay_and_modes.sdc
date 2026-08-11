# Golden: -add_delay accumulation + separate rise/fall are legal.
# Expected: NO SDC-046..049.
create_clock -name c1 -period 10.0 [get_ports clk]
create_clock -name c2 -period 5.0 [get_ports clk2]
set_input_delay -max 2.0 -clock c1 [get_ports din] -add_delay
set_input_delay -max 2.5 -clock c2 [get_ports din] -add_delay
set_input_delay -max 2.0 -rise -clock c1 [get_ports din]
set_input_delay -max 2.5 -fall -clock c1 [get_ports din]
set_output_delay -max 1.0 -min 0.2 -clock c1 [all_outputs]
