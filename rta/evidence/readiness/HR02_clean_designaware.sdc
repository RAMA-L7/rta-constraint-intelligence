# HR02 — clean single-clock SDC (design-aware readiness)
# Every port in HR02_block.v is constrained or legitimately exempt (clock,
# scan control). Netlist supplied via the runner → design-aware mode.
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_clock_uncertainty -setup 0.15 -hold 0.07 [get_clocks clk_core]
set_propagated_clock [get_clocks clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports {din_a din_b}]
set_input_transition 0.2 [all_inputs]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports {dout_a dout_b}]
set_load 0.05 [get_ports {dout_a dout_b}]
set_case_analysis 0 [get_ports scan_en]
