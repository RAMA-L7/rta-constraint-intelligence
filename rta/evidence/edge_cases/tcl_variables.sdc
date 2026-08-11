# Tcl variable indirection — real designs parameterize constraints this way.
# set_input_delay 6.0 (via $IN_DLY) >= period 5.0 → SDC-008 SHOULD fire after
# variable resolution. The checker does NOT resolve variables (only the
# constraint_diff analyzer resolves linked Tcl files).
set sdc_version 2.2

set CLK_PERIOD 5.0
set IN_DLY 6.0
set OUT_DLY 1.0

create_clock -name clk_core -period $CLK_PERIOD [get_ports clk]

set_input_delay -max $IN_DLY -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max $OUT_DLY -min 0.2 -clock clk_core [all_outputs]
