# Golden: create_generated_clock -master_clock names an undefined clock.
# Expected: SDC-047.
create_clock -name clk_a -period 10.0 [get_ports clk]
create_generated_clock -name div2 -master_clock ghost_clk -source [get_ports clk] -divide_by 2 [get_pins U/CLK]
set_input_delay -max 1.0 -min 0.2 -clock clk_a [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
