# Scientific notation values (legal in Tcl/SDC):
#   -period 2.5e-1  == 0.25 ns
#   set_input_delay 3.0e-1 == 0.3 ns  → 0.3 >= 0.25 period → SDC-008 SHOULD fire
# Tool regexes typically match only [\d.]+ so "2.5e-1" may be mis-read as 2.5.
set sdc_version 2.2
create_clock -name clk_fast -period 2.5e-1 [get_ports clk]

set_input_delay -max 3.0e-1 -min 1.0e-2 -clock clk_fast [all_inputs]
set_output_delay -max 1.0e-1 -min 1.0e-2 -clock clk_fast [all_outputs]
