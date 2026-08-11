# Golden: set_input_delay references a clock that is never defined.
# Expected: SDC-046 (undefined clock ref), and NO SDC-008 fallback to clk_a.
create_clock -name clk_a -period 10.0 [get_ports clk]
set_input_delay -max 12.0 -min 0.5 -clock nonexistent_clk [get_ports data_in]
set_output_delay -max 1.0 -min 0.2 -clock clk_a [all_outputs]
