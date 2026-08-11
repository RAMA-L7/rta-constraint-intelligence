# HR12 — otherwise-good SDC analyzed WITHOUT a netlist (SDC-only mode).
# Object references (get_ports/get_pins/all_*) cannot be verified → limited
# design verification, but this must NOT BLOCK readiness: SDC-only readiness
# is honest, not punished for omitting the optional netlist.
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_clock_uncertainty -setup 0.15 -hold 0.07 [get_clocks clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports {din_a din_b}]
set_input_transition 0.2 [all_inputs]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports {dout_a dout_b}]
set_load 0.05 [get_ports {dout_a dout_b}]
set_case_analysis 0 [get_ports scan_en]
