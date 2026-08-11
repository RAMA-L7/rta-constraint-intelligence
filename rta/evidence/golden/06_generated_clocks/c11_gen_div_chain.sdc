# Golden: clk → div2 → div4 via -master_clock; 3 clocks, 3 pairs, all synchronous.
create_clock -name clk -period 5.0 [get_ports clk]
create_generated_clock -name div2 -master_clock clk -source [get_ports clk] -divide_by 2 [get_pins U_DIV/clkout]
create_generated_clock -name div4 -master_clock div2 -source [get_pins U_DIV/clkout] -divide_by 2 [get_pins U_DIV2/clkout]
set_input_delay -max 1.0 -min 0.2 -clock clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk [all_outputs]
