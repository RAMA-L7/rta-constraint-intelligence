# Golden: after Tcl preprocessing $CLK_PERIOD → 2.5, $IN_DLY → 6.0.
# 6.0 >= 2.5 → SDC-008 is the CORRECT result after resolution.
set CLK_PERIOD 2.5
set IN_DLY 6.0
create_clock -name core_clk -period $CLK_PERIOD [get_ports clk]
set_input_delay -max $IN_DLY -min 0.2 -clock core_clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock core_clk [all_outputs]
