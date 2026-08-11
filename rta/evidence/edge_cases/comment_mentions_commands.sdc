# This file is VALID. The comments deliberately mention command names.
# NOTE: do not confuse comments with real commands.
#
# Example usage:
#   create_clock -name clk_core -period 5.0 [get_ports clk]
#   set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]
#   set_input_delay -max 9.0 -min 0.2 -clock clk_core [all_inputs]
#
# (The values above are documentation only — the real constraints below are legal.)

set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
