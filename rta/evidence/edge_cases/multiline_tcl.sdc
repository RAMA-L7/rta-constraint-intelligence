# Multi-line SDC using backslash continuation (standard Tcl syntax).
set sdc_version 2.2

create_clock -name clk_core -period 5.0 \
    [get_ports clk]

set_clock_uncertainty -setup 0.15 -hold 0.08 \
    [get_clocks clk_core]

set_input_delay -max 1.0 -min 0.2 -clock clk_core \
    [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core \
    [all_outputs]
