# Generated clock chain linked ONLY through -source pins (no -master_clock).
# div4's -source is div2's output pin U_DIV/clkout → must resolve to div2 → clk.
# Expected: all pairs synchronous via source_node/gen_node matching, 0 mismatches.
set sdc_version 2.2
create_clock -name clk -period 5.0 [get_ports clk]
create_generated_clock -name div2 -source [get_ports clk] -divide_by 2 [get_pins U_DIV/clkout]
create_generated_clock -name div4 -source [get_pins U_DIV/clkout] -divide_by 2 [get_pins U_DIV2/clkout]

set_input_delay -max 1.0 -min 0.2 -clock clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk [all_outputs]
