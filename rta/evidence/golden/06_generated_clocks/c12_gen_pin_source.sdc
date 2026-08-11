# Golden: div4's -source pin is div2's output pin → still synchronous chain.
create_clock -name clk -period 5.0 [get_ports clk]
create_generated_clock -name div2 -source [get_ports clk] -divide_by 2 [get_pins U_DIV/clkout]
create_generated_clock -name div4 -source [get_pins U_DIV/clkout] -divide_by 2 [get_pins U_DIV2/clkout]
set_input_delay -max 1.0 -min 0.2 -clock clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk [all_outputs]
