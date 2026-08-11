# Truncated / half-finished commands.
set sdc_version 2.2
create_clock -name clk_core
set_clock_uncertainty -setup
set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay
