# Golden regression target (currently FAILS): comments are documentation only.
# Example usage (documentation — must NOT be parsed):
#   create_clock -name clk_core -period 5.0 [get_ports clk]
#   set_input_delay -max 9.0 -min 0.2 -clock clk_core [all_inputs]
#
# The real constraints below are legal → 0 errors expected.
create_clock -name clk_core -period 5.0 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
