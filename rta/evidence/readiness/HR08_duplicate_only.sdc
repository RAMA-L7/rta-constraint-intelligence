# HR08 — duplicate-only design. One exact duplicate input delay (SDC-067,
# info). Everything else clean. Readiness must be READY_WITH_ADVISORIES —
# a redundant duplicate is cleanup (P3), NOT a blocker.
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_a]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din_a]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
