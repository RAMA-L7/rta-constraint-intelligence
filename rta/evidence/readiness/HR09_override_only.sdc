# HR09 — override-only design. A later set_input_delay silently replaces the
# earlier value (SDC-068, info) — cleanup/review item, NOT a blocker.
# Readiness must be READY_WITH_ADVISORIES (the override may be intentional).
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_input_delay -max 2.5 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
