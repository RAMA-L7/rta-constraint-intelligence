# Tcl is CASE-SENSITIVE — CREATE_CLOCK is NOT a valid command.
# A real Tcl interpreter would reject these lines outright.
SET SDC_VERSION 2.2
CREATE_CLOCK -name clk_core -period 5.0 [get_ports clk]
SET_INPUT_DELAY -max 1.0 -min 0.2 -clock clk_core [all_inputs]
SET_OUTPUT_DELAY -max 1.0 -min 0.2 -clock clk_core [all_outputs]
