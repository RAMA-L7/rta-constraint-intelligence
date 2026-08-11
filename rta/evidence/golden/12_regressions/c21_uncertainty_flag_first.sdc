# Golden regression target (currently FAILS): standard flag-first syntax.
# 100.0 ns uncertainty is far above 0.5 ns → SDC-023 expected.
create_clock -name c -period 5.0 [get_ports clk]
set_clock_uncertainty -setup 100.0 -hold 50.0 [get_clocks c]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
