# Golden: a full-line comment mentioning a command name must be ignored.
# create_clock -name fake_clk -period 1.0 [get_ports fake_clk]
create_clock -name real_clk -period 10 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock real_clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock real_clk [all_outputs]
