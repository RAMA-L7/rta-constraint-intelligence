# Exact boundary values:
#   - uncertainty 0.05 → NO SDC-022 (only < 0.05 warns)
#   - uncertainty 0.50 → NO SDC-023 (only > 0.5 warns)
#   - input delay 5.0 == period 5.0 → SDC-008 SHOULD fire (>=)
#   - max_transition 0.05 → NO SDC-026 (only < 0.05 warns)
set sdc_version 2.2
create_clock -name clk_core -period 5.0 [get_ports clk]

set_clock_uncertainty -setup 0.05 -hold 0.025 [get_clocks clk_core]
set_clock_uncertainty -setup 0.50 -hold 0.25 [get_clocks clk_core]
set_max_transition 0.05 [all_nets]

set_input_delay -max 5.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
